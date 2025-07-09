"""
File description
"""

import atexit
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
from numpy.random import Generator as RandomGenrator
from omegaconf import DictConfig
from selenium import webdriver
from selenium.common.exceptions import (
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service

from webdriver.core.options import ChromeOptionsBuilder

# Set up logging
logger = logging.getLogger(__name__)

# TODO
# proxy logic setup

# rotations logic

import time
from functools import wraps

from selenium.common.exceptions import TimeoutException, WebDriverException


def retry(func):
    """Simple retry decorator that uses config from self.config"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Get retry settings from config (add these to your config files)
        max_attempts = getattr(self.config.webdriver, "retry_attempts", 3)
        delay = getattr(self.config.webdriver, "retry_delay", 2.0)

        for attempt in range(max_attempts):
            try:
                return func(self, *args, **kwargs)
            except (TimeoutException, WebDriverException) as e:
                if attempt == max_attempts - 1:  # Last attempt
                    logger.error(
                        f"{func.__name__} failed after {max_attempts} attempts: {e}"
                    )
                    return None  # Return None instead of crashing
                else:
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}. Retrying in {delay}s..."
                    )
                    logger.debug(f"{func.__name__} {str(e)}.")

                    time.sleep(delay)

        return None

    return wrapper


class MyWebDriver:
    """Enhanced existing MyWebDriver class with IP rotation capabilities."""

    def __init__(
        self,
        optionsbuilder: ChromeOptionsBuilder,
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
        # Register cleanup handlers for emergency exits
        atexit.register(self._emergency_cleanup)

        self.config: DictConfig = config
        self.options: Optional[ChromeOptionsBuilder] = optionsbuilder
        self.session_id: str = session_id or "default"
        self.set_proxy: Optional[dict] = None
        self.proxy_list: Optional[list[dict]] = proxy_list
        self.rng: RandomGenrator = np.random.default_rng()

        self.get_page: Callable[
            [str], Optional[Union[Dict, List, str, int, float, bool]]
        ] = self.go_get_json

        self.rotation_counter: Optional[int] = None

        # proxy logic
        if self.config.proxy.enabled:
            logger.debug(" Socks5 proxy enabled.")
            logger.debug(f" {proxy =}")

            logger.debug(f" {proxy_list =}")

            # if given a single proxy, use this, ignore list.
            if proxy is not None:
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

        if optionsbuilder is not None:
            logger.debug("Loading the options.")
            self._init_from_chromeOptionsBuilder()
        else:
            raise ValueError("Need to pass an option builder.")

        logger.debug(f"WebDriver initialized for session: {self.session_id}")

    def _set_proxy_rotation_counter(self):
        """
        set the rotation counter, and resets.
        """
        rotation_type: str = self.config.proxy.rotation.random_type
        interval: list[int] = self.config.proxy.rotation.interval

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
            random_proxy: dict = self.rng.choice(self.proxy_list)
            self.set_proxy = random_proxy
            logger.debug(f"Selected randomly proxy: {random_proxy.get('hostname')}.")
        else:
            logger.warning("No proxy list found.")

    def _init_from_chromeOptionsBuilder(
        self,
    ):
        logger.debug("=" * 6 + " Init WebDriver using Options " + "=" * 6)
        service = Service(
            executable_path=self.config.webdriver.browser.service.executable_path
        )
        if self.config.proxy.enabled:
            options: ChromeOptions = self.options.add_proxy_and_build(
                proxy=self.set_proxy
            )
        else:
            options: ChromeOptions = self.options.build()

        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(self.config.webdriver.timeouts.page_load)

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
        """Get JSON content from document.body.innerText."""
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

    @retry
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
            self.driver = None
            logger.debug(f"WebDriver closed for session: {self.session_id}")

    def _emergency_cleanup(self):
        """Emergency cleanup for unexpected exits."""
        try:
            if hasattr(self, "driver") and self.driver:
                self.driver.quit()
        except:
            pass  # Ignore errors during emergency cleanup

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals."""
        self._emergency_cleanup()
        raise KeyboardInterrupt()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
