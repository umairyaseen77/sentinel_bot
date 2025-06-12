#!/usr/bin/env python3
"""
Inspect Continue buttons and elements after email is filled.
"""

import json
import logging
from app.browser_actor import BrowserActor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def inspect_continue_elements():
    """Inspect what Continue buttons are available."""
    
    print("🔍 Continue Button Inspector")
    print("=" * 30)
    
    # Load profile and master password
    with open('data/profiles.json', 'r') as f:
        profiles = json.load(f)
    
    profile = profiles['Umair']
    profile['headless'] = False
    master_password = "12345678"
    
    browser = BrowserActor(profile, master_password)
    
    try:
        # Start and navigate
        browser.start_session()
        browser.navigate_to_job_search()
        
        input("👀 Step 1: All dialogs cleared? Press Enter to continue to login...")
        
        # Go to login page
        browser.page.click("body", position={"x": 32, "y": 100})  # Hamburger menu
        time.sleep(3)
        
        # Find and click Sign in
        signin_link = browser.page.query_selector("a:has-text('Sign in')")
        if signin_link:
            signin_link.click()
            time.sleep(3)
        
        # Fill email
        email_input = browser.page.query_selector('input[type="text"], input:not([type])')
        if email_input:
            email_input.fill("thehumanz666@gmail.com")
            print("✅ Email filled")
        
        input("👀 Step 2: Email is filled. Now let's inspect what Continue options are available. Press Enter...")
        
        print("\n🔍 INSPECTING ALL CLICKABLE ELEMENTS:")
        
        # Get all buttons
        all_buttons = browser.page.query_selector_all('button')
        print(f"\n📋 Found {len(all_buttons)} buttons:")
        for i, btn in enumerate(all_buttons):
            try:
                if btn.is_visible():
                    text = btn.inner_text() or btn.get_attribute('aria-label') or ''
                    classes = btn.get_attribute('class') or ''
                    btn_id = btn.get_attribute('id') or ''
                    print(f"  Button {i+1}: '{text}' (id: '{btn_id}', classes: {classes[:50]})")
            except:
                continue
        
        # Get all links
        all_links = browser.page.query_selector_all('a')
        print(f"\n📋 Found {len(all_links)} links:")
        for i, link in enumerate(all_links[:10]):  # Show first 10
            try:
                if link.is_visible():
                    text = link.inner_text() or ''
                    href = link.get_attribute('href') or ''
                    if text:
                        print(f"  Link {i+1}: '{text}' -> {href[:50]}")
            except:
                continue
        
        # Get all inputs
        all_inputs = browser.page.query_selector_all('input')
        print(f"\n📋 Found {len(all_inputs)} inputs:")
        for i, inp in enumerate(all_inputs):
            try:
                if inp.is_visible():
                    inp_type = inp.get_attribute('type') or 'text'
                    inp_value = inp.get_attribute('value') or ''
                    inp_name = inp.get_attribute('name') or ''
                    print(f"  Input {i+1}: type='{inp_type}', name='{inp_name}', value='{inp_value[:30]}'")
            except:
                continue
        
        print(f"\n🔍 Looking for elements containing 'continue', 'next', 'submit':")
        
        continue_keywords = ['continue', 'Continue', 'CONTINUE', 'next', 'Next', 'submit', 'Submit']
        
        for keyword in continue_keywords:
            elements = browser.page.query_selector_all(f"*:has-text('{keyword}')")
            visible_elements = [el for el in elements if el.is_visible()]
            
            if visible_elements:
                print(f"\n  ✅ Elements with '{keyword}' ({len(visible_elements)} found):")
                for i, el in enumerate(visible_elements[:3]):
                    try:
                        tag = el.evaluate("el => el.tagName")
                        text = el.inner_text()[:50]
                        classes = el.get_attribute('class') or ''
                        print(f"    {i+1}. {tag}: '{text}' (classes: {classes[:30]})")
                    except:
                        pass
        
        input("\n👀 Step 3: Based on the inspection above, can you identify which element to click for Continue? Press Enter to close...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        browser.close_session()

if __name__ == "__main__":
    import time
    inspect_continue_elements() 