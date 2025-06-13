import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import queue
import json
import os
from .logger import setup_logger, log, GuiQueueHandler
from .main import run_bot
from . import security

# --- Constants ---
PROFILES_PATH = os.path.join('data', 'profiles.json')
MASTER_KEY_HASH_PATH = os.path.join('data', 'master.key')

# --- Profile Management ---
def get_default_profile():
    # This is a template for new profiles created in the wizard
    return {
        "job_site_type": "amazon", # Default to amazon
        "job_site_url": "https://www.amazon.jobs",
        "job_site_username": "",
        "encrypted_job_site_password": "",
        "discord_webhook_url": "",
        "check_interval_minutes": 30,
        "headless": True,
        "max_retries": 3,
        "keywords": {
            "required": ["software", "engineer", "developer"],
            "optional": [],
            "excluded": ["senior", "lead", "manager"]
        },
        "filters": {
            "cities": ["London", "Manchester", "Remote"],
        },
        "email_automation": {
            "enabled": False,
            "email_address": "",
            "encrypted_email_app_password": "",
            "email_imap_server": "imap.gmail.com",
            "confirmation_email_sender": "no-reply@amazon.com",
            "email_check_timeout_seconds": 90,
            "email_polling_interval_seconds": 5
        },
        "amazon_config": {
             "job_site_url": "https://www.amazon.jobs",
             "selectors": {},
             "cookie_modal_selectors": [],
             "page_signatures": []
        },
        "indeed_config": {
            "base_url": "https://uk.indeed.com",
            "search_path": "/jobs",
            "selectors": {},
            "cookie_modal_selectors": [],
            "page_signatures": []
        }
    }

def load_profiles():
    if not os.path.exists(PROFILES_PATH):
        return {}
    with open(PROFILES_PATH, 'r') as f:
        return json.load(f)

def save_profiles(profiles):
    os.makedirs('data', exist_ok=True)
    with open(PROFILES_PATH, 'w') as f:
        json.dump(profiles, f, indent=2)

# --- Main Application ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.master_password = None
        self.profiles = {}
        self.current_profile_name = None
        self.bot_threads = {}
        self.stop_events = {}
        self.status_queues = {}
        
        self.log_queue = queue.Queue()
        global log
        log = setup_logger(self.log_queue)
        self.gui_log_handler = None
        for handler in log.handlers:
            if isinstance(handler, GuiQueueHandler):
                self.gui_log_handler = handler
                break
        
        # Withdraw the main window until setup is complete
        self.withdraw()

        try:
            if self.setup_data():
                self.setup_main_window()
                self.deiconify() # Show the main window
                self.process_log_queue()
                self.process_status_queue()
            else:
                # If setup_data returns False, it means the user cancelled or an error occurred.
                # The app should close gracefully.
                self.quit()

        except Exception as e:
            log.exception("An unhandled error occurred during application startup.")
            messagebox.showerror(
                "Fatal Startup Error",
                f"A critical error occurred and the application must close:\n\n{e}"
            )
            self.quit()


    def setup_data(self):
        # Handle corrupted state first
        if not self.handle_corrupted_state():
            self.quit()
            return False
            
        if self.is_first_run():
            success = self.run_first_run_wizard()
            if not success:
                # User likely cancelled the wizard
                return False
        else:
            success = self.prompt_master_password()
            if not success:
                # User cancelled the password prompt
                return False
        
        try:
            self.profiles = load_profiles()
            if not self.profiles:
                log.warning("Profiles file loaded but is empty. User may need to create a new profile.")
            return True
        except Exception as e:
            log.error(f"Failed to load profiles: {e}")
            messagebox.showerror("Error", f"Failed to load profiles: {e}", parent=self)
            return False

    def is_first_run(self):
        return not os.path.exists(MASTER_KEY_HASH_PATH)

    def handle_corrupted_state(self):
        """Handle case where profiles exist but master key doesn't"""
        if os.path.exists(PROFILES_PATH) and not os.path.exists(MASTER_KEY_HASH_PATH):
            response = messagebox.askyesno(
                "Reset Required", 
                "Application state is corrupted. The profiles exist but the master key is missing.\n\nWould you like to reset and start fresh? This will delete existing profiles.",
                parent=self
            )
            if response:
                try:
                    os.remove(PROFILES_PATH)
                    log.info("Removed corrupted profiles.json file")
                    return True
                except Exception as e:
                    log.error(f"Failed to remove profiles.json: {e}")
                    messagebox.showerror("Error", f"Failed to reset: {e}", parent=self)
                    return False
            else:
                return False
        return True

    def run_first_run_wizard(self):
        wizard = FirstRunWizard(self)
        self.wait_window(wizard) # Wait until wizard is destroyed
        if wizard.success:
            self.master_password = wizard.master_password
            save_profiles(wizard.profiles)
            return True
        return False

    def prompt_master_password(self):
        # This loop allows for retries
        while self.master_password is None:
            password = simpledialog.askstring("Master Password", "Please enter your Master Password:", show='*')
            if password is None: # User cancelled
                return False

            try:
                with open(MASTER_KEY_HASH_PATH, 'rb') as f:
                    stored_hash = f.read()
            except FileNotFoundError:
                messagebox.showerror("Error", "Master key not found. Run the setup wizard again or check your installation.")
                return False
            
            if security.verify_password(stored_hash, password):
                self.master_password = password
                return True
            else:
                messagebox.showerror("Error", "Incorrect Master Password.")
                # Loop continues
        return False

    def setup_main_window(self):
        self.title("Sentinel Bot - Mission Control")
        self.geometry("1100x800")

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Profile Management Frame ---
        profile_frame = ctk.CTkFrame(self)
        profile_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(profile_frame, text="Current Profile:").pack(side="left", padx=(10, 5))
        
        self.profile_menu = ctk.CTkOptionMenu(profile_frame, command=self.on_profile_selected)
        self.profile_menu.pack(side="left", padx=5)

        ctk.CTkButton(profile_frame, text="+ New", width=60, command=self.new_profile).pack(side="left", padx=5)
        ctk.CTkButton(profile_frame, text="Rename", width=80, command=self.rename_profile).pack(side="left", padx=5)
        self.delete_button = ctk.CTkButton(profile_frame, text="- Delete", width=70, fg_color="red", hover_color="#C00000", command=self.delete_profile)
        self.delete_button.pack(side="left", padx=5)

        ctk.CTkButton(profile_frame, text="Change Master Password", width=160, command=self.change_master_password_dialog).pack(side="right", padx=5)

        # --- Tab View ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.tab_view.add("Dashboard & Logs")
        self.tab_view.add("Configuration")
        
        self.setup_dashboard_tab()
        self.setup_configuration_tab()

        self.load_and_display_profiles()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_dashboard_tab(self):
        dashboard_tab = self.tab_view.tab("Dashboard & Logs")
        dashboard_tab.grid_columnconfigure(0, weight=1)
        dashboard_tab.grid_rowconfigure(2, weight=1) # Log box row

        # Main control panel
        control_panel = ctk.CTkFrame(dashboard_tab)
        control_panel.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.start_button = ctk.CTkButton(control_panel, text="► Start Bot", command=self.start_bot)
        self.start_button.pack(side="left", padx=10, pady=10)

        self.stop_button = ctk.CTkButton(control_panel, text="■ Stop Bot", command=self.stop_bot, state="disabled")
        self.stop_button.pack(side="left", padx=10, pady=10)
        
        # Status display panel
        status_panel = ctk.CTkFrame(dashboard_tab)
        status_panel.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
        status_panel.grid_columnconfigure((0,1,2,3), weight=1)

        self.status_label = ctk.CTkLabel(status_panel, text="Status: Idle", text_color="gray")
        self.status_label.grid(row=0, column=0, padx=10, pady=5)
        
        self.last_checked_label = ctk.CTkLabel(status_panel, text="Last Checked: Never")
        self.last_checked_label.grid(row=0, column=1, padx=10, pady=5)

        self.jobs_found_label = ctk.CTkLabel(status_panel, text="Jobs Found (Session): 0")
        self.jobs_found_label.grid(row=0, column=2, padx=10, pady=5)

        self.log_textbox = ctk.CTkTextbox(dashboard_tab, state="disabled", wrap="word")
        self.log_textbox.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def setup_configuration_tab(self):
        self.config_tab = self.tab_view.tab("Configuration")
        self.config_tab_content = ctk.CTkScrollableFrame(self.config_tab)
        self.config_tab_content.pack(expand=True, fill="both", padx=5, pady=5)
        self.config_vars = {} 
        
        save_button = ctk.CTkButton(self.config_tab, text="Save Changes to Profile", command=self.save_current_profile)
        save_button.pack(side="bottom", pady=10, padx=10)


    def build_config_widgets(self, parent_frame, config_data):
        # Clear old widgets
        for widget in parent_frame.winfo_children():
            widget.destroy()

        self.config_vars = {}
        
        # Function to recursively build form
        def create_widgets(parent, data, prefix=""):
            for key, value in data.items():
                current_key = f"{prefix}.{key}" if prefix else key
                
                frame = ctk.CTkFrame(parent)
                frame.pack(fill="x", padx=5, pady=3, anchor="w")
                
                label_text = key.replace("_", " ").title()
                label = ctk.CTkLabel(frame, text=f"{label_text}:", width=200, anchor="w")
                label.pack(side="left", padx=(5, 10))
                
                if isinstance(value, dict):
                    # For nested dictionaries, just show a label and recurse
                    nested_frame = ctk.CTkFrame(parent, fg_color="transparent")
                    nested_frame.pack(fill="x", padx=20, pady=2)
                    ctk.CTkLabel(nested_frame, text=label_text, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
                    create_widgets(nested_frame, value, current_key)
                elif isinstance(value, list):
                     # Handle lists as comma-separated strings
                    entry = ctk.CTkEntry(frame)
                    entry.insert(0, ", ".join(map(str, value)))
                    entry.pack(side="left", fill="x", expand=True, padx=5)
                    self.config_vars[current_key] = entry
                elif isinstance(value, bool):
                    entry = ctk.CTkSwitch(frame, text="")
                    if value: entry.select()
                    else: entry.deselect()
                    entry.pack(side="left", padx=5)
                    self.config_vars[current_key] = entry
                else:
                    is_secret = "password" in key.lower() and "encrypted" in key.lower()
                    entry = ctk.CTkEntry(frame, show="*" if is_secret else None)
                    entry.insert(0, str(value))
                    entry.pack(side="left", fill="x", expand=True, padx=5)
                    self.config_vars[current_key] = entry

        # Create a deep copy to avoid modifying the original profile data
        display_config = json.loads(json.dumps(config_data))
        
        # Decrypt passwords for display purposes and rename keys
        if "encrypted_job_site_password" in display_config:
            try:
                decrypted = security.decrypt(display_config.get("encrypted_job_site_password", ""), self.master_password)
                display_config["job_site_password (enter to change)"] = decrypted
            except:
                display_config["job_site_password (enter to change)"] = "DECRYPTION FAILED"
            del display_config["encrypted_job_site_password"]

        if display_config.get("email_automation", {}).get("encrypted_email_app_password"):
             try:
                decrypted = security.decrypt(display_config["email_automation"]["encrypted_email_app_password"], self.master_password)
                display_config["email_automation"]["app_password (enter to change)"] = decrypted
             except:
                display_config["email_automation"]["app_password (enter to change)"] = "DECRYPTION FAILED"
             del display_config["email_automation"]["encrypted_email_app_password"]

        create_widgets(parent_frame, display_config)


    # --- Profile Logic ---
    def load_and_display_profiles(self):
        self.profiles = load_profiles()
        profile_names = list(self.profiles.keys())
        if not profile_names:
            profile_names = ["No Profiles Found"]

        self.profile_menu.configure(values=profile_names)
        
        if profile_names[0] != "No Profiles Found":
            self.profile_menu.set(profile_names[0])
            self.on_profile_selected(profile_names[0])
        else:
            self.profile_menu.set(profile_names[0])
            self.build_config_widgets(self.config_tab_content, {}) # Clear config tab
            self.start_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")

    def on_profile_selected(self, profile_name):
        if profile_name not in self.profiles or profile_name == "No Profiles Found":
            self.status_label.configure(text="Status: Idle", text_color="gray")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.build_config_widgets(self.config_tab_content, {})
            return

        self.current_profile_name = profile_name
        self.tab_view.set("Dashboard & Logs")
        
        config = self.profiles[profile_name]
        self.build_config_widgets(self.config_tab_content, config)
        
        # Update dashboard status
        if profile_name in self.bot_threads and self.bot_threads[profile_name].is_alive():
            self.status_label.configure(text="Status: Running", text_color="green")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
        else:
            self.status_label.configure(text="Status: Idle", text_color="gray")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
        
        self.last_checked_label.configure(text="Last Checked: Never")
        self.jobs_found_label.configure(text="Jobs Found (Session): 0")


    def new_profile(self):
        profile_name = simpledialog.askstring("New Profile", "Enter a name for the new profile:")
        if profile_name and profile_name not in self.profiles:
            self.profiles[profile_name] = get_default_profile()
            save_profiles(self.profiles)
            self.load_and_display_profiles()
            self.profile_menu.set(profile_name)
        elif profile_name:
            messagebox.showerror("Error", "A profile with that name already exists.")
            
    def rename_profile(self):
        if not self.current_profile_name: return
        
        new_name = simpledialog.askstring("Rename Profile", f"Enter new name for '{self.current_profile_name}':")
        if new_name and new_name not in self.profiles:
            self.profiles[new_name] = self.profiles.pop(self.current_profile_name)
            save_profiles(self.profiles)
            self.load_and_display_profiles()
            self.profile_menu.set(new_name)
        elif new_name:
            messagebox.showerror("Error", "A profile with that name already exists.")

    def delete_profile(self):
        if not self.current_profile_name or self.current_profile_name == "No Profiles Found": return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete the profile '{self.current_profile_name}'?"):
            del self.profiles[self.current_profile_name]
            save_profiles(self.profiles)
            self.load_and_display_profiles()

    def change_master_password_dialog(self):
        current_pw = simpledialog.askstring("Change Master Password", "Enter CURRENT master password:", show='*', parent=self)
        if current_pw is None: return

        try:
            with open(MASTER_KEY_HASH_PATH, 'rb') as f:
                stored_hash = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read master key: {e}")
            return
            
        if not security.verify_password(stored_hash, current_pw):
            messagebox.showerror("Error", "Current master password is incorrect.")
            return

        new_pw = simpledialog.askstring("Change Master Password", "Enter NEW master password:", show='*', parent=self)
        if not new_pw: return
        confirm_pw = simpledialog.askstring("Change Master Password", "Confirm NEW master password:", show='*', parent=self)
        if confirm_pw is None: return
        if new_pw != confirm_pw:
            messagebox.showerror("Error", "New passwords do not match.")
            return
        if len(new_pw) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters long.")
            return

        try:
            # Re-encrypt all sensitive data in all profiles
            for name, cfg in self.profiles.items():
                if cfg.get("encrypted_job_site_password"):
                    plain = security.decrypt(cfg["encrypted_job_site_password"], current_pw)
                    cfg["encrypted_job_site_password"] = security.encrypt(plain, new_pw)
                
                if cfg.get("email_automation", {}).get("encrypted_email_app_password"):
                    plain = security.decrypt(cfg["email_automation"]["encrypted_email_app_password"], current_pw)
                    cfg["email_automation"]["encrypted_email_app_password"] = security.encrypt(plain, new_pw)

            save_profiles(self.profiles)
            with open(MASTER_KEY_HASH_PATH, 'wb') as f:
                f.write(security.hash_password(new_pw))
            self.master_password = new_pw
            messagebox.showinfo("Success", "Master password changed successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to change master password: {e}")

    def save_current_profile(self):
        if not self.current_profile_name: return

        # Helper to set value in nested dict
        def set_nested(d, keys, value):
            for key in keys[:-1]:
                d = d.setdefault(key, {})
            d[keys[-1]] = value

        # Start with a fresh copy of the profile
        updated_config = json.loads(json.dumps(self.profiles[self.current_profile_name]))

        for key_path, widget in self.config_vars.items():
            keys = key_path.split('.')
            if isinstance(widget, ctk.CTkSwitch):
                value = bool(widget.get())
            else: # CTkEntry
                value_str = widget.get()
                # Handle lists
                if "," in value_str and "[" in str(self.profiles[self.current_profile_name].get(keys[0])) : # crude list check
                    value = [item.strip() for item in value_str.split(',')]
                else: # Handle numbers and strings
                    try:
                        value = int(value_str)
                    except ValueError:
                        try:
                            value = float(value_str)
                        except ValueError:
                            value = value_str

            set_nested(updated_config, keys, value)

        # Encrypt sensitive fields before saving, if they have been changed
        if "job_site_password (enter to change)" in updated_config:
            new_password = updated_config["job_site_password (enter to change)"]
            if new_password and new_password != "DECRYPTION FAILED":
                updated_config["encrypted_job_site_password"] = security.encrypt(new_password, self.master_password)
            del updated_config["job_site_password (enter to change)"]

        if updated_config.get("email_automation", {}).get("app_password (enter to change)"):
            new_password = updated_config["email_automation"]["app_password (enter to change)"]
            if new_password and new_password != "DECRYPTION FAILED":
                updated_config["email_automation"]["encrypted_email_app_password"] = security.encrypt(new_password, self.master_password)
            del updated_config["email_automation"]["app_password (enter to change)"]
        
        self.profiles[self.current_profile_name] = updated_config
        save_profiles(self.profiles)
        messagebox.showinfo("Success", f"Profile '{self.current_profile_name}' saved successfully.")
        # Reload the widgets to reflect the saved state
        self.on_profile_selected(self.current_profile_name)


    # --- Bot Threading Logic ---
    def start_bot(self):
        if not self.current_profile_name or self.current_profile_name == "No Profiles Found":
            messagebox.showerror("Error", "No profile selected.")
            return

        name = self.current_profile_name
        if name in self.bot_threads and self.bot_threads[name].is_alive():
            log.warning(f"Bot for '{name}' is already running.")
            return

        log.info(f"Starting bot for profile: {name}...")
        self.status_label.configure(text="Status: Starting...", text_color="orange")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        bot_config = self.profiles[name]
        
        self.stop_events[name] = threading.Event()
        self.status_queues[name] = queue.Queue()
        
        # Pass the master password to the bot thread
        self.bot_threads[name] = threading.Thread(
            target=run_bot, 
            args=(name, bot_config, self.master_password, self.stop_events[name], self.status_queues[name])
        )
        self.bot_threads[name].daemon = True
        self.bot_threads[name].start()
        self.monitor_bot_thread(name)


    def stop_bot(self):
        name = self.current_profile_name
        if not name in self.bot_threads or not self.bot_threads[name].is_alive():
            log.warning(f"Bot for '{name}' is not running.")
            self.stop_button.configure(state="disabled") # Ensure button is disabled if no thread
            return
            
        log.info(f"Stopping bot for profile: {name}...")
        self.status_label.configure(text="Status: Stopping...", text_color="orange")
        self.stop_button.configure(state="disabled")
        if name in self.stop_events:
            self.stop_events[name].set()

    def monitor_bot_thread(self, profile_name):
        if self.bot_threads[profile_name].is_alive():
            self.after(1000, lambda: self.monitor_bot_thread(profile_name))
        else:
            log.info(f"Bot thread for '{profile_name}' has finished.")
            if profile_name == self.current_profile_name:
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                # Check the status queue one last time for the final status
                self.process_status_queue() 
                if self.status_label.cget("text") not in ["Status: Stopped (Error)", "Status: Stopping..."]:
                     self.status_label.configure(text="Status: Idle", text_color="gray")


    def process_log_queue(self):
        try:
            while True:
                record = self.log_queue.get_nowait()
                if self.gui_log_handler:
                    msg = self.gui_log_handler.formatter.format(record)
                else:
                    msg = log.handlers[0].formatter.format(record)
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", msg + "\n")
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_log_queue)

    def process_status_queue(self):
        # Process status queue for the currently selected profile
        if self.current_profile_name and self.current_profile_name in self.status_queues:
            try:
                update = self.status_queues[self.current_profile_name].get_nowait()
                
                if update['type'] == 'status':
                    color_map = {
                        "searching": "lightblue", "sleeping": "gray", "running": "green",
                        "starting": "orange", "stopping": "orange", "error": "red",
                        "stopped": "red", "idle": "gray"
                    }
                    text_value = update['value'].lower()
                    text_color = "white"
                    for key, color in color_map.items():
                        if key in text_value:
                            text_color = color
                            break
                    self.status_label.configure(text=f"Status: {update['value']}", text_color=text_color)
                elif update['type'] == 'last_checked':
                    self.last_checked_label.configure(text=f"Last Checked: {update['value']}")
                elif update['type'] == 'jobs_found':
                    # This should be an absolute count for the session, not incremental
                    self.jobs_found_label.configure(text=f"Jobs Found (Session): {update['value']}")

            except queue.Empty:
                pass
        
        self.after(250, self.process_status_queue)


    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit? This will stop all running bots."):
            any_thread_alive = False
            for name, thread in self.bot_threads.items():
                if thread.is_alive():
                    any_thread_alive = True
                    log.info(f"Signalling stop for profile '{name}'...")
                    self.stop_events[name].set()
            
            if any_thread_alive:
                self.after(200, self.check_if_all_threads_dead)
            else:
                self.destroy()

    def check_if_all_threads_dead(self):
        any_alive = any(t.is_alive() for t in self.bot_threads.values())
        if any_alive:
            self.after(200, self.check_if_all_threads_dead)
        else:
            log.info("All bot threads stopped. Exiting.")
            self.destroy()

# --- First Run Wizard ---
class FirstRunWizard(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.transient(master)
        self.title("Welcome to Sentinel Bot")
        self.geometry("550x450")
        
        self.master_password = None
        self.temp_profile = get_default_profile()
        self.profiles = {}
        self.success = False

        self.current_step = 0
        self.steps = [
            self.create_welcome_step, 
            self.create_master_password_step, 
            self.create_site_credentials_step,
            self.create_finish_step
        ]
        
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        self.run_step()
        self.grab_set()

    def run_step(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.steps[self.current_step]()

    def next_step(self):
        self.current_step += 1
        if self.current_step < len(self.steps):
            self.run_step()
        else:
            self.finish_wizard()

    def create_welcome_step(self):
        ctk.CTkLabel(self.content_frame, text="Welcome to Sentinel Bot!", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        ctk.CTkLabel(self.content_frame, text="This wizard will guide you through creating your first secure monitoring profile.", wraplength=450).pack(pady=10)
        ctk.CTkButton(self.content_frame, text="Get Started", command=self.next_step).pack(pady=30)
        
    def create_master_password_step(self):
        ctk.CTkLabel(self.content_frame, text="Step 1: Create a Master Password", font=ctk.CTkFont(size=20)).pack(pady=10)
        ctk.CTkLabel(self.content_frame, text="This password encrypts all your credentials. Do not forget it!", wraplength=450).pack(pady=5)
        
        ctk.CTkLabel(self.content_frame, text="New Master Password:", anchor="w").pack(fill="x", padx=20, pady=(10,0))
        password_entry = ctk.CTkEntry(self.content_frame, show="*")
        password_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(self.content_frame, text="Confirm Master Password:", anchor="w").pack(fill="x", padx=20, pady=(10,0))
        confirm_entry = ctk.CTkEntry(self.content_frame, show="*")
        confirm_entry.pack(fill="x", padx=20)

        def save_password():
            pw1 = password_entry.get()
            pw2 = confirm_entry.get()
            if not pw1 or len(pw1) < 8:
                messagebox.showerror("Error", "Password must be at least 8 characters long.", parent=self)
                return
            if pw1 != pw2:
                messagebox.showerror("Error", "Passwords do not match.", parent=self)
                return
            
            self.master_password = pw1
            os.makedirs('data', exist_ok=True)
            with open(MASTER_KEY_HASH_PATH, 'wb') as f:
                f.write(security.hash_password(pw1))
            self.next_step()

        ctk.CTkButton(self.content_frame, text="Next", command=save_password).pack(side="bottom", pady=20)

    def create_site_credentials_step(self):
        ctk.CTkLabel(self.content_frame, text="Step 2: Job Site Details", font=ctk.CTkFont(size=20)).pack(pady=10)
        
        ctk.CTkLabel(self.content_frame, text="Profile Name:", anchor="w").pack(fill="x", padx=20)
        name_entry = ctk.CTkEntry(self.content_frame)
        name_entry.pack(fill="x", padx=20)
        name_entry.insert(0, "My First Profile")

        ctk.CTkLabel(self.content_frame, text="Job Site Username (Email):", anchor="w").pack(fill="x", padx=20, pady=(10,0))
        user_entry = ctk.CTkEntry(self.content_frame)
        user_entry.pack(fill="x", padx=20)
        
        ctk.CTkLabel(self.content_frame, text="Job Site Password:", anchor="w").pack(fill="x", padx=20, pady=(10,0))
        pass_entry = ctk.CTkEntry(self.content_frame, show="*")
        pass_entry.pack(fill="x", padx=20)

        def save_step():
            self.profile_name = name_entry.get()
            if not self.profile_name:
                 messagebox.showerror("Error", "Profile name cannot be empty.", parent=self)
                 return

            # These will be encrypted later
            self.temp_profile["job_site_username"] = user_entry.get()
            self.temp_profile["job_site_password_plain"] = pass_entry.get() 
            self.next_step()

        ctk.CTkButton(self.content_frame, text="Next", command=save_step).pack(side="bottom", pady=20)

    def create_finish_step(self):
        ctk.CTkLabel(self.content_frame, text="Setup Complete!", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        ctk.CTkLabel(self.content_frame, text=f"Profile '{getattr(self, 'profile_name', 'Default')}' will be created.\nClick Finish to launch Mission Control.", wraplength=450).pack(pady=10)
        ctk.CTkButton(self.content_frame, text="Finish", command=self.next_step).pack(pady=30)
        
    def finish_wizard(self):
        # Encrypt the password before finishing
        password_plain = self.temp_profile.pop("job_site_password_plain", "")
        if password_plain:
            self.temp_profile["encrypted_job_site_password"] = security.encrypt(password_plain, self.master_password)
        
        self.profiles[self.profile_name] = self.temp_profile
        self.success = True
        self.grab_release()
        self.destroy()
