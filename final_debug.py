#!/usr/bin/env python3
"""
Final targeted debugging for location dialog and hamburger menu inspection.
"""

import json
import time
from playwright.sync_api import sync_playwright

def final_debug():
    """Final debugging to solve remaining issues."""
    
    print("🎯 Final Debug: Location Dialog + Hamburger Menu")
    print("=" * 50)
    
    # Load config
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    
    playwright = None
    browser = None
    page = None
    
    try:
        print("🚀 Opening browser...")
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        print("📂 Loading Amazon Jobs UK...")
        page.goto(profile['job_site_url'], wait_until="domcontentloaded")
        time.sleep(3)
        
        # First dismiss job alerts modal with Escape (we know this works)
        print("🔧 Quick dismiss job alerts modal...")
        page.keyboard.press('Escape')
        time.sleep(2)
        
        input("👀 Step 1: Job alerts should be gone. Can you see the location dialog clearly? Press Enter...")
        
        print("🔍 INVESTIGATING: Location dialog in detail...")
        
        # Let's capture what the location dialog actually looks like
        try:
            # Get all buttons to see what's actually there
            all_buttons = page.query_selector_all("button")
            print(f"Found {len(all_buttons)} buttons on page:")
            
            for i, btn in enumerate(all_buttons[:15]):  # Check first 15 buttons
                try:
                    if btn.is_visible():
                        text = btn.inner_text() or btn.get_attribute('aria-label') or btn.get_attribute('title') or ''
                        classes = btn.get_attribute('class') or ''
                        print(f"  Button {i+1}: '{text}' (classes: {classes[:50]})")
                except:
                    continue
                    
        except Exception as e:
            print(f"Error investigating buttons: {e}")
        
        print("\n🔍 Looking for location-specific elements...")
        
        location_keywords = ['location', 'Location', 'Never allow', 'Allow', 'Block', 'close', 'Close', 'dismiss', 'Dismiss']
        
        for keyword in location_keywords:
            try:
                elements = page.query_selector_all(f"*:has-text('{keyword}')")
                visible_elements = [el for el in elements if el.is_visible()]
                if visible_elements:
                    print(f"  Found {len(visible_elements)} elements with text '{keyword}'")
                    for el in visible_elements[:3]:  # Show first 3
                        try:
                            tag = el.evaluate("el => el.tagName")
                            text = el.inner_text()[:50]
                            print(f"    {tag}: '{text}'")
                        except:
                            pass
            except:
                continue
        
        input("👀 Step 2: Based on the button list above, which button should we click for location? Press Enter...")
        
        print("🔧 TRYING DIFFERENT APPROACHES to dismiss location dialog...")
        
        # Approach 1: Try to find and click specific location buttons
        location_approaches = [
            # Direct text matches
            ("button:has-text('Never allow')", "Never allow button"),
            ("button:has-text('Block')", "Block button"),
            ("button:has-text('Allow this time')", "Allow this time button"),
            
            # Look for close/dismiss patterns
            ("button[aria-label*='close']", "Close button by aria-label"),
            ("button[title*='close']", "Close button by title"),
            ("button[class*='close']", "Close button by class"),
            
            # Try notification/permission patterns
            ("button[class*='notification']", "Notification button"),
            ("button[class*='permission']", "Permission button"),
            ("button[class*='banner']", "Banner button"),
            
            # Generic patterns
            (".close", "Generic close class"),
            ("[data-dismiss]", "Data dismiss attribute"),
        ]
        
        for selector, description in location_approaches:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    print(f"  ✅ Trying {description}: {selector}")
                    element.click()
                    time.sleep(2)
                    
                    # Check if it worked
                    input(f"Did clicking '{description}' dismiss the location dialog? Press Enter...")
                    break
            except:
                continue
        else:
            print("  ⚠️ No location dialog dismiss button found with standard selectors")
            
            # Try browser permission API
            print("  🔄 Trying to deny browser location permission...")
            try:
                # Deny location permission at browser level
                context = browser.new_context(
                    permissions=[],  # No permissions
                    geolocation=None  # No location
                )
                page2 = context.new_page()
                page2.goto(profile['job_site_url'])
                page2.keyboard.press('Escape')
                time.sleep(2)
                print("  ✅ Created new page with denied location permission")
                page.close()
                page = page2
            except Exception as e:
                print(f"  ❌ Browser permission approach failed: {e}")
        
        input("👀 Step 3: Is location dialog finally gone? Press Enter to continue to hamburger menu...")
        
        print("🔧 HAMBURGER MENU: Clicking and inspecting what opens...")
        
        # Click hamburger menu (we know coordinate click works)
        page.click("body", position={"x": 32, "y": 100})
        time.sleep(3)
        print("  ✅ Clicked hamburger menu at coordinates (32, 100)")
        
        # Now inspect what opened
        print("\n🔍 INSPECTING: What appeared after hamburger click...")
        
        try:
            # Look for new elements that might have appeared
            all_links = page.query_selector_all("a")
            all_buttons = page.query_selector_all("button")
            
            print(f"Found {len(all_links)} links and {len(all_buttons)} buttons")
            
            # Look specifically for login-related text
            login_keywords = ['sign', 'Sign', 'login', 'Login', 'account', 'Account', 'profile', 'Profile']
            
            print("\n🔍 Checking for login-related elements:")
            for keyword in login_keywords:
                try:
                    matching_elements = page.query_selector_all(f"*:has-text('{keyword}')")
                    visible_matches = []
                    
                    for el in matching_elements:
                        if el.is_visible():
                            try:
                                text = el.inner_text()
                                tag = el.evaluate("el => el.tagName")
                                href = el.get_attribute('href') if tag == 'A' else ''
                                visible_matches.append((tag, text, href))
                            except:
                                pass
                    
                    if visible_matches:
                        print(f"  Keyword '{keyword}' found in {len(visible_matches)} visible elements:")
                        for tag, text, href in visible_matches[:3]:  # Show first 3
                            href_info = f" (href: {href[:50]})" if href else ""
                            print(f"    {tag}: '{text[:50]}'{href_info}")
                            
                except:
                    continue
                    
        except Exception as e:
            print(f"Error inspecting elements: {e}")
        
        print(f"\n📋 Current State:")
        print(f"  📍 URL: {page.url}")
        print(f"  📄 Title: {page.title()}")
        
        input("👀 FINAL: What login options do you see now? Press Enter to close...")
        
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
    final_debug() 