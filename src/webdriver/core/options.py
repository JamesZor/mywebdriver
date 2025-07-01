"""Options builders for different browsers."""

import logging
from typing import Any, Dict, List, Optional

from selenium.webdriver.chrome.options import Options as ChromeOptions

logger = logging.getLogger(__name__)


class ChromeOptionsBuilder:
    """Builder for Chrome options that can be instantiated via Hydra."""

    def __init__(
        self,
        binary_location: str = "/usr/bin/chromium",
        headless: bool = False,
        arguments: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        **kwargs,
    ):
        logger.debug(f"Setting chrome options. {binary_location = }")
        self.options = ChromeOptions()

        # Set binary location
        self.options.binary_location = binary_location

        # Set headless mode
        if headless:
            logger.debug("setting headless.")
            self.options.add_argument("--headless")
        else:
            logger.debug("setting head.")

        # Add arguments
        if arguments:
            for arg in arguments:
                logger.debug(f"Setting {arg =}")
                self.options.add_argument(arg)

        # Set user agent
        if user_agent:
            self.options.add_argument(f"--user-agent={user_agent}")

        # Set logging preferences
        self.options.set_capability(
            "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
        )

    def build(self) -> ChromeOptions:
        """Return the configured ChromeOptions."""
        logger.debug("returning chrome options.")
        return self.options
