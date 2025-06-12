import imaplib
import email
import re
import time
from email.header import decode_header
from .logger import log

def get_2fa_code(config: dict) -> str:
    """
    Connects to an IMAP server to fetch a 6-digit 2FA code from the latest email.
    Accepts a configuration dictionary for settings.
    """
    email_address = config.get("email_address")
    app_password = config.get("email_app_password")
    imap_server = config.get("email_imap_server")
    sender = config.get("confirmation_email_sender")
    timeout = config.get("email_check_timeout", 90)

    log.info(f"Connecting to IMAP server: {imap_server}...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_address, app_password)
            mail.select("inbox")
            
            status, messages = mail.search(None, f'(UNSEEN FROM "{sender}")')

            if status == "OK" and messages[0]:
                latest_email_id = messages[0].split()[-1]
                log.info("Found a new email from the sender. Fetching content...")
                
                status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
                if status == "OK":
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    if "text/plain" in content_type or "text/html" in content_type:
                                        try:
                                            body = part.get_payload(decode=True).decode()
                                            break
                                        except:
                                            continue
                            else:
                                body = msg.get_payload(decode=True).decode()

                            match = re.search(r'\b\d{6}\b', body)
                            if match:
                                code = match.group(0)
                                log.info(f"Successfully extracted 2FA code: {code}")
                                mail.logout()
                                return code
                log.warning("Could not find a 6-digit code in the latest email.")
            else:
                 log.info("No unread email from sender found.")

            if mail:
                mail.logout()

        except Exception as e:
            log.error(f"An error occurred while checking email: {e}")
            if mail:
                try:
                    mail.logout()
                except:
                    pass
        
        log.info("Retrying in 5 seconds...")
        time.sleep(5)

    raise TimeoutError(f"Could not find 2FA email from {sender} within {timeout} seconds.") 