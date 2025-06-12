#!/usr/bin/env python3
"""
Script to inspect Amazon Jobs UK website structure and find correct selectors.
"""

import json
import time
from app.browser_actor import BrowserActor

def inspect_amazon_structure():
    """Inspect the actual Amazon Jobs UK website."""
    
    print("🔍 Amazon Jobs UK - Structure Inspector")
    print("=" * 45)
    
    # Load config but override selectors for inspection
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False  # Visible browser
    
    browser = BrowserActor(profile)
    
    try:
        print("🚀 Opening Amazon Jobs UK...")
        success = browser.initialize_session()
        
        if success:
            print("✅ Website loaded!")
            print(f"📍 Current URL: {browser.page.url}")
            
            # Wait for page to fully load
            print("⏳ Waiting for page to fully load...")
            time.sleep(5)
            
            # Try to wait for React content to load
            print("⚛️  Waiting for React content...")
            browser.page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)
            
            # Check what's actually on the page
            print("\n🔍 Inspecting page structure...")
            
            # Get page title
            title = browser.page.title()
            print(f"📄 Page title: {title}")
            
            # Try clicking on job search or careers section
            print("\n🎯 Looking for navigation to job listings...")
            nav_selectors = [
                "a[href*='search']",
                "a[href*='jobs']", 
                "a[href*='careers']",
                "button:has-text('Search')",
                "button:has-text('Jobs')",
                ".search-btn",
                ".jobs-link"
            ]
            
            for selector in nav_selectors:
                try:
                    element = browser.page.query_selector(selector)
                    if element:
                        text = element.text_content() or ''
                        href = element.get_attribute('href') or ''
                        print(f"  ✅ Found navigation: {selector} - '{text}' → {href}")
                        
                        # Try clicking the first promising link
                        if 'search' in href.lower() or 'job' in text.lower():
                            print(f"  🔄 Clicking: {text}")
                            element.click()
                            browser.page.wait_for_load_state("networkidle", timeout=5000)
                            time.sleep(2)
                            break
                except Exception as e:
                    continue
            
            # Try to find common job-related elements
            selectors_to_test = [
                ".job-tile",
                ".job-card", 
                ".job-result",
                ".job-listing",
                "[data-test='job-card']",
                "[data-automation-id='jobTitle']",
                ".JobCard",
                ".job-post",
                ".position",
                ".career-card",
                ".opportunity",
                "article",
                ".search-result",
                "[role='listitem']"
            ]
            
            print("\n🎯 Testing job listing selectors...")
            found_elements = []
            
            for selector in selectors_to_test:
                try:
                    elements = browser.page.query_selector_all(selector)
                    if elements:
                        count = len(elements)
                        print(f"  ✅ {selector}: {count} elements found")
                        found_elements.append((selector, count))
                        
                        # Get text from first element to see what it contains
                        if count > 0:
                            try:
                                text = elements[0].text_content()
                                if text and len(text.strip()) > 10:
                                    preview = text.strip()[:100] + "..." if len(text.strip()) > 100 else text.strip()
                                    print(f"      Preview: {preview}")
                            except:
                                pass
                    else:
                        print(f"  ❌ {selector}: 0 elements")
                except Exception as e:
                    print(f"  ⚠️  {selector}: Error - {e}")
            
            # Test search functionality
            print("\n🔍 Testing search elements...")
            search_selectors = [
                "input[type='search']",
                "input[placeholder*='search']",
                "input[placeholder*='job']",
                "input[name='keywords']",
                "input[name='q']",
                ".search-input",
                "#search",
                "[data-test='search-input']"
            ]
            
            for selector in search_selectors:
                try:
                    element = browser.page.query_selector(selector)
                    if element:
                        placeholder = element.get_attribute('placeholder') or ''
                        print(f"  ✅ Search field: {selector} (placeholder: '{placeholder}')")
                except:
                    pass
            
            # Check if it's a React/SPA app
            print("\n⚛️  Checking for React/SPA indicators...")
            react_selectors = [
                "#root",
                "#app", 
                "[data-reactroot]",
                ".react-app"
            ]
            
            for selector in react_selectors:
                if browser.page.query_selector(selector):
                    print(f"  ✅ Found SPA container: {selector}")
            
            print(f"\n📊 Summary:")
            print(f"  📍 URL: {browser.page.url}")
            print(f"  📄 Title: {title}")
            print(f"  🎯 Job elements found: {len(found_elements)}")
            
            if found_elements:
                print(f"  🏆 Best candidate: {found_elements[0][0]} ({found_elements[0][1]} elements)")
            
            print("\n⏸️  Press Enter to close (inspect the browser window first)...")
            input()
            
        else:
            print("❌ Failed to load website")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        browser.close()
        print("✅ Inspection complete!")

if __name__ == "__main__":
    inspect_amazon_structure() 