import sys
import logging
from datetime import datetime, timezone, tzinfo


class TZFormatter(logging.Formatter):
    """Кастомный форматтер для логов"""

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: str = '%',
        tz: tzinfo = timezone.utc
    ) -> None:
        super().__init__(
            fmt=fmt,
            datefmt=datefmt,
            style=style
        )

        self.tz = tz

    def formatTime(
        self,
        record: logging.LogRecord,
        datefmt: str | None = None
    ) -> str:
        tz_time = datetime.fromtimestamp(
            timestamp=record.created,
            tz=self.tz
        )

        if datefmt:
            return tz_time.strftime(datefmt)

        return tz_time.strftime('%Y-%m-%d %H:%M:%S')

    def format(self, record: logging.LogRecord) -> str:
        """Переопределяем format для правильной обработки UTF-8"""
        formatted = super().format(record)

        if isinstance(formatted, str):
            try:
                formatted.encode(encoding='utf-8')
                return formatted

            except UnicodeEncodeError:
                return formatted.encode(
                    encoding='utf-8',
                    errors='replace'
                ).decode(encoding='utf-8')

        return formatted


def setup_logger(
    name: str,
    level: str = "INFO",
    fmt: str = "[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    tz: tzinfo = timezone.utc
) -> logging.Logger:
    """
    Настройка логгера с поддержкой автоматической ротации по дням

    Args:
        name: Имя логгера
        level: Уровень логирования
    """

    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    logger.setLevel(level.upper())

    formatter = TZFormatter(
        fmt=fmt,
        tz=tz
    )

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.propagate = False

    sys.stdout.flush()
    sys.stderr.flush()

    return logger
