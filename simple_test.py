#!/usr/bin/env python3
"""
Simple test to see the bot in action with visible browser.
"""

import json
from app.browser_actor import BrowserActor

def simple_browser_test():
    """Test browser automation with visible window."""
    
    print("🤖 Simple Browser Test - Amazon Jobs")
    print("=" * 40)
    
    # Load the profile config
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    
    # Force visible browser
    profile['headless'] = False
    
    print(f"🌐 Target: {profile['job_site_url']}")
    print(f"👁️  Browser: Visible mode")
    print(f"🔍 Keywords: {', '.join(profile['keywords']['required'])}")
    print(f"📍 Cities: {', '.join(profile['filters']['cities'][:3])}...")
    
    print("\n🚀 Launching browser...")
    
    # Create browser actor
    browser = BrowserActor(profile)
    
    try:
        # Initialize session
        print("📂 Opening Amazon Jobs website...")
        success = browser.initialize_session()
        
        if success:
            print("✅ Browser opened successfully!")
            print("🔍 You should see the Chrome browser window now")
            print("📋 Current page:", browser.page.url)
            
            # Try a simple job search
            print("\n🔎 Searching for jobs...")
            keywords = profile['keywords']['required']
            city = profile['filters']['cities'][0]  # London
            
            search_success = browser.search_jobs(keywords, city)
            
            if search_success:
                print(f"✅ Search completed for: {', '.join(keywords)} in {city}")
            else:
                print("⚠️  Search not available, but page loaded")
            
            # Try scraping
            print("\n📊 Scraping job listings...")
            jobs = browser.scrape_job_listings()
            
            print(f"📋 Found {len(jobs)} job listings")
            
            if jobs:
                print("\n📝 Sample jobs found:")
                for i, job in enumerate(jobs[:3], 1):
                    print(f"  {i}. {job.get('title', 'Unknown Title')}")
                    print(f"     📍 {job.get('location', 'Unknown Location')}")
                    print(f"     🔗 {job.get('url', 'No URL')[:60]}...")
                    print()
            
            print("🎯 Test completed! Check the browser window for results.")
            print("⏸️  Press Enter to close browser...")
            input()
            
        else:
            print("❌ Failed to open browser session")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("🔒 Closing browser...")
        browser.close()
        print("✅ Test complete!")

if __name__ == "__main__":
    simple_browser_test() 