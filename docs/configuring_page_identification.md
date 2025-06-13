# Configuring and Testing `identify_page_type` in BrowserActor

## 1. Overview of the `identify_page_type` System

The `identify_page_type()` method in `BrowserActor` is a crucial component for making web page recognition robust and adaptable across different job sites (e.g., Amazon, Indeed) and for various page states within those sites (e.g., login pages, search results, cookie modals).

**Purpose:**
*   To reliably determine the type of page the browser is currently on.
*   To move page identification logic from hardcoded checks within methods to a configurable system.
*   To enable more intelligent and context-aware actions by the bot.

**Mechanism:**
The system relies on a list called `page_signatures` defined within site-specific configuration sections (e.g., `amazon_config: { page_signatures: [...] }` or `indeed_config: { page_signatures: [...] }`) in your main configuration file (e.g., `profiles.yaml` or a dedicated site config YAML). Each "signature" is a set of rules that, if all met, define a specific page type.

## 2. Structure of `page_signatures`

A `page_signatures` entry is a list of dictionaries, where each dictionary represents one page signature.

**Example YAML/Dictionary Structure:**

```yaml
# Example for amazon_config (or indeed_config, etc.)
page_signatures:
  - page_type: "COOKIE_MODAL" # Must match a BrowserActor.PAGE_TYPE_* constant
    is_modal: true             # Important for modals
    element_exists:
      - "#cookie-consent-banner" # Check if this element is visible
      - "[data-testid='cookie-accept-button']" # OR this one
    # No URL checks needed if the modal can appear on many pages

  - page_type: "LOGIN_EMAIL"   # For Amazon's email/username entry page
    url_contains: ["/ap/signin"]
    element_exists:
      - "input#ap_email"
      - "form[name='signIn']"
    text_contains:
      - "Sign-In" # Check if "Sign-In" text is present in the body
    # is_modal: false (or omitted, as false is default)

  - page_type: "LOGIN_PIN"     # For Amazon's PIN entry page
    url_contains: ["/ap/signin"] # Often same URL as email, but different elements
    element_exists:
      - "input#ap_pin_mobile_field" # Specific PIN field
      - "input#signInSubmit"        # Submit button for PIN
    text_contains:
      - "Enter your PIN"

  - page_type: "SEARCH_RESULTS"
    url_query_param_exists: ["q", "l"] # For Indeed (e.g., /jobs?q=developer&l=london)
                                     # For Amazon, might be a path component like '/app#/jobSearch'
    element_exists:
      - ".jobsearch-SerpJobCard"  # Indeed job card selector
      - "#job-results-list"       # Example Amazon job results container
    # No text_contains needed if elements are strong indicators

  - page_type: "ACCESS_DENIED"
    text_contains:
        - "Sorry, we couldn't find that page" # Example text on an access denied page
        - "Access Denied"
    element_exists:
        - "img[alt='Access Denied']"
```

**Signature Rule Types:**

*   `page_type` (string, **mandatory**): The identifier for the page type. This **must** correspond to one of the `BrowserActor.PAGE_TYPE_*` class constants (e.g., `PAGE_TYPE_LOGIN_PIN`, `PAGE_TYPE_SEARCH_RESULTS`).
*   `is_modal` (boolean, optional, defaults to `false`): Set to `true` if the signature is for a modal dialog (like a cookie banner or a popup) that might overlay other page content. Modal signatures are checked first.
*   `url_matches` (string, optional): A Python regex pattern that the *full current URL* must match.
*   `url_contains` (list of strings, optional): A list of substrings. *All* substrings must be present in the current URL (case-insensitive check on the URL, which is already lowercased by `identify_page_type`).
*   `url_query_param_exists` (list of strings, optional): A list of query parameter *names*. All specified parameter names must exist in the URL's query string (e.g., for `?q=dev&l=lon`, `["q", "l"]` would match). Values are not checked.
*   `element_exists` (list of CSS selectors, optional): A list of CSS selectors. The rule passes if **any one** of these selectors is found and the element is visible on the page within the `default_timeout` (currently 1 second). This implements OR logic for selectors.
*   `text_contains` (list of strings, optional): A list of text snippets. *All* snippets must be present in the page's `body` text content (case-insensitive). This can be performance-intensive and should be used with stable, unique text.
*   `element_has_text` (list of dictionaries, optional): Each dictionary must have `selector` (string) and `text` (string). *All* specified elements must be found, be visible, and their text content must contain the respective text snippet (case-insensitive). This is more targeted than `text_contains`.
    *   Example: `element_has_text: [{selector: "h1", text: "Sign In"}, {selector: "button#continue", text: "Continue"}]`

**Order of Evaluation:**
1.  **Modal Signatures First:** Signatures with `is_modal: true` are evaluated before regular page signatures. This allows the system to identify and potentially handle overlays (like cookie modals) before trying to determine the main page content.
2.  **Order in List Matters:** Within both modal and regular groups, signatures are evaluated in the order they appear in the `page_signatures` list. The first signature where all its defined rules match for the current page will determine the page type. Therefore, more specific signatures should generally be placed before more generic ones.

## 3. Guidance on Creating Effective Signatures

*   **Prioritize Unique & Stable Selectors:**
    *   IDs (`#some-id`) are usually the most stable.
    *   Specific `data-testid` attributes (e.g., `[data-testid='login-button']`) are excellent if available.
    *   Combine classes or attributes for specificity if IDs are not present (e.g., `form.login-form input[name='username']`). Avoid relying solely on generic tag names (`div`, `span`) or highly dynamic classes.
*   **Use URL Checks Strategically:**
    *   `url_contains` is good for distinctive path segments (e.g., `/ap/signin`, `/jobs/results`).
    *   `url_matches` (regex) offers more power for complex patterns but can be harder to maintain.
    *   `url_query_param_exists` is useful for pages differentiated by query parameters (e.g., search result pages).
*   **Use Text Checks Wisely:**
    *   `text_contains` (full body scan) can be slow and brittle if text changes often. Use it for highly stable and unique phrases.
    *   `element_has_text` is preferred for verifying text within specific elements, making it more robust than a general body scan.
*   **Test Selectors:** Use browser developer tools (Elements/Inspector tab, Console) to test your CSS selectors on the live site to ensure they are correct and identify the intended elements uniquely.
*   **Iterative Refinement:** Start with simple, obvious rules and add more as needed for differentiation. It's an iterative process.

## 4. How `identify_page_type` is Used

The `identify_page_type()` method is becoming the central point for page recognition:

*   **Authentication (`perform_multi_step_authentication` for Amazon):** This method now directly calls `identify_page_type()` in its loop to determine which authentication step it's on (e.g., `PAGE_TYPE_LOGIN_PIN`, `PAGE_TYPE_OTP_VERIFICATION`, `PAGE_TYPE_CAPTCHA`) and calls the appropriate handler (e.g., `handle_pin_entry()`).
*   **Navigation Methods (e.g., `navigate_to_job_search`, `navigate_to_indeed_job_search`):** After attempting to navigate to a page, these methods call `identify_page_type()` to verify if they landed on the expected page type (e.g., `PAGE_TYPE_SEARCH_RESULTS`). Warnings are logged if an unexpected page type is encountered.
*   **Extraction Methods (e.g., `extract_job_listings`, `extract_indeed_job_listings`):** These methods call `identify_page_type()` at the beginning to ensure they are on a `PAGE_TYPE_SEARCH_RESULTS` page before attempting to find and extract job data. If not, they log an error and return empty results.
*   **Action Dispatcher (`run_job_search_session`):** A new dispatcher logic at the start of `run_job_search_session` uses `identify_page_type()` to detect common preliminary pages (like `PAGE_TYPE_COOKIE_MODAL`). If a handler is registered for that page type in `self.page_type_handlers`, it's executed (e.g., `_handle_cookie_modal_generic`).

## 5. Testing and Debugging Signatures

Testing `page_signatures` is primarily done by running the bot against the live websites for which the signatures are defined.

*   **Check Bot Logs:**
    *   `identify_page_type()` logs the page type it detects (e.g., "Page type detected: LOGIN_PIN for https://...").
    *   It also logs if no specific signature matched ("No specific page type detected... Returning UNKNOWN.").
    *   Navigation and extraction methods log warnings or errors if `identify_page_type()` returns an unexpected type.
*   **Debugging Misidentification:**
    1.  **Observe Bot Behavior:** Note where the bot gets stuck or performs an incorrect action.
    2.  **Examine Logs:** Check what `identify_page_type()` reported for the problematic page.
    3.  **Inspect Live Page:** Open the problematic URL in your own browser. Use developer tools to:
        *   Verify the current URL matches the `url_matches` or `url_contains` rules.
        *   Test `element_exists` selectors in the console (e.g., `document.querySelectorAll("your_selector").length`). Ensure they are unique enough and visible.
        *   Check if `text_contains` snippets are actually present in the body text.
        *   Verify `element_has_text` selectors and their corresponding text.
    4.  **Adjust Signatures:**
        *   Modify selectors for better stability or uniqueness.
        *   Refine URL patterns.
        *   Adjust or remove text checks if they are too brittle.
        *   Add new, more specific signatures if needed.
        *   Re-order signatures if a more generic one is matching before a more specific one.
    5.  **Timeout Consideration:** Remember that `element_exists` and other element-based checks in `identify_page_type` use a `default_timeout` (currently 1000ms or 1 second). If elements load slower than this, they won't be found. This timeout is for quick identification; handlers for specific page types might use longer, more patient waits if necessary.

## 6. Example: Configuring `cookie_modal_selectors`

The `_handle_cookie_modal_generic` method relies on `cookie_modal_selectors` being defined in the site-specific configuration. This allows the dispatcher to automatically handle cookie popups if `identify_page_type` correctly identifies a `PAGE_TYPE_COOKIE_MODAL` based on its `page_signatures`.

**Example for `indeed_config` in your YAML:**

```yaml
indeed_config:
  base_url: "https://uk.indeed.com"
  search_path: "/jobs"
  # ... other indeed selectors for job extraction ...

  cookie_modal_selectors:  # Used by _handle_cookie_modal_generic
    - "#onetrust-accept-btn-handler"
    - "button[data-testid='cookie-accept-button']"
    # Add other common cookie button selectors for Indeed if they vary

  page_signatures:
    - page_type: "COOKIE_MODAL"
      is_modal: true
      element_exists:
        - "#onetrust-banner-sdk"       # The main banner for the cookie modal
        - "#onetrust-accept-btn-handler" # The accept button itself
      # No URL specific checks, as it can appear on many pages

    - page_type: "SEARCH_RESULTS"
      url_query_param_exists: ["q", "l"] # e.g. /jobs?q=...&l=...
      element_exists:
        - ".jobsearch-SerpJobCard" # Primary job card indicator for Indeed
        - "#resultsCol"            # Main column for results

    # ... other Indeed page signatures (login, job details etc. if needed) ...
```

By defining `cookie_modal_selectors` and a corresponding `PAGE_TYPE_COOKIE_MODAL` signature, the dispatcher system can automatically attempt to close cookie popups when they are detected.
Remember to define similar `cookie_modal_selectors` and `page_signatures` for `amazon_config` and any other sites.
```
