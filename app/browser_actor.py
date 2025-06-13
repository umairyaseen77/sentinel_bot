from playwright.sync_api import sync_playwright, Browser, Page, Playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus # Added quote_plus for URL encoding keywords
import re # For identify_page_type
from .logger import log
# from .authenticator import get_2fa_code
from .security import decrypt
import time
# import logging

class BrowserActor:
    """Manages all browser interactions using Playwright."""

    # Page Type Constants
    PAGE_TYPE_UNKNOWN = "UNKNOWN"
    PAGE_TYPE_LOGIN_EMAIL = "LOGIN_EMAIL"
    PAGE_TYPE_LOGIN_PASSWORD = "LOGIN_PASSWORD"
    PAGE_TYPE_LOGIN_PIN = "LOGIN_PIN"
    PAGE_TYPE_OTP_VERIFICATION = "OTP_VERIFICATION"
    PAGE_TYPE_CAPTCHA = "CAPTCHA"
    PAGE_TYPE_SEARCH_RESULTS = "SEARCH_RESULTS"
    PAGE_TYPE_JOB_DETAILS = "JOB_DETAILS" # For future
    PAGE_TYPE_COOKIE_MODAL = "COOKIE_MODAL"
    PAGE_TYPE_POPUP_MODAL = "POPUP_MODAL" # General popup
    PAGE_TYPE_LANDING_OR_HOME = "LANDING_OR_HOME"
    PAGE_TYPE_ACCESS_DENIED = "ACCESS_DENIED"

    def __init__(self, config: dict, master_password: str = None):
        self.config = config
        self.master_password = master_password
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self.context = None
        self.session_active = False
        self.page_type_handlers = {
            self.PAGE_TYPE_COOKIE_MODAL: self._handle_cookie_modal_generic,
            # self.PAGE_TYPE_CAPTCHA: self.handle_captcha, # Example for future
        }

    def _handle_cookie_modal_generic(self) -> bool:
        log.info("Checking for generic cookie modal...")
        job_site_type = self.config.get('job_site_type', 'amazon')
        site_config_name = f"{job_site_type}_config"

        site_specific_config = self.config.get(site_config_name, {})
        if not site_specific_config and job_site_type == 'amazon': # Fallback for Amazon's old structure
            site_specific_config = self.config

        cookie_selectors = site_specific_config.get('cookie_modal_selectors', [])

        if not cookie_selectors:
            log.debug(f"No 'cookie_modal_selectors' defined for site_type '{job_site_type}'.")
            # Special fallback for Amazon if old handle_cookies is still around and no selectors are configured
            if job_site_type == 'amazon' and hasattr(self, 'handle_cookies') and callable(getattr(self, 'handle_cookies')):
                 log.info("No specific cookie selectors for Amazon, attempting old handle_cookies().")
                 return self.handle_cookies() # Call existing method
            return False

        for selector in cookie_selectors:
            try:
                element = self.page.locator(selector).first # Use .first to be safe
                if element.is_visible(timeout=2000): # Short timeout to check
                    log.info(f"Found and clicking cookie modal element: {selector}")
                    element.click(timeout=3000)
                    self.page.wait_for_timeout(1000) # Wait for action to complete
                    log.info(f"Cookie modal handled by selector: {selector}")
                    return True
            except Exception as e:
                log.debug(f"Cookie selector {selector} not found or action failed: {e}")
                continue
        log.info("No configured cookie modal elements found or handled by generic handler.")
        return False

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

    # def handle_cookies(self): # Commented out - Replaced by _handle_cookie_modal_generic and dispatcher
    #     """Handle cookie consent dialogs."""
    #     try:
    #         cookie_selectors = [
    #             "button:has-text('Accept all')",
    #             "button:has-text('Accept All')",
    #             "button:has-text('Accept cookies')",
    #             "button:has-text('Accept Cookies')",
    #             "#onetrust-accept-btn-handler",
    #             "[data-test='accept-cookies']",
    #             ".cookie-accept",
    #             "button[id*='accept']"
    #         ]

    #         for selector in cookie_selectors:
    #             try:
    #                 element = self.page.query_selector(selector)
    #                 if element and element.is_visible():
    #                     log.info(f"Accepting cookies with: {selector}")
    #                     element.click()
    #                     self.page.wait_for_timeout(1000)
    #                     return True
    #             except:
    #                 continue

    #     except Exception as e:
    #         log.warning(f"Cookie handling failed: {e}")

    #     return False

    def navigate_to_job_search(self) -> bool: # Amazon specific navigation
        """Navigate to the Amazon job search area."""
        try:
            # Amazon Jobs UK loads on main page first
            job_site_url = self.config.get('job_site_url')
            if not job_site_url:
                log.error("job_site_url not found in config for Amazon navigation.")
                return False
            log.info(f"Navigating to Amazon main site: {job_site_url}")
            
            self.page.goto(job_site_url, wait_until="domcontentloaded", timeout=10000)
            
            # Handle popups first (Amazon specific)
            if not self.handle_popups():
                log.warning("Amazon popup handling had issues, continuing...")
            
            # Navigate to actual job search page
            target_url = job_site_url.rstrip('/') + '/app#/jobSearch'
            log.info(f"Navigating to Amazon job search page: {target_url}")
            self.page.goto(target_url, wait_until="domcontentloaded", timeout=10000)
            self.page.wait_for_load_state('domcontentloaded', timeout=5000)

            page_type = self.identify_page_type()
            expected_types = [self.PAGE_TYPE_SEARCH_RESULTS, self.PAGE_TYPE_LANDING_OR_HOME, self.PAGE_TYPE_UNKNOWN]
            if page_type not in expected_types:
                log.warning(f"Navigated to Amazon job search, but page type is '{page_type}', not one of {expected_types}. URL: {self.page.url}")
            elif page_type == self.PAGE_TYPE_UNKNOWN:
                 log.info(f"Page type for Amazon job search page is UNKNOWN. URL: {self.page.url}. Proceeding with legacy interaction; consider defining page_signatures.")
            else:
                 log.info(f"Successfully landed on Amazon job search. Page type: {page_type}. URL: {self.page.url}")

            log.info("Checking for cookies on Amazon job search page...")
            self.handle_cookies()
            
            log.info("Dismissing potential job alerts modal on Amazon job search page (second pass)...")
            self.page.keyboard.press('Escape')
            self.page.wait_for_timeout(1000) # Shortened wait
            
            return True
            
        except Exception as e:
            log.error(f"Failed to navigate to Amazon job search: {e}", exc_info=True)
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
            current_page_type = self.identify_page_type()
            log.info(f"Landed on page type: {current_page_type} after clicking sign-in.")
            # Expecting PAGE_TYPE_LOGIN_EMAIL or similar.
            if current_page_type not in [self.PAGE_TYPE_LOGIN_EMAIL, self.PAGE_TYPE_LOGIN_PASSWORD, self.PAGE_TYPE_LOGIN_PIN, self.PAGE_TYPE_OTP_VERIFICATION, self.PAGE_TYPE_CAPTCHA]:
                log.warning(f"Initial page after sign-in click is '{current_page_type}', expected a login page type. Proceeding to multi-step auth, which will handle the current page.")

            return self.perform_multi_step_authentication()
                
        except Exception as e:
            log.error(f"Login failed: {e}", exc_info=True) # Added exc_info for more details
            return False

    def perform_multi_step_authentication(self) -> bool:
        """Perform multi-step Amazon authentication using identified page types."""
        try:
            log.info("Starting multi-step authentication flow using identify_page_type().")
            
            encrypted_password = self.config.get('amazon_password')
            if not encrypted_password:
                log.error("Amazon password not found in configuration for multi-step auth.")
                return False

            password = decrypt(encrypted_password, self.master_password)
            if not password:
                log.error("Failed to decrypt Amazon password for multi-step auth.")
                return False
            log.info("Password decrypted successfully for multi-step auth.")

            # The first step (e.g., email entry) is assumed to have been triggered by login()
            # and perform_multi_step_authentication is called when we are on the page *after* initial email/user submission.
            # Or, if identify_page_type() identifies PAGE_TYPE_LOGIN_EMAIL here, handle_email_entry could be called.

            max_attempts = 10
            attempt = 0
            previous_page_type_for_stuck_detection = None
            page_type_retry_count = {}

            while attempt < max_attempts:
                attempt += 1
                current_page_type = self.identify_page_type()
                log.info(f"Auth Attempt {attempt}/{max_attempts}: Current page type identified as '{current_page_type}'. URL: {self.page.url}")

                if current_page_type == previous_page_type_for_stuck_detection and \
                   current_page_type != self.PAGE_TYPE_UNKNOWN: # Avoid getting stuck on UNKNOWN if signatures are missing
                    page_type_retry_count[current_page_type] = page_type_retry_count.get(current_page_type, 0) + 1
                    if page_type_retry_count[current_page_type] >= 3:
                        log.warning(f"Stuck on page type '{current_page_type}' for {page_type_retry_count[current_page_type]} attempts.")
                        # Specific break-out logic could be added here if needed, e.g., for OTP_VERIFICATION
                        # For now, general failure if stuck too long.
                        log.error(f"Authentication failed: Stuck on page type '{current_page_type}'.")
                        return False
                else:
                    page_type_retry_count = {current_page_type: 1} # Reset counter for the current type

                previous_page_type_for_stuck_detection = current_page_type

                action_taken_this_step = False
                if current_page_type == self.PAGE_TYPE_LOGIN_EMAIL:
                    log.info("Currently on LOGIN_EMAIL page. Attempting to handle email entry.")
                    if not self.handle_email_entry(): return False
                    action_taken_this_step = True
                elif current_page_type == self.PAGE_TYPE_LOGIN_PIN:
                    log.info("Currently on LOGIN_PIN page. Attempting to handle PIN entry.")
                    if not self.handle_pin_entry(password): return False
                    action_taken_this_step = True
                elif current_page_type == self.PAGE_TYPE_OTP_VERIFICATION:
                    log.info("Currently on OTP_VERIFICATION page. Attempting to handle 2FA code entry/selection.")
                    # This might internally handle method selection then code entry.
                    if not self.handle_2fa_code_entry(): return False
                    action_taken_this_step = True
                elif current_page_type == self.PAGE_TYPE_CAPTCHA:
                    log.info("Currently on CAPTCHA page. Attempting to handle CAPTCHA.")
                    if not self.handle_captcha(): return False
                    action_taken_this_step = True
                elif current_page_type == self.PAGE_TYPE_SEARCH_RESULTS or \
                     current_page_type == self.PAGE_TYPE_LANDING_OR_HOME:
                    log.info(f"Authentication successful: Landed on page type '{current_page_type}'.")
                    return True
                elif current_page_type == self.PAGE_TYPE_UNKNOWN:
                    log.warning(f"Unknown page type detected (attempt {attempt}). Logging details and waiting.")
                    self.log_current_page_details()
                    # Specific stuck detection for UNKNOWN state
                    page_type_retry_count[self.PAGE_TYPE_UNKNOWN] = page_type_retry_count.get(self.PAGE_TYPE_UNKNOWN, 0) + 1
                    if page_type_retry_count.get(self.PAGE_TYPE_UNKNOWN, 0) >= 3:
                         log.error("Too many consecutive UNKNOWN page types. Authentication failed.")
                         return False
                    self.page.wait_for_timeout(5000) # Wait before next poll if unknown
                    action_taken_this_step = True # Consumed an attempt by waiting
                else: # An unexpected but known page type encountered
                    log.warning(f"Unexpected page type '{current_page_type}' during auth flow (attempt {attempt}). Waiting.")
                    self.log_current_page_details()
                    self.page.wait_for_timeout(5000) # Wait
                    action_taken_this_step = True # Consumed an attempt

                # If an action was taken (handler called or waited for UNKNOWN),
                # a page transition is expected. We might not need an additional generic wait.
                # If no specific action was taken (e.g. unexpected known page type), a small wait is good.
                if action_taken_this_step and current_page_type not in [self.PAGE_TYPE_SEARCH_RESULTS, self.PAGE_TYPE_LANDING_OR_HOME]:
                     log.debug(f"Action taken for {current_page_type}, will re-identify page type in next iteration.")
                     # self.page.wait_for_timeout(1000) # Optional short wait for page to settle after action
                elif not action_taken_this_step: # Should not happen if all types are handled
                     log.error(f"No action defined for page type {current_page_type}. Auth flow stuck.")
                     return False


            log.error(f"Authentication failed after {max_attempts} attempts (exceeded max attempts).")
            return False
            
        except Exception as e:
            log.error(f"An unexpected error occurred in perform_multi_step_authentication: {e}", exc_info=True)
            return False

    def identify_page_type(self, default_timeout: int = 1000) -> str:
        current_url = ""
        try:
            current_url = self.page.url.lower()
        except Exception as e:
            log.warning(f"Could not get current URL in identify_page_type: {e}")
            return self.PAGE_TYPE_UNKNOWN # Cannot do much without URL

        job_site_type = self.config.get('job_site_type', 'amazon') # Default to amazon
        site_config_name = f"{job_site_type}_config"
        site_specific_config = self.config.get(site_config_name, {})

        # Fallback for Amazon if no explicit 'amazon_config' section exists yet
        if not site_specific_config and job_site_type == 'amazon' and 'job_site_url' in self.config:
            log.debug(f"Using root config for Amazon as '{site_config_name}' not found.")
            site_specific_config = self.config

        if not site_specific_config:
            log.warning(f"No specific config found for job_site_type '{job_site_type}' (expected key: {site_config_name} or root config for amazon).")
            return self.PAGE_TYPE_UNKNOWN

        page_signatures = site_specific_config.get('page_signatures', [])
        if not page_signatures:
            log.debug(f"No page_signatures defined for site type '{job_site_type}'.")
            return self.PAGE_TYPE_UNKNOWN

        # Separate modal and page signatures
        modal_signatures = [s for s in page_signatures if s.get('is_modal', False)]
        regular_page_signatures = [s for s in page_signatures if not s.get('is_modal', False)]

        # 1. Check Modals First
        for signature in modal_signatures:
            page_type = signature.get('page_type', self.PAGE_TYPE_UNKNOWN)
            rules_matched = 0
            rules_defined = 0

            # URL Checks
            if 'url_matches' in signature:
                rules_defined += 1
                if re.search(signature['url_matches'], current_url):
                    rules_matched += 1
                else: continue
            if 'url_contains' in signature:
                rules_defined += 1
                if all(sub_str.lower() in current_url for sub_str in signature['url_contains']):
                    rules_matched += 1
                else: continue
            if 'url_query_param_exists' in signature:
                rules_defined += 1
                parsed_url = urlparse(current_url)
                query_params = set(parsed_url.query.split('&')) if parsed_url.query else set()
                actual_params = {p.split('=')[0] for p in query_params}
                if all(param_name in actual_params for param_name in signature['url_query_param_exists']):
                    rules_matched +=1
                else: continue

            # Element Exists Check
            if 'element_exists' in signature:
                rules_defined += 1
                found_element = False
                for selector in signature['element_exists']:
                    try:
                        if self.page.locator(selector).is_visible(timeout=default_timeout):
                            found_element = True
                            break
                    except Exception: continue
                if found_element: rules_matched += 1
                else: continue

            # Text Contains Check
            if 'text_contains' in signature:
                rules_defined += 1
                try:
                    body_text = self.page.locator('body').text_content(timeout=default_timeout).lower()
                    if all(text_snippet.lower() in body_text for text_snippet in signature['text_contains']):
                        rules_matched += 1
                    else: continue
                except Exception: continue

            # Element Has Text Check
            if 'element_has_text' in signature:
                rules_defined +=1
                all_elements_have_text = True
                for item in signature['element_has_text']:
                    try:
                        elem_text = self.page.locator(item['selector']).text_content(timeout=default_timeout)
                        if item['text'].lower() not in elem_text.lower():
                            all_elements_have_text = False
                            break
                    except Exception:
                        all_elements_have_text = False
                        break
                if all_elements_have_text: rules_matched += 1
                else: continue

            if rules_defined > 0 and rules_matched == rules_defined:
                log.info(f"Modal page type detected: {page_type} for {current_url}")
                return page_type

        # 2. Check Regular Pages if no modal matched
        for signature in regular_page_signatures:
            page_type = signature.get('page_type', self.PAGE_TYPE_UNKNOWN)
            rules_matched = 0
            rules_defined = 0
            # URL Checks
            if 'url_matches' in signature:
                rules_defined += 1
                if re.search(signature['url_matches'], current_url): rules_matched += 1
                else: continue
            if 'url_contains' in signature:
                rules_defined += 1
                if all(sub_str.lower() in current_url for sub_str in signature['url_contains']): rules_matched += 1
                else: continue
            if 'url_query_param_exists' in signature:
                rules_defined += 1
                parsed_url = urlparse(current_url)
                query_params = set(parsed_url.query.split('&')) if parsed_url.query else set()
                actual_params = {p.split('=')[0] for p in query_params}
                if all(param_name in actual_params for param_name in signature['url_query_param_exists']): rules_matched +=1
                else: continue
            # Element Exists
            if 'element_exists' in signature:
                rules_defined += 1
                found_element = False
                for selector in signature['element_exists']:
                    try:
                        if self.page.locator(selector).is_visible(timeout=default_timeout):
                            found_element = True
                            break
                    except Exception: continue
                if found_element: rules_matched += 1
                else: continue
            # Text Contains
            if 'text_contains' in signature:
                rules_defined += 1
                try:
                    body_text = self.page.locator('body').text_content(timeout=default_timeout).lower()
                    if all(text_snippet.lower() in body_text for text_snippet in signature['text_contains']): rules_matched += 1
                    else: continue
                except Exception: continue
            # Element Has Text
            if 'element_has_text' in signature:
                rules_defined +=1
                all_elements_have_text = True
                for item in signature['element_has_text']:
                    try:
                        elem_text = self.page.locator(item['selector']).text_content(timeout=default_timeout)
                        if item['text'].lower() not in elem_text.lower():
                            all_elements_have_text = False; break
                    except Exception: all_elements_have_text = False; break
                if all_elements_have_text: rules_matched += 1
                else: continue

            if rules_defined > 0 and rules_matched == rules_defined:
                log.info(f"Page type detected: {page_type} for {current_url}")
                return page_type

        log.info(f"No specific page type detected for {current_url} using signatures. Returning UNKNOWN.")
        return self.PAGE_TYPE_UNKNOWN

    # def detect_current_step(self) -> str: # Marked for removal/replacement
    #     # This method is now specific to Amazon's multi-step authentication flow
    #     # and acts as a translator from the generic identify_page_type
    #     pass # To be removed or fully replaced by direct identify_page_type usage.

    def log_current_page_details(self):
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

    def extract_job_listings(self) -> list: # Amazon specific
        """Extract job listings from the current Amazon page."""
        try:
            log.info("Extracting job listings for Amazon...")
            current_page_type = self.identify_page_type()
            expected_types = [self.PAGE_TYPE_SEARCH_RESULTS, self.PAGE_TYPE_UNKNOWN] # UNKNOWN as fallback
            if current_page_type not in expected_types:
                log.error(f"Cannot extract Amazon jobs. Expected {expected_types}, got '{current_page_type}'. URL: {self.page.url}")
                return []
            if current_page_type == self.PAGE_TYPE_UNKNOWN:
                 log.warning(f"Amazon page type is UNKNOWN for extraction at {self.page.url}. Signatures may need update.")

            amazon_cfg = self.config.get('amazon_config', {})
            selectors = amazon_cfg.get('selectors', {})
            job_card_s = selectors.get('job_card', "div[class*='job-tile'], div.job") # More generic Amazon fallback
            title_s = selectors.get('title', "h3[class*='job-title']")
            company_s = selectors.get('company', "[class*='company-name']") # Often not present or fixed
            location_s = selectors.get('location', "[class*='job-location']")
            link_s = selectors.get('link', "a[class*='job-link']")

            log.info(f"Using Amazon job card selector: '{job_card_s}'")
            try:
                self.page.wait_for_selector(job_card_s, timeout=10000) # Increased timeout
            except Exception as e_wait:
                log.error(f"Failed to find Amazon job cards with '{job_card_s}': {e_wait}")
                if self.identify_page_type() == self.PAGE_TYPE_ACCESS_DENIED: log.error("Access denied on Amazon.")
                return []
            
            job_elements = self.page.locator(job_card_s).all()
            log.info(f"Found {len(job_elements)} potential Amazon job cards.")
            jobs = []
            base_url = self.config.get('job_site_url', "https://www.amazon.jobs")

            for element in job_elements:
                if not element.is_visible(timeout=200): continue # Skip non-visible cards quickly
                try:
                    title = element.locator(title_s).first.text_content(timeout=100).strip() if element.locator(title_s).count() > 0 else ""
                    # Amazon is usually the company, but if a selector is provided, use it.
                    company = "Amazon" # Default
                    if company_s and element.locator(company_s).count() > 0:
                        company_text = element.locator(company_s).first.text_content(timeout=100).strip()
                        if company_text : company = company_text # Override default if found

                    location = element.locator(location_s).first.text_content(timeout=100).strip() if element.locator(location_s).count() > 0 else ""
                    link_href = element.locator(link_s).first.get_attribute('href', timeout=100) if element.locator(link_s).count() > 0 else ""
                    link = urljoin(base_url, link_href) if link_href else ""

                    if title: # Consider title essential
                        jobs.append({'title': title, 'company': company, 'location': location, 'link': link,
                                     'description': f"{title} at {company} in {location}", # Simple description
                                     'source': 'Amazon'})
                    else:
                        log.debug(f"Skipping Amazon job card, title seems missing.")
                        
                except Exception as e_detail:
                    log.warning(f"Error extracting detail from an Amazon job card: {e_detail}")
            
            log.info(f"Extracted {len(jobs)} Amazon job listings.")
            return jobs
        except Exception as e:
            log.error(f"Failed to extract Amazon job listings: {e}", exc_info=True); return []

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

            # --- Start of new dispatcher block ---
            if self.page:
                try:
                    log.info("Running initial page type dispatch for common modals...")
                    # Allow up to 2 attempts to handle modals that might overlay each other or refresh the page
                    for attempt in range(2):
                        current_page_type = self.identify_page_type()
                        log.info(f"Dispatcher (attempt {attempt+1}): Identified page type: {current_page_type}")

                        if current_page_type in self.page_type_handlers:
                            handler = self.page_type_handlers[current_page_type]
                            log.info(f"Dispatcher: Found handler for {current_page_type}, executing...")
                            action_taken = handler()

                            if action_taken:
                                log.info(f"Dispatcher: Handler for {current_page_type} took action. Re-evaluating page if another attempt is left.")
                                if attempt == 1:
                                    current_page_type = self.identify_page_type()
                                    log.info(f"Dispatcher: Final page type after handling modal on last attempt: {current_page_type}")
                                # Loop will continue and re-identify if attempt < 1
                            else:
                                log.info(f"Dispatcher: Handler for {current_page_type} reported no action. Proceeding.")
                                break
                        else:
                            log.info(f"Dispatcher: No specific handler for page type {current_page_type}. Proceeding.")
                            break
                    log.info("Initial page type dispatch complete.")
                except Exception as e_dispatch:
                    log.error(f"Error during initial page type dispatch: {e_dispatch}", exc_info=True)
            else:
                log.error("Page object not available for initial dispatch in run_job_search_session. Critical failure.")
                return [] # Cannot proceed without a page
            # --- End of new dispatcher block ---

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
            
            # Specific Indeed cookie handling removed, should be handled by dispatcher
            # if PAGE_TYPE_COOKIE_MODAL is identified and configured for Indeed.

            # You might want to add a check here to ensure the page loaded correctly,
            # e.g., by looking for a known element on the search results page.
            # For PoC, we assume navigation is successful if no immediate error.
            page_type = self.identify_page_type()
            expected_types = [self.PAGE_TYPE_SEARCH_RESULTS, self.PAGE_TYPE_UNKNOWN] # UNKNOWN as fallback
            if page_type not in expected_types :
                 log.warning(f"Navigated to Indeed, but page type is '{page_type}', not one of {expected_types}. URL: {search_url}")
            elif page_type == self.PAGE_TYPE_UNKNOWN:
                log.info(f"Page type for Indeed job search is UNKNOWN. URL: {search_url}. Proceeding; consider defining page_signatures.")
            else:
                log.info(f"Successfully navigated to Indeed search results. Page type: {page_type}")
            
            return True
        except Exception as e:
            log.error(f"Failed to navigate to Indeed URL {search_url}: {e}", exc_info=True)
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

            current_page_type = self.identify_page_type()
            expected_types = [self.PAGE_TYPE_SEARCH_RESULTS, self.PAGE_TYPE_UNKNOWN]
            if current_page_type not in expected_types:
                log.error(f"Cannot extract Indeed jobs. Expected {expected_types}, got '{current_page_type}'. URL: {self.page.url}")
                return []
            if current_page_type == self.PAGE_TYPE_UNKNOWN:
                 log.warning(f"Indeed page type is UNKNOWN for extraction at {self.page.url}. Signatures may need update.")

            try:
                self.page.wait_for_selector(job_card_selector, timeout=10000)
            except Exception as e_wait:
                log.error(f"Failed to find Indeed job cards with '{job_card_selector}': {e_wait}")
                if self.identify_page_type() == self.PAGE_TYPE_ACCESS_DENIED: log.error("Access denied on Indeed.")
                return []

            log.info("Extracting Indeed job listings...")
            job_elements = self.page.locator(job_card_selector).all()
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