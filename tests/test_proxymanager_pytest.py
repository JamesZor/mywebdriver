import logging
from pathlib import Path

import pytest
from omegaconf import OmegaConf

import webdriver.core.factory as factory
from webdriver import MullvadProxyManager, MyWebDriver

# logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


@pytest.fixture
def basic_proxy_fetch():
    """Fixture to have the raw proxy list"""
    pm: MullvadProxyManager = MullvadProxyManager()
    proxy_list: list[dict] = pm.fetch_proxy_list()
    return pm, proxy_list


@pytest.fixture
def basic_webdriver_setup():
    """Fixture to get basic cfg adn optionsbuilder"""
    cfg = factory.load_package_config(config_name="test_config")
    optionsbuilder = factory.get_webdrive_chrome_optionbuilder(config=cfg)
    return cfg, optionsbuilder


def test_basic_mullvard():
    pm: MullvadProxyManager = MullvadProxyManager()

    assert pm.max_workers == 8, "Expected workers set to 8."

    assert pm.project_root == Path(
        "/home/james/bet_project/webdriver"
    ), "Incorrect home path"

    assert pm.data_dir == Path(
        "/home/james/bet_project/webdriver/data/proxies/"
    ), "Incorrect data path"

    assert pm.check_wg_mullvad_connection(), "Not connect to wg / mullvard"


def test_proxy_fetch():

    pm: MullvadProxyManager = MullvadProxyManager()

    proxy_list = pm.fetch_proxy_list()

    assert isinstance(proxy_list, list), "Expecting a list of dicts."
    assert len(proxy_list) > 0, "Expecting a none empty list."

    p1 = proxy_list[0]
    required_keys = ["proxy_url", "city", "country", "hostname"]
    for key in required_keys:
        assert key in p1, f"proxy list elements require {key}."


def test_check_proxy(basic_proxy_fetch, basic_webdriver_setup):
    # Unpack the fixture return values
    pm, proxy_list = basic_proxy_fetch
    cfg, optionsbuilder = basic_webdriver_setup
    idx: int = 20
    p: dict = proxy_list[idx]
    logger.debug(OmegaConf.to_yaml(cfg))
    proxy_results = pm.check_proxy(optionsbuilder=optionsbuilder, config=cfg, proxy=p)
    logger.debug(f"{proxy_results = }")


def test_check_proxy_list(basic_proxy_fetch, basic_webdriver_setup): 
