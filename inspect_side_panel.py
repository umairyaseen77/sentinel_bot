#!/usr/bin/env python3
"""
Inspect side panel contents to find exact login element.
"""

import json
import time
from playwright.sync_api import sync_playwright

def inspect_side_panel():
    """Inspect exactly what's in the side panel."""
    
    print("🔍 Side Panel Inspector")
    print("=" * 30)
    
    # Load config
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    
    playwright = None
    browser = None
    page = None
    
    try:
        print("🚀 Opening browser with location permission denied...")
        playwright = sync_playwright().start()
        
        # Create context with no location permission (this solves location dialog)
        context = playwright.chromium.launch(headless=False).new_context(
            permissions=[],  # No permissions
            geolocation=None  # No location
        )
        page = context.new_page()
        
        page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        print("📂 Loading Amazon Jobs UK...")
        page.goto(profile['job_site_url'], wait_until="domcontentloaded")
        time.sleep(3)
        
        # Dismiss job alerts modal
        print("🔧 Dismissing job alerts...")
        page.keyboard.press('Escape')
        time.sleep(2)
        
        print("🔧 Opening hamburger menu...")
        page.click("body", position={"x": 32, "y": 100})
        time.sleep(3)
        
        input("👀 Can you see the side panel is open? Press Enter to inspect its contents...")
        
        print("🔍 DETAILED SIDE PANEL INSPECTION:")
        print("=" * 40)
        
        # Look for the side panel container
        try:
            # Common side panel selectors
            side_panel_selectors = [
                ".side-panel",
                ".sidebar", 
                ".nav-panel",
                ".menu-panel",
                "[role='navigation']",
                "nav",
                ".drawer",
                ".offcanvas"
            ]
            
            side_panel = None
            for selector in side_panel_selectors:
                try:
                    panel = page.query_selector(selector)
                    if panel and panel.is_visible():
                        side_panel = panel
                        print(f"  ✅ Found side panel: {selector}")
                        break
                except:
                    continue
            
            if not side_panel:
                print("  ⚠️ Specific side panel not found, checking all visible elements...")
                
            # Get all visible links and buttons
            all_links = page.query_selector_all("a")
            all_buttons = page.query_selector_all("button")
            
            visible_links = []
            visible_buttons = []
            
            print("\n📋 ALL VISIBLE LINKS:")
            for i, link in enumerate(all_links):
                try:
                    if link.is_visible():
                        text = link.inner_text().strip()
                        href = link.get_attribute('href') or ''
                        if text:  # Only show links with text
                            visible_links.append((text, href))
                            print(f"  {len(visible_links)}. '{text}' -> {href}")
                except:
                    continue
            
            print(f"\n📋 ALL VISIBLE BUTTONS:")
            for i, button in enumerate(all_buttons):
                try:
                    if button.is_visible():
                        text = button.inner_text().strip()
                        aria_label = button.get_attribute('aria-label') or ''
                        classes = button.get_attribute('class') or ''
                        if text or aria_label:  # Only show buttons with text or aria-label
                            visible_buttons.append((text, aria_label, classes))
                            print(f"  {len(visible_buttons)}. '{text}' (aria: '{aria_label}', classes: {classes[:50]})")
                except:
                    continue
            
            print(f"\n🔍 LOOKING FOR LOGIN/SIGN/ACCOUNT PATTERNS:")
            
            # Check for login patterns in links
            login_patterns = ['sign', 'login', 'account', 'user', 'profile', 'member']
            
            for pattern in login_patterns:
                matching_links = [link for link in visible_links if pattern.lower() in link[0].lower()]
                if matching_links:
                    print(f"\n  ✅ Links containing '{pattern}':")
                    for text, href in matching_links:
                        print(f"    📎 '{text}' -> {href}")
                
                matching_buttons = [btn for btn in visible_buttons if pattern.lower() in btn[0].lower() or pattern.lower() in btn[1].lower()]
                if matching_buttons:
                    print(f"\n  ✅ Buttons containing '{pattern}':")
                    for text, aria, classes in matching_buttons:
                        print(f"    🔘 '{text}' (aria: '{aria}')")
            
            # Check page text for any sign-in references
            print(f"\n🔍 SEARCHING PAGE TEXT for signin/login URLs:")
            try:
                page_content = page.content()
                login_urls = []
                
                # Look for Amazon sign-in URLs
                if 'signin' in page_content.lower():
                    lines = page_content.split('\n')
                    for line in lines:
                        if 'signin' in line.lower() and ('http' in line or 'href' in line):
                            login_urls.append(line.strip()[:100])
                
                if login_urls:
                    print("  ✅ Found potential login URLs in page source:")
                    for url in login_urls[:5]:  # Show first 5
                        print(f"    🔗 {url}")
                else:
                    print("  ❌ No signin URLs found in page source")
                    
            except Exception as e:
                print(f"  ❌ Error searching page content: {e}")
            
        except Exception as e:
            print(f"❌ Error inspecting side panel: {e}")
        
        print(f"\n📋 Current Status:")
        print(f"  📍 URL: {page.url}")
        print(f"  📄 Title: {page.title()}")
        
        input("👀 Based on the lists above, which element should we click for login? Press Enter to close...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if page and not page.is_closed():
            page.close()
        if 'context' in locals():
            context.close()
        if 'browser' in locals():
            browser.close()
        if playwright:
            playwright.stop()
        print("✅ Browser closed!")

if __name__ == "__main__":
    inspect_side_panel() 