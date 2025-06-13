#!/usr/bin/env python3
"""
Test script to run the bot with visible browser and live logging.
"""

import threading
import queue
import time
from app.main import run_bot
from app.gui import load_profiles
from app.security import decrypt
from app.logger import setup_logger

def test_bot():
    """Test the bot with live logging in terminal."""
    
    print("🤖 Sentinel Bot - Live Test Mode")
    print("=" * 50)
    
    # Setup logging to console
    log_queue = queue.Queue()
    log = setup_logger(log_queue)
    
    # Load profiles
    try:
        profiles = load_profiles()
        if not profiles:
            print("❌ No profiles found. Please run the GUI first to create a profile.")
            return
            
        profile_name = list(profiles.keys())[0]
        profile_config = profiles[profile_name].copy()
        
        print(f"📋 Using profile: {profile_name}")
        print(f"🌐 Job site: {profile_config['job_site_url']}")
        print(f"👁️  Browser mode: {'Visible' if not profile_config.get('headless', True) else 'Headless'}")
        print(f"⏱️  Check interval: {profile_config.get('check_interval_minutes', 30)} minutes")
        
        # Ask for master password to decrypt credentials
        import getpass
        master_password = getpass.getpass("🔐 Enter master password: ")
        
        # Decrypt sensitive fields
        try:
            if 'encrypted_job_site_password' in profile_config:
                profile_config['job_site_password'] = decrypt(profile_config['encrypted_job_site_password'], master_password)
                del profile_config['encrypted_job_site_password']
                
            if 'encrypted_email_app_password' in profile_config:
                profile_config['email_app_password'] = decrypt(profile_config['encrypted_email_app_password'], master_password)
                del profile_config['encrypted_email_app_password']
                
            print("✅ Credentials decrypted successfully")
        except Exception as e:
            print(f"❌ Failed to decrypt credentials. Wrong password? {e}")
            return
            
        # Setup threading
        stop_event = threading.Event()
        status_queue = queue.Queue()
        
        print("\n🚀 Starting bot thread...")
        print("📝 Live logs will appear below:")
        print("-" * 50)
        
        # Start bot in background thread
        bot_thread = threading.Thread(
            target=run_bot,
            args=(
                profile_name,
                profile_config,
                master_password,
                stop_event,
                status_queue,
                log_queue,
            ),
        )
        bot_thread.daemon = True
        bot_thread.start()
        
        # Process logs and status in real-time
        try:
            while bot_thread.is_alive():
                # Process log queue
                try:
                    while True:
                        record = log_queue.get_nowait()
                        print(f"[{record.levelname}] {record.getMessage()}")
                except queue.Empty:
                    pass
                
                # Process status queue
                try:
                    while True:
                        status = status_queue.get_nowait()
                        print(f"🔄 {status['type'].upper()}: {status['value']}")
                except queue.Empty:
                    pass
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping bot (Ctrl+C pressed)...")
            stop_event.set()
            bot_thread.join(timeout=10)
            print("✅ Bot stopped successfully")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bot() 