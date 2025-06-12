"""
Gmail Connection Debugging Script
Helps diagnose and fix Gmail IMAP authentication issues
"""

import imaplib
import json
import sys
from app.security import decrypt

def test_gmail_connection_detailed():
    """Detailed Gmail connection testing with step-by-step diagnostics."""
    
    print("🔍 GMAIL CONNECTION DIAGNOSTICS")
    print("=" * 50)
    
    # Load configuration
    try:
        with open("data/profiles.json", "r") as f:
            profiles = json.load(f)
        
        profile = profiles.get("Umair", {})
        email_config = profile.get("email_automation", {})
        
        if not email_config:
            print("❌ No email automation config found!")
            return False
            
        email_address = email_config.get("email_address")
        print(f"📧 Email Address: {email_address}")
        
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False
    
    # Get master password
    master_password = input("🔐 Enter master password: ").strip()
    
    try:
        # Decrypt app password
        encrypted_password = email_config["encrypted_app_password"]
        app_password = decrypt(encrypted_password, master_password)
        print(f"🔓 App Password Length: {len(app_password)} characters")
        print(f"🔓 App Password Format: {'*' * (len(app_password) - 4)}{app_password[-4:]}")
        
    except Exception as e:
        print(f"❌ Failed to decrypt password: {e}")
        return False
    
    # Test different connection approaches
    print("\n🧪 Testing Gmail IMAP Connection...")
    
    # Test 1: Basic connection
    print("\n1️⃣ Testing basic IMAP connection...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        print("✅ IMAP SSL connection established")
        
        # Test 2: Authentication
        print("\n2️⃣ Testing authentication...")
        try:
            # Clean the app password (remove spaces)
            clean_password = app_password.replace(" ", "").replace("-", "")
            print(f"🧹 Cleaned password length: {len(clean_password)}")
            
            result = mail.login(email_address, clean_password)
            print(f"✅ Authentication successful: {result}")
            
            # Test 3: Mailbox access
            print("\n3️⃣ Testing mailbox access...")
            mail.select("inbox")
            print("✅ Inbox access successful")
            
            # Test 4: Email search
            print("\n4️⃣ Testing email search...")
            status, messages = mail.search(None, 'ALL')
            if status == "OK":
                count = len(messages[0].split()) if messages[0] else 0
                print(f"✅ Found {count} emails in inbox")
            
            mail.logout()
            print("\n🎉 All tests passed! Gmail connection is working.")
            return True
            
        except imaplib.IMAP4.error as e:
            print(f"❌ Authentication failed: {e}")
            
            # Provide specific troubleshooting
            error_str = str(e).lower()
            if "invalid credentials" in error_str:
                print("\n🔧 TROUBLESHOOTING STEPS:")
                print("1. Verify 2FA is enabled on your Google account")
                print("2. Generate a NEW App Password:")
                print("   - Go to: https://myaccount.google.com/apppasswords")
                print("   - Select 'Mail' as the app")
                print("   - Copy the 16-character password exactly")
                print("3. Make sure you're using the App Password, not your regular password")
                print("4. Try removing spaces from the App Password")
                
                # Test with different password formats
                print("\n🔄 Trying alternative password formats...")
                
                # Try original password with spaces
                try:
                    mail2 = imaplib.IMAP4_SSL("imap.gmail.com", 993)
                    mail2.login(email_address, app_password)
                    print("✅ Original password format worked!")
                    mail2.logout()
                    return True
                except:
                    print("❌ Original format failed")
                
                # Try lowercase
                try:
                    mail3 = imaplib.IMAP4_SSL("imap.gmail.com", 993)
                    mail3.login(email_address, clean_password.lower())
                    print("✅ Lowercase password worked!")
                    mail3.logout()
                    return True
                except:
                    print("❌ Lowercase format failed")
                
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 NETWORK TROUBLESHOOTING:")
        print("1. Check your internet connection")
        print("2. Verify firewall isn't blocking IMAP (port 993)")
        print("3. Try connecting from a different network")
        return False

def generate_new_app_password_guide():
    """Provide step-by-step guide for generating new App Password."""
    
    print("\n" + "=" * 60)
    print("📱 STEP-BY-STEP APP PASSWORD GENERATION")
    print("=" * 60)
    
    print("\n1️⃣ Enable 2-Factor Authentication:")
    print("   🔗 https://myaccount.google.com/security")
    print("   ✓ Click '2-Step Verification'")
    print("   ✓ Follow the setup process")
    
    print("\n2️⃣ Generate App Password:")
    print("   🔗 https://myaccount.google.com/apppasswords")
    print("   ✓ Select app: 'Mail'")
    print("   ✓ Select device: 'Windows Computer' or 'Other'")
    print("   ✓ Click 'Generate'")
    
    print("\n3️⃣ Copy the Password:")
    print("   ✓ Copy the 16-character password (e.g., 'abcd efgh ijkl mnop')")
    print("   ✓ Include spaces as shown")
    print("   ✓ Don't use your regular Gmail password")
    
    print("\n4️⃣ Test the Password:")
    print("   ✓ Run this script again")
    print("   ✓ Enter the new App Password exactly as generated")
    
    print("\n💡 IMPORTANT NOTES:")
    print("   • App Passwords are 16 characters long")
    print("   • They contain letters and numbers only")
    print("   • Spaces are usually included in the display")
    print("   • Each App Password can only be viewed once")
    print("   • You can generate multiple App Passwords")

def interactive_setup():
    """Interactive setup with real-time validation."""
    
    print("\n" + "=" * 60)
    print("🔧 INTERACTIVE GMAIL SETUP")
    print("=" * 60)
    
    email = input("\n📧 Gmail address: ").strip()
    
    print(f"\n🔑 For {email}, you need an App Password.")
    print("Have you already generated one? (y/n): ", end="")
    has_password = input().strip().lower()
    
    if has_password != 'y':
        generate_new_app_password_guide()
        input("\nPress Enter when you have generated the App Password...")
    
    app_password = input("\n🔑 Enter App Password (16 chars): ").strip()
    
    # Validate format
    clean_password = app_password.replace(" ", "").replace("-", "")
    if len(clean_password) != 16:
        print(f"⚠️  Warning: Password length is {len(clean_password)}, expected 16")
    
    # Test immediately
    print(f"\n🧪 Testing {email} with provided password...")
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email, clean_password)
        mail.select("inbox")
        mail.logout()
        
        print("✅ Test successful! Password is working.")
        
        # Update configuration
        master_password = input("\n🔐 Master password for encryption: ").strip()
        
        from app.security import encrypt
        encrypted_password = encrypt(app_password, master_password)
        
        # Update profile
        try:
            with open("data/profiles.json", "r") as f:
                profiles = json.load(f)
            
            profile_name = "Umair"
            if profile_name in profiles:
                profiles[profile_name]["email_automation"] = {
                    "enabled": True,
                    "email_address": email,
                    "encrypted_app_password": encrypted_password
                }
                
                with open("data/profiles.json", "w") as f:
                    json.dump(profiles, f, indent=2)
                
                print("✅ Configuration updated successfully!")
                return True
            
        except Exception as e:
            print(f"❌ Failed to update config: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\n🔄 Try generating a new App Password and run this again.")
        return False

def main():
    """Main function."""
    
    print("🔍 GMAIL AUTHENTICATION DEBUGGER")
    print("=" * 50)
    
    print("\nWhat would you like to do?")
    print("1. Test existing configuration")
    print("2. Interactive setup with new App Password")
    print("3. View App Password generation guide")
    
    choice = input("\nChoice (1-3): ").strip()
    
    if choice == "1":
        test_gmail_connection_detailed()
    elif choice == "2":
        interactive_setup()
    elif choice == "3":
        generate_new_app_password_guide()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main() 