"""
File description
"""

import logging
from typing import Any, Dict, Optional

from omegaconf import DictConfig
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
        config: Optional[DictConfig] = None,
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
        self.session_id: str = session_id or "default"
        self.config: Optional[DictConfig] = config

        if config:
            logger.debug("Using passed config file.")
            # Use configuration
            self.headless: bool = config.webdriver.browser.headless
            self.timeout: float = config.webdriver.browser.timeout
            self.binary_location: str = config.webdriver.browser.binary_location
            self.driver_path: str = config.webdriver.browser.driver_path
        else:
            logger.debug("No cofig file passed, using direct parameters.")
            # Use direct parameters (backward compatibility)
            self.headless: bool = kwargs.get("headless", False)
            self.timeout: float = kwargs.get("timeout", 30)
            self.binary_location: str = kwargs.get(
                "binary_location", "/usr/bin/chromium"
            )
            self.driver_path: str = kwargs.get("driver_path", "/usr/bin/chromedriver")

        # Initialize browser
        self.options: Options = self._configure_chrome_options()
        self.service: Service = Service(executable_path=self.driver_path)
        self.driver: webdriver.Chrome = self._initialize_driver()

        logger.info(f"WebDriver initialized for session: {self.session_id}")

    def _configure_chrome_options(self) -> Options:
        """Configure Chrome options based on settings."""
        options = Options()
        options.binary_location = self.binary_location

        if self.headless:
            options.add_argument("--headless")

        # Basic stable options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")

        # Performance options
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--disable-javascript")
        return options

    def _initialize_driver(self) -> webdriver.Chrome:
        """
        Initialize and return a Chrome WebDriver instance.

        Returns:
            Configured Chrome WebDriver
        """
        return webdriver.Chrome(service=self.service, options=self.options)

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
        else:
            print("Direct parameters used:")
            print(f"  headless: {self.headless}")
            print(f"  timeout: {self.timeout}")
            print(f"  binary_location: {self.binary_location}")
            print(f"  driver_path: {self.driver_path}")
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


################################################################################
############################## Testing area                 ####################
################################################################################
if __name__ == "__main__":
    logging.basicConfig(
        # Configure logging
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
