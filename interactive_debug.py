#!/usr/bin/env python3
"""
Interactive debugging script to see live browser action and understand the exact flow.
"""

import json
import time
from app.browser_actor import BrowserActor
from playwright.sync_api import sync_playwright

def interactive_debug():
    """Interactive debugging with live browser observation."""
    
    print("🔍 Interactive Amazon Jobs UK Debug Session")
    print("=" * 50)
    print("This script will open the browser and pause at each step")
    print("so we can see exactly what's happening and plan the automation.")
    print()
    
    # Load config
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False  # Always visible for debugging
    
    print(f"🌐 Target: {profile['job_site_url']}")
    print(f"👤 Username: {profile['job_site_username']}")
    print()
    
    playwright = None
    browser = None
    page = None
    
    try:
        print("🚀 STEP 1: Opening Amazon Jobs UK...")
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
        
        input("👀 PAUSE: Look at the browser window. Do you see any popups/dialogs? Press Enter when ready to continue...")
        
        print("\n🔍 STEP 2: Checking for dialogs...")
        
        # Check what dialogs are visible
        print("Looking for location permission dialog...")
        location_elements = page.query_selector_all("button:has-text('Never allow'), button:has-text('Allow this time'), button:has-text('Block')")
        if location_elements:
            print(f"  ✅ Found {len(location_elements)} location permission buttons")
            for i, elem in enumerate(location_elements):
                try:
                    text = elem.inner_text()
                    print(f"    Button {i+1}: '{text}'")
                except:
                    pass
        else:
            print("  ❌ No location permission dialog found")
        
        print("Looking for job alerts dialog...")
        alerts_elements = page.query_selector_all("button:has-text('Sign up for job alerts'), input[placeholder*='Email'], input[placeholder*='Postcode']")
        if alerts_elements:
            print(f"  ✅ Found {len(alerts_elements)} job alerts elements")
        else:
            print("  ❌ No job alerts dialog found")
        
        input("👀 PAUSE: Can you see both dialogs clearly? Press Enter to try handling them...")
        
        print("\n🔧 STEP 3: Handling dialogs...")
        
        # Handle location permission - click "Never allow"
        try:
            never_allow = page.query_selector("button:has-text('Never allow')")
            if never_allow and never_allow.is_visible():
                print("  🔄 Clicking 'Never allow' for location...")
                never_allow.click()
                time.sleep(2)
            else:
                print("  ⚠️ 'Never allow' button not found or not visible")
        except Exception as e:
            print(f"  ❌ Error with location dialog: {e}")
        
        # Handle job alerts dialog - look for close button or dismiss
        try:
            # Look for X button or close button
            close_buttons = page.query_selector_all("button[aria-label*='close'], button[aria-label*='Close'], button:has-text('×'), .close")
            if close_buttons:
                print(f"  🔄 Found {len(close_buttons)} close buttons, clicking first one...")
                close_buttons[0].click()
                time.sleep(2)
            else:
                print("  ⚠️ No close button found for job alerts dialog")
        except Exception as e:
            print(f"  ❌ Error with job alerts dialog: {e}")
        
        # Handle cookie consent if present
        try:
            accept_cookies = page.query_selector("button:has-text('Accept all')")
            if accept_cookies and accept_cookies.is_visible():
                print("  🔄 Accepting cookies...")
                accept_cookies.click()
                time.sleep(2)
        except Exception as e:
            print(f"  ❌ Error with cookies: {e}")
        
        input("👀 PAUSE: Are the dialogs now gone? Can you see the main page clearly? Press Enter to continue...")
        
        print("\n🔍 STEP 4: Looking for login options...")
        
        # Look for login elements in top left
        print("Searching for login elements in various locations...")
        
        login_selectors = [
            "button:has-text('Sign in')",
            "button:has-text('Sign In')",
            "button:has-text('Login')",
            "a:has-text('Sign in')",
            "a:has-text('Sign In')",
            "a:has-text('Login')",
            "[data-test*='sign-in']",
            "[aria-label*='sign']",
            ".sign-in",
            ".login"
        ]
        
        found_login_elements = []
        for selector in login_selectors:
            try:
                elements = page.query_selector_all(selector)
                for elem in elements:
                    if elem.is_visible():
                        try:
                            text = elem.inner_text() or elem.get_attribute('aria-label') or ''
                            bound_box = elem.bounding_box()
                            location = f"({int(bound_box['x'])}, {int(bound_box['y'])})" if bound_box else "unknown"
                            found_login_elements.append((selector, text, location))
                        except:
                            pass
            except:
                continue
        
        if found_login_elements:
            print("  ✅ Found potential login elements:")
            for i, (selector, text, location) in enumerate(found_login_elements, 1):
                print(f"    {i}. {selector} - '{text}' at {location}")
        else:
            print("  ❌ No obvious login elements found")
        
        print("\n🔍 Also checking top-left corner specifically...")
        
        # Check elements in top-left area (first 200x200 pixels)
        try:
            all_clickable = page.query_selector_all("button, a, [role='button']")
            top_left_elements = []
            
            for elem in all_clickable[:20]:  # Check first 20 clickable elements
                try:
                    if elem.is_visible():
                        bound_box = elem.bounding_box()
                        if bound_box and bound_box['x'] < 300 and bound_box['y'] < 300:  # Top-left area
                            text = elem.inner_text() or elem.get_attribute('aria-label') or elem.get_attribute('title') or ''
                            if text:
                                top_left_elements.append((text, int(bound_box['x']), int(bound_box['y'])))
                except:
                    continue
            
            if top_left_elements:
                print("  📍 Clickable elements in top-left area:")
                for text, x, y in top_left_elements[:10]:
                    print(f"    • '{text}' at ({x}, {y})")
            else:
                print("  ❌ No clickable elements found in top-left area")
                
        except Exception as e:
            print(f"  ❌ Error checking top-left area: {e}")
        
        input("👀 PAUSE: Can you see any login options? Where exactly is the login button/link? Press Enter when ready...")
        
        print("\n📋 STEP 5: Current page analysis...")
        print(f"  📍 Current URL: {page.url}")
        print(f"  📄 Page title: {page.title()}")
        
        # Get some page content to understand what we're looking at
        try:
            page_text = page.inner_text('body')
            lines = [line.strip() for line in page_text.split('\n') if line.strip() and len(line.strip()) > 5]
            print("  📝 First few lines of page content:")
            for line in lines[:10]:
                print(f"    {line}")
        except:
            print("  ❌ Could not get page content")
        
        print("\n✋ Debugging session complete!")
        print("Based on what you see in the browser, please tell me:")
        print("1. Are both dialogs now dismissed?")
        print("2. Where exactly is the login button/link?")
        print("3. What should the next steps be?")
        
        input("Press Enter to close the browser...")
        
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
    interactive_debug() 