# Automated Job Search Bot

## Overview

This project is an automated bot designed to search for job listings across multiple platforms (currently supporting Amazon Jobs and Indeed), filter them based on user-defined criteria, and send notifications for new matching jobs via Discord. It aims to streamline the job search process by automating repetitive tasks.

## Key Features

-   **Multi-Site Support:** Capable of searching on different job platforms (e.g., Amazon Jobs, Indeed).
-   **Configurable Profiles:** Allows users to define multiple job search profiles, each with its own set of keywords, location filters, target sites, and notification settings.
-   **Advanced Filtering:** Supports required and excluded keywords, as well as city-based location filtering.
-   **Discord Notifications:** Sends alerts for new, relevant job listings directly to a configured Discord webhook.
-   **Automated Login & 2FA:** Handles login processes for sites like Amazon, including support for 2-Factor Authentication code retrieval via email (Gmail currently supported).
-   **Smart Page Identification:** Utilizes a configurable system to intelligently identify different page types (login, search results, cookie modals, etc.) for more robust browser automation.
-   **Extensible Design:** Built with future expansion to other job sites in mind.

## Tech Stack

-   Python 3.8+
-   Playwright for browser automation
-   PyYAML for configuration management
-   SQLite for state management (seen jobs)

## Directory Structure

-   `app/`: Core application logic (browser interaction, authentication, main bot process, etc.).
-   `docs/`: Detailed documentation files.
-   `profiles.yaml` (example name): Main YAML configuration file for profiles and settings. (You will need to create this file).
-   `requirements.txt`: Python dependencies.
-   `run_gui.py`: (Assumed) Main script to run the bot with a GUI.
-   `tests/`: Unit tests for utility functions.

## Prerequisites

-   Python (3.8 or newer recommended)
-   `pip` (Python package installer)
-   Git (for cloning the repository)
-   Access to a terminal or command line interface

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright Browsers:**
    Playwright needs to download browser binaries. Run the following command:
    ```bash
    playwright install --with-deps
    # Or, to install only chromium (if that's all you need):
    # playwright install chromium
    ```

5.  **Create a Sample Profile File:**
    The scripts expect a JSON profile at `data/profiles.json`. Create the file with minimal fields:
    ```json
    {
      "Umair": {
        "job_site_url": "https://www.jobsatamazon.co.uk/",
        "job_site_username": "your-email@example.com",
        "job_site_password": "your-password"
      }
    }
    ```
    Adjust the values to match your credentials.

## Configuration

The bot is configured using a YAML file, typically named `profiles.yaml`, located in the root directory. You will need to create this file.

-   **Example File:** If an example configuration file (e.g., `profiles.yaml.example`) is provided in the repository, copy it to `profiles.yaml` and modify it according to your needs. Otherwise, you'll need to create it from scratch.
-   **Detailed Guide:** For a comprehensive explanation of all configuration options, including profile setup, site-specific settings (Amazon, Indeed), keyword/filter configuration, Discord webhook setup, and email automation for 2FA, please refer to the [Configuration Guide](./docs/configuration_guide.md).
-   **Page Identification:** Understanding how the bot identifies pages is key for advanced configuration. See the [Page Identification Guide](./docs/configuring_page_identification.md).

## Running the Bot

To run the bot (assuming a GUI entry point `run_gui.py`):
```bash
python run_gui.py
```
If there's a different main script, use that instead (e.g., `python main.py`).

`run_gui.py` launches a Tkinter-based window and therefore requires access to a
graphical display. On a headless server the script may fail to start unless you
provide a virtual display (e.g., via `xvfb-run`) or connect through remote
desktop.

```bash
xvfb-run -a python run_gui.py
```

If you have already created your profiles with the GUI you can run the bot
without the interface using the command-line helper:

```bash
python manual_run.py
```
This reads the profiles stored in `data/profiles.json` and runs the automation
directly in the console.

Check the console output and log files (e.g., in a `logs` directory or `automation_test.log`) for activity, status updates, and any errors.

## Documentation

For more detailed information, please refer to the following documents in the `docs/` directory:

-   **[Configuration Guide](./docs/configuration_guide.md):** Full details on setting up `profiles.yaml`.
-   **[Page Identification System](./docs/configuring_page_identification.md):** How to configure page signatures for robust automation.
-   **[Developer Guide](./docs/developer_guide.md):** Information for developers, including how to add support for new job sites.
-   **[User Setup and Usage Guide](./docs/user_guide_setup.md):** Detailed steps for installation, configuration, and common troubleshooting.

## Contributing

(Optional: Add guidelines here if you wish to accept contributions, e.g., "Contributions are welcome! Please fork the repository and submit a pull request.")

## License

(Optional: Specify your project's license here, e.g., "This project is licensed under the MIT License.")
