"""
Enhanced WebDriver module with error handling, retries, and configuration.

This module extends the basic Selenium WebDriver with additional functionality:
- Proper error handling
- Retry mechanisms for intermittent failures
- Configurable timeouts and wait strategies
- Logging for debugging
"""

import json
import logging
import time
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple, Union

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sofascore.infrastructure.mullvadproxymanager import MullvadProxyManager

# Set up logging
logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions=(WebDriverException,),
):
    """
    Retry decorator for WebDriver operations.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier (e.g., 2.0 means delay doubles each retry)
        exceptions: Tuple of exceptions that trigger a retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_attempts, delay
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(f"Retry triggered for {func.__name__}: {str(e)}")
                    mtries -= 1
                    time.sleep(mdelay)
                    mdelay *= backoff
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Enhance the MyWebDriver class with proxy rotation
class MyWebDriver:
    """Enhanced existing MyWebDriver class with IP rotation capabilities."""

    def __init__(
        self,
        headless: bool = False,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: int = 30,
        page_load_timeout: int = 30,
        binary_location: str = "/usr/bin/chromium",
        driver_path: str = "/usr/bin/chromedriver",
        disable_images: bool = False,
        disable_javascript: bool = False,
        # IP rotation parameters
        enable_rotation: bool = False,
        rotation_interval: int = 10,
        countries: Optional[List[str]] = None,
    ):
        """
        Initialize WebDriver with custom options and IP rotation capabilities.

        Args:
            headless: Whether to run Chrome in headless mode
            proxy: Optional proxy server (format: "host:port")
            user_agent: Custom user agent string
            timeout: Default timeout for find_element operations
            page_load_timeout: Timeout for page loading
            binary_location: Path to Chrome binary
            driver_path: Path to chromedriver executable
            disable_images: Whether to disable image loading
            disable_javascript: Whether to disable JavaScript
            enable_rotation: Whether to enable IP rotation
            rotation_interval: Number of requests before rotating IP
            countries: Optional list of country codes to filter proxies by
        """
        self.timeout = timeout

        # Setup IP rotation if enabled
        self.enable_rotation = enable_rotation
        self.rotation_interval = rotation_interval
        self.request_counter = 0

        if self.enable_rotation:
            self.proxy_manager = MullvadProxyManager(countries=countries)
            if not proxy:  # If no specific proxy is provided, get a random one
                self.proxy_manager.process_proxies()
                proxy_info = self.proxy_manager.get_random_proxy()
                proxy = proxy_info.get("proxy_url")
                self.current_proxy_info = proxy_info
                logger.info(
                    f"Using proxy: {proxy_info.get('country')} - {proxy_info.get('city')}"
                )

        self.options = self._configure_options(
            headless=headless,
            proxy=proxy,
            user_agent=user_agent,
            binary_location=binary_location,
            disable_images=disable_images,
            disable_javascript=disable_javascript,
        )

        self.service = Service(executable_path=driver_path)
        self.driver = self._initialize_driver()
        self.driver.set_page_load_timeout(page_load_timeout)

        if self.enable_rotation:
            # Verify the current IP
            _, self.current_ip = self.proxy_manager.verify_ip_change()

        logger.info("WebDriver initialized successfully")

    def _configure_options(
        self,
        headless: bool,
        proxy: Optional[str],
        user_agent: Optional[str],
        binary_location: str,
        disable_images: bool,
        disable_javascript: bool,
    ) -> Options:
        """
        Configure Chrome options.

        Args:
            headless: Whether to run Chrome in headless mode
            proxy: Optional proxy server
            user_agent: Custom user agent string
            binary_location: Path to Chrome binary
            disable_images: Whether to disable image loading
            disable_javascript: Whether to disable JavaScript

        Returns:
            Configured Chrome options
        """
        options = Options()

        # Set binary location
        options.binary_location = binary_location

        # Set capabilities for logging
        options.set_capability(
            "goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"}
        )

        # Add headless option if needed
        if headless:
            options.add_argument("--headless")

        # Add proxy if specified
        if proxy:
            options.add_argument(f"--proxy-server={proxy}")

        # Add user agent if specified
        if user_agent:
            options.add_argument(f"--user-agent={user_agent}")

        # Common options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")

        # Performance options
        if disable_images:
            options.add_argument("--blink-settings=imagesEnabled=false")

        if disable_javascript:
            options.add_argument("--disable-javascript")

        return options

    def _initialize_driver(self) -> webdriver.Chrome:
        """
        Initialize and return a Chrome WebDriver instance.

        Returns:
            Configured Chrome WebDriver
        """
        try:
            driver = webdriver.Chrome(service=self.service, options=self.options)
            return driver
        except WebDriverException as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    ##############################
    ###  Proxy methods
    ##############################

    def get_ip_info(self) -> Dict:
        """
        Get information about the current IP and proxy.

        Returns:
            Dictionary with IP and proxy information
        """
        MULLVAD_IP_ADDR = "https://am.i.mullvad.net/json"
        try:
            self.driver.get(MULLVAD_IP_ADDR)
            ip_data = self.get_json_content()

            if not ip_data:
                logger.warning("Could not get IP data from MULLVAD_ID")
                return {}

            result = {
                "ip": ip_data.get("ip", "unknown"),
                "is_mullvad": ip_data.get("mullvad_exit_ip", False),
                "country": ip_data.get("country", "unknown"),
                "city": ip_data.get("city", "unknown"),
                "requests_since_rotation": self.request_counter,
            }

            if hasattr(self, "current_proxy_info"):
                result.update(
                    {
                        "proxy_country": self.current_proxy_info.get("country"),
                        "proxy_city": self.current_proxy_info.get("city"),
                        "proxy_hostname": self.current_proxy_info.get("hostname"),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error getting IP info: {str(e)}")
            return {"error": str(e)}

    def verify_ip_change(
        self, previous_ip: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify that the IP has changed by checking Mullvad's IP verification service.

        Args:
            previous_ip: Previous IP address to compare against

        Returns:
            Tuple of (success, current_ip)
        """
        try:
            ip_data_response = self.get_ip_info()

            # Check for empty ip_data_response
            if not ip_data_response:
                logger.warning(f"Warning. Issue connecting via proxy")
                return False, previous_ip

            current_ip = ip_data_response.get("ip", "unknown")

            # Check if IP has changed
            if previous_ip and current_ip == previous_ip:
                logger.warning(f"IP has not changed: {current_ip}")
                return False, previous_ip

            logger.info(f"Current IP: {current_ip}")
            return True, current_ip

        except Exception as e:
            logger.error(f"Error verifying IP change: {str(e)}")
            return False, None

    def driver_ip_reset(self) -> Dict:
        """
        Helper method for rotate_ip - resets driver with new proxy

        Returns:
            Dictionary with proxy information
        """
        # Get a random proxy
        proxy_info = self.proxy_manager.get_random_proxy()
        proxy_url = proxy_info.get("proxy_url")

        logger.info(
            f"Attempting IP rotation to {proxy_info.get('country')} - {proxy_info.get('city')}"
        )

        # Close the current driver
        self.close()

        # Create new options with the new proxy
        self.options = self._configure_options(
            headless=self.options.arguments
            and "--headless" in " ".join(self.options.arguments),
            proxy=proxy_url,
            user_agent=next(
                (
                    arg.replace("--user-agent=", "")
                    for arg in self.options.arguments
                    if arg.startswith("--user-agent=")
                ),
                None,
            ),
            binary_location=self.options.binary_location,
            disable_images=self.options.arguments
            and "--blink-settings=imagesEnabled=false"
            in " ".join(self.options.arguments),
            disable_javascript=self.options.arguments
            and "--disable-javascript" in " ".join(self.options.arguments),
        )

        # Initialize a new driver with the new proxy
        self.driver = self._initialize_driver()

        # Update current proxy info
        self.current_proxy_info = proxy_info

        return proxy_info

    def rotate_ip(self) -> bool:
        """
        Rotate to a new random SOCKS5 proxy from Mullvad's list.

        Returns:
            Boolean indicating success
        """
        if not self.enable_rotation:
            logger.warning("IP rotation is not enabled")
            return False

        # Store the current URL and IP
        previous_ip = self.current_ip
        current_url = self.driver.current_url if hasattr(self, "driver") else None

        # Try up to 5 times to get a different IP
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                # Reset driver with new proxy
                proxy_info = self.driver_ip_reset()

                # Verify the IP has changed
                success, new_ip = self.verify_ip_change(previous_ip)

                if success:
                    # IP successfully changed
                    self.current_ip = new_ip
                    self.request_counter = 0  # Reset request counter

                    # Navigate back to the previous URL if available
                    if current_url and current_url != "about:blank":
                        self.navigate(current_url)

                    logger.info(
                        f"Successfully rotated IP to {new_ip} ({proxy_info.get('country')}) on attempt {attempt+1}"
                    )
                    return True

                logger.warning(
                    f"Attempt {attempt+1}/{max_attempts}: IP rotation did not change IP"
                )

            except Exception as e:
                logger.error(f"Error during IP rotation attempt {attempt+1}: {str(e)}")

        # All attempts failed
        logger.error(f"Failed to rotate IP after {max_attempts} attempts")
        return False

    def _driver_ip_reset(self, proxy_info: Dict) -> Dict:
        """
        Helper method for rotate_ip - resets driver with new proxy

        Returns:
            Dictionary with proxy information
        """
        # Get a random proxy
        proxy_url = proxy_info.get("proxy_url")

        logger.info(
            f"Attempting IP rotation to {proxy_info.get('country')} - {proxy_info.get('city')}"
        )

        # Close the current driver
        self.close()

        # Create new options with the new proxy
        self.options = self._configure_options(
            headless=self.options.arguments
            and "--headless" in " ".join(self.options.arguments),
            proxy=proxy_url,
            user_agent=next(
                (
                    arg.replace("--user-agent=", "")
                    for arg in self.options.arguments
                    if arg.startswith("--user-agent=")
                ),
                None,
            ),
            binary_location=self.options.binary_location,
            disable_images=self.options.arguments
            and "--blink-settings=imagesEnabled=false"
            in " ".join(self.options.arguments),
            disable_javascript=self.options.arguments
            and "--disable-javascript" in " ".join(self.options.arguments),
        )

        # Initialize a new driver with the new proxy
        self.driver = self._initialize_driver()

        # Update current proxy info
        self.current_proxy_info = proxy_info

        return proxy_info

    def _rotate_ip(self, proxy: Dict) -> bool:
        """
        Rotate to a new random SOCKS5 proxy from Mullvad's list.

        Returns:
            Boolean indicating success
        """
        if not self.enable_rotation:
            logger.warning("IP rotation is not enabled")
            return False

        # Store the current URL and IP
        previous_ip = self.current_ip
        current_url = self.driver.current_url if hasattr(self, "driver") else None

        # Try up to 5 times to get a different IP
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                # Reset driver with new proxy
                proxy_info = self._driver_ip_reset(proxy)

                # Verify the IP has changed
                success, new_ip = self.verify_ip_change(previous_ip)

                if success:
                    # IP successfully changed
                    self.current_ip = new_ip
                    self.request_counter = 0  # Reset request counter

                    # Navigate back to the previous URL if available
                    if current_url and current_url != "about:blank":
                        self.navigate(current_url)

                    logger.info(
                        f"Successfully rotated IP to {new_ip} ({proxy_info.get('country')}) on attempt {attempt+1}"
                    )
                    return True

                logger.warning(
                    f"Attempt {attempt+1}/{max_attempts}: IP rotation did not change IP"
                )

            except Exception as e:
                logger.error(f"Error during IP rotation attempt {attempt+1}: {str(e)}")

        # All attempts failed
        logger.error(f"Failed to rotate IP after {max_attempts} attempts")
        return False

    ##############################
    ###  Main methods
    ##############################

    def ip_counter(self) -> None:
        """
        Method to handle IP rotation based on request counter
        """
        if self.enable_rotation:
            self.request_counter += 1
            if self.request_counter >= self.rotation_interval:
                self.rotate_ip()

    @retry(max_attempts=3, delay=2.0)
    def navigate(self, url: str) -> None:
        """
        Navigate to the specified URL with retry logic and IP rotation.

        Args:
            url: URL to navigate to
        """
        try:
            # Check if we need to rotate IP before navigation
            self.ip_counter()

            logger.info(f"Navigating to {url}")
            self.driver.get(url)

        except TimeoutException:
            logger.warning(f"Timeout while loading {url}")
            raise
        except WebDriverException as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            raise

    @property
    def current_url(self) -> str:
        """Get the current URL."""
        return self.driver.current_url

    def get_page_source(self) -> str:
        """Get the page source."""
        return self.driver.page_source

    def save_screenshot(self, filename: str) -> None:
        """
        Save a screenshot of the current page.

        Args:
            filename: Path to save the screenshot
        """
        try:
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved to {filename}")
        except WebDriverException as e:
            logger.error(f"Failed to save screenshot: {str(e)}")
            raise

    def wait_for_element(self, by, value, timeout=None):
        """
        Wait for an element to be present and return it.

        Args:
            by: Method to locate element (e.g., By.ID)
            value: Value to search for
            timeout: Wait timeout in seconds (uses default if None)

        Returns:
            WebElement object
        """
        timeout = timeout or self.timeout
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for element {by}={value}")
            raise
        except WebDriverException as e:
            logger.error(f"Error waiting for element {by}={value}: {str(e)}")
            raise

    def execute_script(self, script, *args):
        """
        Execute JavaScript in the current window.

        Args:
            script: JavaScript to execute
            *args: Arguments to pass to the script

        Returns:
            Result of the script execution
        """
        try:
            return self.driver.execute_script(script, *args)
        except WebDriverException as e:
            logger.error(f"Error executing script: {str(e)}")
            raise

    def get_json_content(self):
        """..."""
        JAVASCRIPT_COMMAND = "return document.body.innerText"
        json_content = self.execute_script(JAVASCRIPT_COMMAND)

        if json_content:
            return json.loads(json_content)
        else:
            logger.warning(f"Error getting json content @ {self.current_url}")

    def close(self):
        """Close the browser and free resources."""
        try:
            if hasattr(self, "driver") and self.driver:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
        except WebDriverException as e:
            logger.warning(f"Error closing WebDriver: {str(e)}")

    def __enter__(self):
        """Support for context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context."""
        self.close()


################################################################################
############################## Testing area                 ####################
################################################################################
if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize with automatic IP rotation every 5 requests
    driver = MyWebDriver(
        headless=False,
        enable_rotation=True,
        rotation_interval=2,
    )
    driver.get_ip_info()

    test_url = "https://api.sofascore.com/api/v1/tournament/1/season/41886/events"
    driver.navigate(test_url)
    driver.get_json_content()
    driver.rotate_ip()
    driver.get_ip_info()
    driver.navigate(test_url)
    driver.get_json_content()

##    p_l = driver.proxy_manager.fetch_proxy_list()
##    v_p = driver._test_proxy_list(p_l[80:88])
##    v_p
##    ################################################################################
##    ############################## can we get through the blocks ###################
##    ################################################################################
##
##    test_url = "https://api.sofascore.com/api/v1/tournament/1/season/41886/events"
##
##    # Configure logging
##    logging.basicConfig(
##        level=logging.INFO,
##        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
##    )
##
##    # Initialize with automatic IP rotation every 5 requests
##    driver = MyWebDriver(
##        headless=False,
##        enable_rotation=True,
##        rotation_interval=5,
##    )
##    ll = driver.proxy_manager.fetch_proxy_list()
##
##    results_l = [{}]*len(ll)
##
##    for i, proxy in enumerate(ll):
##        if driver._rotate_ip(proxy):
##            driver.navigate(test_url)
##            results = driver.get_json_content()
##
##            driver_details = driver.get_ip_info()
##            results_l[i] = {
##                    'proxy': driver_details,
##                    'json': results
##            }
##results_l
##
##valid_proxies = []
##for i, dic in enumerate(results_l):
##    if dic:  # Check if dictionary exists
##        j = dic.get('json')
##        ip = dic.get('proxy').get('ip')
##
##        if j:
##            e = j.get('events')
##            if e:
##                print(f"{i=} : {ip=}")
##
##    """
##i=18 : ip='103.136.147.4'
##i=19 : ip='103.136.147.66'
##i=20 : ip='103.136.147.130'
##i=21 : ip='103.136.147.198'
##i=50 : ip='104.193.135.197'
##i=51 : ip='104.193.135.101'
##i=54 : ip='38.240.225.37'
##i=55 : ip='38.240.225.69'
##i=56 : ip='193.32.127.211'
##i=57 : ip='193.32.127.190'
##i=58 : ip='193.32.127.223'
##i=59 : ip='193.32.127.201'
##i=60 : ip='193.32.127.235'
##i=61 : ip='193.32.127.169'
##i=85 : ip='193.32.248.130'
##i=86 : ip='193.32.248.142'
##i=87 : ip='193.32.248.155'
##i=88 : ip='193.32.248.168'
##i=89 : ip='193.32.248.181'
##i=90 : ip='193.32.248.194'
##i=91 : ip='193.32.248.244'
##i=92 : ip='193.32.248.234'
##i=93 : ip='185.254.75.13'
##i=94 : ip='185.254.75.14'
##i=95 : ip='185.254.75.15'
##i=96 : ip='185.213.155.200'
##    """
##
##vaild_proxies
##    ################################################################################
##    ############################## new tests 2025-03-22       ####################
##    ################################################################################
##    # Configure logging
##    logging.basicConfig(
##        level=logging.INFO,
##        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
##    )
##
##    # Initialize with automatic IP rotation every 5 requests
##    driver = MyWebDriver(
##        headless=False,
##    )
##    # Initialize with automatic IP rotation every 5 requests
##    driver = MyWebDriver(
##        headless=False,
##        enable_rotation=True,
##        rotation_interval=5,
##    )
##
##    driver.navigate("https://am.i.mullvad.net/json")
##    driver.get_json_content()
##    driver.navigate("https://example.com")
##    driver.get_ip_info()
##    # Check current IP information
##    ip_info = driver.get_ip_info()
##    print(f"Current IP: {ip_info['ip']} ({ip_info['country']})")
##    driver.rotate_ip()
##
##    ip_info1 = driver.get_ip_info()
##    print(f"Current IP: {ip_info1['ip']} ({ip_info1['country']})")
##    ip_data = [{}] * 20
##    ## loop test
##    for i, x in enumerate(range(0, 20)):
##        driver.rotate_ip()
##        ip_info = driver.get_ip_info()
##        ip_data[i] = ip_info
##        print(f"Current IP: {ip_info.get('ip')} ({ip_info.get('country')})")
##
##    for x in ip_data:
##        print(f"Current IP: {x.get('ip','no_ip')} ({x.get('country','fail')})")
##
##    ip_data = [{}] * 20
##    ## loop test
##    for i, x in enumerate(range(0, 20)):
##        driver.navigate("https://www.google.com")
##        ip_info = driver.get_ip_info()
##        ip_data[i] = ip_info
##        print(f"Current IP: {ip_info.get('ip')} ({ip_info.get('country')})")
##    ip_data
##
##    ################################################################################
##    ############################## Basic tests 2025-03-22       ####################
##    ################################################################################
##    # Configure logging
##    logging.basicConfig(
##        level=logging.INFO,
##        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
##    )
##
##    # Test the WebDriver
##    driver = WebDriver(headless=False)
##    driver.navigate("https://www.sofascore.com")
##    print(f"Current URL: {driver.current_url}")
##
##    ### match_id
##    match_id = "12437019"
##    base_url = "https://api.sofascore.com/api/v1/event/"
##    ## basic match info
##    driver.navigate(base_url + match_id)
##    driver.get_page_data()
##
##    import json
##
##    # Method 4: Execute JavaScript to get page content
##    json_content = driver.execute_script("return document.body.innerText")
##    match_data = json.loads(json_content)
##    match_data
##
##    driver.close()
