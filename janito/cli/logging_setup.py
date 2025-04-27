import os
import logging


from janito.agent.runtime_config import runtime_config


def setup_verbose_logging(args):
    if runtime_config.get("verbose_http", False) or runtime_config.get(
        "verbose_http_raw", False
    ):
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        httpx_logger.addHandler(handler)

    if runtime_config.get("verbose_http_raw", False):
        os.environ["HTTPX_LOG_LEVEL"] = "trace"

        httpcore_logger = logging.getLogger("httpcore")
        httpcore_logger.setLevel(logging.DEBUG)
        handler_core = logging.StreamHandler()
        handler_core.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        httpcore_logger.addHandler(handler_core)

        # Re-add handler to httpx logger in case
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        httpx_logger.addHandler(handler)
