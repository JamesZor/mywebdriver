# test_webdriver_pytest.py
import json
import logging

import pytest
from omegaconf import DictConfig, OmegaConf

import webdriver.core.factory as factory
from webdriver import MullvadProxyManager, MyWebDriver

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


DEFAULT_HOSTNAME: str = "gb-glw-wg-001"

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
    logger.debug("=" * 15 + " Running pytest webdriver creation test " + "=" * 15)
    logger.debug(f"Config loaded: {OmegaConf.to_yaml(basic_config)}")

    # Setup
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(basic_config)
    logger.debug(f"Chrome options created: {chrome_optionbuilder}")

    # Test
    logger.debug("Creating webdriver...")
    webdriver: MyWebDriver = MyWebDriver(
        config=basic_config,
        optionsbuilder=chrome_optionbuilder,
        session_id="test_basic",
    )

    logger.debug("Webdriver created successfully!")

    # Assertions - This is what pytest checks!
    assert webdriver is not None, "WebDriver should be created successfully"
    assert hasattr(webdriver, "close"), "WebDriver should have close method"

    assert webdriver.config is basic_config, "Webdriver config is incorrect"
    assert (
        webdriver.options is chrome_optionbuilder
    ), "Webdriver has correct options builder"

    # check configs been set up
    # proxy
    assert (
        webdriver.config.proxy.enabled is False
    ), f"Expected proxy.enabled as false got {webdriver.config.proxy.enabled}."
    assert (
        webdriver.set_proxy is None
    ), f"Expected none set_proxy, got {webdriver.set_proxy}"

    assert webdriver.proxy_list is None, "Expected none proxy list."

    assert (
        webdriver.config.proxy.rotation.enabled is False
    ), f"Expected rotation enabled as false, got {webdriver.config.proxy.rotation.enabled}"

    assert (
        webdriver.get_page.__func__ is webdriver.go_get_json.__func__
    ), f"Expected get_page to be go_get_json, but got {webdriver.get_page.__func__}"
    # Cleanup

    assert hasattr(webdriver, "driver"), "Expecting mywebdrive to have driver"
    assert webdriver.driver, f"Expecting driver, not none, {webdriver.driver}"

    webdriver.close()

    assert webdriver.driver is None, f"webdriver is closed, {webdriver.driver}"


def test_basic_webdriver_get_data(basic_config):
    """Test basic WebDriver can fetch data from a URL."""
    # setup
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(basic_config)
    logger.debug(f"Chrome options\n {chrome_optionbuilder}")

    webdriver: MyWebDriver = MyWebDriver(
        optionsbuilder=chrome_optionbuilder,
        config=basic_config,
        session_id="pytest_get_data",
    )

    logger.debug(f"Getting data from: {TEST_URL_MULLVAD}")
    data = webdriver.get_page(TEST_URL_MULLVAD)
    logger.debug(f"Data:\n{data}")

    assert data is not None, "Data context is None, should be something."
    assert isinstance(data, dict), f"Data context is not a dict: {type(data)}"
    hostname = data.get("mullvad_exit_ip_hostname")

    assert hostname == DEFAULT_HOSTNAME, f"Hostnames don't match: {hostname =}"

    webdriver.close()


def test_webdriver_with_proxy(proxy_enabled_config):
    """Test WebDriver creation with proxy configuration."""
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(
        proxy_enabled_config
    )

    webdriver = MyWebDriver(
        optionsbuilder=chrome_optionbuilder,
        config=proxy_enabled_config,
        proxy=TEST_PROXY_DICT,
        session_id="test_proxy",
    )
    logger.debug(f"Getting data from: {TEST_URL_MULLVAD}")
    data = webdriver.get_page(TEST_URL_MULLVAD)
    logger.debug(f"Data:\n{data}")

    assert data is not None, "Data context is None, should be something."
    assert isinstance(data, dict), f"Data context is not a dict: {type(data)}"
    hostname = data.get("mullvad_exit_ip_hostname").replace("-socks5", "")

    assert hostname == TEST_PROXY_DICT.get(
        "hostname"
    ), f"Hostnames don't match: {hostname =}"

    webdriver.close()


def test_proxy_rotation(rotation_enabled_config):
    """Test that proxy rotation actually rotates between different proxies."""
    # TODO: This is your more complex test to convert
    # Hint: You'll need the rotation_enabled_config fixture
    # and should assert that different hostnames are used
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(
        rotation_enabled_config
    )
    webdriver = MyWebDriver(
        optionsbuilder=chrome_optionbuilder,
        config=rotation_enabled_config,
        proxy_list=TEST_PROXY_LIST,
        session_id="test_proxy",
    )

    # check to see if it sets rotation and proxy correctly
    # first get a set of hostname
    proxy_urls: set = {x.get("proxy_url") for x in TEST_PROXY_LIST if x is not None}
    for x in proxy_urls:
        logger.debug(f"set of proxys: {x}.")
    assert webdriver.set_proxy is not None, "Expecting set_proxy to not be None."
    assert (
        webdriver.set_proxy.get("proxy_url") in proxy_urls
    ), f"Expecting set_proxy to be in test list: {webdriver.set_proxy.get('proxy_url')}"
    assert (
        webdriver.config.proxy.rotation.enabled
    ), f"Expected rotation enabled as true, got {webdriver.config.proxy.rotation.enabled}"
    assert (
        webdriver.rotation_counter is not None
    ), f"Expected an int for rotation_counter, got {webdriver.rotation_counter}."
    assert (
        webdriver.rotation_counter == 3
    ), f"Expected an int 3 for rotation_counter, got {webdriver.rotation_counter}."

    assert (
        webdriver.get_page.__func__ is webdriver.go_get_json_rotation.__func__
    ), f"Expected get_page to be go_get_json, but got {webdriver.get_page.__func__}"

    proxy_host_name = webdriver.set_proxy.get("hostname")
    logger.debug(f"webdriver proxy set to: {proxy_host_name}")

    results = {}
    for i in range(3):
        data = webdriver.get_page(TEST_URL_MULLVAD)
        assert data is not None, "Data context is None, should be something."
        assert isinstance(data, dict), f"Data context is not a dict: {type(data)}"

        hostname = data.get("mullvad_exit_ip_hostname").replace("-socks5", "")
        assert hostname == proxy_host_name, f"Hostnames don't match: {hostname =}"

    webdriver.close()


# Example of parametrized test (advanced)
@pytest.mark.parametrize("proxy_data", TEST_PROXY_LIST[:2])  # Test with first 2 proxies
def test_individual_proxies(proxy_enabled_config, proxy_data):
    """Test each proxy individually."""
    # TODO: You could implement this to test each proxy works
    pass
