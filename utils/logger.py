import logging
from .config import LOG_LEVEL

logger = logging.getLogger("davomat")
level = getattr(logging, LOG_LEVEL, logging.INFO)
logger.setLevel(level)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)
