"""
Full Automation Test for Amazon Jobs UK Login
Tests the complete automatic authentication flow including:
- Email entry
- PIN entry  
- 2FA code retrieval from email
- Captcha solving
- Job searching
"""

import logging
import sys
import json
from app.browser_actor import BrowserActor
from app.security import decrypt

def setup_logging():
    """Setup detailed logging for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('automation_test.log')
        ]
    )

def load_test_config():
    """Load the test configuration."""
    try:
        with open("data/profiles.json", "r") as f:
            profiles = json.load(f)
        
        profile = profiles.get("Umair", {})
        if not profile:
            print("❌ Profile 'Umair' not found!")
            return None
        
        # Check if email automation is configured
        email_config = profile.get('email_automation', {})
        if not email_config.get('enabled'):
            print("❌ Email automation not configured!")
            print("   Run: python setup_email_automation.py")
            return None
        
        return profile
        
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return None

def test_automatic_authentication():
    """Test the complete automatic authentication flow."""
    
    print("🤖 Starting Full Automation Test")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    
    # Load configuration
    config = load_test_config()
    if not config:
        return False
    
    # Get master password
    master_password = input("🔐 Enter master password (12345678): ").strip()
    if not master_password:
        master_password = "12345678"
    
    print(f"\n📧 Email: {config.get('email_automation', {}).get('email_address')}")
    print(f"🎯 Target: {config['job_site_url']}")
    print(f"🔍 Keywords: {', '.join(config.get('keywords', {}).get('required', []))}")
    print(f"📍 Locations: {', '.join(config.get('locations', []))}")
    print()
    
    # Initialize browser actor
    try:
        print("🚀 Initializing browser automation...")
        browser_actor = BrowserActor(config, master_password)
        
        # Start browser session
        print("🌐 Starting browser session...")
        if not browser_actor.start_session():
            print("❌ Failed to start browser session")
            return False
        
        print("✅ Browser session started")
        
        # Navigate to job search
        print("🧭 Navigating to Amazon Jobs UK...")
        if not browser_actor.navigate_to_job_search():
            print("❌ Failed to navigate to job search")
            browser_actor.close_session()
            return False
        
        print("✅ Navigation successful")
        
        # Test automatic login
        print("\n🔐 Starting automatic authentication...")
        print("   This will test:")
        print("   ✓ Email entry")
        print("   ✓ PIN entry")
        print("   ✓ 2FA code retrieval from email")
        print("   ✓ Automatic captcha solving")
        print()
        
        login_success = browser_actor.login()
        
        if login_success:
            print("✅ Automatic authentication completed successfully!")
            
            # Test job search
            print("\n🔍 Testing job search functionality...")
            if browser_actor.search_jobs():
                print("✅ Job search successful")
                
                # Extract some job listings
                print("📋 Extracting job listings...")
                jobs = browser_actor.extract_job_listings()
                
                if jobs:
                    print(f"✅ Found {len(jobs)} job listings:")
                    for i, job in enumerate(jobs[:5], 1):  # Show first 5
                        print(f"   {i}. {job['title']} - {job['location']}")
                else:
                    print("⚠️  No job listings found")
            else:
                print("⚠️  Job search had issues")
        else:
            print("❌ Automatic authentication failed")
            
        # Keep browser open for inspection
        print(f"\n🔍 Browser will remain open for 30 seconds for inspection...")
        print("   Current URL:", browser_actor.page.url)
        
        import time
        time.sleep(30)
        
        # Close session
        print("🔚 Closing browser session...")
        browser_actor.close_session()
        
        return login_success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logging.error(f"Full automation test failed: {e}", exc_info=True)
        return False

def test_email_only():
    """Test only the email reading functionality."""
    
    print("📧 Testing Email Reading Only")
    print("=" * 40)
    
    config = load_test_config()
    if not config:
        return False
    
    master_password = input("🔐 Enter master password: ").strip()
    
    try:
        browser_actor = BrowserActor(config, master_password)
        
        print("📬 Testing email connection and code retrieval...")
        code = browser_actor.get_2fa_code_from_email()
        
        if code:
            print(f"✅ Successfully retrieved code: {code}")
            return True
        else:
            print("❌ Failed to retrieve code from email")
            return False
            
    except Exception as e:
        print(f"❌ Email test failed: {e}")
        return False

def main():
    """Main test function."""
    
    print("🤖 SENTINEL BOT - FULL AUTOMATION TEST")
    print("=" * 60)
    print()
    
    # Check what user wants to test
    print("What would you like to test?")
    print("1. Full automatic authentication (email + browser)")
    print("2. Email reading only")
    print("3. Setup email automation")
    print()
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        success = test_automatic_authentication()
    elif choice == "2":
        success = test_email_only()
    elif choice == "3":
        import subprocess
        subprocess.run([sys.executable, "setup_email_automation.py"])
        return
    else:
        print("❌ Invalid choice")
        return
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TEST COMPLETED SUCCESSFULLY!")
        print("✅ Automatic authentication is working!")
    else:
        print("❌ TEST FAILED")
        print("💡 Check the logs for more details")
    print("=" * 60)

if __name__ == "__main__":
    main() 