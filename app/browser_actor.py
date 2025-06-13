from playwright.sync_api import sync_playwright, Browser, Page, Playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus # Added quote_plus for URL encoding keywords
from .logger import log
# from .authenticator import get_2fa_code # Not directly used by BrowserActor after previous refactors
from .security import decrypt # Ensure this is imported if perform_multi_step_authentication is kept for Amazon
import time
# import logging # Replaced by log

class BrowserActor:
    """Manages all browser interactions using Playwright."""

    def __init__(self, config: dict, master_password: str = None):
        self.config = config
        self.master_password = master_password
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self.context = None
        self.session_active = False

    def start_session(self) -> bool:
        """Start browser session with proper popup handling."""
        try:
            log.info("Starting browser session...")
            
            self.playwright = sync_playwright().start()
            
            # Launch browser
            browser = self.playwright.chromium.launch(
                headless=self.config.get('headless', False)
            )
            
            # Create context with location permission denied (prevents location dialog)
            self.context = browser.new_context(
                permissions=[],  # No permissions granted
                geolocation=None,  # No location access
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.page = self.context.new_page()
            self.browser = browser
            
            log.info("Browser session started successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to start browser session: {e}")
            return False

    def handle_popups(self) -> bool:
        """Handle popups and modals on Amazon Jobs UK."""
        try:
            log.info("Handling popups and modals...")
            
            # Wait a moment for page to load
            self.page.wait_for_timeout(3000)
            
            # Step 1: Dismiss job alerts modal with Escape key (this works reliably)
            log.info("Dismissing job alerts modal...")
            self.page.keyboard.press('Escape')
            self.page.wait_for_timeout(2000)
            
            # Step 2: Handle cookies (check multiple times as they may appear on different pages)
            self.handle_cookies()
            
            # Note: Location dialog is prevented by browser context settings
            log.info("Popup handling completed")
            return True
            
        except Exception as e:
            log.error(f"Failed to handle popups: {e}")
            return False
    
    def handle_cookies(self):
        """Handle cookie consent dialogs."""
        try:
            cookie_selectors = [
                "button:has-text('Accept all')",
                "button:has-text('Accept All')",
                "button:has-text('Accept cookies')",
                "button:has-text('Accept Cookies')",
                "#onetrust-accept-btn-handler",
                "[data-test='accept-cookies']",
                ".cookie-accept",
                "button[id*='accept']"
            ]
            
            for selector in cookie_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.is_visible():
                        log.info(f"Accepting cookies with: {selector}")
                        element.click()
                        self.page.wait_for_timeout(1000) # Changed from time.sleep(2)
                        return True
                except:
                    continue
                    
        except Exception as e:
            log.warning(f"Cookie handling failed: {e}")
            
        return False

    def navigate_to_job_search(self) -> bool:
        """Navigate to the job search area."""
        try:
            # Amazon Jobs UK loads on main page first
            job_site_url = self.config['job_site_url']
            log.info(f"Navigating to {job_site_url}")
            
            self.page.goto(job_site_url, wait_until="domcontentloaded")
            
            # Handle popups first
            if not self.handle_popups():
                log.warning("Popup handling had issues, continuing...")
            
            # Navigate to actual job search page
            target_url = job_site_url.rstrip('/') + '/app#/jobSearch'
            log.info(f"Navigating to job search: {target_url}")
            self.page.goto(target_url, wait_until="domcontentloaded")
            self.page.wait_for_load_state('domcontentloaded', timeout=5000) # Changed from time.sleep(3)
            
            # Handle cookies again on job search page
            log.info("Checking for cookies on job search page...")
            self.handle_cookies()
            
            # Handle job alerts modal that may reappear on job search page
            log.info("Checking for job alerts modal on job search page...")
            self.page.keyboard.press('Escape')
            self.page.wait_for_timeout(2000) # Changed from time.sleep(2)
            
            return True
            
        except Exception as e:
            log.error(f"Failed to navigate to job search: {e}")
            return False

    def login(self) -> bool:
        """Attempt to login to Amazon account with multi-step authentication."""
        try:
            log.info("Starting multi-step Amazon login process...")
            
            # Step 0: First handle any blocking dialogs
            self.handle_cookies()
            
            # Dismiss job alerts modal that might be blocking
            log.info("Dismissing any job alerts modal before login...")
            self.page.keyboard.press('Escape')
            self.page.wait_for_timeout(2000) # Changed from time.sleep(2)
            
            # Step 1: Click hamburger menu to open side panel
            log.info("Opening hamburger menu...")
            self.page.click("body", position={"x": 32, "y": 100})
            # Wait for side panel to open
            self.page.wait_for_selector("a:has-text('Sign in')", timeout=5000) # Changed from time.sleep(3)
            
            # Step 2: Look for login/signin options in the side panel
            login_selectors = [
                "a:has-text('Sign in')",
                "a:has-text('Sign In')", 
                "button:has-text('Sign in')",
                "button:has-text('Sign In')",
                "a:has-text('Login')",
                "button:has-text('Login')",
                "[href*='signin']",
                "[href*='login']",
                "a[href*='amazon'][href*='signin']"
            ]
            
            login_found = False
            for selector in login_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    for element in elements:
                        if element.is_visible():
                            text = element.inner_text() or element.get_attribute('aria-label') or ''
                            href = element.get_attribute('href') or ''
                            
                            log.info(f"Found login option: '{text}' -> {href}")
                            
                            # Click the first visible login option
                            element.click()
                            self.page.wait_for_url("**/ap/signin**", timeout=7000) # Changed from time.sleep(5)
                            login_found = True
                            break
                    
                    if login_found:
                        break
                        
                except Exception as e:
                    log.warning(f"Error checking selector {selector}: {e}")
                    continue
            
            if not login_found:
                log.warning("No login options found in side panel")
                return False
            
            # Now we should be on the login flow
            return self.perform_multi_step_authentication()
                
        except Exception as e:
            log.error(f"Login failed: {e}")
            return False

    def perform_multi_step_authentication(self) -> bool:
        """Perform multi-step Amazon authentication with smart step detection."""
        try:
            log.info("Starting multi-step authentication flow...")
            
            # Decrypt password
            # Assuming self.config is the profile_config
            encrypted_password = self.config.get('amazon_password')
            if not encrypted_password:
                log.error("Amazon password not found in configuration")
                return False

            password = decrypt(encrypted_password, self.master_password)
            if not password:
                log.error("Failed to decrypt Amazon password")
                return False
            
            log.info("Password decrypted successfully")
            
            # Step 1: Email entry
            if not self.handle_email_entry():
                log.error("Email entry failed")
                return False
            
            # Multi-step authentication with retry logic
            max_attempts = 10
            attempt = 0
            previous_step = None
            step_retry_count = {}
            
            while attempt < max_attempts:
                attempt += 1
                current_step = self.detect_current_step()
                
                log.info(f"Attempt {attempt}: Detected step - {current_step}")
                
                # Check if we're stuck in the same step
                if current_step == previous_step:
                    step_retry_count[current_step] = step_retry_count.get(current_step, 0) + 1
                    if step_retry_count[current_step] >= 3:
                        log.warning(f"Stuck in step '{current_step}' for 3 attempts, trying to break out...")
                        
                        # Try to break out of loops
                        if current_step == "verification_method":
                            log.info("Breaking out of verification method loop...")
                            self.page.wait_for_timeout(10000)  # Wait longer, Changed from time.sleep(10)
                            # Try to detect if we actually moved to next step
                            new_step = self.detect_current_step()
                            if new_step != current_step:
                                current_step = new_step
                                log.info(f"Successfully broke out, new step: {current_step}")
                            else:
                                log.error("Failed to break out of verification method loop")
                                return False
                        else:
                            log.error(f"Unable to break out of step: {current_step}")
                            return False
                else:
                    # Reset retry count for new step
                    step_retry_count = {current_step: 1}
                
                previous_step = current_step
                
                # Handle each step
                if current_step == "pin_entry":
                    if not self.handle_pin_entry(password):
                        log.error("PIN entry failed")
                        return False
                        
                elif current_step == "verification_method":
                    if not self.handle_verification_method_selection():
                        log.error("Verification method selection failed")
                        return False
                        
                elif current_step == "2fa_code":
                    if not self.handle_2fa_code_entry():
                        log.error("2FA code entry failed")
                        return False
                        
                elif current_step == "captcha":
                    if not self.handle_captcha():
                        log.error("Captcha handling failed")
                        return False
                        
                elif current_step == "success":
                    log.info("Authentication completed successfully!")
                    return True
                    
                elif current_step == "unknown":
                    log.warning(f"Unknown authentication step detected on attempt {attempt}")
                    # Log current page details for debugging
                    self.log_current_page_details()
                    
                    # Wait a bit and try again
                    self.page.wait_for_timeout(5000) # Changed from time.sleep(5)
                    
                    # If we've been stuck on unknown for too long, fail
                    if step_retry_count.get("unknown", 0) >= 3:
                        log.error("Too many unknown steps, authentication failed")
                        return False
                
                # Wait between steps
                self.page.wait_for_timeout(3000) # Changed from time.sleep(3)
            
            log.error(f"Authentication failed after {max_attempts} attempts")
            return False
            
        except Exception as e:
            log.error(f"Multi-step authentication failed: {e}")
            return False

    def detect_current_step(self) -> str:
        """Detect which step of the authentication process we're currently on with improved efficiency."""
        default_timeout = 1500  # ms
        page_text_lower = None  # Initialize

        try:
            current_url = self.page.url.lower() # Keep URL check as it's efficient

            # PIN Entry Detection
            pin_indicators = [
                'enter your personal pin', # text
                'personal pin', # text
                'input[placeholder*="pin"]', # selector
                'input[name*="pin"]', # selector
                'input[id*="pin"]' # selector
            ]
            if self.page.locator('input#ap_pin_mobile_field').is_visible(timeout=default_timeout):
                log.info("PIN page detected by specific selector #ap_pin_mobile_field")
                return "pin_entry"

            pin_selector_found = False
            for indicator in pin_indicators:
                if indicator.startswith('input['):  # Is a selector
                    try:
                        if self.page.locator(indicator).is_visible(timeout=default_timeout):
                            log.info(f"PIN page detected via selector: {indicator}")
                            pin_selector_found = True
                            return "pin_entry"
                    except Exception: # Playwright might throw if selector is invalid / times out
                        continue
            if not pin_selector_found:
                if page_text_lower is None:
                    try:
                        page_text_lower = self.page.inner_text('body', timeout=default_timeout).lower()
                    except Exception as e:
                        log.warning(f"Could not get page_text for PIN (text) detection: {e}")
                        page_text_lower = ""

                if page_text_lower:
                    for indicator in pin_indicators:
                        if not indicator.startswith('input['):  # Is text
                            if indicator in page_text_lower:
                                log.info(f"PIN page detected via text: {indicator}")
                                return "pin_entry"

            # Verification Method Detection
            # Current logic is fairly specific, let's adapt it with timeouts
            try:
                if self.page.locator('text="Where should we send your verification code"').is_visible(timeout=default_timeout):
                    send_button = self.page.locator('button:has-text("Send verification code")')
                    if send_button.is_visible(timeout=default_timeout) and send_button.is_enabled(timeout=default_timeout):
                        log.info("Verification method page detected")
                        return "verification_method"
            except Exception:
                pass # Element not visible or other error

            # 2FA Code Entry Detection
            code_indicators = [
                'a verification code has been sent', # text
                'enter the verification code', # text
                'verification code sent to', # text
                'input[placeholder*="verification"]', # selector
                'input[placeholder*="code"]' # selector
            ]
            if self.page.locator('input#cvf-input-code').is_visible(timeout=default_timeout):
                log.info("2FA code page detected by specific selector #cvf-input-code")
                return "2fa_code"
            if self.page.locator('input[name="otpCode"]').is_visible(timeout=default_timeout):
                log.info("2FA code page detected by specific selector input[name=\"otpCode\"]")
                return "2fa_code"

            code_selector_found = False
            for indicator in code_indicators:
                if indicator.startswith('input['):  # Is a selector
                    try:
                        if self.page.locator(indicator).is_visible(timeout=default_timeout):
                            log.info(f"2FA code page detected via selector: {indicator}")
                            code_selector_found = True
                            return "2fa_code"
                    except Exception:
                        continue
            if not code_selector_found:
                if page_text_lower is None:
                    try:
                        page_text_lower = self.page.inner_text('body', timeout=default_timeout).lower()
                    except Exception as e:
                        log.warning(f"Could not get page_text for 2FA (text) detection: {e}")
                        page_text_lower = ""

                if page_text_lower:
                    for indicator in code_indicators:
                        if not indicator.startswith('input['):  # Is text
                            if indicator in page_text_lower:
                                log.info(f"2FA code page detected via text: {indicator}")
                                return "2fa_code"

            # CAPTCHA Detection
            captcha_indicators = [
                'img[src*="captcha"]', # selector
                'img[alt*="captcha"]', # selector
                '[class*="captcha"]', # selector
                'enter the characters', # text
                'prove you are human', # text
                'select all images', # text
                'choose all', # text
                'let\'s confirm you are human' #text
            ]
            if self.page.locator('input#captchacharacters').is_visible(timeout=default_timeout):
                log.info("CAPTCHA page detected by specific selector #captchacharacters")
                return "captcha"
            # The img[alt*="captcha"] is already in captcha_indicators, but checking it early.
            try:
                if self.page.locator('img[alt*="captcha"]').is_visible(timeout=default_timeout):
                    log.info("CAPTCHA page detected by specific selector img[alt*=\"captcha\"]")
                    return "captcha"
            except Exception:
                pass


            captcha_selector_found = False
            for indicator in captcha_indicators:
                if indicator.startswith(('img[', '[class*=', 'input#')): # Is a selector
                    try:
                        if self.page.locator(indicator).is_visible(timeout=default_timeout):
                            log.info(f"CAPTCHA page detected via selector: {indicator}")
                            captcha_selector_found = True
                            return "captcha"
                    except Exception:
                        continue
            if not captcha_selector_found:
                if page_text_lower is None:
                    try:
                        page_text_lower = self.page.inner_text('body', timeout=default_timeout).lower()
                    except Exception as e:
                        log.warning(f"Could not get page_text for CAPTCHA (text) detection: {e}")
                        page_text_lower = ""

                if page_text_lower:
                    for indicator in captcha_indicators:
                        if not indicator.startswith(('img[', '[class*=', 'input#')):  # Is text
                            if indicator in page_text_lower:
                                log.info(f"CAPTCHA page detected via text: {indicator}")
                                return "captcha"

            # Success Detection (URL based)
            if 'jobsatamazon' in current_url and 'login' not in current_url:
                # Consider adding a specific element check if needed for robustness
                # e.g. and self.page.locator('#some_job_search_results_container').is_visible(timeout=default_timeout)
                log.info("Success detected by URL")
                return "success"

            # If we can't determine the step after all checks
            log.warning(f"Unknown authentication step. URL: {current_url}")
            return "unknown"

        except Exception as e:
            log.error(f"Error detecting current step: {e}")
            return "unknown"

    def log_current_page_details(self):
        """Log current page details for debugging."""
        try:
            current_url = self.page.url
            page_title = self.page.title()
            page_text_snippet = self.page.inner_text('body')[:500]  # First 500 chars
            
            log.info("=== CURRENT PAGE DETAILS ===")
            log.info(f"URL: {current_url}")
            log.info(f"Title: {page_title}")
            log.info(f"Page text snippet: {page_text_snippet}")
            log.info("============================")
            
        except Exception as e:
            log.error(f"Failed to log page details: {e}")

    def handle_email_entry(self) -> bool:
        """Handle email entry step."""
        try:
            log.info("Handling email entry step...")
            
            # Wait for page to load
            self.page.wait_for_load_state('domcontentloaded', timeout=5000) # Changed from time.sleep(3)
            
            # Look for email input field
            email_selectors = [
                'input[type="email"]', 
                'input[name="email"]', 
                '#ap_email',
                'input[name="username"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]',
                'input[placeholder*="mobile"]',
                'input[id*="email"]',
                'input[class*="email"]',
                'input[type="text"]',
                'input:not([type])'
            ]
            
            email_filled = False
            for selector in email_selectors:
                try:
                    email_field = self.page.query_selector(selector)
                    if email_field and email_field.is_visible():
                        job_site_username = self.config.get('job_site_username')
                        if not job_site_username:
                            log.error("job_site_username not found in config for email entry")
                            return False
                        email_field.fill(job_site_username)
                        log.info(f"Email filled with {selector}: {job_site_username}")
                        email_filled = True
                        break
                except Exception as e:
                    log.warning(f"Failed to fill email with {selector}: {e}")
                    continue
            
            if not email_filled:
                log.error("No email field found or filled")
                return False
            
            # Click next/continue button
            next_selectors = [
                'button:has-text("Next")',
                'button:has-text("NEXT")',
                'button:has-text("Continue")',
                'button:has-text("CONTINUE")',
                'input[type="submit"]',
                '#continue',
                'button[type="submit"]',
                'button[class*="continue"]',
                'button[id*="continue"]',
                'button[id*="next"]'
            ]
            
            next_clicked = False
            for selector in next_selectors:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible():
                        button.click()
                        self.page.wait_for_load_state('domcontentloaded', timeout=7000) # Changed from time.sleep(5)
                        log.info(f"Clicked next button with selector: {selector}")
                        next_clicked = True
                        break
                except Exception as e:
                    log.warning(f"Failed to click next with {selector}: {e}")
                    continue
            
            if not next_clicked:
                # Try pressing Enter key as alternative
                log.info("No next button found, trying Enter key...")
                try:
                    self.page.keyboard.press('Enter')
                    self.page.wait_for_load_state('domcontentloaded', timeout=7000) # Changed from time.sleep(5)
                    log.info("Pressed Enter key as next")
                except Exception as e:
                    log.warning(f"Failed to press Enter: {e}")
                    return False
            
            log.info("Email entry step completed")
            return True
            
        except Exception as e:
            log.error(f"Email entry step failed: {e}")
            return False

    def handle_pin_entry(self, password: str) -> bool:
        """Handle PIN entry step with improved detection."""
        try:
            log.info("Handling PIN entry step...")
            
            # Wait for page to load
            self.page.wait_for_load_state('domcontentloaded', timeout=5000) # Changed from time.sleep(3)
            
            # Look for PIN input field with more specific selectors
            pin_selectors = [
                'input[placeholder*="PIN"]',
                'input[placeholder*="pin"]',
                'input[name*="pin"]',
                'input[id*="pin"]',
                'input[type="password"]',
                'input[class*="pin"]',
                # More generic selectors for PIN pages
                'input[type="text"]',
                'input:not([type])'
            ]
            
            pin_field = None
            for selector in pin_selectors:
                try:
                    field = self.page.query_selector(selector)
                    if field and field.is_visible():
                        # Double-check this is actually a PIN field by checking the page context
                        page_text = self.page.inner_text('body').lower()
                        if 'pin' in page_text or 'personal' in page_text:
                            pin_field = field
                            log.info(f"Found PIN field with selector: {selector}")
                            break
                except:
                    continue
            
            if not pin_field:
                log.error("No PIN field found")
                return False
            
            # Use the password as PIN (assuming it's the same)
            pin_field.fill(password)
            log.info("PIN filled successfully")
            
            # Click next button
            next_selectors = [
                'button:has-text("Next")',
                'button:has-text("NEXT")',
                'button:has-text("Continue")',
                'input[type="submit"]',
                'button[type="submit"]'
            ]
            
            next_clicked = False
            for selector in next_selectors:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible() and not button.is_disabled():
                        button.click()
                        self.page.wait_for_load_state('domcontentloaded', timeout=7000) # Changed from time.sleep(5)
                        log.info(f"Clicked next button after PIN entry: {selector}")
                        next_clicked = True
                        break
                except Exception as e:
                    continue
            
            if not next_clicked:
                # Try Enter key as fallback
                log.info("No next button found, trying Enter key...")
                try:
                    self.page.keyboard.press('Enter')
                    self.page.wait_for_load_state('domcontentloaded', timeout=7000) # Changed from time.sleep(5)
                    log.info("Pressed Enter key after PIN entry")
                except Exception as e:
                    log.warning(f"Failed to press Enter: {e}")
                    return False
            
            log.info("PIN entry step completed")
            return True
            
        except Exception as e:
            log.error(f"PIN entry step failed: {e}")
            return False

    def handle_verification_method_selection(self) -> bool:
        """Handle verification method selection (choose email)."""
        try:
            log.info("Handling verification method selection...")
            
            # Wait for page to load
            self.page.wait_for_load_state('domcontentloaded', timeout=5000) # Changed from time.sleep(3)
            
            # Check if we're actually on the verification method page
            page_text = self.page.inner_text('body').lower()
            if 'where should we send your verification code' not in page_text:
                log.info("Not on verification method page, skipping...")
                return True
            
            # Look for email verification option (should be selected by default)
            email_option_selectors = [
                'input[type="radio"][value*="email"]',
                'button:has-text("Email verification")',
                'input[id*="email"]',
                'label:has-text("Email")'
            ]
            
            # Try to select email option if not already selected
            email_selected = False
            for selector in email_option_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.is_visible():
                        # Check if it's already selected
                        if selector.startswith('input[type="radio"]'):
                            if not element.is_checked():
                                element.click()
                                log.info(f"Selected email verification option: {selector}")
                                email_selected = True
                                self.page.wait_for_timeout(2000) # Changed from time.sleep(2)
                        else:
                            element.click()
                            log.info(f"Selected email verification option: {selector}")
                            email_selected = True
                            self.page.wait_for_timeout(2000) # Changed from time.sleep(2)
                        break
                except:
                    continue
            
            # Click send verification code button
            send_selectors = [
                'button:has-text("Send verification code")',
                'button:has-text("Send code")',
                'button:has-text("Continue")',
                'button:has-text("Next")',
                'input[type="submit"]'
            ]
            
            send_clicked = False
            for selector in send_selectors:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible() and not button.is_disabled():
                        button.click()
                        self.page.wait_for_load_state('domcontentloaded', timeout=7000) # Changed from time.sleep(5)
                        log.info(f"Clicked send verification code: {selector}")
                        send_clicked = True
                        break
                except Exception as e:
                    continue
            
            if not send_clicked:
                log.warning("Could not find or click send verification code button")
                return False
            
            # Wait a bit longer to see if page changes
            self.page.wait_for_timeout(10000) # Changed from time.sleep(10)
            
            # Check if we've moved to the next step
            new_page_text = self.page.inner_text('body').lower()
            if 'where should we send your verification code' not in new_page_text:
                log.info("Successfully moved past verification method selection")
                return True
            else:
                log.warning("Still on verification method page after clicking send")
                return False
            
        except Exception as e:
            log.error(f"Verification method selection failed: {e}")
            return False

    def handle_2fa_code_entry(self) -> bool:
        """Handle 2FA verification code entry with manual intervention."""
        try:
            log.info("Handling 2FA verification code entry...")
            
            # Wait for page to load
            # time.sleep(3) -> Kept for manual intervention as per plan
            
            # Look for verification code input
            code_selectors = [
                'input[placeholder*="verification"]',
                'input[placeholder*="code"]',
                'input[name*="code"]',
                'input[id*="code"]',
                'input[type="text"]',
                'input:not([type])'
            ]
            
            code_field = None
            for selector in code_selectors:
                try:
                    field = self.page.query_selector(selector)
                    if field and field.is_visible():
                        code_field = field
                        log.info(f"Found 2FA code field with selector: {selector}")
                        break
                except:
                    continue
            
            if not code_field:
                log.error("No 2FA code field found")
                return False
            
            # Check if email automation is configured and working
            email_config = self.config.get('email_automation', {})
            if email_config.get('enabled'):
                log.info("Attempting automatic 2FA code retrieval...")
                verification_code = self.get_2fa_code_from_email()
                
                if verification_code:
                    # Fill the verification code automatically
                    code_field.fill(verification_code)
                    log.info(f"Automatically filled 2FA code: {verification_code}")
                    
                    # Click next button
                    self.click_next_button()
                    return True
                else:
                    log.warning("Automatic 2FA code retrieval failed, falling back to manual entry")
            
            # Manual intervention required
            log.info("⚠️  MANUAL INTERVENTION REQUIRED: 2FA Code Entry")
            log.info("📧 Please check your email for the verification code")
            log.info("⏳ You have 120 seconds to:")
            log.info("   1. Check your email for the Amazon verification code")
            log.info("   2. Enter the code in the browser window")
            log.info("   3. Click Next")
            
            # Wait for manual intervention
            time.sleep(120)
            
            # Check if the code was entered and we moved to next step
            current_url = self.page.url
            if 'verification' not in current_url.lower() and 'code' not in current_url.lower():
                log.info("2FA code appears to have been successfully entered!")
                return True
            
            # Try to help with next button if still on verification page
            self.click_next_button()
            
            log.info("2FA code entry step completed")
            return True
            
        except Exception as e:
            log.error(f"2FA code entry failed: {e}")
            return False

    def click_next_button(self):
        """Helper method to click next/continue buttons."""
        next_selectors = [
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button:has-text("Verify")',
            'input[type="submit"]',
            'button[type="submit"]'
        ]
        
        for selector in next_selectors:
            try:
                button = self.page.query_selector(selector)
                if button and button.is_visible() and not button.is_disabled():
                    button.click()
                    self.page.wait_for_load_state('domcontentloaded', timeout=7000) # Changed from time.sleep(5)
                    log.info(f"Clicked next button: {selector}")
                    return True
            except:
                continue
        
        return False

    def handle_captcha(self) -> bool:
        """Handle captcha with manual intervention (realistic approach)."""
        try:
            log.info("Captcha detected - requiring manual intervention")
            
            # Wait for captcha to load
            # time.sleep(3) -> Kept for manual intervention as per plan
            
            # Log what type of captcha we're dealing with
            captcha_info = self.analyze_captcha()
            
            log.info("⚠️  MANUAL INTERVENTION REQUIRED: Captcha Solving")
            log.info(f"🧩 Captcha type detected: {captcha_info}")
            log.info("⏳ You have 180 seconds (3 minutes) to:")
            log.info("   1. Solve the captcha in the browser window")
            log.info("   2. Click submit/continue")
            log.info("   3. Complete any additional verification steps")
            
            # Wait for manual captcha solving
            time.sleep(180)
            
            # Check if captcha was solved
            current_url = self.page.url
            page_text = self.page.inner_text('body').lower()
            
            if 'captcha' not in current_url.lower() and 'captcha' not in page_text:
                log.info("Captcha appears to have been solved!")
                return True
            
            log.info("Captcha handling completed (manual intervention)")
            return True
            
        except Exception as e:
            log.error(f"Captcha handling failed: {e}")
            return False

    def analyze_captcha(self) -> str:
        """Analyze what type of captcha we're dealing with."""
        try:
            page_text = self.page.inner_text('body').lower()
            
            # Check for different captcha types
            if 'select all images' in page_text or 'choose all' in page_text:
                return "Image Selection Captcha (e.g., 'Select all beds')"
            elif 'enter the characters' in page_text:
                return "Text-based Captcha"
            elif 'recaptcha' in page_text or self.page.query_selector('.g-recaptcha'):
                return "Google reCAPTCHA"
            elif 'prove you are human' in page_text:
                return "Human Verification Challenge"
            else:
                return "Unknown Captcha Type"
                
        except:
            return "Captcha Detection Error"

    def get_2fa_code_from_email(self) -> str:
        """Automatically retrieve 2FA verification code from email."""
        try:
            import imaplib
            import email
            from email.header import decode_header
            import re
            import time
            
            log.info("Attempting to retrieve 2FA code from email...")
            
            # Check if email automation is configured
            email_config = self.config.get('email_automation', {})
            if not email_config.get('enabled'):
                log.warning("Email automation not configured. Run setup_email_automation.py first.")
                return None
            
            # Get email credentials from configuration
            email_address = email_config.get('email_address', self.config.get('job_site_username'))
            
            try:
                # from .security import decrypt # This is already imported at the top
                email_password = decrypt(email_config.get('encrypted_app_password'), self.master_password)
                if not email_password:
                    log.error("Failed to decrypt email app password, or password not found in email_config")
                    return None
                log.info("Email app password decrypted successfully")
            except Exception as e:
                log.error(f"Failed to decrypt email app password: {e}")
                return None
            
            # Gmail IMAP settings
            imap_server = "imap.gmail.com"
            imap_port = 993
            
            # Wait a bit for the email to arrive
            log.info("Waiting 10 seconds for verification email to arrive...")
            time.sleep(10)
            
            # Connect to email
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
            
            try:
                mail.login(email_address, email_password)
                log.info("Successfully connected to email account")
                
                # Select inbox
                mail.select("inbox")
                
                # Search for recent Amazon verification emails
                search_criteria = [
                    '(FROM "amazon" SUBJECT "verification")',
                    '(FROM "amazon" SUBJECT "code")',
                    '(FROM "amazon" SUBJECT "Amazon Jobs")',
                    '(SUBJECT "verification code")',
                    '(SUBJECT "Amazon Jobs verification")',
                    '(FROM "no-reply@amazon" SUBJECT "verification")',
                    '(FROM "amazon.com" SUBJECT "code")'
                ]
                
                verification_code = None
                
                for criteria in search_criteria:
                    try:
                        # Search for emails from today
                        status, messages = mail.search(None, criteria)
                        
                        if status == "OK" and messages[0]:
                            # Get the most recent email
                            email_ids = messages[0].split()
                            if email_ids:
                                latest_email_id = email_ids[-1]
                                
                                # Fetch the email
                                status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
                                
                                if status == "OK":
                                    # Parse the email
                                    raw_email = msg_data[0][1]
                                    email_message = email.message_from_bytes(raw_email)
                                    
                                    # Extract email content
                                    email_body = self.extract_email_body(email_message)
                                    email_subject = email_message.get("Subject", "")
                                    
                                    log.info(f"Checking email with subject: {email_subject}")
                                    
                                    # Look for verification code patterns
                                    code_patterns = [
                                        r'\b(\d{6})\b',  # 6 digit code
                                        r'\b(\d{4})\b',  # 4 digit code
                                        r'\b(\d{8})\b',  # 8 digit code
                                        r'verification code[:\s]*(\d+)',
                                        r'code[:\s]*(\d+)',
                                        r'Your.*code.*?(\d+)',
                                        r'Enter.*code.*?(\d+)',
                                        r'(\d+).*verification'
                                    ]
                                    
                                    for pattern in code_patterns:
                                        matches = re.findall(pattern, email_body, re.IGNORECASE)
                                        if matches:
                                            # Get the first match that looks like a verification code
                                            for match in matches:
                                                if len(match) >= 4 and len(match) <= 8:
                                                    verification_code = match
                                                    log.info(f"Found verification code: {verification_code}")
                                                    break
                                        
                                        if verification_code:
                                            break
                                    
                                    if verification_code:
                                        break
                    except Exception as e:
                        log.warning(f"Error searching with criteria '{criteria}': {e}")
                        continue
                
                mail.logout()
                
                if verification_code:
                    log.info(f"Successfully retrieved 2FA code: {verification_code}")
                    return verification_code
                else:
                    log.warning("No verification code found in recent emails")
                    # Try waiting a bit longer and search again
                    log.info("Waiting additional 15 seconds for email...")
                    time.sleep(15)
                    
                    # Try one more time with broader search
                    try:
                        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
                        mail.login(email_address, email_password)
                        mail.select("inbox")
                        
                        # Broader search for any recent emails
                        status, messages = mail.search(None, 'ALL')
                        if status == "OK" and messages[0]:
                            email_ids = messages[0].split()
                            # Check last 5 emails
                            for email_id in email_ids[-5:]:
                                try:
                                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                                    if status == "OK":
                                        raw_email = msg_data[0][1]
                                        email_message = email.message_from_bytes(raw_email)
                                        email_body = self.extract_email_body(email_message)
                                        
                                        # Look for any numeric codes
                                        matches = re.findall(r'\b(\d{4,8})\b', email_body)
                                        for match in matches:
                                            if len(match) >= 4 and len(match) <= 8:
                                                log.info(f"Found potential code in recent email: {match}")
                                                mail.logout()
                                                return match
                                except:
                                    continue
                        
                        mail.logout()
                    except:
                        pass
                    
                    return None
                    
            except Exception as e:
                log.error(f"Email login failed: {e}")
                log.info("Note: For Gmail, you need to enable 2FA and create an App Password")
                log.info("Run: python setup_email_automation.py")
                return None
                
        except Exception as e:
            log.error(f"Failed to retrieve 2FA code from email: {e}")
            # Fallback: try to extract code from page if it's pre-filled or visible
            return self.extract_code_from_page()

    def extract_email_body(self, email_message):
        """Extract text content from email message."""
        try:
            body = ""
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    elif content_type == "text/html" and not body:
                        html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        # Strip HTML tags for simple text extraction
                        import re
                        body = re.sub(r'<[^>]+>', '', html_body)
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            return body
            
        except Exception as e:
            log.error(f"Error extracting email body: {e}")
            return ""

    def extract_code_from_page(self):
        """Try to extract verification code from the current page if visible."""
        try:
            # Sometimes the code might be pre-filled or visible on the page
            page_text = self.page.inner_text('body')
            
            import re
            code_patterns = [
                r'\b(\d{6})\b',
                r'\b(\d{4})\b', 
                r'\b(\d{8})\b'
            ]
            
            for pattern in code_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    for match in matches:
                        if len(match) >= 4 and len(match) <= 8:
                            log.info(f"Found code on page: {match}")
                            return match
            
            return None
            
        except Exception as e:
            log.error(f"Error extracting code from page: {e}")
            return None

    def search_jobs(self) -> bool:
        """Search for jobs based on profile criteria."""
        try:
            log.info("Searching for jobs...")
            
            # Wait for page to load
            self.page.wait_for_load_state('domcontentloaded', timeout=5000) # Changed from time.sleep(3)
            
            # Look for search inputs
            search_selectors = [
                'input[placeholder*="Search"]',
                'input[placeholder*="job"]',
                'input[type="search"]',
                '#search-jobs'
            ]
            
            # Fill in search keywords
            keywords = ' '.join(self.config.get('keywords', {}).get('required', []))
            if keywords:
                for selector in search_selectors:
                    try:
                        search_field = self.page.query_selector(selector)
                        if search_field and search_field.is_visible():
                            search_field.fill(keywords)
                            log.info(f"Filled search with keywords: {keywords}")
                            break
                    except:
                        continue
            
            # Look for location input
            location_selectors = [
                'input[placeholder*="location"]',
                'input[placeholder*="postcode"]', 
                'input[placeholder*="city"]'
            ]
            
            # Fill in location
            locations = self.config.get('locations', [])
            if locations:
                location = locations[0]  # Use first location
                for selector in location_selectors:
                    try:
                        location_field = self.page.query_selector(selector)
                        if location_field and location_field.is_visible():
                            location_field.fill(location)
                            log.info(f"Filled location: {location}")
                            break
                    except:
                        continue
            
            # Submit search
            search_button_selectors = [
                'button:has-text("Search")',
                'input[type="submit"]',
                'button[type="submit"]'
            ]
            
            for selector in search_button_selectors:
                try:
                    search_button = self.page.query_selector(selector)
                    if search_button and search_button.is_visible():
                        search_button.click()
                        self.page.wait_for_load_state('networkidle', timeout=10000) # Changed from time.sleep(5)
                        log.info("Search submitted")
                        break
                except:
                    continue
            
            return True
            
        except Exception as e:
            log.error(f"Job search failed: {e}")
            return False

    def extract_job_listings(self) -> list:
        """Extract job listings from the current page."""
        try:
            log.info("Extracting job listings...")
            
            # Wait for results to load
            self.page.wait_for_selector("div[class*='job']", timeout=7000) # Changed from time.sleep(5)
            
            # Use the selectors we discovered that work
            job_selectors = [
                "div[class*='job']",
                ".job-listing",
                "[data-test*='job']",
                ".job-item"
            ]
            
            jobs = []
            
            for selector in job_selectors:
                try:
                    job_elements = self.page.query_selector_all(selector)
                    if job_elements:
                        log.info(f"Found {len(job_elements)} job elements with selector: {selector}")
                        
                        for element in job_elements:
                            if element.is_visible():
                                try:
                                    # Extract job details
                                    title_elem = element.query_selector("h1, h2, h3, .title, [class*='title']")
                                    title = title_elem.inner_text() if title_elem else "Unknown Title"
                                    
                                    company_elem = element.query_selector(".company, [class*='company']")
                                    company = company_elem.inner_text() if company_elem else "Amazon"
                                    
                                    location_elem = element.query_selector(".location, [class*='location']")
                                    location = location_elem.inner_text() if location_elem else "Unknown Location"
                                    
                                    # Get the link
                                    link_elem = element.query_selector("a")
                                    link = link_elem.get_attribute('href') if link_elem else ""
                                    
                                    job = {
                                        'title': title.strip(),
                                        'company': company.strip(), 
                                        'location': location.strip(),
                                        'link': link,
                                        'description': f"{title} at {company} in {location}"
                                    }
                                    
                                    jobs.append(job)
                                    
                                except Exception as e:
                                    log.warning(f"Error extracting job details: {e}")
                                    continue
                        
                        if jobs:
                            break  # Found jobs with this selector, stop trying others
                            
                except Exception as e:
                    log.warning(f"Error with selector {selector}: {e}")
                    continue
            
            log.info(f"Extracted {len(jobs)} job listings")
            return jobs
            
        except Exception as e:
            log.error(f"Failed to extract job listings: {e}")
            return []

    def close_session(self):
        """Clean up browser session."""
        try:
            if self.page and not self.page.is_closed():
                self.page.close()
            if self.context:
                self.context.close() 
            if self.browser and self.browser.is_connected():
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            
            self.session_active = False
            log.info("Browser session closed")
            
        except Exception as e:
            log.error(f"Error closing browser session: {e}")

    def run_job_search_session(self) -> list:
        """Run a complete job search session, dispatching to site-specific methods."""
        job_site_type = self.config.get('job_site_type', 'amazon') # Default to amazon if not specified
        jobs = []

        try:
            if not self.start_session():
                return []

            if job_site_type == 'indeed':
                log.info("Running Indeed job search session.")
                # Get keywords and location for Indeed
                # Ensure keywords is a list of strings
                keywords_config = self.config.get('keywords', {})
                required_keywords = keywords_config.get('required', [])
                optional_keywords = keywords_config.get('optional', [])
                combined_keywords = required_keywords + optional_keywords

                # Ensure location is a string
                filters_config = self.config.get('filters', {})
                cities = filters_config.get('cities', [])
                location_str = cities[0] if cities else self.config.get('default_location', "") # Fallback if needed

                if not combined_keywords or not location_str:
                    log.error("Keywords or location missing for Indeed search in profile config.")
                    if not combined_keywords:
                        log.error(f"Combined keywords list is empty. Required: {required_keywords}, Optional: {optional_keywords}")
                    if not location_str:
                        log.error(f"Location string is empty. Cities: {cities}, Default location: {self.config.get('default_location', '')}")
                    return []

                if not self.navigate_to_indeed_job_search(combined_keywords, location_str):
                    log.error("Failed to navigate to Indeed job search page.")
                    return []

                jobs = self.extract_indeed_job_listings()

            elif job_site_type == 'amazon': # Existing Amazon logic
                log.info("Running Amazon job search session.")
                if not self.navigate_to_job_search(): # Amazon specific navigation
                    return []

                if self.config.get('job_site_username'): # Amazon specific login
                    login_success = self.login()
                    if login_success:
                        log.info("Amazon login successful.")
                    else:
                        log.warning("Amazon login failed, continuing without login.")

                if not self.search_jobs(): # Amazon specific search
                    log.warning("Amazon job search failed, trying to extract from current page.")

                jobs = self.extract_job_listings() # Amazon specific extraction (assuming this is the generic one for now)
            
            else:
                log.error(f"Unsupported job_site_type: {job_site_type}")
                return []
            
            log.info(f"Job search session completed for {job_site_type}. Found {len(jobs)} jobs.")
            return jobs
            
        except Exception as e:
            log.error(f"Job search session failed for {job_site_type}: {e}")
            return []
        finally:
            self.close_session()

    # --- Indeed Specific Methods ---

    def navigate_to_indeed_job_search(self, keywords: list, location: str) -> bool:
        """Constructs and navigates to the Indeed job search URL."""
        indeed_cfg = self.config.get('indeed_config')
        if not indeed_cfg:
            log.error("Indeed configuration ('indeed_config') not found in profile.")
            return False

        base_url = indeed_cfg.get('base_url', "https://uk.indeed.com")
        search_path = indeed_cfg.get('search_path', "/jobs")

        # Encode keywords and location for URL
        query_keywords = quote_plus(" ".join(keywords))
        query_location = quote_plus(location)

        search_url = f"{base_url.rstrip('/')}{search_path}?q={query_keywords}&l={query_location}"

        log.info(f"Navigating to Indeed job search: {search_url}")
        try:
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=10000)
            
            # Handle Indeed cookie popup (example)
            try:
                cookie_button = self.page.locator("#onetrust-accept-btn-handler") # Common Indeed cookie button
                if cookie_button.is_visible(timeout=5000): # Check visibility with a timeout
                    cookie_button.click(timeout=3000) # Click with a timeout
                    log.info("Accepted Indeed cookies.")
                    self.page.wait_for_timeout(1000) # Wait for action to complete
            except Exception as e:
                log.warning(f"Indeed cookie handling failed or not needed: {e}")

            # You might want to add a check here to ensure the page loaded correctly,
            # e.g., by looking for a known element on the search results page.
            # For PoC, we assume navigation is successful if no immediate error.
            
            return True
        except Exception as e:
            log.error(f"Failed to navigate to Indeed URL {search_url}: {e}")
            return False

    def extract_indeed_job_listings(self) -> list:
        """Extracts job listings from Indeed search results page."""
        indeed_cfg = self.config.get('indeed_config')
        if not indeed_cfg:
            log.error("Indeed configuration ('indeed_config') not found for extraction.")
            return []

        selectors = indeed_cfg.get('selectors')
        if not selectors:
            log.error("Indeed selectors not found in 'indeed_config'.")
            return []

        job_card_selector = selectors.get('job_card')
        if not job_card_selector:
            log.error("Indeed 'job_card' selector not found in config.")
            return []

        base_url = indeed_cfg.get('base_url', "https://uk.indeed.com")

        jobs = []
        try:
            log.info(f"Waiting for Indeed job cards with selector: {job_card_selector}")
            self.page.wait_for_selector(job_card_selector, timeout=10000) # Wait for the first card

            log.info("Extracting Indeed job listings...")
            job_elements = self.page.locator(job_card_selector).all() # Get all job cards
            log.info(f"Found {len(job_elements)} potential Indeed job cards.")

            for element in job_elements:
                try:
                    title = ""
                    title_elem = element.locator(selectors['title']).first # Use .first to avoid error if multiple, take one
                    if title_elem.is_visible(timeout=500): # Quick check
                       title = title_elem.text_content(timeout=500) or ""

                    company = ""
                    company_elem = element.locator(selectors['company']).first
                    if company_elem.is_visible(timeout=500):
                        company = company_elem.text_content(timeout=500) or ""

                    location = ""
                    location_elem = element.locator(selectors['location']).first
                    if location_elem.is_visible(timeout=500):
                        location = location_elem.text_content(timeout=500) or ""

                    link = ""
                    link_elem = element.locator(selectors['link']).first # Link often same as title
                    if link_elem:
                        href = link_elem.get_attribute('href', timeout=500)
                        if href:
                            link = urljoin(base_url, href) # Ensure absolute URL

                    description_snippet = ""
                    desc_selector = selectors.get('description_snippet')
                    if desc_selector:
                        desc_elem = element.locator(desc_selector).first
                        if desc_elem.is_visible(timeout=500):
                             description_snippet = desc_elem.text_content(timeout=500) or ""

                    if title and company: # Consider a job valid if it has at least title and company
                        job_data = {
                            'title': title.strip(),
                            'company': company.strip(),
                            'location': location.strip(),
                            'link': link.strip(),
                            'description': description_snippet.strip(), # Using 'description' for consistency
                            'source': 'Indeed'
                        }
                        jobs.append(job_data)
                        log.debug(f"Extracted Indeed job: {title} at {company}")
                    else:
                        log.warning("Skipping an Indeed job card, title or company missing.")

                except Exception as e_card:
                    log.warning(f"Error extracting details from an Indeed job card: {e_card}")
                    continue

            log.info(f"Extracted {len(jobs)} Indeed job listings.")
            return jobs
            
        except Exception as e:
            log.error(f"Failed to extract Indeed job listings: {e}")
            return []

    # --- Modified Main Session Runner ---