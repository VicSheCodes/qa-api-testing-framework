import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


class TestLogger:
    """
    Centralized logging configuration for test suite.

    Features:
    - Console and file logging
    - Rotating file handlers
    - Structured log format
    - Separate log levels for console and file
    """

    def __init__(
        self,
        name: str = "qa_tests",
        log_dir: str = "reports/logs",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5
    ):
        self.name = name
        self.log_dir = Path(log_dir)
        self.console_level = console_level
        self.file_level = file_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Capture all levels
        self.logger.propagate = False  # Prevent duplicate logs

        # Clear existing handlers
        self.logger.handlers.clear()

        # Setup handlers
        self._setup_console_handler()
        self._setup_file_handlers()

    def _setup_console_handler(self):
        """Setup colored console output"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)

        # Colored format for console
        console_format = logging.Formatter(
            fmt='%(asctime)s [%(levelname)-8s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

    def _setup_file_handlers(self):
        """Setup rotating file handlers"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Current session log (detailed)
        session_log = self.log_dir / f"test_session_{timestamp}.log"
        session_handler = logging.FileHandler(session_log, mode='w', encoding='utf-8')
        session_handler.setLevel(self.file_level)

        # Detailed format for file
        file_format = logging.Formatter(
            fmt='%(asctime)s [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        session_handler.setFormatter(file_format)
        self.logger.addHandler(session_handler)

        # Rotating main log (keeps history)
        main_log = self.log_dir / "main.log"
        rotating_handler = RotatingFileHandler(
            main_log,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        rotating_handler.setLevel(self.file_level)
        rotating_handler.setFormatter(file_format)
        self.logger.addHandler(rotating_handler)

        # Error-only log
        error_log = self.log_dir / "errors.log"
        error_handler = RotatingFileHandler(
            error_log,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        self.logger.addHandler(error_handler)

    def get_logger(self) -> logging.Logger:
        """Get configured logger instance"""
        return self.logger

    def purge_all_logs(self):
        """
        Delete all log files in the log directory.
        Warning: This removes ALL logs including history.
        """
        if not self.log_dir.exists():
            return

        for handler in self.logger.handlers[:]:
            if isinstance(handler, (logging.FileHandler, RotatingFileHandler)):
                handler.close()
                self.logger.removeHandler(handler)

        for log_file in self.log_dir.glob("*.log*"):
            try:
                log_file.unlink()
                print(f"Deleted: {log_file.name}")
            except Exception as e:
                print(f"Failed tto delete {log_file.name}: {e}")

        self._setup_file_handlers()

    def clear_main_logs(self):
        """
        Clear content of main.log and errors.log while keeping session logs.
        """
        main_log = self.log_dir / "main.log"
        error_log = self.log_dir / "errors.log"

        for handler in self.logger.handlers[:]:
            if isinstance(handler, RotatingFileHandler):
                handler.close()
                self.logger.removeHandler(handler)

        if main_log.exists():
            main_log.unlink()
        for backup in self.log_dir.glob("main.log.*"):
            backup.unlink()

        if error_log.exists():
            error_log.unlink()
        for backup in self.log_dir.glob("errors.log.*"):
            backup.unlink()

        self._setup_file_handlers()

    def purge_old_sessions(self, days: int = 7):
        """
        Delete session logs older than specified days.

        Args:
            days: Delete session logs older than this many days
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        for log_file in self.log_dir.glob("test_session_*.log"):
            try:
                # Extract timestamp from filename (test_session_YYYYMMDD_HHMMSS.log)
                timestamp_str = log_file.stem.replace("test_session_", "")
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
                    print(f"Deleted old session: {log_file.name}")
            except (ValueError, Exception) as e:
                print(f"Skipped {log_file.name}: {e}")

        print(f"Purged {deleted_count} old session log(s)")

    def get_log_stats(self) -> dict:
        """
        Get statistics about log files.

        Returns:
            Dictionary with log file information
        """
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "session_logs": 0,
            "rotating_logs": 0,
            "oldest_session": None,
            "newest_session": None
        }

        if not self.log_dir.exists():
            return stats

        session_dates = []

        for log_file in self.log_dir.glob("*.log*"):
            stats["total_files"] += 1
            stats["total_size_mb"] += log_file.stat().st_size / (1024 * 1024)

            if log_file.name.startswith("test_session_"):
                stats["session_logs"] += 1
                try:
                    timestamp_str = log_file.stem.replace("test_session_", "")
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    session_dates.append(file_date)
                except ValueError:
                    pass
            elif log_file.name in ["main.log", "errors.log"]:
                stats["rotating_logs"] += 1

        if session_dates:
            stats["oldest_session"] = min(session_dates).strftime("%Y-%m-%d %H:%M:%S")
            stats["newest_session"] = max(session_dates).strftime("%Y-%m-%d %H:%M:%S")

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats


# Global logger instance
_test_logger = None


def get_test_logger(
    name: str = "qa_tests",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
) -> logging.Logger:
    """
    Get or create singleton test logger.

    Args:
        name: Logger name
        console_level: Logging level for console output
        file_level: Logging level for file output

    Returns:
        Configured logger instance
    """
    global _test_logger

    if _test_logger is None:
        test_logger_config = TestLogger(
            name=name,
            console_level=console_level,
            file_level=file_level
        )
        _test_logger = test_logger_config.get_logger()

    return _test_logger


def log_test_start(test_name: str, params: dict = None):
    """Log test start with parameters"""
    logger = get_test_logger()
    logger.info("=" * 80)
    logger.info(f"TEST START: {test_name}")
    if params:
        logger.info(f"Parameters: {params}")
    logger.info("=" * 80)


def log_test_end(test_name: str, status: str, duration: float = None):
    """Log test end with status"""
    logger = get_test_logger()
    status_emoji = "✓" if status.upper() == "PASSED" else "✗"

    logger.info("-" * 80)
    msg = f"TEST END: {test_name} - {status_emoji} {status.upper()}"
    if duration:
        msg += f" ({duration:.2f}s)"
    logger.info(msg)
    logger.info("-" * 80)


def log_api_request(method: str, endpoint: str, status_code: int,
                    response_time: float, request_num: int = None):
    """Log API request details"""
    logger = get_test_logger()

    req_prefix = f"Request #{request_num}: " if request_num else ""
    status_symbol = "✓" if 200 <= status_code < 300 else "✗"

    logger.info(
        f"{req_prefix}{status_symbol} {method} {endpoint} "
        f"→ {status_code} ({response_time:.3f}s)"
    )


def log_api_response_body(body, max_length: int = 200):
    """Log API response body (truncated)"""
    logger = get_test_logger()
    body_str = str(body)

    if len(body_str) > max_length:
        body_str = body_str[:max_length] + "..."

    logger.debug(f"Response body: {body_str}")


def log_error(error: Exception, context: str = None):
    """Log error with context"""
    logger = get_test_logger()

    if context:
        logger.error(f"Error in {context}: {type(error).__name__}: {str(error)}")
    else:
        logger.error(f"{type(error).__name__}: {str(error)}")

    logger.debug("Traceback:", exc_info=True)


def log_metric(metric_name: str, value, unit: str = None):
    """Log performance metric"""
    logger = get_test_logger()
    unit_str = f" {unit}" if unit else ""
    logger.info(f"METRIC: {metric_name} = {value}{unit_str}")

