import requests
from .logger import log

class Notifier:
    """Handles sending notifications to Discord."""

    def __init__(self, webhook_url: str):
        """Initializes with the Discord webhook URL from the profile config."""
        if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
             log.warning("Discord webhook URL is not set or invalid. Notifications will be disabled.")
             self.webhook_url = None
        else:
             self.webhook_url = webhook_url

    def send_new_job_alert(self, job: dict):
        """Sends a formatted Discord embed for a new job."""
        if not self.webhook_url:
            log.warning(f"Skipping new job notification because webhook is not configured: {job.get('title')}")
            return

        embed = {
            "title": f"🚀 New Job Posting Found",
            "url": job.get('url', None),
            "color": 3066993, # A nice green color
            "fields": [
                {
                    "name": "Job Title",
                    "value": job.get('title', 'N/A'),
                    "inline": False
                },
                {
                    "name": "Direct Link",
                    "value": f"[Apply Here]({job.get('url', '#')})",
                    "inline": False
                }
            ],
            "footer": {
                "text": "Sentinel Bot | Your friendly neighborhood job scout"
            }
        }

        payload = {
            "embeds": [embed]
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            log.info(f"Successfully sent notification for job: {job.get('title')}")
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to send Discord notification for job {job.get('title')}: {e}")

    def send_critical_alert(self, message: str):
        """Sends a simple, non-embed message to Discord for critical errors."""
        if not self.webhook_url:
            log.warning(f"Skipping critical alert because webhook is not configured: {message}")
            return
            
        payload = {
            "content": f"🚨 **CRITICAL ALERT** 🚨\n\n`{message}`"
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            log.info("Successfully sent critical alert to Discord.")
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to send critical alert to Discord: {e}") 