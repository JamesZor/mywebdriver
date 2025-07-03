# test_basic.py
import logging

from omegaconf import DictConfig

from webdriver import MullvadProxyManager, MyWebDriver
from webdriver.core.factory import create_webdriver_with_hydra

# Configure logging
# logging.basicConfig(level=logging.DEBUG)

logging.basicConfig(level=logging.DEBUG)


def test_basic_webdriver():
    """Test basic WebDriver functionality."""

    # Test 1: Direct parameters (backward compatibility)
    print("Testing direct parameters...")
    driver = MyWebDriver(headless=True, session_id="test_1")
    driver.navigate("https://www.sscardapane.it/tutorials/hydra-tutorial/")
    print(f"Current URL: {driver.current_url}")
    driver.close()

    # Test 2: Config object (when you add Hydra)
    print("Testing config object...")

    config = DictConfig(
        {
            "browser": {
                "headless": True,
                "timeout": 30,
                "binary_location": "/usr/bin/chromium",
                "driver_path": "/usr/bin/chromedriver",
            }
        }
    )
    driver = MyWebDriver(config=config, session_id="test_2")
    driver.navigate("https://www.sscardapane.it/tutorials/hydra-tutorial/")
    print(f"Current URL: {driver.current_url}")
    driver.close()

    print("Basic tests passed!")


def test_basic_webdriver_with_head():
    """Test basic WebDriver functionality."""

    # Test 1: Direct parameters (backward compatibility)
    print("Testing direct parameters...")
    driver = create_webdriver_with_hydra(config_name="config")
    test_url = "https://www.sscardapane.it/tutorials/hydra-tutorial/"
    driver.navigate(test_url)
    print(f"Current URL: {driver.current_url}")

    assert driver.current_url == test_url, "urls do not match"

    driver.close()


def test_basic_webdriver_with_head_proxy_manager():
    """Test basic WebDriver functionality."""

    pm = MullvadProxyManager()

    driver: MyWebDriver = MyWebDriver(config=pm._load_package_config())
    test_url: str = "https://am.i.mullvad.net/json"
    print(driver.go_get_json(test_url))


def test_getting_json_content() -> None:
    driver = create_webdriver_with_hydra()
    test_url: str = "https://api.sofascore.com/api/v1/tournament/1"
    #    test_url: str = "https://am.i.mullvad.net/json"

    driver.navigate(test_url)
    print(f"==================================\nCurrent URL: {driver.current_url}")
    print("=" * 10)
    #    webpage_data = driver.get_json_content_debug()
    webpage_data = driver.get_json_content()

    print(webpage_data)
    print("=" * 10)


if __name__ == "__main__":
    #    test_basic_webdriver_with_head()
    test_getting_json_content()
