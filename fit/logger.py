import logging
from typing import Any

from tqdm import tqdm


class Logger(logging.Logger):
    """
    Custom logger class that extends the standard logging.Logger to add colored output.
    """

    """The colors used for the logger."""
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
        "RESET": "\033[0m",
    }

    def __init__(self, name: str, level: int = logging.INFO) -> None:
        super().__init__(name, level)

        if not self.hasHandlers():
            formatter = logging.Formatter("%(message)s")

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.addHandler(console_handler)

            self.propagate = False

    def format_message(self, level: str, message: str) -> str:
        """
        Function that formats a  log message with the appropriate color based on the log level.

        :param level: the log level.
        :param message: the log message.
        :return: the formatted log message.
        """

        color = self.COLORS.get(level, "")
        reset = self.COLORS["RESET"]
        return f"[{color}{level}{reset}] {message}"

    def debug(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        """
        Function that logs a debug message.

        :param msg: the debug message.
        :param args: the additional arguments passed to the logger.
        :param kwargs: the additional keyword arguments passed to the logger.
        """

        super().debug(self.format_message("DEBUG", msg), *args, **kwargs)

    def info(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        """
        Function that logs an info message.

        :param msg: the info message.
        :param args: the additional arguments passed to the logger.
        :param kwargs: the additional keyword arguments passed to the logger.
        """

        super().info(self.format_message("INFO", msg), *args, **kwargs)

    def warning(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        """
        Function that logs a warning message.

        :param msg: the warning message.
        :param args: the additional arguments passed to the logger.
        :param kwargs: the additional keyword arguments passed to the logger.
        """

        super().warning(self.format_message("WARNING", msg), *args, **kwargs)

    def error(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        """
        Function that logs an error message.

        :param msg: the error message.
        :param args: the additional arguments passed to the logger.
        :param kwargs: the additional keyword arguments passed to the logger.
        """

        super().error(self.format_message("ERROR", msg), *args, **kwargs)

    def critical(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        """
        Function that logs a critical message.

        :param msg: the critical message.
        :param args: the additional arguments passed to the logger.
        :param kwargs: the additional keyword arguments passed to the logger.
        """

        super().critical(self.format_message("CRITICAL", msg), *args, **kwargs)
        raise SystemExit(1)


def get() -> logging.Logger:
    """
    Function that gets a logger instance with the custom Logger class.

    :return: the logger instance.
    """

    logging.setLoggerClass(Logger)
    return logging.getLogger("fit")


class TqdmLoggingHandler(logging.Handler):
    """
    A custom logging handler class that redirects log messages through tqdm's `write` method.
    """

    def __init__(self, level: Any = logging.NOTSET) -> None:
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        """
        Function that emits a log record.

        :param record: the log record to be emitted.
        """

        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)
