# test_basic.py
import logging

from omegaconf import DictConfig

from webdriver import MyWebDriver

# Configure logging
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
    driver = MyWebDriver(headless=False, session_id="test_1")
    driver.navigate("https://www.sscardapane.it/tutorials/hydra-tutorial/")

    print(f"Current URL: {driver.current_url}")
    driver._print_config()
    driver.close()


if __name__ == "__main__":
    test_basic_webdriver()
