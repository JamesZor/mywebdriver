"""Options builders for different browsers."""

import logging
from typing import Any, Dict, List, Optional

from omegaconf import DictConfig
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

        logger.debug("=" * 6 + " Init Chrome Option builder " + "=" * 6)
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

        logger.debug("-" * 6 + " End Chrome Option builder " + "-" * 6)

    def proxy_sock5(self, config_socks5: DictConfig) -> None:
        """
        sock55_ip, is the proxy_url of the form socks5://10.124.0.155:1080
        """
        logger.debug(f"Setting socks5 proxy. {config_socks5 =}")
        self.options.add_argument(f"--proxy-server={config_socks5.proxy_url}")
        self.options.add_argument(
            f"--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE {config_socks5.socks5}"
        )

    def build(self) -> ChromeOptions:
        """Return the configured ChromeOptions."""
        logger.debug("returning chrome options.")
        return self.options
