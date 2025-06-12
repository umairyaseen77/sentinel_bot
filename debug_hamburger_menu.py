#!/usr/bin/env python3
"""
Debug hamburger menu to find proper way to open side panel with login options.
"""

import json
import time
import logging
from app.browser_actor import BrowserActor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_hamburger_menu():
    """Debug the hamburger menu opening."""
    
    print("🍔 Hamburger Menu Debugger")
    print("=" * 30)
    
    # Load profile
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False
    
    browser = BrowserActor(profile)
    
    try:
        # Start and navigate
        browser.start_session()
        browser.navigate_to_job_search()
        
        input("👀 Step 1: Ready to debug hamburger menu? Press Enter...")
        
        print("\n🔍 STEP 1: Looking for hamburger menu buttons...")
        
        # Check all the buttons we found
        hamburger_selectors = [
            "button:has-text('Open side menu')",
            "button[aria-label*='menu']",
            "button[aria-label*='Menu']",
            "button[aria-label*='navigation']",
            "button[aria-label*='open']",
            "button[class*='menu']",
            "button[class*='hamburger']",
            "button[class*='nav']",
            ".menu-toggle",
            ".hamburger",
            ".nav-toggle"
        ]
        
        for i, selector in enumerate(hamburger_selectors, 1):
            try:
                elements = browser.page.query_selector_all(selector)
                if elements:
                    print(f"  {i}. Found {len(elements)} elements with selector: {selector}")
                    for j, elem in enumerate(elements):
                        if elem.is_visible():
                            try:
                                text = elem.inner_text() or elem.get_attribute('aria-label') or ''
                                bound_box = elem.bounding_box()
                                coords = f"({int(bound_box['x'])}, {int(bound_box['y'])})" if bound_box else "unknown"
                                print(f"    Element {j+1}: '{text}' at {coords}")
                            except:
                                pass
            except:
                continue
        
        print("\n🔍 STEP 2: Trying coordinate click at (32, 100)...")
        browser.page.click("body", position={"x": 32, "y": 100})
        time.sleep(3)
        
        # Check if anything changed
        all_links_after = browser.page.query_selector_all('a')
        signin_links = [link for link in all_links_after if 'sign' in (link.inner_text() or '').lower()]
        
        print(f"Found {len(signin_links)} sign-in related links after coordinate click")
        for i, link in enumerate(signin_links):
            try:
                text = link.inner_text()
                href = link.get_attribute('href') or ''
                print(f"  {i+1}. '{text}' -> {href}")
            except:
                pass
        
        if not signin_links:
            print("❌ No sign-in links found. Let's try other approaches...")
            
            print("\n🔍 STEP 3: Trying to find menu button by screenshot position...")
            
            # Try clicking on different hamburger-like positions
            positions = [
                (20, 20),   # Top-left corner
                (30, 30),
                (40, 40),
                (50, 50),
                (20, 60),   # Slightly lower
                (60, 20),   # Slightly right
            ]
            
            for x, y in positions:
                print(f"\nTrying click at ({x}, {y})...")
                try:
                    browser.page.click("body", position={"x": x, "y": y})
                    time.sleep(2)
                    
                    # Check for new signin links
                    new_links = browser.page.query_selector_all('a')
                    new_signin = [link for link in new_links if 'sign' in (link.inner_text() or '').lower()]
                    
                    if new_signin:
                        print(f"  ✅ Success! Found {len(new_signin)} sign-in links after clicking ({x}, {y})")
                        for link in new_signin:
                            try:
                                text = link.inner_text()
                                href = link.get_attribute('href') or ''
                                print(f"    • '{text}' -> {href}")
                            except:
                                pass
                        break
                    else:
                        print(f"  ❌ No sign-in links found after clicking ({x}, {y})")
                        
                except Exception as e:
                    print(f"  ❌ Error clicking ({x}, {y}): {e}")
        
        input("\n👀 Step 4: Can you see the side panel with login options now? Press Enter...")
        
        print("\n🔍 STEP 4: Final check for all visible sign-in related elements...")
        
        # Final comprehensive check
        all_elements = browser.page.query_selector_all('*')
        signin_elements = []
        
        for elem in all_elements:
            try:
                if elem.is_visible():
                    text = elem.inner_text() or ''
                    if any(keyword in text.lower() for keyword in ['sign in', 'sign-in', 'signin', 'login', 'log in']):
                        tag = elem.evaluate("el => el.tagName")
                        href = elem.get_attribute('href') if tag == 'A' else ''
                        signin_elements.append((tag, text.strip(), href))
            except:
                continue
        
        if signin_elements:
            print(f"✅ Found {len(signin_elements)} sign-in related elements:")
            for i, (tag, text, href) in enumerate(signin_elements, 1):
                href_info = f" -> {href}" if href else ""
                print(f"  {i}. {tag}: '{text}'{href_info}")
        else:
            print("❌ No sign-in elements found anywhere on the page")
        
        input("\nPress Enter to close...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        browser.close_session()

if __name__ == "__main__":
    debug_hamburger_menu() 