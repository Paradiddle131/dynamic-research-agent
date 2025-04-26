import logging
import sys
import os
_library_name = "scrapegraph"
_log_level = os.environ.get("SCRAPEGRAPH_LOG_LEVEL", "WARNING").upper()
_log_level = getattr(logging, _log_level, logging.WARNING)
_logger = logging.getLogger(_library_name)
_logger.setLevel(_log_level)
_logger.propagate = False
if not _logger.hasHandlers():
    _handler = logging.StreamHandler(sys.stdout)
    _formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
def get_logger(name: str = None) -> logging.Logger:
    """Returns a logger instance."""
    if name:
        return logging.getLogger(f"{_library_name}.{name}")
    return _logger
def set_verbosity(level):
    _logger.setLevel(level)
def set_verbosity_debug():
    set_verbosity(logging.DEBUG)
def set_verbosity_info():
    set_verbosity(logging.INFO)
