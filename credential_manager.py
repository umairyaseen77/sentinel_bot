"""
Credential Management System for Sentinel Bot
Allows updating Amazon email, PIN, master password, Gmail settings, and other authentication details
"""

import json
import os
from app.security import encrypt, decrypt
import getpass

class CredentialManager:
    def __init__(self):
        self.profiles_file = "data/profiles.json"
        
    def load_profiles(self):
        try:
            with open(self.profiles_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ No profiles found. Run initial setup first.")
            return None
        except Exception as e:
            print(f"❌ Error loading profiles: {e}")
            return None
    
    def save_profiles(self, profiles):
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.profiles_file, "w") as f:
                json.dump(profiles, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error saving profiles: {e}")
            return False
    
    def verify_master_password(self, master_password, profile):
        try:
            if 'encrypted_job_site_password' in profile:
                decrypt(profile['encrypted_job_site_password'], master_password)
                return True
            return False
        except:
            return False
    
    def update_amazon_credentials(self):
        print("🛒 UPDATE AMAZON CREDENTIALS")
        print("=" * 40)
        
        profiles = self.load_profiles()
        if not profiles:
            return False
        
        profile_name = "Umair"
        if profile_name not in profiles:
            print(f"❌ Profile '{profile_name}' not found!")
            return False
        
        profile = profiles[profile_name]
        
        # Get master password
        master_password = getpass.getpass("🔑 Enter master password: ")
        
        if not self.verify_master_password(master_password, profile):
            print("❌ Master password is incorrect!")
            return False
        
        print(f"\n📧 Current Amazon email: {profile.get('job_site_username', 'Not set')}")
        
        # Update email
        new_email = input("📧 Enter new Amazon email (or press Enter to keep current): ").strip()
        if new_email:
            profile['job_site_username'] = new_email
            print(f"✅ Amazon email updated to: {new_email}")
        
        # Update PIN/Password
        print("\n🔑 Update Amazon PIN/Password:")
        new_password = getpass.getpass("🔑 Enter new Amazon PIN/Password (or press Enter to keep current): ")
        if new_password:
            profile['encrypted_job_site_password'] = encrypt(new_password, master_password)
            print("✅ Amazon PIN/Password updated and encrypted")
        
        # Save changes
        if self.save_profiles(profiles):
            print("✅ Amazon credentials updated successfully!")
            return True
        else:
            print("❌ Failed to save changes!")
            return False
    
    def update_gmail_settings(self):
        print("📧 UPDATE GMAIL SETTINGS")
        print("=" * 40)
        
        profiles = self.load_profiles()
        if not profiles:
            return False
        
        profile_name = "Umair"
        if profile_name not in profiles:
            print(f"❌ Profile '{profile_name}' not found!")
            return False
        
        profile = profiles[profile_name]
        
        # Get master password
        master_password = getpass.getpass("🔑 Enter master password: ")
        
        if not self.verify_master_password(master_password, profile):
            print("❌ Master password is incorrect!")
            return False
        
        email_config = profile.get('email_automation', {})
        
        print(f"\n📧 Current Gmail: {email_config.get('email_address', 'Not set')}")
        print(f"🔧 Automation enabled: {email_config.get('enabled', False)}")
        
        # Update Gmail address
        new_gmail = input("📧 Enter new Gmail address (or press Enter to keep current): ").strip()
        if new_gmail:
            if 'email_automation' not in profile:
                profile['email_automation'] = {}
            profile['email_automation']['email_address'] = new_gmail
            print(f"✅ Gmail address updated to: {new_gmail}")
        
        # Update App Password
        print("\n🔑 Update Gmail App Password:")
        print("   Generate new App Password at: https://myaccount.google.com/apppasswords")
        new_app_password = getpass.getpass("🔑 Enter new Gmail App Password (16 chars, or press Enter to keep current): ")
        if new_app_password:
            clean_password = new_app_password.replace(" ", "").replace("-", "")
            if len(clean_password) != 16:
                print(f"⚠️  Warning: App Password should be 16 characters, got {len(clean_password)}")
            
            if 'email_automation' not in profile:
                profile['email_automation'] = {}
            
            profile['email_automation']['encrypted_app_password'] = encrypt(new_app_password, master_password)
            profile['email_automation']['enabled'] = True
            print("✅ Gmail App Password updated and encrypted")
        
        # Save changes
        if self.save_profiles(profiles):
            print("✅ Gmail settings updated successfully!")
            return True
        else:
            print("❌ Failed to save changes!")
            return False
    
    def change_master_password(self):
        print("🔐 CHANGE MASTER PASSWORD")
        print("=" * 40)
        
        profiles = self.load_profiles()
        if not profiles:
            return False
        
        profile_name = "Umair"
        if profile_name not in profiles:
            print(f"❌ Profile '{profile_name}' not found!")
            return False
        
        profile = profiles[profile_name]
        
        # Get current master password
        current_master = getpass.getpass("🔑 Enter CURRENT master password: ")
        
        if not self.verify_master_password(current_master, profile):
            print("❌ Current master password is incorrect!")
            return False
        
        # Get new master password
        new_master = getpass.getpass("🆕 Enter NEW master password: ")
        confirm_master = getpass.getpass("🔄 Confirm NEW master password: ")
        
        if new_master != confirm_master:
            print("❌ Passwords don't match!")
            return False
        
        if len(new_master) < 8:
            print("❌ Master password must be at least 8 characters!")
            return False
        
        try:
            # Decrypt all encrypted fields with old password
            decrypted_data = {}
            
            if 'encrypted_job_site_password' in profile:
                decrypted_data['job_site_password'] = decrypt(profile['encrypted_job_site_password'], current_master)
            
            email_config = profile.get('email_automation', {})
            if email_config.get('encrypted_app_password'):
                decrypted_data['app_password'] = decrypt(email_config['encrypted_app_password'], current_master)
            
            # Re-encrypt with new master password
            if 'job_site_password' in decrypted_data:
                profile['encrypted_job_site_password'] = encrypt(decrypted_data['job_site_password'], new_master)
            
            if 'app_password' in decrypted_data:
                profile['email_automation']['encrypted_app_password'] = encrypt(decrypted_data['app_password'], new_master)
            
            # Save updated profiles
            if self.save_profiles(profiles):
                print("✅ Master password changed successfully!")
                print("🔐 All encrypted data has been re-encrypted with the new password.")
                return True
            else:
                print("❌ Failed to save updated profiles!")
                return False
                
        except Exception as e:
            print(f"❌ Error changing master password: {e}")
            return False
    
    def view_current_settings(self):
        print("👁️  CURRENT SETTINGS")
        print("=" * 40)
        
        profiles = self.load_profiles()
        if not profiles:
            return False
        
        profile_name = "Umair"
        if profile_name not in profiles:
            print(f"❌ Profile '{profile_name}' not found!")
            return False
        
        profile = profiles[profile_name]
        
        print(f"\n📋 Profile: {profile_name}")
        print(f"🛒 Amazon Email: {profile.get('job_site_username', 'Not set')}")
        print(f"🔐 Amazon Password: {'Set (encrypted)' if profile.get('encrypted_job_site_password') else 'Not set'}")
        print(f"🎯 Target Site: {profile.get('job_site_url', 'Not set')}")
        
        keywords = profile.get('keywords', {})
        print(f"🔍 Required Keywords: {', '.join(keywords.get('required', []))}")
        print(f"❌ Excluded Keywords: {', '.join(keywords.get('excluded', []))}")
        
        locations = profile.get('locations', [])
        print(f"📍 Locations: {', '.join(locations)}")
        
        print(f"⏰ Check Interval: {profile.get('check_interval_minutes', 30)} minutes")
        print(f"🌐 Headless Mode: {profile.get('headless', False)}")
        
        email_config = profile.get('email_automation', {})
        if email_config:
            print(f"\n📧 Gmail Address: {email_config.get('email_address', 'Not set')}")
            print(f"🔧 Email Automation: {'ENABLED' if email_config.get('enabled') else 'DISABLED'}")
            print(f"🔑 Gmail App Password: {'Set (encrypted)' if email_config.get('encrypted_app_password') else 'Not set'}")
        else:
            print("\n📧 Gmail Automation: Not configured")
        
        return True

def main():
    manager = CredentialManager()
    
    while True:
        print("\n" + "=" * 60)
        print("🔧 SENTINEL BOT - CREDENTIAL MANAGER")
        print("=" * 60)
        
        print("\nWhat would you like to do?")
        print("1. 👁️  View current settings")
        print("2. 🛒 Update Amazon credentials (email & PIN)")
        print("3. 📧 Update Gmail settings")
        print("4. 🔐 Change master password")
        print("5. 🚪 Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            manager.view_current_settings()
        elif choice == "2":
            manager.update_amazon_credentials()
        elif choice == "3":
            manager.update_gmail_settings()
        elif choice == "4":
            manager.change_master_password()
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 