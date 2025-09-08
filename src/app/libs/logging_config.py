import logging
import sys

def setup_logging():
    # Get the root logger
    logger = logging.getLogger()

    # Set the overall logging level for the root logger
    # This example sets it to INFO, but you can adjust as needed
    logger.setLevel(logging.INFO)

    # For the 'httpx' library, set the logging level to WARNING
    # This will suppress the INFO level messages that are being logged as errors
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Add a handler to output logs to stdout, if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    print("Logging configured: 'httpx' log level set to WARNING.")
