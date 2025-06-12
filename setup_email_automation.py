"""
Setup script for configuring automatic email reading for 2FA codes.
This script helps set up Gmail App Password for automatic authentication.
"""

import sys
import json
from app.security import encrypt

def setup_gmail_automation():
    """Setup Gmail App Password for automatic 2FA code reading."""
    
    print("=" * 60)
    print("📧 GMAIL AUTOMATION SETUP")
    print("=" * 60)
    print()
    
    print("To enable automatic 2FA code reading, you need to:")
    print("1. Enable 2-Factor Authentication on your Gmail account")
    print("2. Generate an App Password for this application")
    print()
    
    print("🔗 SETUP INSTRUCTIONS:")
    print("1. Go to: https://myaccount.google.com/security")
    print("2. Under 'Signing in to Google', enable '2-Step Verification'")
    print("3. Under '2-Step Verification', click 'App passwords'")
    print("4. Generate a new app password for 'Mail'")
    print("5. Copy the 16-character password (e.g., 'abcd efgh ijkl mnop')")
    print()
    
    # Get user input
    email = input("📧 Enter your Gmail address (theumairyaseen@gmail.com): ").strip()
    if not email:
        email = "theumairyaseen@gmail.com"
    
    app_password = input("🔑 Enter your Gmail App Password (16 characters): ").strip().replace(" ", "")
    
    if len(app_password) != 16:
        print("❌ App Password should be 16 characters long!")
        return False
    
    master_password = input("🔐 Enter your master password (12345678): ").strip()
    if not master_password:
        master_password = "12345678"
    
    try:
        # Encrypt the app password
        encrypted_app_password = encrypt(app_password, master_password)
        
        # Update the profile with email automation settings
        try:
            with open("data/profiles.json", "r") as f:
                profiles = json.load(f)
        except:
            profiles = {}
        
        # Update the existing profile
        profile_name = "Umair"  # Default profile name
        if profile_name in profiles:
            profiles[profile_name]["email_automation"] = {
                "enabled": True,
                "email_address": email,
                "encrypted_app_password": encrypted_app_password
            }
            
            with open("data/profiles.json", "w") as f:
                json.dump(profiles, f, indent=2)
            
            print()
            print("✅ Email automation configured successfully!")
            print(f"📧 Email: {email}")
            print("🔐 App Password: [ENCRYPTED]")
            print()
            print("🚀 You can now run the bot with automatic 2FA!")
            return True
        else:
            print(f"❌ Profile '{profile_name}' not found!")
            return False
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def test_email_connection():
    """Test email connection with the configured settings."""
    
    print("\n" + "=" * 60)
    print("🧪 TESTING EMAIL CONNECTION")
    print("=" * 60)
    
    try:
        import imaplib
        import json
        from app.security import decrypt
        
        # Load profile
        with open("data/profiles.json", "r") as f:
            profiles = json.load(f)
        
        profile = profiles.get("Umair", {})
        email_config = profile.get("email_automation", {})
        
        if not email_config.get("enabled"):
            print("❌ Email automation not configured!")
            return False
        
        email_address = email_config["email_address"]
        master_password = input("🔐 Enter master password: ").strip()
        
        # Decrypt app password
        app_password = decrypt(email_config["encrypted_app_password"], master_password)
        
        print(f"📧 Testing connection to {email_address}...")
        
        # Test IMAP connection
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email_address, app_password)
        mail.select("inbox")
        
        # Test search
        status, messages = mail.search(None, 'ALL')
        if status == "OK":
            email_count = len(messages[0].split()) if messages[0] else 0
            print(f"✅ Connection successful! Found {email_count} emails in inbox.")
        else:
            print("❌ Search test failed!")
            return False
        
        mail.logout()
        print("✅ Email automation is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print()
        print("💡 Common issues:")
        print("   - Make sure 2FA is enabled on your Google account")
        print("   - Use App Password, not your regular Gmail password")
        print("   - Check that 'Less secure app access' is disabled (use App Password instead)")
        return False

if __name__ == "__main__":
    print("🤖 Sentinel Bot - Email Automation Setup")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_email_connection()
    else:
        success = setup_gmail_automation()
        
        if success:
            test = input("\n🧪 Would you like to test the email connection? (y/n): ").strip().lower()
            if test == 'y':
                test_email_connection() 