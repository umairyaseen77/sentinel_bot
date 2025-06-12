"""
Quick Gmail Authentication Test
"""

import imaplib

def quick_test():
    email = "thehumanz666@gmail.com"
    
    print("🧪 Quick Gmail Test")
    print("=" * 30)
    
    # Test the password you entered
    password = input("🔑 Enter your App Password exactly as you have it: ").strip()
    
    print(f"\n📧 Testing: {email}")
    print(f"🔑 Password length: {len(password)}")
    
    # Try different formats
    formats_to_try = [
        ("Original", password),
        ("No spaces", password.replace(" ", "")),
        ("No spaces/dashes", password.replace(" ", "").replace("-", "")),
        ("Lowercase", password.replace(" ", "").lower())
    ]
    
    for format_name, test_password in formats_to_try:
        print(f"\n🔄 Trying {format_name} format: {len(test_password)} chars")
        
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            result = mail.login(email, test_password)
            mail.logout()
            
            print(f"✅ SUCCESS with {format_name} format!")
            print(f"✅ Working password: {test_password}")
            return test_password
            
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    print("\n❌ All formats failed. You need a new App Password.")
    print("\n🔗 Generate new App Password:")
    print("1. Go to: https://myaccount.google.com/apppasswords")
    print("2. Delete old 'Mail' passwords")
    print("3. Create new 'Mail' password")
    print("4. Copy it EXACTLY as shown")
    
    return None

if __name__ == "__main__":
    quick_test() 