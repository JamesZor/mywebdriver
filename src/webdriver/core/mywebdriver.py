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
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from webdriver.core.options import ChromeOptionsBuilder

# Set up logging
logger = logging.getLogger(__name__)


# TODO
# add timeout limits
# option builder improve handling


class MyWebDriver:
    """Enhanced existing MyWebDriver class with IP rotation capabilities."""

    def __init__(
        self,
        config: DictConfig,
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
        if config:
            if self._is_valid_config(config):
                # Use Hydra instantiation
                self._init_from_hydra_config(config)
        else:
            logger.error("Config validation failed")
            raise ValueError("Config structure is invalid")

        #
        self.session_id: str = session_id or "default"
        self.config: DictConfig = config
        logger.debug(f"Config file:\n{OmegaConf.to_yaml(config)}.")
        logger.info(f"WebDriver initialized for session: {self.session_id}")

    def _is_valid_config(self, config: DictConfig) -> bool:
        """
        Validate config structure using OmegaConf's safe access methods.
        """
        logger.debug("=== Config Validation ===")
        logger.debug(f"Config type: {type(config)}")
        logger.debug(f"Config keys: {list(config.keys()) if config else 'None'}")

        try:
            # Check required top-level sections exist
            webdriver_section = OmegaConf.select(config, "webdriver")
            proxy_section = OmegaConf.select(config, "proxy")

            logger.debug(f"Webdriver section found: {webdriver_section is not None}")
            logger.debug(f"Proxy section found: {proxy_section is not None}")

            if webdriver_section is None:
                logger.error("Missing 'webdriver' section in config")
                return False

            if proxy_section is None:
                logger.error("Missing 'proxy' section in config")
                return False

            # Check webdriver.browser section
            browser_section = OmegaConf.select(config, "webdriver.browser")
            logger.debug(f"Browser section found: {browser_section is not None}")

            if browser_section is None:
                logger.error("Missing 'webdriver.browser' section in config")
                return False

            # If we have _target_, validate Hydra structure
            target = OmegaConf.select(config, "webdriver.browser._target_")
            if target:
                logger.debug(f"Found _target_: {target}")

                # Check required Hydra fields
                service_target = OmegaConf.select(
                    config, "webdriver.browser.service._target_"
                )
                options_target = OmegaConf.select(
                    config, "webdriver.browser.options._target_"
                )

                logger.debug(f"Service _target_: {service_target}")
                logger.debug(f"Options _target_: {options_target}")

                if not service_target or not options_target:
                    logger.error("Hydra config missing service or options _target_")
                    return False

            logger.debug("✅ Config validation passed")
            return True

        except Exception as e:
            logger.error(f"Config validation error: {e}")
            logger.debug(f"❌ Config validation failed: {e}")
            return False
        finally:
            logger.debug("--- END Config Validation ---")

    def _init_from_hydra_config(self, config: DictConfig):
        """Initialize using Hydra instantiate."""
        logger.debug("=" * 6 + " Init WebDriver using Hydra " + "=" * 6)

        # Build the options using the options builder
        options_builder: ChromeOptionsBuilder = instantiate(
            config.webdriver.browser.options
        )

        # Proxy socks5
        options_builder.proxy_sock5(config.socks5)
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
            self.driver.set_page_load_timeout(config.timeouts.page_load)

        logger.debug("=" * 6 + " Init WebDriver using Hydra " + "=" * 6)

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
            logger.info(f"WebDriver closed for session: {self.session_id}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
