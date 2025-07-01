"""
File description
"""

import logging
from typing import Any, Dict, Optional

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

# Set up logging
logger = logging.getLogger(__name__)


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
            logger.debug("=== END Config Validation ===")

    def _init_from_hydra_config(self, config: DictConfig):
        """Initialize using Hydra instantiate."""
        logger.debug("Initializing WebDriver using Hydra instantiate")

        # Build the options using the options builder
        options_builder = instantiate(config.webdriver.browser.options)
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

    def close(self) -> None:
        """Close the driver."""
        if hasattr(self, "driver") and self.driver:
            self.driver.quit()
            logger.info(f"WebDriver closed for session: {self.session_id}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
