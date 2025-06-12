import logging
import sys
from logging.handlers import RotatingFileHandler, QueueHandler
import os
import queue

class GuiQueueHandler(QueueHandler):
    def __init__(self, log_queue):
        super().__init__(log_queue)

def setup_logger(queue=None):
    """Set up the sentinel logger."""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    log = logging.getLogger("sentinel")
    log.setLevel(logging.INFO)
    log.propagate = False

    # Clear existing handlers to avoid duplicates
    if log.hasHandlers():
        log.handlers.clear()

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

    # File handler
    fh = RotatingFileHandler('logs/bot.log', maxBytes=1024*1024*5, backupCount=3) # 5MB per file, 3 backups
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    log.addHandler(fh)
    
    # GUI handler
    if queue:
        qh = GuiQueueHandler(queue)
        qh.setLevel(logging.INFO)
        qh.setFormatter(formatter)
        log.addHandler(qh)

    return log

# Global logger instance (will be re-initialized by GUI)
log = setup_logger() 