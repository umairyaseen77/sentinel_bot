# Configuration Guide

This guide provides a detailed explanation of the `profiles.yaml` configuration file used by the Automated Job Search Bot. This file allows you to define multiple job search profiles, each tailored to specific sites, keywords, locations, and other settings.

## File Format and Location

The configuration is managed in a YAML file named `profiles.yaml` located in the root directory of the project. You will need to create this file if it doesn't exist. It's recommended to copy an example file (e.g., `profiles.yaml.example`) if one is provided and then customize it.

YAML (YAML Ain't Markup Language) is a human-readable data serialization standard. Pay attention to indentation (usually 2 spaces) as it defines the structure.

## Main Structure

The `profiles.yaml` file typically contains a top-level key `profiles`, under which each job search profile is defined by a unique name (e.g., `my_amazon_python_search`).

```yaml
# profiles.yaml
profiles:
  profile_name_1:
    # ... settings for profile 1 ...
  profile_name_2:
    # ... settings for profile 2 ...
```

## Global Profile Settings

These settings are configured directly under each profile name (e.g., `profile_name_1`).

*   **`job_site_type`** (string, Mandatory)
    *   Specifies the job site to target for this profile.
    *   Supported values: `"amazon"`, `"indeed"`. (More can be added by developers).
    *   Example: `job_site_type: "indeed"`

*   **`check_interval_minutes`** (integer, Optional)
    *   The time in minutes the bot will wait before re-checking for jobs after completing a cycle for this profile.
    *   Default: `30`
    *   Example: `check_interval_minutes: 60`

*   **`max_retries`** (integer, Optional)
    *   The maximum number of times the bot will retry an operation (like session initialization or a step in authentication) after an error before giving up on that cycle for this profile.
    *   Default: `3`
    *   Example: `max_retries: 5`

*   **`discord_webhook_url`** (string, Optional)
    *   The Discord webhook URL to which new job notifications for this profile will be sent. If omitted, Discord notifications are disabled for this profile.
    *   Example: `discord_webhook_url: "https://discord.com/api/webhooks/your_webhook_id/your_webhook_token"`

*   **`keywords`** (dictionary, Optional)
    *   Defines keywords to filter job titles.
    *   `required: list[string]` (Optional): A list of keywords. Job titles *must* contain at least one of these keywords (case-insensitive).
    *   `optional: list[string]` (Optional): For some sites like Indeed, these keywords are added to the search query but are not strict requirements for filtering after results are fetched.
    *   `excluded: list[string]` (Optional): A list of keywords. Job titles containing any of these keywords (case-insensitive) will be excluded.
    *   Example:
        ```yaml
        keywords:
          required: ["Python Developer", "Software Engineer"]
          optional: ["Django", "Flask", "Remote"] # Used in Indeed search query
          excluded: ["Senior", "Lead", "Manager"]
        ```

*   **`filters`** (dictionary, Optional)
    *   Additional filters for job listings.
    *   `cities: list[string]` (Optional): A list of cities to search in. The bot will iterate through these cities. If empty or omitted, a generic search (no specific city) or a `default_location` might be used. Case-insensitive matching.
    *   Example:
        ```yaml
        filters:
          cities: ["London", "Manchester", "Remote"]
        ```

*   **`default_location`** (string, Optional)
    *   Used by some site integrations (like Indeed) if the `filters.cities` list is empty or not provided. This allows for a generic search focused on a broader area if no specific cities are listed.
    *   Example: `default_location: "United Kingdom"`

*   **`master_password`** (string, Optional)
    *   If you have encrypted sensitive information in your configuration (like `email_app_password` or site passwords starting with `enc:`), provide the master password here for decryption.
    *   **Security Note:** Storing the master password directly in the config file reduces the security of encrypted values. Consider environment variables or other secure means for production. For local use, this is convenient.
    *   Example: `master_password: "yourSecretMasterPassword"`

*   **`email_automation`** (dictionary, Optional)
    *   Settings for enabling 2-Factor Authentication (2FA) code retrieval from an email account (primarily for Amazon login).
    *   `enabled: bool` (Optional, Default: `false`): Set to `true` to enable this feature.
    *   `email_address: string`: The email address to monitor.
    *   `email_app_password: string`: The app password for the email account. **This can be stored encrypted (e.g., `"enc:your_encrypted_password"`) if a `master_password` is also provided for the profile.**
    *   `email_imap_server: string`: The IMAP server address (e.g., `"imap.gmail.com"`).
    *   `confirmation_email_sender: string`: The email address from which the 2FA/confirmation emails are expected (e.g., `"no-reply@amazon.com"`).
    *   `email_check_timeout_seconds: int` (Optional, Default: `90`): Total time to wait for the 2FA email.
    *   `email_polling_interval_seconds: int` (Optional, Default: `5`): How often to check the inbox for new emails.
    *   Example:
        ```yaml
        email_automation:
          enabled: true
          email_address: "your_email@gmail.com"
          email_app_password: "enc:your_encrypted_gmail_app_password" # Or plaintext: "yourGmailAppPassword"
          email_imap_server: "imap.gmail.com"
          confirmation_email_sender: "no-reply@amazon.com"
          email_check_timeout_seconds: 120
          email_polling_interval_seconds: 10
        ```

## Site-Specific Configuration Sections

Based on the `job_site_type`, you'll need to provide a corresponding site-specific configuration block (e.g., `amazon_config` if `job_site_type: "amazon"`).

### `amazon_config` (for `job_site_type: "amazon"`)

*   **`job_site_url`** (string, Mandatory)
    *   The base URL for the Amazon Jobs site you are targeting.
    *   Example: `job_site_url: "https://www.amazon.jobs"`
*   **`job_site_username`** (string, Optional)
    *   Username (email) for logging into Amazon Jobs. Required if login is desired.
*   **`amazon_password`** (string, Optional)
    *   Password for Amazon Jobs. Can be plaintext or encrypted (e.g., `"enc:your_encrypted_password"`) if a `master_password` is provided.
*   **`selectors`** (dictionary, Optional but Recommended for stable scraping)
    *   CSS selectors used to extract job details from Amazon search result pages.
    *   `job_card: string` (e.g., `"div[class*='job-tile'], div.job"`)
    *   `title: string` (e.g., `"h3[class*='job-title']"`)
    *   `company: string` (Optional, e.g., `"[class*='company-name']"`; often defaults to "Amazon")
    *   `location: string` (e.g., `"[class*='job-location']"`)
    *   `link: string` (e.g., `"a[class*='job-link']"`)
    *   Example:
        ```yaml
        amazon_config:
          job_site_url: "https://www.amazon.jobs"
          job_site_username: "your_amazon_email@example.com"
          amazon_password: "enc:your_encrypted_amazon_password"
          selectors:
            job_card: ".job-tile"
            title: ".job-title"
            location: ".location"
            link: "a.job-link"
          # cookie_modal_selectors and page_signatures would also go under amazon_config
        ```
*   **`cookie_modal_selectors`** (list[string], Optional)
    *   A list of CSS selectors used by the generic cookie handler (`_handle_cookie_modal_generic`) to find and click cookie consent buttons. This is used if `identify_page_type` detects a `PAGE_TYPE_COOKIE_MODAL`.
    *   Example: `cookie_modal_selectors: ["#sp-cc-accept", "button.accept-cookies"]`
*   **`page_signatures`** (list[dictionary], Optional but Recommended)
    *   Crucial for the "smart page handling" feature. This defines how the bot identifies different pages on the Amazon site (login steps, search results, etc.).
    *   Refer to the **[Page Identification System Guide](./configuring_page_identification.md)** for full details on structure and rules.
    *   Example (conceptual):
        ```yaml
        page_signatures:
          - page_type: "LOGIN_EMAIL"
            url_contains: ["/ap/signin"]
            element_exists: ["#ap_email"]
          # ... more signatures for PIN, OTP, CAPTCHA, SEARCH_RESULTS etc. ...
        ```

### `indeed_config` (for `job_site_type: "indeed"`)

*   **`base_url`** (string, Mandatory)
    *   The base URL for the Indeed site (e.g., "https://uk.indeed.com", "https://www.indeed.com").
    *   Example: `base_url: "https://uk.indeed.com"`
*   **`search_path`** (string, Mandatory)
    *   The path for job searches on Indeed.
    *   Example: `search_path: "/jobs"`
*   **`selectors`** (dictionary, Mandatory for scraping)
    *   CSS selectors used to extract job details from Indeed search result pages.
    *   `job_card: string` (e.g., `".jobsearch-SerpJobCard"`)
    *   `title: string` (e.g., `"h2.jobTitle > a"`)
    *   `company: string` (e.g., `"[data-testid='company-name']"`)
    *   `location: string` (e.g., `"[data-testid='text-location']"`)
    *   `link: string` (e.g., `"h2.jobTitle > a"`)
    *   `description_snippet: string` (e.g., `".job-snippet"`)
    *   Example:
        ```yaml
        indeed_config:
          base_url: "https://uk.indeed.com"
          search_path: "/jobs"
          selectors:
            job_card: ".jobsearch-SerpJobCard"
            title: "h2.jobTitle > a"
            company: "[data-testid='company-name']"
            location: "[data-testid='text-location']"
            link: "h2.jobTitle > a"
            description_snippet: ".job-snippet"
          # cookie_modal_selectors and page_signatures would also go under indeed_config
        ```
*   **`cookie_modal_selectors`** (list[string], Optional)
    *   Selectors for Indeed's cookie consent modal.
    *   Example: `cookie_modal_selectors: ["#onetrust-accept-btn-handler"]`
*   **`page_signatures`** (list[dictionary], Optional but Recommended)
    *   Defines how the bot identifies different pages on Indeed.
    *   Refer to the **[Page Identification System Guide](./configuring_page_identification.md)** for full details.
    *   Example (conceptual):
        ```yaml
        page_signatures:
          - page_type: "COOKIE_MODAL"
            element_exists: ["#onetrust-accept-btn-handler"]
            is_modal: true
          - page_type: "SEARCH_RESULTS"
            url_query_param_exists: ["q", "l"]
            element_exists: ["#resultsCol", ".jobsearch-SerpJobCard"]
          # ... more signatures ...
        ```

## Page Identification System (`page_signatures`)

This is a critical part of the configuration for robust bot operation. It allows the bot to "understand" what kind of page it's currently on.

**Please refer to the detailed [Page Identification System Guide](./docs/configuring_page_identification.md) for a full explanation of how to structure `page_signatures`, the available rule types (`url_matches`, `element_exists`, `text_contains`, etc.), and best practices for creating effective signatures.**

A brief summary of a signature object:
```yaml
- page_type: "TYPE_NAME"  # e.g., "LOGIN_EMAIL", "SEARCH_RESULTS"
  is_modal: false         # Optional, true if this signature is for a modal overlay
  url_matches: "regex_pattern" # Optional regex for full URL
  url_contains: ["substring1", "substring2"] # Optional, all must be in URL
  url_query_param_exists: ["param1", "param2"] # Optional, query params must exist
  element_exists: ["selector1", "selector2"] # Optional, ANY visible selector passes
  text_contains: ["text snippet1", "text snippet2"] # Optional, ALL must be in body text
  element_has_text: # Optional, ALL conditions must be met
    - selector: "css_selector_for_element1"
      text: "expected text in element1"
    - selector: "css_selector_for_element2"
      text: "expected text in element2"
```
The order of signatures in the `page_signatures` list matters, as the first matching signature determines the page type. Modals are checked first, then regular pages.

## Complete Profile Examples

### Example 1: Amazon Profile

```yaml
# profiles.yaml
profiles:
  amazon_python_london:
    job_site_type: "amazon"
    check_interval_minutes: 45
    discord_webhook_url: "YOUR_DISCORD_WEBHOOK_URL"
    master_password: "yourSecretMasterPassword" # Only if passwords below are encrypted
    keywords:
      required: ["Python", "Software Engineer"]
      excluded: ["Senior", "Principal", "Manager"]
    filters:
      cities: ["London, UK", "Cambridge, UK"]
    email_automation:
      enabled: true
      email_address: "your_email@gmail.com"
      email_app_password: "enc:your_encrypted_gmail_app_password"
      email_imap_server: "imap.gmail.com"
      confirmation_email_sender: "no-reply@amazon.com" # Adjust as needed
    amazon_config:
      job_site_url: "https://www.amazon.jobs" # Or specific regional amazon.jobs URL
      job_site_username: "your_amazon_jobs_email@example.com"
      amazon_password: "enc:your_encrypted_amazon_jobs_password"
      selectors:
        job_card: ".job-tile"
        title: ".job-title"
        location: ".location"
        link: "a" # Usually the whole card or title area is a link
      cookie_modal_selectors:
        - "#sp-cc-accept" # Example Amazon cookie button
      page_signatures:
        - page_type: "COOKIE_MODAL"
          element_exists: ["#sp-cc-accept"]
          is_modal: true
        - page_type: "LOGIN_EMAIL"
          url_contains: ["/ap/signin"]
          element_exists: ["#ap_email"]
        - page_type: "LOGIN_PIN" # Assuming Amazon uses PIN after email
          url_contains: ["/ap/signin"]
          element_exists: ["#ap_password"] # Amazon often uses 'password' ID for PIN too
          text_contains: ["Password"] # Differentiator if email and pin page are similar
        - page_type: "OTP_VERIFICATION"
          element_exists: ["#cvf-input-code"]
          text_contains: ["Verification required", "One Time Password"]
        - page_type: "CAPTCHA"
          element_exists: ["#captchacharacters"]
        - page_type: "SEARCH_RESULTS"
          url_contains: ["/app#/jobSearch", "/jobs"] # Amazon URL can vary
          element_exists: [".job-tile-lists", ".search-results-container"]
```

### Example 2: Indeed Profile

```yaml
# profiles.yaml
profiles:
  indeed_python_remote:
    job_site_type: "indeed"
    check_interval_minutes: 60
    discord_webhook_url: "YOUR_DISCORD_WEBHOOK_URL"
    keywords:
      required: ["Python Developer"]
      optional: ["Remote", "Backend"] # Added to search query
      excluded: ["Intern", "Junior"]
    filters:
      cities: ["Remote"] # Indeed handles "Remote" well as a location
    # default_location: "United Kingdom" # If cities was empty
    indeed_config:
      base_url: "https://uk.indeed.com"
      search_path: "/jobs"
      selectors:
        job_card: ".jobsearch-SerpJobCard"
        title: "h2.jobTitle > a"
        company: "[data-testid='company-name']"
        location: "[data-testid='text-location']"
        link: "h2.jobTitle > a"
        description_snippet: ".job-snippet"
      cookie_modal_selectors:
        - "#onetrust-accept-btn-handler"
      page_signatures:
        - page_type: "COOKIE_MODAL"
          element_exists: ["#onetrust-accept-btn-handler"]
          is_modal: true
        - page_type: "SEARCH_RESULTS"
          element_exists: ["#resultsCol", ".jobsearch-SerpJobCard", "#mosaic-provider-jobcards"] # Common Indeed containers/cards
          url_contains: ["/jobs", "/q-"] # Indeed search result URLs
        - page_type: "CAPTCHA"
          element_exists: ["iframe[title*='captcha']", ".h-captcha-challenge", "#recaptcha-anchor"]
          url_contains: ["/challenge", "/account/login"] # Captcha can appear on login too
```

This guide should provide users with the necessary information to configure the bot effectively. Remember to replace placeholder values with your actual data.
