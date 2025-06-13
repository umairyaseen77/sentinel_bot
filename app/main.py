import time
import threading
import queue
import datetime
from .logger import log
from .state_manager import StateManager
from .notifier import Notifier
from .browser_actor import BrowserActor
from typing import List, Dict

def filter_jobs(jobs: List[Dict[str, str]], keywords_config: Dict, filters_config: Dict = None) -> List[Dict[str, str]]:
    """
    Filters jobs based on required/excluded keywords and location filters.
    """
    if not jobs:
        return []

    filtered_jobs = []
    
    # Get keyword filters
    required_keywords = [k.lower() for k in keywords_config.get('required', [])]
    excluded_keywords = [k.lower() for k in keywords_config.get('excluded', [])]
    
    # Get location filters from the 'filters' dictionary
    allowed_cities = []
    if filters_config and filters_config.get('cities'):
        allowed_cities = [city.lower() for city in filters_config['cities']]
    
    for job in jobs:
        title_lower = job.get('title', '').lower()
        description_lower = job.get('description', '').lower()
        job_text = title_lower + " " + description_lower
        location_lower = job.get('location', '').lower()
        
        # Check required keywords (at least one must be present in title or description)
        if required_keywords and not any(keyword in job_text for keyword in required_keywords):
            log.debug(f"Skipping job '{job['title']}' - no required keywords found")
            continue
            
        # Check excluded keywords (none should be present in title or description)
        if excluded_keywords and any(keyword in job_text for keyword in excluded_keywords):
            log.debug(f"Skipping job '{job['title']}' - contains excluded keyword")
            continue
        
        # Check location filter
        if allowed_cities and not any(city in location_lower for city in allowed_cities):
            log.debug(
                f"Skipping job '{job['title']}' in '{job.get('location')}' - location not in allowed list: {allowed_cities}"
            )
            continue
            
        filtered_jobs.append(job)
        
    return filtered_jobs

def run_bot(
    profile_name: str,
    profile_config: Dict,
    master_password: str,
    stop_event: threading.Event,
    status_queue: queue.Queue,
    log_queue: queue.Queue | None = None,
):
    """
    Main function to run the Sentinel Bot for a specific profile.
    This function is stateless and receives all config as arguments.
    """
    log.info(f"--- Sentinel Bot Thread Starting for Profile: {profile_name} ---")
    
    # Unpack config
    check_interval_minutes = profile_config.get("check_interval_minutes", 30)
    sleep_interval_seconds = check_interval_minutes * 60
    max_retries = profile_config.get("max_retries", 3)
    error_sleep_seconds = 5 * 60 # Sleep for 5 minutes on error

    # Initialize components with profile-specific config
    state_manager = StateManager(profile_name)
    notifier = Notifier(profile_config.get("discord_webhook_url"))
    # Pass master_password to BrowserActor for decryption
    browser_actor = BrowserActor(profile_config, master_password)

    retry_count = 0
    
    while not stop_event.is_set():
        try:
            log.info(f"[{profile_name}] Starting new job search session...")
            status_queue.put({"type": "status", "value": "Searching..."})
            
            # The browser_actor now handles the entire session internally
            scraped_jobs = browser_actor.run_job_search_session()

            # Normalize job entries to use 'url' as the key for links
            for job in scraped_jobs:
                if 'url' not in job and job.get('link'):
                    job['url'] = job.get('link')
            
            status_queue.put({"type": "last_checked", "value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            log.info(f"[{profile_name}] Session finished. Scraped {len(scraped_jobs)} total jobs.")

            # Get already seen job URLs from the database
            seen_urls = state_manager.get_seen_urls()

            # Filter out jobs that have already been seen using the normalized URL
            new_jobs = [job for job in scraped_jobs if job.get('url') and job['url'] not in seen_urls]
            
            if not new_jobs:
                log.info(f"[{profile_name}] No new job listings found.")
            else:
                log.info(f"[{profile_name}] Found {len(new_jobs)} new listings (before filtering).")
                
                # Apply keyword and location filters to the new jobs
                filtered_new_jobs = filter_jobs(
                    new_jobs,
                    profile_config.get("keywords", {}),
                    profile_config.get("filters", {})
                )
                
                if filtered_new_jobs:
                    log.info(f"[{profile_name}] Found {len(filtered_new_jobs)} new jobs matching filters. Notifying...")
                    status_queue.put({"type": "jobs_found", "value": len(filtered_new_jobs)})
                    
                    for job in filtered_new_jobs:
                        notifier.send_new_job_alert(job)
                else:
                    log.info(f"[{profile_name}] No new jobs matched the configured filters.")

                # Save all new (unfiltered) job URLs to the database to prevent re-notifying
                state_manager.save_jobs(new_jobs)

            # Reset retry count after a successful run
            retry_count = 0
            
            log.info(f"[{profile_name}] Sleeping for {check_interval_minutes} minutes...")
            status_queue.put({"type": "status", "value": f"Sleeping..."})
            stop_event.wait(sleep_interval_seconds)

        except Exception as e:
            log.exception(f"[{profile_name}] An unexpected error occurred in the main loop (attempt {retry_count + 1}/{max_retries}).")
            retry_count += 1
            
            if retry_count >= max_retries:
                log.error(f"[{profile_name}] Max retries exceeded. Bot for this profile will stop.")
                notifier.send_critical_alert(f"Bot for profile '{profile_name}' stopped after {max_retries} consecutive errors.")
                status_queue.put({"type": "status", "value": "Stopped (Error)"})
                break
            
            notifier.send_critical_alert(f"Error in profile '{profile_name}' (retry {retry_count}/{max_retries}): {e}")
            log.info(f"[{profile_name}] Waiting for {error_sleep_seconds / 60:.0f} minutes before retrying.")
            status_queue.put({"type": "status", "value": f"Error, retrying..."})
            stop_event.wait(error_sleep_seconds)

    log.info(f"[{profile_name}] Thread received stop signal. Cleaning up...")
    state_manager.close()
    log.info(f"--- Sentinel Bot Thread Stopped for Profile: {profile_name} ---")
