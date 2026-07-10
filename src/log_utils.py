import sys
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "version_checker.log"


class Tee:
    """Mirrors writes to a primary stream and an open log file."""

    def __init__(self, primary, log_file):
        self.primary = primary
        self.log_file = log_file

    def write(self, text):
        self.primary.write(text)
        self.log_file.write(text)
        self.log_file.flush()

    def flush(self):
        self.primary.flush()
        self.log_file.flush()


def open_log_file():
    """Open logs/version_checker.log for appending, with a run-start banner."""
    LOG_PATH.parent.mkdir(exist_ok=True)
    log_file = open(LOG_PATH, "a")
    log_file.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===\n")
    log_file.flush()
    return log_file


def enable_file_logging():
    """Tee stdout and stderr to logs/version_checker.log for the process lifetime."""
    log_file = open_log_file()
    sys.stdout = Tee(sys.stdout, log_file)
    sys.stderr = Tee(sys.stderr, log_file)
    return log_file
