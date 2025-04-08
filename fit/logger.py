import logging
from typing import Any

from tqdm import tqdm


class Logger(logging.Logger):
    """Custom logger with colored output like Pwntools."""

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
        color = self.COLORS.get(level, "")
        reset = self.COLORS["RESET"]
        return f"[{color}{level}{reset}] {message}"

    def debug(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        super().debug(self.format_message("DEBUG", msg), *args, **kwargs)

    def info(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        super().info(self.format_message("INFO", msg), *args, **kwargs)

    def warning(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        super().warning(self.format_message("WARNING", msg), *args, **kwargs)

    def error(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        super().error(self.format_message("ERROR", msg), *args, **kwargs)

    def critical(self, msg: str, *args: object, **kwargs: Any) -> None:  # type: ignore
        super().critical(self.format_message("CRITICAL", msg), *args, **kwargs)
        raise SystemExit(1)


def get() -> logging.Logger:
    logging.setLoggerClass(Logger)
    return logging.getLogger("fit")


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level: Any = logging.NOTSET) -> None:
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)
