from playwright.sync_api import sync_playwright, Browser, Page, Playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .logger import log
from .authenticator import get_2fa_code
import time
import logging

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
            logging.info("Starting browser session...")
            
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
            
            logging.info("Browser session started successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start browser session: {e}")
            return False

    def handle_popups(self) -> bool:
        """Handle popups and modals on Amazon Jobs UK."""
        try:
            logging.info("Handling popups and modals...")
            
            # Wait a moment for page to load
            time.sleep(3)
            
            # Step 1: Dismiss job alerts modal with Escape key (this works reliably)
            logging.info("Dismissing job alerts modal...")
            self.page.keyboard.press('Escape')
            time.sleep(2)
            
            # Step 2: Handle cookies (check multiple times as they may appear on different pages)
            self.handle_cookies()
            
            # Note: Location dialog is prevented by browser context settings
            logging.info("Popup handling completed")
            return True
            
        except Exception as e:
            logging.error(f"Failed to handle popups: {e}")
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
                        logging.info(f"Accepting cookies with: {selector}")
                        element.click()
                        time.sleep(2)
                        return True
                except:
                    continue
                    
        except Exception as e:
            logging.warning(f"Cookie handling failed: {e}")
            
        return False

    def navigate_to_job_search(self) -> bool:
        """Navigate to the job search area."""
        try:
            # Amazon Jobs UK loads on main page first
            job_site_url = self.config['job_site_url']
            logging.info(f"Navigating to {job_site_url}")
            
            self.page.goto(job_site_url, wait_until="domcontentloaded")
            
            # Handle popups first
            if not self.handle_popups():
                logging.warning("Popup handling had issues, continuing...")
            
            # Navigate to actual job search page
            target_url = job_site_url.rstrip('/') + '/app#/jobSearch'
            logging.info(f"Navigating to job search: {target_url}")
            self.page.goto(target_url, wait_until="domcontentloaded")
            time.sleep(3)
            
            # Handle cookies again on job search page
            logging.info("Checking for cookies on job search page...")
            self.handle_cookies()
            
            # Handle job alerts modal that may reappear on job search page
            logging.info("Checking for job alerts modal on job search page...")
            self.page.keyboard.press('Escape')
            time.sleep(2)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to navigate to job search: {e}")
            return False

    def login(self) -> bool:
        """Attempt to login to Amazon account with multi-step authentication."""
        try:
            logging.info("Starting multi-step Amazon login process...")
            
            # Step 0: First handle any blocking dialogs
            self.handle_cookies()
            
            # Dismiss job alerts modal that might be blocking
            logging.info("Dismissing any job alerts modal before login...")
            self.page.keyboard.press('Escape')
            time.sleep(2)
            
            # Step 1: Click hamburger menu to open side panel
            logging.info("Opening hamburger menu...")
            self.page.click("body", position={"x": 32, "y": 100})
            time.sleep(3)
            
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
                            
                            logging.info(f"Found login option: '{text}' -> {href}")
                            
                            # Click the first visible login option
                            element.click()
                            time.sleep(5)
                            login_found = True
                            break
                    
                    if login_found:
                        break
                        
                except Exception as e:
                    logging.warning(f"Error checking selector {selector}: {e}")
                    continue
            
            if not login_found:
                logging.warning("No login options found in side panel")
                return False
            
            # Now we should be on the login flow
            return self.perform_multi_step_authentication()
                
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False

    def perform_multi_step_authentication(self) -> bool:
        """Perform multi-step Amazon authentication with smart step detection."""
        try:
            logging.info("Starting multi-step authentication flow...")
            
            # Decrypt password
            encrypted_password = self.config['profiles'][self.current_profile]['amazon_password']
            password = self.decrypt_data(encrypted_password, self.master_password)
            if not password:
                logging.error("Failed to decrypt Amazon password")
                return False
            
            logging.info("Password decrypted successfully")
            
            # Step 1: Email entry
            if not self.handle_email_entry():
                logging.error("Email entry failed")
                return False
            
            # Multi-step authentication with retry logic
            max_attempts = 10
            attempt = 0
            previous_step = None
            step_retry_count = {}
            
            while attempt < max_attempts:
                attempt += 1
                current_step = self.detect_current_step()
                
                logging.info(f"Attempt {attempt}: Detected step - {current_step}")
                
                # Check if we're stuck in the same step
                if current_step == previous_step:
                    step_retry_count[current_step] = step_retry_count.get(current_step, 0) + 1
                    if step_retry_count[current_step] >= 3:
                        logging.warning(f"Stuck in step '{current_step}' for 3 attempts, trying to break out...")
                        
                        # Try to break out of loops
                        if current_step == "verification_method":
                            logging.info("Breaking out of verification method loop...")
                            time.sleep(10)  # Wait longer
                            # Try to detect if we actually moved to next step
                            new_step = self.detect_current_step()
                            if new_step != current_step:
                                current_step = new_step
                                logging.info(f"Successfully broke out, new step: {current_step}")
                            else:
                                logging.error("Failed to break out of verification method loop")
                                return False
                        else:
                            logging.error(f"Unable to break out of step: {current_step}")
                            return False
                else:
                    # Reset retry count for new step
                    step_retry_count = {current_step: 1}
                
                previous_step = current_step
                
                # Handle each step
                if current_step == "pin_entry":
                    if not self.handle_pin_entry(password):
                        logging.error("PIN entry failed")
                        return False
                        
                elif current_step == "verification_method":
                    if not self.handle_verification_method_selection():
                        logging.error("Verification method selection failed")
                        return False
                        
                elif current_step == "2fa_code":
                    if not self.handle_2fa_code_entry():
                        logging.error("2FA code entry failed")
                        return False
                        
                elif current_step == "captcha":
                    if not self.handle_captcha():
                        logging.error("Captcha handling failed")
                        return False
                        
                elif current_step == "success":
                    logging.info("Authentication completed successfully!")
                    return True
                    
                elif current_step == "unknown":
                    logging.warning(f"Unknown authentication step detected on attempt {attempt}")
                    # Log current page details for debugging
                    self.log_current_page_details()
                    
                    # Wait a bit and try again
                    time.sleep(5)
                    
                    # If we've been stuck on unknown for too long, fail
                    if step_retry_count.get("unknown", 0) >= 3:
                        logging.error("Too many unknown steps, authentication failed")
                        return False
                
                # Wait between steps
                time.sleep(3)
            
            logging.error(f"Authentication failed after {max_attempts} attempts")
            return False
            
        except Exception as e:
            logging.error(f"Multi-step authentication failed: {e}")
            return False

    def detect_current_step(self) -> str:
        """Detect which step of the authentication process we're currently on."""
        try:
            current_url = self.page.url.lower()
            page_text = self.page.inner_text('body').lower()
            
            # Check for PIN entry page
            pin_indicators = [
                'enter your personal pin',
                'personal pin',
                'input[placeholder*="pin"]',
                'input[name*="pin"]',
                'input[id*="pin"]'
            ]
            
            for indicator in pin_indicators:
                if indicator.startswith('input['):
                    # This is a selector
                    try:
                        element = self.page.query_selector(indicator)
                        if element and element.is_visible():
                            logging.info(f"PIN page detected via selector: {indicator}")
                            return "pin_entry"
                    except:
                        continue
                else:
                    # This is text to search for
                    if indicator in page_text:
                        logging.info(f"PIN page detected via text: {indicator}")
                        return "pin_entry"
            
            # Check for verification method selection (but be more specific)
            if 'where should we send your verification code' in page_text and 'email' in page_text:
                # Make sure we're not stuck in a loop
                send_button = self.page.query_selector('button:has-text("Send verification code")')
                if send_button and send_button.is_visible() and not send_button.is_disabled():
                    logging.info("Verification method page detected")
                    return "verification_method"
            
            # Check for 2FA code entry
            code_indicators = [
                'a verification code has been sent',
                'enter the verification code',
                'verification code sent to',
                'input[placeholder*="verification"]',
                'input[placeholder*="code"]'
            ]
            
            for indicator in code_indicators:
                if indicator.startswith('input['):
                    try:
                        element = self.page.query_selector(indicator)
                        if element and element.is_visible():
                            logging.info(f"2FA code page detected via selector: {indicator}")
                            return "2fa_code"
                    except:
                        continue
                else:
                    if indicator in page_text:
                        logging.info(f"2FA code page detected via text: {indicator}")
                        return "2fa_code"
            
            # Check for captcha (more comprehensive)
            captcha_indicators = [
                'img[src*="captcha"]',
                'img[alt*="captcha"]',
                '[class*="captcha"]',
                'enter the characters',
                'prove you are human',
                'select all images',
                'choose all',
                'let\'s confirm you are human'
            ]
            
            for indicator in captcha_indicators:
                if indicator.startswith(('img[', '[class')):
                    try:
                        element = self.page.query_selector(indicator)
                        if element and element.is_visible():
                            logging.info(f"Captcha detected via selector: {indicator}")
                            return "captcha"
                    except:
                        continue
                else:
                    if indicator in page_text:
                        logging.info(f"Captcha detected via text: {indicator}")
                        return "captcha"
            
            # Check for successful login (back to jobs site)
            if 'jobsatamazon' in current_url and 'login' not in current_url:
                return "success"
            
            # If we can't determine the step, return unknown
            return "unknown"
            
        except Exception as e:
            logging.error(f"Error detecting current step: {e}")
            return "unknown"

    def log_current_page_details(self):
        """Log current page details for debugging."""
        try:
            current_url = self.page.url
            page_title = self.page.title()
            page_text_snippet = self.page.inner_text('body')[:500]  # First 500 chars
            
            logging.info("=== CURRENT PAGE DETAILS ===")
            logging.info(f"URL: {current_url}")
            logging.info(f"Title: {page_title}")
            logging.info(f"Page text snippet: {page_text_snippet}")
            logging.info("============================")
            
        except Exception as e:
            logging.error(f"Failed to log page details: {e}")

    def handle_email_entry(self) -> bool:
        """Handle email entry step."""
        try:
            logging.info("Handling email entry step...")
            
            # Wait for page to load
            time.sleep(3)
            
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
                        email_field.fill(self.config['job_site_username'])
                        logging.info(f"Email filled with {selector}: {self.config['job_site_username']}")
                        email_filled = True
                        break
                except Exception as e:
                    logging.warning(f"Failed to fill email with {selector}: {e}")
                    continue
            
            if not email_filled:
                logging.error("No email field found or filled")
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
                        time.sleep(5)
                        logging.info(f"Clicked next button with selector: {selector}")
                        next_clicked = True
                        break
                except Exception as e:
                    logging.warning(f"Failed to click next with {selector}: {e}")
                    continue
            
            if not next_clicked:
                # Try pressing Enter key as alternative
                logging.info("No next button found, trying Enter key...")
                try:
                    self.page.keyboard.press('Enter')
                    time.sleep(5)
                    logging.info("Pressed Enter key as next")
                except Exception as e:
                    logging.warning(f"Failed to press Enter: {e}")
                    return False
            
            logging.info("Email entry step completed")
            return True
            
        except Exception as e:
            logging.error(f"Email entry step failed: {e}")
            return False

    def handle_pin_entry(self, password: str) -> bool:
        """Handle PIN entry step with improved detection."""
        try:
            logging.info("Handling PIN entry step...")
            
            # Wait for page to load
            time.sleep(3)
            
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
                            logging.info(f"Found PIN field with selector: {selector}")
                            break
                except:
                    continue
            
            if not pin_field:
                logging.error("No PIN field found")
                return False
            
            # Use the password as PIN (assuming it's the same)
            pin_field.fill(password)
            logging.info("PIN filled successfully")
            
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
                        time.sleep(5)
                        logging.info(f"Clicked next button after PIN entry: {selector}")
                        next_clicked = True
                        break
                except Exception as e:
                    continue
            
            if not next_clicked:
                # Try Enter key as fallback
                logging.info("No next button found, trying Enter key...")
                try:
                    self.page.keyboard.press('Enter')
                    time.sleep(5)
                    logging.info("Pressed Enter key after PIN entry")
                except Exception as e:
                    logging.warning(f"Failed to press Enter: {e}")
                    return False
            
            logging.info("PIN entry step completed")
            return True
            
        except Exception as e:
            logging.error(f"PIN entry step failed: {e}")
            return False

    def handle_verification_method_selection(self) -> bool:
        """Handle verification method selection (choose email)."""
        try:
            logging.info("Handling verification method selection...")
            
            # Wait for page to load
            time.sleep(3)
            
            # Check if we're actually on the verification method page
            page_text = self.page.inner_text('body').lower()
            if 'where should we send your verification code' not in page_text:
                logging.info("Not on verification method page, skipping...")
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
                                logging.info(f"Selected email verification option: {selector}")
                                email_selected = True
                                time.sleep(2)
                        else:
                            element.click()
                            logging.info(f"Selected email verification option: {selector}")
                            email_selected = True
                            time.sleep(2)
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
                        time.sleep(5)
                        logging.info(f"Clicked send verification code: {selector}")
                        send_clicked = True
                        break
                except Exception as e:
                    continue
            
            if not send_clicked:
                logging.warning("Could not find or click send verification code button")
                return False
            
            # Wait a bit longer to see if page changes
            time.sleep(10)
            
            # Check if we've moved to the next step
            new_page_text = self.page.inner_text('body').lower()
            if 'where should we send your verification code' not in new_page_text:
                logging.info("Successfully moved past verification method selection")
                return True
            else:
                logging.warning("Still on verification method page after clicking send")
                return False
            
        except Exception as e:
            logging.error(f"Verification method selection failed: {e}")
            return False

    def handle_2fa_code_entry(self) -> bool:
        """Handle 2FA verification code entry with manual intervention."""
        try:
            logging.info("Handling 2FA verification code entry...")
            
            # Wait for page to load
            time.sleep(3)
            
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
                        logging.info(f"Found 2FA code field with selector: {selector}")
                        break
                except:
                    continue
            
            if not code_field:
                logging.error("No 2FA code field found")
                return False
            
            # Check if email automation is configured and working
            email_config = self.config.get('email_automation', {})
            if email_config.get('enabled'):
                logging.info("Attempting automatic 2FA code retrieval...")
                verification_code = self.get_2fa_code_from_email()
                
                if verification_code:
                    # Fill the verification code automatically
                    code_field.fill(verification_code)
                    logging.info(f"Automatically filled 2FA code: {verification_code}")
                    
                    # Click next button
                    self.click_next_button()
                    return True
                else:
                    logging.warning("Automatic 2FA code retrieval failed, falling back to manual entry")
            
            # Manual intervention required
            logging.info("⚠️  MANUAL INTERVENTION REQUIRED: 2FA Code Entry")
            logging.info("📧 Please check your email for the verification code")
            logging.info("⏳ You have 120 seconds to:")
            logging.info("   1. Check your email for the Amazon verification code")
            logging.info("   2. Enter the code in the browser window")
            logging.info("   3. Click Next")
            
            # Wait for manual intervention
            time.sleep(120)
            
            # Check if the code was entered and we moved to next step
            current_url = self.page.url
            if 'verification' not in current_url.lower() and 'code' not in current_url.lower():
                logging.info("2FA code appears to have been successfully entered!")
                return True
            
            # Try to help with next button if still on verification page
            self.click_next_button()
            
            logging.info("2FA code entry step completed")
            return True
            
        except Exception as e:
            logging.error(f"2FA code entry failed: {e}")
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
                    time.sleep(5)
                    logging.info(f"Clicked next button: {selector}")
                    return True
            except:
                continue
        
        return False

    def handle_captcha(self) -> bool:
        """Handle captcha with manual intervention (realistic approach)."""
        try:
            logging.info("Captcha detected - requiring manual intervention")
            
            # Wait for captcha to load
            time.sleep(3)
            
            # Log what type of captcha we're dealing with
            captcha_info = self.analyze_captcha()
            
            logging.info("⚠️  MANUAL INTERVENTION REQUIRED: Captcha Solving")
            logging.info(f"🧩 Captcha type detected: {captcha_info}")
            logging.info("⏳ You have 180 seconds (3 minutes) to:")
            logging.info("   1. Solve the captcha in the browser window")
            logging.info("   2. Click submit/continue")
            logging.info("   3. Complete any additional verification steps")
            
            # Wait for manual captcha solving
            time.sleep(180)
            
            # Check if captcha was solved
            current_url = self.page.url
            page_text = self.page.inner_text('body').lower()
            
            if 'captcha' not in current_url.lower() and 'captcha' not in page_text:
                logging.info("Captcha appears to have been solved!")
                return True
            
            logging.info("Captcha handling completed (manual intervention)")
            return True
            
        except Exception as e:
            logging.error(f"Captcha handling failed: {e}")
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
            
            logging.info("Attempting to retrieve 2FA code from email...")
            
            # Check if email automation is configured
            email_config = self.config.get('email_automation', {})
            if not email_config.get('enabled'):
                logging.warning("Email automation not configured. Run setup_email_automation.py first.")
                return None
            
            # Get email credentials from configuration
            email_address = email_config.get('email_address', self.config['job_site_username'])
            
            try:
                from .security import decrypt
                email_password = decrypt(email_config['encrypted_app_password'], self.master_password)
                logging.info("Email app password decrypted successfully")
            except Exception as e:
                logging.error(f"Failed to decrypt email app password: {e}")
                return None
            
            # Gmail IMAP settings
            imap_server = "imap.gmail.com"
            imap_port = 993
            
            # Wait a bit for the email to arrive
            logging.info("Waiting 10 seconds for verification email to arrive...")
            time.sleep(10)
            
            # Connect to email
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
            
            try:
                mail.login(email_address, email_password)
                logging.info("Successfully connected to email account")
                
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
                                    
                                    logging.info(f"Checking email with subject: {email_subject}")
                                    
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
                                                    logging.info(f"Found verification code: {verification_code}")
                                                    break
                                        
                                        if verification_code:
                                            break
                                    
                                    if verification_code:
                                        break
                    except Exception as e:
                        logging.warning(f"Error searching with criteria '{criteria}': {e}")
                        continue
                
                mail.logout()
                
                if verification_code:
                    logging.info(f"Successfully retrieved 2FA code: {verification_code}")
                    return verification_code
                else:
                    logging.warning("No verification code found in recent emails")
                    # Try waiting a bit longer and search again
                    logging.info("Waiting additional 15 seconds for email...")
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
                                                logging.info(f"Found potential code in recent email: {match}")
                                                mail.logout()
                                                return match
                                except:
                                    continue
                        
                        mail.logout()
                    except:
                        pass
                    
                    return None
                    
            except Exception as e:
                logging.error(f"Email login failed: {e}")
                logging.info("Note: For Gmail, you need to enable 2FA and create an App Password")
                logging.info("Run: python setup_email_automation.py")
                return None
                
        except Exception as e:
            logging.error(f"Failed to retrieve 2FA code from email: {e}")
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
            logging.error(f"Error extracting email body: {e}")
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
                            logging.info(f"Found code on page: {match}")
                            return match
            
            return None
            
        except Exception as e:
            logging.error(f"Error extracting code from page: {e}")
            return None

    def search_jobs(self) -> bool:
        """Search for jobs based on profile criteria."""
        try:
            logging.info("Searching for jobs...")
            
            # Wait for page to load
            time.sleep(3)
            
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
                            logging.info(f"Filled search with keywords: {keywords}")
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
                            logging.info(f"Filled location: {location}")
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
                        time.sleep(5)
                        logging.info("Search submitted")
                        break
                except:
                    continue
            
            return True
            
        except Exception as e:
            logging.error(f"Job search failed: {e}")
            return False

    def extract_job_listings(self) -> list:
        """Extract job listings from the current page."""
        try:
            logging.info("Extracting job listings...")
            
            # Wait for results to load
            time.sleep(5)
            
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
                        logging.info(f"Found {len(job_elements)} job elements with selector: {selector}")
                        
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
                                    logging.warning(f"Error extracting job details: {e}")
                                    continue
                        
                        if jobs:
                            break  # Found jobs with this selector, stop trying others
                            
                except Exception as e:
                    logging.warning(f"Error with selector {selector}: {e}")
                    continue
            
            logging.info(f"Extracted {len(jobs)} job listings")
            return jobs
            
        except Exception as e:
            logging.error(f"Failed to extract job listings: {e}")
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
            logging.info("Browser session closed")
            
        except Exception as e:
            logging.error(f"Error closing browser session: {e}")

    def run_job_search_session(self) -> list:
        """Run a complete job search session."""
        try:
            # Start browser
            if not self.start_session():
                return []
            
            # Navigate to job search
            if not self.navigate_to_job_search():
                return []
            
            # Attempt login (optional)
            if self.config.get('job_site_username'):
                login_success = self.login()
                if login_success:
                    logging.info("Login successful")
                else:
                    logging.warning("Login failed, continuing without login")
            
            # Search for jobs
            if not self.search_jobs():
                logging.warning("Job search failed, trying to extract from current page")
            
            # Extract job listings
            jobs = self.extract_job_listings()
            
            return jobs
            
        except Exception as e:
            logging.error(f"Job search session failed: {e}")
            return []
            
        finally:
            self.close_session() 