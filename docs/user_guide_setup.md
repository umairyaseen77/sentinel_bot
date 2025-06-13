# User Setup and Usage Guide

Welcome to the Automated Job Search Bot! This guide will walk you through setting up and running the bot to automate your job searches.

## 1. Installation & Setup

### Prerequisites
Before you begin, ensure you have the following installed:
-   Python (version 3.8 or newer is recommended)
-   `pip` (Python's package installer, usually comes with Python)
-   Git (for cloning the project repository)

### Steps

1.  **Clone the Repository:**
    Open your terminal or command prompt and run:
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
    (Replace `<repository_url>` and `<repository_directory>` with the actual URL and folder name).

2.  **Create a Virtual Environment (Highly Recommended):**
    This creates an isolated environment for the bot's dependencies.
    ```bash
    python -m venv venv
    ```
    Activate the virtual environment:
    -   On macOS and Linux: `source venv/bin/activate`
    -   On Windows: `venv\Scripts\activate`
    You should see `(venv)` at the beginning of your terminal prompt.

3.  **Install Dependencies:**
    Install all required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright Browsers:**
    Playwright needs to download browser binaries to control them.
    ```bash
    playwright install --with-deps
    ```
    This installs browsers like Chromium, Firefox, and WebKit along with their operating system dependencies. If you only intend to use a specific browser (e.g., Chromium, which is often default for Playwright scripts), you can install just that: `playwright install chromium`.

## 2. Core Configuration (`profiles.yaml`)

The bot's behavior is controlled by a configuration file named `profiles.yaml`, which you need to create in the root directory of the project. This file can contain multiple "profiles," each defining a specific job search task.

**Refer to the comprehensive [Configuration Guide](./configuration_guide.md) for a full list and detailed explanation of all available settings.**

### Essential First Steps for a New Profile:

1.  **Create `profiles.yaml`:** If an example like `profiles.yaml.example` exists, copy it to `profiles.yaml`. Otherwise, create a new empty file.
2.  **Define a Profile:**
    ```yaml
    # profiles.yaml
    profiles:
      my_first_search: # Choose a unique name for your profile
        job_site_type: "indeed" # Or "amazon"

        keywords:
          required: ["Software Developer", "Python"]
          # optional: ["Remote", "API"] # Useful for Indeed search query
          excluded: ["Senior", "Lead Architect"]

        filters:
          cities: ["London, UK", "Remote"] # List of cities to search

        # default_location: "United Kingdom" # Used if 'cities' is empty, for some sites

        discord_webhook_url: "YOUR_DISCORD_WEBHOOK_URL_HERE" # Get this from your Discord server

        # Add site-specific config block below (e.g., indeed_config or amazon_config)
    ```

### Site-Specific Initial Setup

#### For Amazon (`job_site_type: "amazon"`)
   - Add an `amazon_config` block under your profile.
   - **Essential:**
     ```yaml
     amazon_config:
       job_site_url: "https://www.amazon.jobs" # Or your regional Amazon Jobs URL
     ```
   - **For Login (Optional but often needed for full access):**
     ```yaml
     amazon_config:
       # ... job_site_url ...
      job_site_username: "your_amazon_login_email@example.com"
      encrypted_job_site_password: "enc:YourEncryptedPassword"
     ```
   - **2FA Email Automation (for Amazon Login):**
     If Amazon login requires 2FA via email, configure the `email_automation` section under your profile (not under `amazon_config`):
     ```yaml
     email_automation:
       enabled: true
       email_address: "your_email_for_2fa_codes@gmail.com"
       email_app_password: "YourGmailAppPassword" # Or "enc:YourEncryptedAppPassword"
       email_imap_server: "imap.gmail.com"
       confirmation_email_sender: "no-reply@amazon.com" # Check actual sender for Amazon emails
     ```
     *   **Important for `email_app_password`:** For services like Gmail or Outlook, you usually need to generate an "app-specific password" from your email account settings if you have 2-Step Verification enabled on the email account itself. Do not use your main email password directly here if your email provider offers app passwords.

#### For Indeed (`job_site_type: "indeed"`)
   - Add an `indeed_config` block under your profile.
   - **Essential:**
     ```yaml
     indeed_config:
       base_url: "https://uk.indeed.com" # Or your regional Indeed URL
       search_path: "/jobs"
     ```
   - Indeed searches generally do not require login.

### Master Password & Encrypting Passwords (Optional)
If you want to encrypt sensitive information like your job site or email passwords:
1.  Set a `master_password: "your-chosen-master-key"` at the root of your profile.
2.  Prefix the encrypted values with `enc:`. For example, `encrypted_job_site_password: "enc:U2FsdGVkX1..."`.
3.  You'll need a separate mechanism or script using the `app/security.py` module's `encrypt_data` function to generate these encrypted strings.
    *(Developer Note: A helper script for encryption could be a future addition to the project.)*

## 3. Running the Bot

1.  Ensure your virtual environment is activated.
2.  Open your terminal in the project's root directory.
3.  Run the bot using its main script (assuming `run_gui.py`):
    ```bash
    python run_gui.py
    ```
    (If a different main script exists, like `main_cli.py`, use that.)

### Monitoring
-   **Console Output:** The bot will print log messages to the console, showing its current activities, jobs found, errors, etc.
-   **Log Files:** Detailed logs are typically saved to a file (e.g., `automation_test.log` or in a `logs/` directory). Check `app/logger.py` for the configured log file path. These logs are essential for debugging.
-   **GUI:** If `run_gui.py` provides a graphical user interface, it will display status and allow interaction.

## 4. Troubleshooting Common Issues

*   **Bot Doesn't Start / Crashes Immediately:**
    *   **Python Version:** Verify you're using Python 3.8 or newer (`python --version`).
    *   **Dependencies:** Ensure all packages are installed: `pip install -r requirements.txt`.
    *   **Playwright Browsers:** Browsers might be missing: `playwright install --with-deps`.
    *   **`profiles.yaml` Errors:**
        *   File not found: Make sure `profiles.yaml` is in the root directory.
        *   YAML Syntax: Incorrect indentation or formatting. Use a YAML validator online to check.
        *   Missing critical config values (e.g., `job_site_type`, site-specific URLs). Check console/log errors.

*   **No Jobs Found:**
    *   **Configuration:** Double-check `job_site_type`, keywords (especially `required`), `filters.cities`, and site-specific URLs in `profiles.yaml`.
    *   **Selectors Changed:** Job sites frequently update their HTML structure. If selectors in `amazon_config.selectors` or `indeed_config.selectors` are outdated, the bot won't find job details. This is a common issue. You may need to update these by inspecting the website's current HTML (see Developer Guide or `configuring_page_identification.md`). Check logs for warnings from `identify_page_type` or errors during extraction.
    *   **Network/Site Issues:** The job site might be down, blocking your IP, or presenting an unexpected page (like a different type of CAPTCHA).
    *   **Too Restrictive Filters:** Your keywords/filters might be too narrow.

*   **Login Failures (Amazon):**
    *   **Credentials:** Verify `job_site_username` and that `encrypted_job_site_password` decrypts correctly when using a `master_password`.
    *   **CAPTCHA:** Amazon might present a CAPTCHA. The bot has limited CAPTCHA handling (relies on `page_signatures` to identify it and then requires manual intervention in the browser window it controls).
    *   **2FA Email Automation Issues:**
        *   `email_automation` not enabled or misconfigured in `profiles.yaml`.
        *   Incorrect IMAP server settings or app password.
        *   Email account's IMAP access might be disabled.
        *   Firewall blocking IMAP connections.
        *   Amazon changed the sender email or email format for 2FA codes.
        *   Check logs carefully for messages from `app.authenticator` or `BrowserActor` regarding email fetching.

*   **No Discord Notifications:**
    *   Verify `discord_webhook_url` is correct in `profiles.yaml`.
    *   Ensure the webhook is still valid and has permissions in your Discord server.

*   **Bot Seems Slow or "Sloppy":**
    *   **`check_interval_minutes`:** This determines how often the bot re-checks for a profile. Adjust as needed.
    *   **Page Signatures:** Very complex or numerous `page_signatures`, especially those relying heavily on `text_contains` on large page bodies, can slow down `identify_page_type`. Ensure signatures are as efficient as possible.
    *   **Website Performance:** The target website itself might be slow.

**Always check the bot's log files for detailed error messages and operational flow – they are your primary tool for diagnosing problems!**
