# test_basic.py
import json
import logging

from omegaconf import DictConfig, OmegaConf

import webdriver.core.factory as factory
from webdriver import MullvadProxyManager, MyWebDriver

# Configure logging
# logging.basicConfig(level=logging.DEBUG)

logging.basicConfig(level=logging.DEBUG)


def test_basic_webdriver():
    """Test basic WebDriver functionality."""
    print("=" * 15 + " Running Simple webdriver setup" + "=" * 15)

    # here we load the config
    cfg: DictConfig = factory.load_package_config(config_name="test_config")
    print(f"print cfg:\n{OmegaConf.to_yaml(cfg)}\n.")
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(cfg)

    print(f"chrome options: {chrome_optionbuilder}.")

    options = chrome_optionbuilder.build()

    webdriver = MyWebDriver(config=cfg, options=options, session_id="test1")

    # TODO
    # update webdriver to have cfg input
    # call webdriver

    webdriver.close()

    print("-" * 15 + " Basic tests passed! " + "-" * 15)


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
    test_basic_webdriver()
# test_basic_webdriver_with_head()
#    test_getting_json_content()
