import os
import logging


def setup_verbose_logging(args):
    if args.verbose_http or args.verbose_http_raw:
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        httpx_logger.addHandler(handler)

    if args.verbose_http_raw:
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
