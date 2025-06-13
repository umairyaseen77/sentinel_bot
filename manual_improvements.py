#!/usr/bin/env python3
"""
Quick test for the improvements: cookies handling and login flow.
"""

import json
import logging
from app.browser_actor import BrowserActor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_improvements():
    """Test the improved cookie handling and login flow."""
    
    print("🔧 Testing Improvements: Cookies + Login")
    print("=" * 40)
    
    # Load profile
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False
    
    browser = BrowserActor(profile)
    
    try:
        # Start session
        if not browser.start_session():
            print("❌ Failed to start browser")
            return
        
        # Navigate
        if not browser.navigate_to_job_search():
            print("❌ Failed to navigate")
            return
        
        input("👀 Check 1: Are ALL cookies dialogs gone? Press Enter...")
        
        # Try login
        login_success = browser.login()
        if login_success:
            print("✅ Login successful!")
        else:
            print("⚠️ Login not successful")
        
        input("👀 Check 2: Did login work or get further? Press Enter to close...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        browser.close_session()

if __name__ == "__main__":
    test_improvements() 