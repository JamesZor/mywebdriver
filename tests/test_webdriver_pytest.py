# test_webdriver_pytest.py
import json
import logging

import pytest
from omegaconf import DictConfig, OmegaConf

import webdriver.core.factory as factory
from webdriver import MullvadProxyManager, MyWebDriver

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

TEST_PROXY_DICT: dict = {
    "country": "Switzerland",
    "city": "Zurich",
    "socks5": "10.124.0.121",
    "hostname": "ch-zrh-wg-001",
    "proxy_url": "socks5://10.124.0.121:1080",
    "checked_at": "2025-07-03T21:34:09.946244",
}
TEST_PROXY_LIST: list[dict] = [
    {
        "country": "Switzerland",
        "city": "Zurich",
        "socks5": "10.124.0.121",
        "hostname": "ch-zrh-wg-001",
        "proxy_url": "socks5://10.124.0.121:1080",
        "checked_at": "2025-07-03T21:34:09.946244",
    },
    {
        "country": "Australia",
        "city": "Sydney",
        "socks5": "10.124.0.215",
        "hostname": "au-syd-wg-102",
        "proxy_url": "socks5://10.124.0.215:1080",
        "checked_at": "2025-07-04T13:50:42.086451",
    },
    {
        "country": "Canada",
        "city": "Vancouver",
        "socks5": "10.124.0.13",
        "hostname": "ca-van-wg-201",
        "proxy_url": "socks5://10.124.0.13:1080",
        "checked_at": "2025-07-04T13:50:50.156475",
    },
    {
        "country": "Germany",
        "city": "Berlin",
        "socks5": "10.124.0.7",
        "hostname": "de-ber-wg-001",
        "proxy_url": "socks5://10.124.0.7:1080",
        "checked_at": "2025-07-04T13:50:55.847510",
    },
]

TEST_URL_MULLVAD: str = "https://am.i.mullvad.net/json"


# FIXTURES - These handle setup/teardown automatically
@pytest.fixture
def basic_config():
    """Fixture to provide basic config for tests."""
    return factory.load_package_config(config_name="test_config")


@pytest.fixture
def proxy_enabled_config():
    """Fixture to provide proxy-enabled config."""
    override = ["proxy.enabled=true"]
    return factory.load_package_config(config_name="test_config", overrides=override)


@pytest.fixture
def rotation_enabled_config():
    """Fixture for proxy rotation enabled config."""
    override = ["proxy.enabled=true", "proxy.rotation.enabled=true"]
    return factory.load_package_config(config_name="test_config", overrides=override)


def test_basic_webdriver_creation(basic_config):
    """Test that WebDriver can be created and closed without errors."""
    # Add debug output like your original tests!
    print("=" * 15 + " Running pytest webdriver creation test " + "=" * 15)
    print(f"Config loaded: {OmegaConf.to_yaml(basic_config)}")

    # Setup
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(basic_config)
    print(f"Chrome options created: {chrome_optionbuilder}")

    # Test
    print("Creating webdriver...")
    webdriver = MyWebDriver(
        config=basic_config, optionsbulder=chrome_optionbuilder, session_id="test_basic"
    )
    print("Webdriver created successfully!")

    # Assertions - This is what pytest checks!
    assert webdriver is not None, "WebDriver should be created successfully"
    assert hasattr(webdriver, "close"), "WebDriver should have close method"

    # Cleanup
    print("Closing webdriver...")
    webdriver.close()
    print("Test completed!")

    # Could add more assertions here about the state after closing


# YOUR TURN: Convert this next test
def test_basic_webdriver_get_data(basic_config):
    """Test basic WebDriver can fetch data from a URL."""
    # TODO: You fill this in following the pattern above
    # 1. Setup chrome_optionbuilder and webdriver
    # 2. Define test_url
    # 3. Call webdriver.get_page()
    # 4. Add assertions about the returned data
    # 5. Cleanup
    pass


# PARTIALLY COMPLETED: You can finish this one
def test_webdriver_with_proxy(proxy_enabled_config):
    """Test WebDriver creation with proxy configuration."""
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(
        proxy_enabled_config
    )

    webdriver = MyWebDriver(
        config=proxy_enabled_config,
        optionsbulder=chrome_optionbuilder,
        proxy=TEST_PROXY_DICT,
        session_id="test_proxy",
    )

    # TODO: Add your assertions here
    # What should you test about the webdriver when using a proxy?

    webdriver.close()


# CHALLENGE: Convert your rotation test
def test_proxy_rotation():
    """Test that proxy rotation actually rotates between different proxies."""
    # TODO: This is your more complex test to convert
    # Hint: You'll need the rotation_enabled_config fixture
    # and should assert that different hostnames are used
    pass


# Example of parametrized test (advanced)
@pytest.mark.parametrize("proxy_data", TEST_PROXY_LIST[:2])  # Test with first 2 proxies
def test_individual_proxies(proxy_enabled_config, proxy_data):
    """Test each proxy individually."""
    # TODO: You could implement this to test each proxy works
    pass
