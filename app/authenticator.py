import imaplib
import email
import re
import time
import socket # For socket.error
from email.header import decode_header
from .logger import log
from .security import decrypt

def get_2fa_code(config: dict, master_password: str = None) -> str:
    """
    Connects to an IMAP server to fetch a 6-digit 2FA code from the latest email.
    Accepts a configuration dictionary for settings and an optional master_password for decryption.
    """
    email_address = config.get("email_address")
    app_password_val = config.get("email_app_password")
    imap_server = config.get("email_imap_server")
    sender = config.get("confirmation_email_sender")
    timeout = config.get("email_check_timeout_seconds", 90) # Clarified unit
    polling_interval = config.get("email_polling_interval_seconds", 5) # New

    log.info(f"Attempting to fetch 2FA code from {email_address} via {imap_server}. Sender: '{sender}'. Timeout: {timeout}s, Polling: {polling_interval}s.")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        mail = None # Initialize mail to None for each attempt cycle
        try:
            log.debug(f"Connecting to IMAP server: {imap_server}...")
            mail = imaplib.IMAP4_SSL(imap_server)
            log.debug(f"Logging in as {email_address}...")

            if not app_password_val:
                log.error(f"Email app password not found in config for {email_address}.")
                raise ValueError(f"Email app password not found for {email_address}")

            actual_app_password = app_password_val
            if master_password and isinstance(app_password_val, str) and app_password_val.startswith("enc:"):
                try:
                    log.debug(f"Attempting to decrypt email app password for {email_address}.")
                    actual_app_password = decrypt(app_password_val, master_password)
                    if not actual_app_password: # Decryption failed but didn't raise error, or returned empty
                        log.error(f"Failed to decrypt email app password for {email_address}, or result was empty.")
                        raise ValueError(f"Decryption failed for email app password for {email_address}")
                    log.info(f"Successfully decrypted email app password for {email_address}.")
                except Exception as e:
                    log.error(f"Error decrypting email app password for {email_address}: {e}", exc_info=True)
                    raise ValueError(f"Decryption error for email app password for {email_address}: {e}")
            elif master_password and isinstance(app_password_val, str) and not app_password_val.startswith("enc:"):
                log.warning(f"Master password provided for {email_address}, but app password does not appear encrypted. Using as is.")
            elif not master_password and isinstance(app_password_val, str) and app_password_val.startswith("enc:"):
                log.error(f"Email app password for {email_address} appears encrypted, but no master password provided.")
                raise ValueError(f"Encrypted email app password found for {email_address} but no master password provided.")

            mail.login(email_address, actual_app_password)
            log.debug("Selecting inbox...")
            mail.select("inbox")
            log.debug(f"Searching for unseen email from sender: {sender}...")
            
            # Search for unseen emails from the specific sender
            status, messages = mail.search(None, f'(UNSEEN FROM "{sender}")')

            if status == "OK" and messages[0]:
                latest_email_id = messages[0].split()[-1] # Get the ID of the most recent email
                log.info(f"Found new email from sender '{sender}'. Fetching content for email ID {latest_email_id}...")
                
                status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
                if status == "OK":
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    # Prefer text/plain, but fallback to text/html
                                    if "text/plain" in content_type:
                                        try:
                                            body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                            break
                                        except:
                                            continue
                                    elif "text/html" in content_type and not body: # Only use html if plain not found
                                        try:
                                            # Basic HTML to text conversion (remove tags)
                                            html_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                            body = re.sub('<[^<]+?>', '', html_body)
                                        except:
                                            continue
                            else: # Not multipart
                                try:
                                    body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                                except:
                                    pass # Could not decode

                            if body:
                                # Regex to find a 6-digit code
                                match = re.search(r'\b(\d{6})\b', body)
                                if match:
                                    code = match.group(0)
                                    log.info(f"Successfully extracted 2FA code: {code} from email for {email_address}")
                                    # Logout is handled in finally
                                    return code
                                else:
                                    log.warning(f"Could not find a 6-digit code in the latest email from '{sender}' for {email_address}. Body snippet: {body[:200]}...")
                            else:
                                log.warning(f"Email body from '{sender}' for {email_address} was empty or could not be decoded.")
                else:
                    log.warning(f"Failed to fetch email content for ID {latest_email_id} from '{sender}' for {email_address}.")
            else:
                 log.info(f"No unread email from sender '{sender}' found this poll for {email_address}.")

        except ConnectionRefusedError as e:
            log.error(f"IMAP connection refused for {imap_server}: {e}. Aborting check for {email_address}.")
            break
        except (imaplib.IMAP4.error, socket.error) as e:
            log.error(f"IMAP/socket error for {email_address} on {imap_server}: {e}. Will retry after polling interval.")
        except Exception as e:
            log.error(f"An unexpected error occurred while checking email for {email_address}: {e}")
        finally:
            if mail:
                try:
                    log.debug(f"Logging out from IMAP server ({email_address}).")
                    mail.logout()
                except Exception as e_logout:
                    log.error(f"Error during IMAP logout for {email_address}: {e_logout}")
            mail = None # Ensure mail is None for next loop iteration if logout failed or connection error
        
        # Wait before retrying or break if timeout is near
        time_elapsed = time.time() - start_time
        if time_elapsed < timeout - polling_interval:
            log.info(f"Waiting {polling_interval}s before next poll for {email_address}...")
            time.sleep(polling_interval)
        elif time_elapsed < timeout:
            log.info(f"Timeout for {email_address} nearly reached ({timeout - time_elapsed:.1f}s remaining), proceeding to final check or exit.")
        else: # Timeout reached or exceeded
            log.info(f"Timeout reached for {email_address} while waiting for email from '{sender}'.")
            break

    raise TimeoutError(f"Could not find 2FA email from {sender} for {email_address} within {timeout} seconds after multiple polls.")