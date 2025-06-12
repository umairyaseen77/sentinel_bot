#!/usr/bin/env python3
"""
Final working test using the complete browser automation solution.
"""

import json
import time
import logging
from app.browser_actor import BrowserActor

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_complete_automation():
    """Test the complete automation with all fixes applied."""
    
    print("🚀 Final Working Test - Complete Amazon Jobs UK Automation")
    print("=" * 60)
    
    # Load profile
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False  # Always visible for testing
    
    print(f"🎯 Profile: Umair")
    print(f"🌐 Target: {profile['job_site_url']}")
    print(f"👤 Username: {profile['job_site_username']}")
    print(f"🔍 Keywords: {profile.get('keywords', {})}")
    print(f"📍 Locations: {profile.get('filters', {}).get('cities', [])}")
    print()
    
    # Create browser actor
    browser = BrowserActor(profile)
    
    try:
        print("🔧 Step 1: Starting browser session...")
        if not browser.start_session():
            print("❌ Failed to start browser session")
            return
        print("✅ Browser session started")
        
        print("\n🔧 Step 2: Navigating to job search...")
        if not browser.navigate_to_job_search():
            print("❌ Failed to navigate to job search")
            return
        print("✅ Navigation completed")
        
        input("\n👀 CHECKPOINT: Can you see Amazon Jobs UK loaded without popups? Press Enter to continue...")
        
        print("\n🔧 Step 3: Attempting login...")
        if profile.get('job_site_username'):
            login_success = browser.login()
            if login_success:
                print("✅ Login successful!")
            else:
                print("⚠️ Login failed or not completed, continuing without login")
        else:
            print("ℹ️ No credentials provided, skipping login")
        
        input("\n👀 CHECKPOINT: Is login completed? Press Enter to continue to job search...")
        
        print("\n🔧 Step 4: Searching for jobs...")
        search_success = browser.search_jobs()
        if search_success:
            print("✅ Job search completed")
        else:
            print("⚠️ Job search had issues, trying to extract from current page")
        
        print("\n🔧 Step 5: Extracting job listings...")
        jobs = browser.extract_job_listings()
        
        print(f"\n📊 RESULTS:")
        print(f"Found {len(jobs)} job listings")
        
        if jobs:
            print("\n📋 First few jobs:")
            for i, job in enumerate(jobs[:5], 1):
                print(f"  {i}. {job['title']}")
                print(f"     Company: {job['company']}")
                print(f"     Location: {job['location']}")
                print(f"     Link: {job['link'][:50]}...")
                print()
        else:
            print("❌ No jobs found - this might indicate selectors need adjustment")
        
        print("✅ AUTOMATION COMPLETE!")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Error during automation: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        browser.close_session()
        print("✅ Browser closed")

if __name__ == "__main__":
    test_complete_automation() 