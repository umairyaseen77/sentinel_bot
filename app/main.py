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
    
    # Get location filters
    allowed_cities = []
    if filters_config and filters_config.get('cities'):
        allowed_cities = [city.lower() for city in filters_config['cities']]
    
    for job in jobs:
        title_lower = job['title'].lower()
        location_lower = job.get('location', '').lower()
        
        # Check required keywords (at least one must be present)
        if required_keywords and not any(keyword in title_lower for keyword in required_keywords):
            log.debug(f"Skipping job '{job['title']}' - no required keywords found")
            continue
            
        # Check excluded keywords (none should be present)
        if excluded_keywords and any(keyword in title_lower for keyword in excluded_keywords):
            log.debug(f"Skipping job '{job['title']}' - contains excluded keyword")
            continue
        
        # Check location filter
        if allowed_cities and not any(city in location_lower for city in allowed_cities):
            log.debug(f"Skipping job '{job['title']}' in '{job.get('location')}' - location not in allowed list")
            continue
            
        filtered_jobs.append(job)
        
    return filtered_jobs

def run_bot(profile_name: str, profile_config: Dict, stop_event: threading.Event, status_queue: queue.Queue):
    """
    Main function to run the Sentinel Bot for a specific profile.
    This function is stateless and receives all config as arguments.
    """
    log.info(f"--- Sentinel Bot Thread Starting for Profile: {profile_name} ---")
    
    # Unpack config with new structure
    check_interval_minutes = profile_config.get("check_interval_minutes", 30)
    sleep_interval_default = check_interval_minutes * 60  # Convert to seconds
    sleep_interval_error = profile_config.get("max_retries", 3) * 60  # Error sleep based on retries
    max_retries = profile_config.get("max_retries", 3)

    # Initialize components with profile-specific config
    state_manager = StateManager(profile_name)
    notifier = Notifier(profile_config.get("discord_webhook_url"))
    browser_actor = BrowserActor(profile_config)

    retry_count = 0
    
    try:
        log.info("Attempting initial session setup...")
        status_queue.put({"type": "status", "value": "Initializing..."})
        if not browser_actor.initialize_session():
            raise ConnectionError("Failed to initialize browser session during startup.")
    except Exception as e:
        log.exception(f"[{profile_name}] Critical error during startup. Bot will exit.")
        status_queue.put({"type": "status", "value": "Startup failed"})
        notifier.send_critical_alert(f"Bot for profile '{profile_name}' failed to start: {e}")
        browser_actor.close()
        state_manager.close()
        return

    while not stop_event.is_set():
        try:
            # Check session validity
            if not browser_actor.is_session_valid():
                log.warning(f"[{profile_name}] Session is no longer valid. Re-initializing...")
                status_queue.put({"type": "status", "value": "Re-initializing..."})
                if not browser_actor.initialize_session():
                    retry_count += 1
                    if retry_count >= max_retries:
                        log.error(f"[{profile_name}] Failed to re-initialize session after {max_retries} attempts.")
                        status_queue.put({"type": "status", "value": "Max retries exceeded"})
                        break
                    log.error(f"[{profile_name}] Failed to re-initialize session. Retry {retry_count}/{max_retries}")
                    status_queue.put({"type": "status", "value": f"Retry {retry_count}/{max_retries}"})
                    stop_event.wait(sleep_interval_error)
                    continue
                else:
                    retry_count = 0  # Reset retry count on successful initialization

            # Perform job search if configured
            keywords = profile_config.get("keywords", {}).get("required", [])
            cities = profile_config.get("filters", {}).get("cities", [])
            
            # Try searching with different cities
            search_performed = False
            if cities and keywords:
                for city in cities:
                    status_queue.put({"type": "status", "value": f"Searching jobs in {city}..."})
                    if browser_actor.search_jobs(keywords, city):
                        search_performed = True
                        break  # Use first successful search
                        
            if not search_performed and keywords:
                # Try generic search without location
                status_queue.put({"type": "status", "value": "Searching jobs (no location)..."})
                browser_actor.search_jobs(keywords)

            # Scrape job listings
            status_queue.put({"type": "status", "value": "Scraping job listings..."})
            scraped_jobs = browser_actor.scrape_job_listings()
            status_queue.put({"type": "last_checked", "value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            
            if not scraped_jobs:
                log.info(f"[{profile_name}] No job listings found on current page.")
                status_queue.put({"type": "status", "value": "No jobs found"})
            else:
                log.info(f"[{profile_name}] Scraped {len(scraped_jobs)} job listings.")
                
                # Check for new jobs
                seen_urls = state_manager.get_seen_urls()
                new_jobs = [job for job in scraped_jobs if job['url'] not in seen_urls]

                if not new_jobs:
                    log.info(f"[{profile_name}] No new jobs found (all already seen).")
                    status_queue.put({"type": "status", "value": "No new jobs"})
                else:
                    log.info(f"[{profile_name}] Found {len(new_jobs)} new listings (before filtering).")
                    
                    # Apply filters
                    filtered_new_jobs = filter_jobs(
                        new_jobs, 
                        profile_config.get("keywords", {}),
                        profile_config.get("filters", {})
                    )
                    
                    if filtered_new_jobs:
                        log.info(f"[{profile_name}] Found {len(filtered_new_jobs)} jobs matching filters. Notifying...")
                        status_queue.put({"type": "jobs_found", "value": len(filtered_new_jobs)})
                        
                        # Send notifications
                        for job in filtered_new_jobs:
                            try:
                                notifier.send_new_job_alert(job)
                            except Exception as e:
                                log.error(f"[{profile_name}] Failed to send notification for job '{job['title']}': {e}")
                    else:
                        log.info(f"[{profile_name}] No new jobs matched the configured filters.")
                        status_queue.put({"type": "status", "value": "No matches found"})
                    
                    # Save all new jobs (even if filtered out) to avoid re-processing
                    state_manager.save_jobs(new_jobs)

            # Sleep until next check
            log.info(f"[{profile_name}] Sleeping for {check_interval_minutes} minutes...")
            status_queue.put({"type": "status", "value": f"Sleeping for {check_interval_minutes}m..."})
            if stop_event.wait(sleep_interval_default):
                break  # Stop event was set during sleep

        except Exception as e:
            if stop_event.is_set():
                log.info(f"[{profile_name}] Shutting down, ignoring error during exit.")
                break
                
            retry_count += 1
            log.exception(f"[{profile_name}] An unexpected error occurred in the main loop (attempt {retry_count}/{max_retries}).")
            status_queue.put({"type": "status", "value": f"Error (retry {retry_count}/{max_retries})"})
            
            if retry_count >= max_retries:
                log.error(f"[{profile_name}] Max retries exceeded. Bot will exit.")
                status_queue.put({"type": "status", "value": "Max retries exceeded"})
                notifier.send_critical_alert(f"Bot for profile '{profile_name}' stopped after {max_retries} errors. Last error: {e}")
                break
            else:
                notifier.send_critical_alert(f"Error in profile '{profile_name}' (retry {retry_count}/{max_retries}): {e}")
                log.info(f"[{profile_name}] Waiting for {sleep_interval_error}s before retrying.")
                if stop_event.wait(sleep_interval_error):
                    break

    log.info(f"[{profile_name}] Thread received stop signal. Cleaning up...")
    status_queue.put({"type": "status", "value": "Stopping..."})
    browser_actor.close()
    state_manager.close()
    log.info(f"--- Sentinel Bot Thread Stopped for Profile: {profile_name} ---") 