#!/usr/bin/env python3
"""
Test login with proper master password handling.
"""

import json
import logging
import getpass
from app.browser_actor import BrowserActor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_login_with_password():
    """Test login with proper master password."""
    
    print("🔐 Login Test with Master Password")
    print("=" * 40)
    
    # Load profile
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False
    
    # Get master password
    master_password = "12345678"  # We know this from previous tests
    print(f"🔑 Using master password: {'*' * len(master_password)}")
    
    # Create browser actor with master password
    browser = BrowserActor(profile, master_password)
    
    try:
        # Start session
        if not browser.start_session():
            print("❌ Failed to start browser")
            return
        
        # Navigate
        if not browser.navigate_to_job_search():
            print("❌ Failed to navigate")
            return
        
        input("👀 Check 1: All dialogs cleared? Press Enter...")
        
        # Try login
        print("🔐 Attempting login with decrypted password...")
        login_success = browser.login()
        if login_success:
            print("✅ Login successful!")
        else:
            print("⚠️ Login not successful")
        
        input("👀 Check 2: Did both email AND password get filled? Press Enter...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        browser.close_session()

if __name__ == "__main__":
    test_login_with_password() 