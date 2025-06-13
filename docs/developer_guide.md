# Developer Guide

This guide is for developers looking to understand the codebase of the Automated Job Search Bot, contribute to its development, or extend its functionality—particularly by adding support for new job sites.

## Code Structure Overview

The project is organized into several key directories and files:

-   **`app/`**: The main Python package containing the core application logic.
    -   `main.py`: Contains the `run_bot` function, which orchestrates the execution of a single job search profile, managing its lifecycle, threading, and interaction with other components.
    -   `browser_actor.py`: The heart of the browser automation. This class manages Playwright browser instances, handles navigation, site interactions (login, search, scraping), and implements the smart page identification system (`identify_page_type`). Site-specific logic is largely contained or dispatched from here.
    -   `state_manager.py`: Manages an SQLite database to keep track of jobs that have already been seen and notified, preventing duplicate alerts.
    -   `logger.py`: Configures the application-wide logger.
    -   `notifier.py`: Handles sending notifications, currently implemented for Discord webhooks.
    -   `authenticator.py`: A standalone utility for fetching 2FA codes from an IMAP email account. Note that `BrowserActor` also has its own internal method for email 2FA specific to its flow.
    -   `security.py`: Provides utility functions for encrypting and decrypting sensitive configuration data (like passwords).
-   **`docs/`**: Contains detailed documentation files, including this guide.
-   **`profiles.yaml`** (example name): The main YAML configuration file where users define job search profiles and bot settings. (This file needs to be created by the user).
-   **`requirements.txt`**: Lists all Python dependencies required for the project.
-   **`run_gui.py`** (or similar, e.g., `main_cli.py`): The main entry point script to start the application.
-   **`tests/`**: Contains unit tests.
    -   `unit/`: Unit tests for specific modules and functions that do not require live browser interaction.

## Adding Support for a New Job Site

Extending the bot to support a new job site involves changes in configuration and Python code, primarily within `BrowserActor`.

### Step 1: Update Configuration (`profiles.yaml`)

1.  **Define a New `job_site_type`:**
    Choose a simple, unique string identifier for the new site (e.g., `"linkedin"`, `"my_custom_board"`).

2.  **Create a Site-Specific Configuration Block:**
    Add a new top-level key to your profile in `profiles.yaml` named `[new_site_type]_config` (e.g., `linkedin_config:`). Inside this block, you'll define parameters specific to the new site:
    *   **`base_url`**: The main URL for the site (e.g., `"https://www.linkedin.com"`).
    *   **`search_path`**: If the site uses a specific path for searches (like Indeed's `/jobs`).
    *   **Other URLs**: Any other key URLs needed (e.g., login page URL if not easily navigable).
    *   **`selectors`**: A dictionary of CSS selectors crucial for scraping job data. Common selectors include:
        *   `job_card`: Selector for the main container of individual job listings.
        *   `title`: Selector for the job title.
        *   `company`: Selector for the company name.
        *   `location`: Selector for the job location.
        *   `url`: Selector for the direct link to the job posting.
        *   `description_snippet`: (Optional) Selector for a brief job description.
    *   **`cookie_modal_selectors`**: (Optional) A list of CSS selectors for cookie consent buttons if the site has a cookie modal that needs to be handled by the generic `_handle_cookie_modal_generic` method.
    *   **`page_signatures`**: (Highly Recommended) A list of page signature objects. This is essential for the `identify_page_type()` system to correctly recognize different pages on the new site (e.g., search results, login pages, cookie modals). Refer extensively to the [Page Identification System Guide](./configuring_page_identification.md) for how to structure these.

    Example for a hypothetical `mycustomsite_config`:
    ```yaml
    mycustomsite_config:
      base_url: "https://jobs.mycustomsite.com"
      selectors:
        job_card: "div.job-listing-item"
        title: "h2.job-title"
        company: "span.company-name"
        location: "span.job-location"
        url: "a.job-details-link"
      cookie_modal_selectors: ["button#accept-cookies-btn"]
      page_signatures:
        - page_type: "COOKIE_MODAL"
          element_exists: ["button#accept-cookies-btn"]
          is_modal: true
        - page_type: "SEARCH_RESULTS"
          url_contains: ["/search/results"]
          element_exists: ["div.search-results-list"]
        # ... other signatures for login, etc., if applicable
    ```

### Step 2: Extend `BrowserActor.run_job_search_session`

This method in `app/browser_actor.py` orchestrates the job search process. You'll need to add a new branch to its main conditional logic:

```python
# In BrowserActor.run_job_search_session
# ...
elif job_site_type == '[new_site_type]': # Your new site type string
    log.info(f"Running [New Site Name] job search session.")
    # Get keywords and cities from self.config as done for Indeed/Amazon
    # ...

    if cities:
        for city_to_search in cities:
            log.info(f"Searching [New Site Name] jobs for keywords '{' '.join(combined_keywords)}' in: {city_to_search}")
            if not self.navigate_to_[new_site_type]_job_search(combined_keywords, city_to_search):
                log.error(f"Failed to navigate to [New Site Name] for location: {city_to_search}.")
                continue
            # Optional: Call login method if this site requires login per city or search
            # jobs_from_city = self.login_and_extract_[new_site_type](...)
            jobs_from_city = self.extract_[new_site_type]_job_listings()
            all_scraped_jobs.extend(jobs_from_city)
    else: # Generic search
        log.info(f"Performing generic [New Site Name] job search...")
        default_loc = self.config.get('default_location', "") # Or site-specific default
        if not self.navigate_to_[new_site_type]_job_search(combined_keywords, default_loc):
            # handle error
            pass
        jobs_from_generic_search = self.extract_[new_site_type]_job_listings()
        all_scraped_jobs.extend(jobs_from_generic_search)
# ...
```

### Step 3: Implement New Site-Specific Methods in `BrowserActor`

Create the following methods within the `BrowserActor` class:

1.  **`navigate_to_[new_site_type]_job_search(self, keywords: list, location: str) -> bool`**
    *   Construct the correct search URL for the new site using `base_url`, `search_path` (if any), keywords, and location (remember to URL-encode parameters using `urllib.parse.quote_plus`).
    *   Use `self.page.goto(search_url, wait_until="domcontentloaded")`.
    *   After navigation, call `page_type = self.identify_page_type()`. Log a warning if `page_type` is not `PAGE_TYPE_SEARCH_RESULTS` (or `PAGE_TYPE_UNKNOWN` as a fallback during development). This confirms you've landed on what you expect to be a search results page.
    *   Handle any very simple, site-specific initial interactions here if they are not covered by the generic dispatcher (e.g., a unique welcome popup that isn't a standard cookie modal).
    *   Return `True` on success, `False` on failure.

2.  **`extract_[new_site_type]_job_listings(self) -> list`**
    *   Call `page_type = self.identify_page_type()` at the beginning. If not `PAGE_TYPE_SEARCH_RESULTS` (or `PAGE_TYPE_UNKNOWN`), log an error and return an empty list.
    *   Fetch the site-specific selectors from `self.config.get('[new_site_type]_config', {}).get('selectors', {})`.
    *   Use `self.page.wait_for_selector(job_card_selector, timeout=...)` to ensure job cards are present.
    *   Get all job card elements: `job_elements = self.page.locator(job_card_selector).all()`.
    *   Loop through `job_elements`. For each element:
        *   Extract `title`, `company`, `location`, the job `url`, and `description` using the configured selectors and Playwright's `element.locator().first.text_content()` or `element.locator().first.get_attribute('href')`.
        *   Use `try-except` blocks for each piece of data to handle cases where a selector might not find an element in a particular card.
        *   Ensure URLs are absolute using `urllib.parse.urljoin(base_url, relative_link)`.
        *   Append a dictionary of the extracted job data (`{"url": ..., "title": ..., "company": ...}`) to a list. Include `source: '[New Site Name]'`.
    *   Return the list of job dictionaries.

3.  **Login Methods (If Applicable)**
    *   If the new site requires login:
        *   `login_[new_site_type](self) -> bool`: Handles the sequence of actions to initiate login (e.g., clicking a login button).
        *   `perform_[new_site_type]_auth_flow(self) -> bool`: Manages the multi-step authentication process, using `self.identify_page_type()` and site-specific `page_signatures` to navigate through login stages (email, password, 2FA, CAPTCHA). This will be similar in structure to `perform_multi_step_authentication` for Amazon.
        *   You may need specific handlers like `handle_[new_site_type]_password_entry()`.

### Step 4: Testing

*   Create a new profile in `profiles.yaml` specifically for your new site.
*   Define comprehensive `page_signatures` for all relevant pages (search results, login steps, cookie modals, captchas). This is often iterative.
*   Define accurate `selectors` for job data extraction.
*   Run the bot with this profile.
*   Closely monitor logs from `BrowserActor`, especially `identify_page_type` messages, to debug your signatures and selectors.
*   Adjust configurations until job search and extraction work reliably.

## Logging Conventions

-   The application uses a centralized logger configured in `app/logger.py`.
-   Import and use it in modules via `from .logger import log`.
-   Standard levels:
    -   `log.info()`: General operational information.
    -   `log.debug()`: Detailed information for debugging.
    -   `log.warning()`: Potential issues or non-critical errors.
    -   `log.error()`: Errors that affect an operation but might allow the bot to continue or retry.
    -   `log.exception()` or `log.error(..., exc_info=True)`: For logging errors with full stack traces, especially in `try-except` blocks.

## Error Handling Philosophy

-   Employ `try-except` blocks for operations prone to failure, such as network requests (`page.goto()`, API calls), browser interactions (`element.click()`, `element.fill()`), and file/database operations.
-   Log errors clearly, providing context. Use `exc_info=True` for unexpected exceptions to capture stack traces.
-   The `BrowserActor` includes retry logic for session initialization and authentication steps, configured by `max_retries` in the profile.
-   Fail gracefully: If a profile experiences repeated critical errors, it should stop after `max_retries` and not impact other profiles (if running concurrently in a multi-profile setup not yet implemented in `main.py`).

## Unit Testing

-   Unit tests for utility functions and non-browser-dependent logic are located in `tests/unit/`.
-   Tests are written using Python's `unittest` module.
-   When adding new utility functions or complex business logic that doesn't directly involve Playwright's `page` object, please include corresponding unit tests.
-   Run tests from the project root: `python -m unittest discover tests`

This guide should provide a solid starting point for developers wishing to extend or maintain the bot.
