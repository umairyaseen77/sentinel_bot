#!/usr/bin/env python3
"""
Inspect the job search page specifically to find job listing selectors.
"""

import json
import time
from app.browser_actor import BrowserActor

def inspect_job_search():
    """Inspect the job search page content."""
    
    print("🔍 Amazon Jobs UK - Job Search Page Inspector")
    print("=" * 50)
    
    # Load config
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False  # Visible browser
    
    browser = BrowserActor(profile)
    
    try:
        print("🚀 Opening Amazon Jobs UK and navigating to job search...")
        success = browser.initialize_session()
        
        if success:
            print("✅ Successfully reached job search page!")
            print(f"📍 Current URL: {browser.page.url}")
            
            # Wait for job search page to load
            print("⏳ Waiting for job search content to load...")
            time.sleep(5)
            
            # Get page title
            title = browser.page.title()
            print(f"📄 Page title: {title}")
            
            # Look for all possible job-related elements
            print("\n🔍 Testing potential job selectors...")
            
            selectors_to_test = [
                "div[data-test*='job']",
                "div[class*='job']",
                "div[class*='Job']", 
                "div[class*='position']",
                "div[class*='listing']",
                "div[class*='card']",
                "div[class*='result']",
                ".search-result",
                "article",
                "[role='listitem']",
                "li",
                "div[data-automation-id]",
                ".tile",
                ".item"
            ]
            
            found_elements = []
            
            for selector in selectors_to_test:
                try:
                    elements = browser.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        count = len(elements)
                        print(f"  ✅ {selector}: {count} elements")
                        
                        # Check if elements contain job-like content
                        try:
                            first_element = elements[0]
                            text = first_element.inner_text()[:200] if first_element.inner_text() else ""
                            
                            # Look for job-related keywords in the text
                            job_indicators = ['warehouse', 'fulfil', 'shift', 'hour', 'pay', 'apply', 'associate', 'operator']
                            if any(indicator in text.lower() for indicator in job_indicators):
                                found_elements.append((selector, count, text[:100] + "..."))
                                print(f"      🎯 Likely job content: {text[:100]}...")
                        except:
                            pass
                    else:
                        print(f"  ❌ {selector}: 0 elements")
                except Exception as e:
                    print(f"  ⚠️  {selector}: Error - {e}")
            
            # Show the most promising selectors
            if found_elements:
                print(f"\n🏆 Most promising job selectors:")
                for selector, count, preview in found_elements[:5]:
                    print(f"  🎯 {selector} ({count} elements)")
                    print(f"      Preview: {preview}")
                    print()
            
            # Check for search functionality
            print("🔍 Looking for search inputs...")
            search_inputs = browser.page.query_selector_all('input')
            for i, input_elem in enumerate(search_inputs[:10]):
                try:
                    placeholder = input_elem.get_attribute('placeholder') or ''
                    input_type = input_elem.get_attribute('type') or 'text'
                    name = input_elem.get_attribute('name') or ''
                    print(f"  Input {i+1}: type='{input_type}', placeholder='{placeholder}', name='{name}'")
                except:
                    continue
            
            # Look for filter options
            print("\n🎛️  Looking for filter options...")
            try:
                selects = browser.page.query_selector_all('select')
                for i, select in enumerate(selects[:5]):
                    try:
                        options = select.query_selector_all('option')
                        option_texts = [opt.inner_text() for opt in options[:5]]
                        print(f"  Filter {i+1}: {', '.join(option_texts[:3])}...")
                    except:
                        continue
            except:
                pass
            
            print("\n⏸️  Press Enter to close (inspect the browser window for visual confirmation)...")
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
    inspect_job_search() 