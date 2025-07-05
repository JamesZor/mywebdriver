"""
File description
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
from hydra.utils import instantiate
from numpy.random import Generator as RandomGenrator
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
# proxy logic setup

# rotations logic


class MyWebDriver:
    """Enhanced existing MyWebDriver class with IP rotation capabilities."""

    def __init__(
        self,
        optionsbulder: ChromeOptionsBuilder,
        config: Optional[DictConfig] = None,
        proxy: Optional[dict[str, Union[str, bool]]] = None,
        proxy_list: Optional[list[dict]] = None,
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
        logger.debug("++++ WebDriver starting. ++++")

        self.config: DictConfig = config
        self.options: Optional[ChromeOptions] = optionsbulder
        self.session_id: str = session_id or "default"
        self.set_proxy: Optional[dict] = None
        self.proxy_list: Optional[list[dict]] = proxy_list
        self.rng: RandomGenrator = np.random.default_rng()

        self.get_page: Callable[
            [str], Optional[Union[Dict, List, str, int, float, bool]]
        ] = self.go_get_json

        self.rotation_counter: Optional[int] = None

        # proxy logic
        if self.proxy.enabled:
            logger.debug(" Socks5 proxy enabled.")

            # if given a single proxy, use this, ignore list.
            if proxy:
                logger.debug(
                    f"Setting drivers proxy,from given arg: {proxy.get('hostname')}."
                )
                self.set_proxy: dict[str, Union[str, bool]] = proxy

            elif proxy_list:  # otherwise, if proxy list get random from list.
                self._set_random_proxy_from_list()

                # rotation:
                if self.config.proxy.rotation.enabled:
                    logger.debug(" Proxy socks5 rotation enabled")

                    self._set_proxy_rotation_counter()

                    self.get_page = self.go_get_json_rotation

        if optionsbulder:
            logger.debug("Loading the options.")
            self._init_from_chromeOptions(
                optionsbulder,
                executable_path=config.webdriver.browser.service.executable_path,
                page_timeout=config.webdriver.timeouts.page_load,
            )

        logger.debug(f"WebDriver initialized for session: {self.session_id}")

    def _set_proxy_rotation_counter(self):
        """
        set the rotation counter, and resets.
        """
        rotation_type: str = self.config.rotation.random_type
        interval: list[int] = self.config.rotation.interval

        if rotation_type == "fixed":
            self.rotation_counter: int = interval[0]
            logger.debug(f"Setting counter, fixed {self.rotation_counter =}.")
        elif rotation_type == "uniform":
            self.rotation_counter: int = self.rng.integers(
                low=interval[0], high=interval[1], endpoint=True, dtype=int
            )
            logger.debug(f"Setting counter, uniform {self.rotation_counter =}.")
        else:
            logger.warning(
                f"Could not set the rotation counter: { rotation_type =}, { interval =}."
            )

    def _set_random_proxy_from_list(self) -> None:
        """
        Randomly set a proxy from the given proxy list.
        """
        if self.proxy_list:
            random_proxy: dict = self.rng.choice(self.proxy_list, size=1)
            self.set_proxy = random_proxy
            logger.debug(f"Selected randomly proxy: {random_proxy.get('hostname')}.")
        else:
            logger.warning("No proxy list found.")

    def _init_from_chromeOptionsBuilder(
        self,
        executable_path: str = "/usr/bin/chromedriver",
        page_timeout: int = 10,
    ):
        logger.debug("=" * 6 + " Init WebDriver using Options " + "=" * 6)
        service = Service(executable_path=self.config.browser.service.binary_location)
        if self.config.proxy.enabled:
            options: ChromeOptions = self.options.add_proxy_and_build(
                proxy=self.set_proxy
            )
        else:
            options: ChromeOptions = self.options.build(proxy=self.set_proxy)

        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(self.config.webdriver.timeouts.page_load)

    def _init_from_chromeOptions(
        self,
        options: ChromeOptions,
        executable_path: str = "/usr/bin/chromedriver",
        page_timeout: int = 10,
    ):
        logger.debug("=" * 6 + " Init WebDriver using Options " + "=" * 6)
        service = Service(
            executable_path=executable_path
        )  # Fixed typo and missing parenthesis
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(page_timeout)

    def _init_from_hydra_config(self, config: DictConfig):
        # old func - see to remove / modify
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

    def go_get_json_rotation(
        self, url: str
    ) -> Optional[Union[Dict, List, str, int, float, bool]]:
        """navigate and get_json_content"""

        if self.rotation_counter <= 0:
            logger.debug("rotation_counter resetting and init driver.")
            # reset the driver and counter
            self._set_proxy_rotation_counter()
            self._set_random_proxy_from_list()
            self.driver.close()
            self._init_from_chromeOptionsBuilder()
        else:
            logger.debug("Getting url, decreasing counter.")
            self.rotation_counter -= 1

        return self.go_get_json(url)

    def close(self) -> None:
        """Close the driver."""
        if hasattr(self, "driver") and self.driver:
            self.driver.quit()
            logger.debug(f"WebDriver closed for session: {self.session_id}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
