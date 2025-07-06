# test_basic.py
import json
import logging

from omegaconf import DictConfig, OmegaConf

import webdriver.core.factory as factory
from webdriver import MullvadProxyManager, MyWebDriver

# Configure logging
# logging.basicConfig(level=logging.DEBUG)

logging.basicConfig(level=logging.DEBUG)

ht: str = "+" * 8

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


def test_basic_webdriver():
    """Test basic WebDriver functionality."""
    print("=" * 15 + " Running Simple webdriver setup" + "=" * 15)

    # here we load the config
    cfg: DictConfig = factory.load_package_config(config_name="test_config")
    print(ht + f"print cfg:\n{OmegaConf.to_yaml(cfg)}\n.")
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(cfg)

    print(ht + f"chrome options: {chrome_optionbuilder}.")
    webdriver = MyWebDriver(
        config=cfg, optionsbulder=chrome_optionbuilder, session_id="test1"
    )
    webdriver.close()
    print("-" * 15 + " Basic tests passed! " + "-" * 15)


def test_basic_webdriver_get_data():
    """Test basic WebDriver functionality."""
    print("=" * 15 + " Running Simple webdriver setup" + "=" * 15)
    # here we load the config
    cfg: DictConfig = factory.load_package_config(config_name="test_config")
    print(ht + f"print cfg:\n{OmegaConf.to_yaml(cfg)}\n.")
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(cfg)

    print(ht + f"chrome options: {chrome_optionbuilder}.")
    webdriver = MyWebDriver(
        config=cfg, optionsbulder=chrome_optionbuilder, session_id="test1"
    )

    test_url: str = "https://am.i.mullvad.net/json"

    print(ht + f"Getting data from: {test_url =}.")

    data = webdriver.get_page(test_url)

    print(ht + f"Got data:\n{data}.")
    webdriver.close()
    print("-" * 15 + " Basic tests passed! " + "-" * 15)


def test_basic_webdriver_setup_prox():
    """Test basic WebDriver functionality."""
    print("=" * 15 + " Running Simple webdriver setup" + "=" * 15)
    # here we load the config
    # set an hydra override to enable proxy
    override = ["proxy.enabled=true"]

    cfg: DictConfig = factory.load_package_config(
        config_name="test_config", overrides=override
    )
    print(ht + f"print cfg:\n{OmegaConf.to_yaml(cfg)}\n.")
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(cfg)

    print(ht + f"chrome options: {chrome_optionbuilder}.")

    test_proxy = TEST_PROXY_DICT
    print(ht + f"Using the proxy: {test_proxy =}.")

    webdriver = MyWebDriver(
        config=cfg,
        optionsbulder=chrome_optionbuilder,
        proxy=test_proxy,
        session_id="test1",
    )

    webdriver.close()
    print("-" * 15 + " Basic tests passed! " + "-" * 15)


def test_webdriver_setup_prox_and_get():
    """Test basic WebDriver functionality."""
    print("=" * 15 + " Running Simple webdriver setup" + "=" * 15)
    # here we load the config
    # set an hydra override to enable proxy
    override = ["proxy.enabled=true"]

    cfg: DictConfig = factory.load_package_config(
        config_name="test_config", overrides=override
    )
    print(ht + f"print cfg:\n{OmegaConf.to_yaml(cfg)}\n.")
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(cfg)

    print(ht + f"chrome options: {chrome_optionbuilder}.")

    test_proxy = TEST_PROXY_DICT
    print(ht + f"Using the proxy: {test_proxy =}.")

    webdriver = MyWebDriver(
        config=cfg,
        optionsbulder=chrome_optionbuilder,
        proxy=test_proxy,
        session_id="test1",
    )
    test_url: str = "https://am.i.mullvad.net/json"
    print(ht + f"Getting data from: {test_url =}.")
    data = webdriver.get_page(test_url)
    print(ht + f"Got data:\n{data}.")
    webdriver.close()
    print("-" * 15 + " Basic tests passed! " + "-" * 15)


def test_webdriver_setup_proxy_list():
    """Test basic WebDriver functionality."""
    print("=" * 15 + " Running Simple webdriver setup" + "=" * 15)
    # here we load the config
    # set an hydra override to enable proxy
    #    override = ["proxy.enabled=true", "proxy.rotation.enabled=true"]
    override = ["proxy.enabled=true"]

    cfg: DictConfig = factory.load_package_config(
        config_name="test_config", overrides=override
    )
    print(ht + f"print cfg:\n{OmegaConf.to_yaml(cfg)}\n.")
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(cfg)

    print(ht + f"chrome options: {chrome_optionbuilder}.")

    test_proxy_list = TEST_PROXY_LIST

    print(ht + f"Using the proxy:")
    for p in test_proxy_list:
        print(p.get("hostname"))

    webdriver = MyWebDriver(
        config=cfg,
        optionsbulder=chrome_optionbuilder,
        proxy_list=test_proxy_list,
        session_id="test1",
    )
    test_url: str = "https://am.i.mullvad.net/json"
    print(ht + f"Getting data from: {test_url =}.")
    data = webdriver.get_page(test_url)
    print(ht + f"Got data:\n{data}.")
    webdriver.close()
    print("-" * 15 + " Basic tests passed! " + "-" * 15)


def test_webdriver_rotation_fixed():
    """Test basic WebDriver functionality."""
    print("=" * 15 + " Running Simple webdriver setup" + "=" * 15)
    # here we load the config
    # set an hydra override to enable proxy
    override = ["proxy.enabled=true", "proxy.rotation.enabled=true"]

    cfg: DictConfig = factory.load_package_config(
        config_name="test_config", overrides=override
    )
    print(ht + f"print cfg:\n{OmegaConf.to_yaml(cfg)}\n.")
    chrome_optionbuilder = factory.get_webdrive_chrome_optionbuilder(cfg)

    print(ht + f"chrome options: {chrome_optionbuilder}.")

    test_proxy_list = TEST_PROXY_LIST

    print(ht + f"Using the proxy:")
    for p in test_proxy_list:
        print(p.get("hostname"))

    webdriver = MyWebDriver(
        config=cfg,
        optionsbulder=chrome_optionbuilder,
        proxy_list=test_proxy_list,
        session_id="test1",
    )
    test_url: str = "https://am.i.mullvad.net/json"
    print(ht + f"Getting data from: {test_url =}.")

    results = {}

    for i in range(3):
        data = webdriver.get_page(test_url)
        name = data.get("mullvad_exit_ip_hostname")
        if name in results:
            results[name] += 1
        else:
            results[name] = 1

    print(ht + f"Got data:\n{results}.")
    webdriver.close()
    print("-" * 15 + " Basic tests passed! " + "-" * 15)


if __name__ == "__main__":
    # test_basic_webdriver()
    #   test_basic_webdriver_get_data()
    #    test_basic_webdriver_setup_prox()
    #    test_webdriver_setup_prox_and_get()
    #    test_webdriver_setup_proxy_list()
    test_webdriver_rotation_fixed()

# test_basic_webdriver_with_head()
#    test_getting_json_content()
