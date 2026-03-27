"""
Logging configuration module.

Provides centralized logging setup for the janito CLI.
"""

import logging


def setup_logging(log_levels: str = None):
    """Configure logging based on --log argument.
    
    Args:
        log_levels: Comma-separated list of log levels (e.g., "info,debug")
                   Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    # Configure root logger
    logger = logging.getLogger()
    
    if log_levels:
        # Parse log levels from comma-separated string
        levels = [l.strip().upper() for l in log_levels.split(',')]
        
        # Set handlers for each level
        for level in levels:
            if level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
                handler = logging.StreamHandler()
                handler.setLevel(getattr(logging, level))
                handler.setFormatter(logging.Formatter(
                    f'%(levelname)s: %(message)s' if level == 'INFO' 
                    else f'%(levelname)s: %(name)s: %(message)s'
                ))
                logger.addHandler(handler)
                logger.setLevel(getattr(logging, level))
    else:
        # Default: no logging output
        logger.setLevel(logging.CRITICAL + 1)
