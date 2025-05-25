import logging
import os
import re


class PIIObfuscatingFilter(logging.Filter):
    """
    A logging filter that obfuscates PII in log records.

    Generated with copilot.
    """

    def __init__(self, name=""):
        super().__init__(name)
        self.phone_regex = re.compile(
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        )
        self.email_regex = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        self.long_number_regex = re.compile(
            r"(?<!\d\.)(?<!\d/)(?<!\w[/:])\b\d{5,}\b(?!\.\d)(?!/)"
        )  # Avoid matching parts of URLs or version numbers
        self.api_key_regex = re.compile(
            r"\b[a-f0-9]{10,}\b\.{3}?"
        )  # Catches your example da75315f54...
        self.coords_regex = re.compile(
            r"-?\d{1,3}\.\d{5,}"
        )  # Matches numbers like 40.024583 or -105.2717583
        self.sensitive_url_path_regex = re.compile(
            r"(https://[^/]+/)[^/]+(-[0-9]{10,})(/[^/]+)?"
        )
        self.plist_bytes_regex = re.compile(r"b'<\?xml vers'[^']*'")
        self.account_json_regex = re.compile(r'("ids":\s*){[^}]+}')

    def _obfuscate(self, message):
        message = self.phone_regex.sub("[REDACTED]", message)
        message = self.email_regex.sub("[REDACTED]", message)
        message = self.api_key_regex.sub("[REDACTED]...", message)
        message = self.coords_regex.sub("[REDACTED]", message)

        match = self.sensitive_url_path_regex.search(message)
        if match:
            if match.group(2) and match.group(
                3
            ):  # e.g. anisette-v3-server-393848543228.us-west1.run.app
                message = self.sensitive_url_path_regex.sub(r"\1[REDACTED]\3", message)
            elif match.group(
                2
            ):  # For URLs that might only have the server hash part without a trailing path
                message = self.sensitive_url_path_regex.sub(r"\1[REDACTED]", message)

        def long_num_replacer(match):
            num_str = match.group(0)
            if len(num_str) > 4:
                return "[REDACTED]"
            return num_str

        message = self.long_number_regex.sub(long_num_replacer, message)
        message = self.plist_bytes_regex.sub("[REDACTED]", message)
        message = self.account_json_regex.sub(r"\1{[REDACTED]}", message)

        return message

    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self._obfuscate(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                self._obfuscate(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


def setup_logging() -> logging.Logger:
    if not os.getenv("GITHUB_ACTION"):
        logging.basicConfig(level=logging.DEBUG)
        return logging.getLogger("findmydad")
    logger = logging.getLogger("findmydad")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    pii_filter = PIIObfuscatingFilter()
    handler.addFilter(pii_filter)
    logger.addHandler(handler)
    return logger
