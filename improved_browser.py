#!/usr/bin/env python3
"""
Improved browser automation based on live debugging results.
"""

import json
import time
from playwright.sync_api import sync_playwright

def improved_automation():
    """Improved automation based on debugging findings."""
    
    print("🚀 Improved Amazon Jobs UK Automation")
    print("=" * 45)
    
    # Load config
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    
    playwright = None
    browser = None
    page = None
    
    try:
        print("🌐 Opening browser...")
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Set user agent
        page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        print("📂 Navigating to Amazon Jobs UK...")
        page.goto(profile['job_site_url'], wait_until="domcontentloaded")
        time.sleep(3)
        
        print("🔧 Step 1: Handle location warning banner...")
        # Handle the location warning banner - look for "Close banner"
        try:
            close_banner_selectors = [
                "button:has-text('Close banner')",
                "[aria-label*='close banner']",
                "[aria-label*='Close banner']",
                "button[aria-label*='close']"
            ]
            
            for selector in close_banner_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        print(f"  ✅ Closing location banner with: {selector}")
                        element.click()
                        time.sleep(2)
                        break
                except:
                    continue
            else:
                print("  ⚠️ Location banner close button not found")
                
        except Exception as e:
            print(f"  ❌ Error handling location banner: {e}")
        
        print("🔧 Step 2: Handle job alerts signup modal...")
        # Handle job alerts modal - look for X button or modal dismissal
        try:
            # Try various ways to close the job alerts modal
            modal_close_selectors = [
                "button[aria-label='close']",
                "button[aria-label='Close']",
                "[data-dismiss='modal']",
                "button.close",
                ".modal-close",
                "button[type='button'][aria-label*='close']",
                # Try clicking outside the modal
                ".modal-backdrop",
                # Look for specific close text
                "button:has-text('×')",
                "button[title='Close']"
            ]
            
            for selector in modal_close_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        print(f"  ✅ Closing job alerts modal with: {selector}")
                        element.click()
                        time.sleep(2)
                        break
                except:
                    continue
            else:
                print("  ⚠️ Job alerts modal close button not found")
                # Try pressing Escape key as alternative
                try:
                    print("  🔄 Trying Escape key to close modal...")
                    page.keyboard.press('Escape')
                    time.sleep(2)
                except:
                    pass
                    
        except Exception as e:
            print(f"  ❌ Error handling job alerts modal: {e}")
        
        print("🔧 Step 3: Accept cookies...")
        # Handle cookies
        try:
            cookie_selectors = [
                "button:has-text('Accept all')",
                "button:has-text('Accept All')",
                "#onetrust-accept-btn-handler"
            ]
            
            for selector in cookie_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        print(f"  ✅ Accepting cookies with: {selector}")
                        element.click()
                        time.sleep(2)
                        break
                except:
                    continue
                    
        except Exception as e:
            print(f"  ❌ Error handling cookies: {e}")
        
        input("👀 CHECKPOINT: Are the dialogs now dismissed? Press Enter to continue...")
        
        print("🔧 Step 4: Click hamburger menu (Open side menu)...")
        # Click the hamburger menu that was found at (32, 0)
        try:
            hamburger_selectors = [
                "button:has-text('Open side menu.')",
                "[aria-label*='menu']",
                ".hamburger",
                ".menu-toggle", 
                "button[aria-label*='Open menu']",
                "button[aria-label*='Menu']"
            ]
            
            for selector in hamburger_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        print(f"  ✅ Clicking hamburger menu with: {selector}")
                        element.click()
                        time.sleep(3)
                        break
                except:
                    continue
            else:
                print("  ⚠️ Hamburger menu not found, trying coordinate click...")
                # Try clicking at the coordinates we found (32, 0)
                try:
                    page.click("body", position={"x": 32, "y": 100})  # Slightly lower than 0
                    time.sleep(3)
                    print("  ✅ Clicked at hamburger menu coordinates")
                except:
                    print("  ❌ Coordinate click failed")
                    
        except Exception as e:
            print(f"  ❌ Error clicking hamburger menu: {e}")
        
        input("👀 CHECKPOINT: Did the side menu open? Can you see login options now? Press Enter to continue...")
        
        print("🔧 Step 5: Look for login options in side menu...")
        # Look for login options that should now be visible
        try:
            login_selectors = [
                "a:has-text('Sign in')",
                "a:has-text('Sign In')",
                "button:has-text('Sign in')",
                "button:has-text('Sign In')",
                "a:has-text('Login')",
                "button:has-text('Login')",
                "[href*='signin']",
                "[href*='login']",
                ".sign-in",
                ".login"
            ]
            
            found_login = False
            for selector in login_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        if element.is_visible():
                            text = element.inner_text() or element.get_attribute('aria-label') or ''
                            print(f"  ✅ Found login option: {selector} - '{text}'")
                            
                            # Try clicking the first visible login option
                            if not found_login:
                                print(f"  🔄 Clicking login option...")
                                element.click()
                                time.sleep(3)
                                found_login = True
                                break
                except:
                    continue
                    
            if not found_login:
                print("  ❌ No login options found in side menu")
                
        except Exception as e:
            print(f"  ❌ Error looking for login options: {e}")
        
        print(f"\n📋 Final Status:")
        print(f"  📍 Current URL: {page.url}")
        print(f"  📄 Page title: {page.title()}")
        
        input("👀 FINAL: What do you see now? Press Enter to close...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if page and not page.is_closed():
            page.close()
        if browser and browser.is_connected():
            browser.close()
        if playwright:
            playwright.stop()
        print("✅ Browser closed!")

if __name__ == "__main__":
    improved_automation() 