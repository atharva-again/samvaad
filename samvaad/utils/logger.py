import logging
import sys
import os

def setup_logger(name: str = "samvaad") -> logging.Logger:
    """
    Configure and return a standard logger for the application.
    Uses log level from LOG_LEVEL env var (default INFO).
    """
    logger = logging.getLogger(name)
    
    # Only configure if no handlers exist to avoid duplicates
    if not logger.handlers:
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        logger.setLevel(log_level)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Prevent propagation to root logger if using uvicorn's handled loop
        logger.propagate = False

    return logger

# Create a default logger instance
logger = setup_logger()
