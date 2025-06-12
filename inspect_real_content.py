#!/usr/bin/env python3
"""
Inspect the actual content on Amazon Jobs UK page after popup handling.
"""

import json
import time
from app.browser_actor import BrowserActor

def inspect_content():
    """Inspect actual page content."""
    
    print("🔍 Amazon Jobs UK - Content Inspector")
    print("=" * 45)
    
    # Load config
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False  # Visible browser
    
    browser = BrowserActor(profile)
    
    try:
        print("🚀 Opening Amazon Jobs UK...")
        success = browser.initialize_session()
        
        if success:
            print("✅ Website loaded and popups handled!")
            print(f"📍 Current URL: {browser.page.url}")
            
            # Wait for content to load
            print("⏳ Waiting for content...")
            time.sleep(5)
            
            # Get page title
            title = browser.page.title()
            print(f"📄 Page title: {title}")
            
            # Get all text content on the page
            print("\n📝 All visible text content:")
            print("-" * 40)
            
            try:
                # Get all text content
                all_text = browser.page.inner_text('body')
                lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                
                # Show first 50 lines of content
                for i, line in enumerate(lines[:50], 1):
                    if len(line) > 5:  # Only show meaningful lines
                        print(f"{i:2d}. {line}")
                
                if len(lines) > 50:
                    print(f"... and {len(lines) - 50} more lines")
                    
            except Exception as e:
                print(f"Error getting text content: {e}")
            
            # Look for specific patterns that might be jobs
            print(f"\n🔍 Looking for job-related patterns...")
            
            # Check for common job-related words in the content
            job_keywords = ['position', 'role', 'career', 'opportunity', 'hiring', 'apply', 'jobs', 'work']
            
            try:
                page_content = browser.page.inner_text('body').lower()
                found_keywords = [kw for kw in job_keywords if kw in page_content]
                print(f"📋 Job keywords found: {', '.join(found_keywords)}")
            except:
                pass
            
            # Check for any clickable elements that might lead to jobs
            print(f"\n🔗 Looking for navigation links...")
            
            try:
                links = browser.page.query_selector_all('a')
                job_links = []
                
                for link in links[:20]:  # Check first 20 links
                    try:
                        text = link.inner_text().strip()
                        href = link.get_attribute('href')
                        
                        if text and href and any(word in text.lower() for word in ['job', 'career', 'position', 'search', 'browse']):
                            job_links.append((text, href))
                    except:
                        continue
                
                if job_links:
                    print("📍 Found potentially useful links:")
                    for text, href in job_links[:10]:
                        print(f"  • {text} → {href}")
                else:
                    print("❌ No obvious job-related links found")
                    
            except Exception as e:
                print(f"Error checking links: {e}")
            
            print("\n⏸️  Press Enter to close (check the browser window for visual inspection)...")
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
    inspect_content() 