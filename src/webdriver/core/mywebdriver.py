"""
File description
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf
from selenium import webdriver
from selenium.common.exceptions import (
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service

from webdriver.core.options import ChromeOptionsBuilder
from webdriver.utils import is_valid_chrome_webdriver_config

# Set up logging
logger = logging.getLogger(__name__)


# TODO
# add timeout limits
# option builder improve handling
class MyWebDriver:
    """Enhanced existing MyWebDriver class with IP rotation capabilities."""

    def __init__(
        self,
        config: Optional[DictConfig] = None,
        options: Optional[ChromeOptions] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize WebDriver with config or direct parameters.

        Args:
            config: Hydra configuration object
            session_id: Unique identifier for this driver instance
            **kwargs: Direct parameters for backward compatibility
        """
        self.config: Optional[DictConfig] = config
        self.options: Optional[ChromeOptions] = options
        self.session_id: str = session_id or "default"

        if config:
            if is_valid_chrome_webdriver_config(config):
                # Use Hydra instantiation
                self._init_from_hydra_config(config)
                logger.debug(f"Config file:\n{OmegaConf.to_yaml(config)}.")
        elif options:
            self._init_from_chromeOptions(options)

        else:
            logger.error("Initialisation failed, no valid config or options")
            raise ValueError("Config structure is invalid")

        #
        logger.debug(f"WebDriver initialized for session: {self.session_id}")

    def _init_from_chromeOptions(
        self,
        options: ChromeOptions,
        binary_location: str = "/usr/bin/chromedriver",
        page_timeout: int = 10,
    ):
        logger.debug("=" * 6 + " Init WebDriver using Options " + "=" * 6)
        service = Service(
            executable_path=binary_location
        )  # Fixed typo and missing parenthesis
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(page_timeout)

    def _init_from_hydra_config(self, config: DictConfig):
        """Initialize using Hydra instantiate."""
        logger.debug("=" * 6 + " Init WebDriver using Hydra " + "=" * 6)
        # Build the options using the options builder
        options_builder: ChromeOptionsBuilder = instantiate(
            config.webdriver.browser.options
        )

        # Proxy socks5
        if self.socks5:
            options_builder.proxy_sock5(self.socks5)

        # DEBUG: Print all Chrome options before creating driver
        options_builder.debug_chrome_options()

        options = options_builder.build()

        # Create the service
        service = instantiate(config.webdriver.browser.service)

        # Create the driver
        self.driver = instantiate(
            config.webdriver.browser, service=service, options=options
        )

        # Set timeouts
        if hasattr(config, "timeouts"):
            self.driver.implicitly_wait(config.timeouts.implicit)

            # Set page load timeout - important for bottleneck!
            page_load_timeout = config.timeouts.page_load
            self.driver.set_page_load_timeout(page_load_timeout)
            logger.debug(f"Set page load timeout to {page_load_timeout} seconds")

        logger.debug("=" * 6 + " WebDriver init complete " + "=" * 6)

    def navigate(self, url: str) -> None:
        """Navigate to URL."""
        logger.debug(f"[{self.session_id}] Navigating to: {url}")
        self.driver.get(url)

    def _print_config(self):
        """Print the current configuration for debugging."""
        print("=== WebDriver Configuration ===")
        if self.config:
            from omegaconf import OmegaConf

            print(OmegaConf.to_yaml(self.config))
        print("================================")

    @property
    def current_url(self) -> str:
        """Get current URL."""
        return self.driver.current_url

    def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in the current window.

        Args:
            script: JavaScript to execute
            *args: Arguments to pass to the script

        Returns:
            Result of the script execution (type depends on what JS returns)
        """
        try:
            return self.driver.execute_script(script, *args)
        except WebDriverException as e:
            logger.error(f"Error executing script: {str(e)}")
            raise

    def get_json_content(self) -> Optional[Union[Dict, List, str, int, float, bool]]:
        """
        Get JSON content from document.body.innerText.

        Returns:
            Parsed JSON content or None if parsing fails
        """
        JAVASCRIPT_COMMAND = "return document.body.innerText"

        try:
            json_content = self.execute_script(JAVASCRIPT_COMMAND)

            if not json_content:
                logger.warning(f"No content found at {self.current_url}")
                return None

            if not isinstance(json_content, str):
                logger.warning(
                    f"Expected string, got {type(json_content)} at {self.current_url}"
                )
                return None

            return json.loads(json_content)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON content at {self.current_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting JSON content at {self.current_url}: {e}")
            return None

    def go_get_json(
        self, url: str
    ) -> Optional[Union[Dict, List, str, int, float, bool]]:
        """navigate and get_json_content"""
        self.navigate(url)
        return self.get_json_content()

    def close(self) -> None:
        """Close the driver."""
        if hasattr(self, "driver") and self.driver:
            self.driver.quit()
            logger.debug(f"WebDriver closed for session: {self.session_id}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
