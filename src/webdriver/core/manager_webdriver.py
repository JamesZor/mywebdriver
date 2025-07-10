import logging
from typing import Dict, List, Optional

from omegaconf import DictConfig

import webdriver.core.factory as factory
from webdriver.core.mywebdriver import MyWebDriver
from webdriver.core.options import ChromeOptionsBuilder
from webdriver.core.proxy_manager import MullvadProxyManager

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class ManagerWebdriver:
    """
    Handles the proxy and mywebdrivers
    """

    def __init__(
        self,
        proxy_max_workers: int = 10,
        proxy_force_refresh: bool = False,
        proxy_max_cache_age: float = 24.0,
        config_name: Optional[str] = "default",
    ) -> None:
        """
        setup and run the proxy manager.
        """
        self.proxy_manager: MullvadProxyManager = MullvadProxyManager(
            max_workers=proxy_max_workers
        )

        if not self.proxy_manager.check_wg_mullvad_connection():
            logger.error("Need to be connected to wire guard.")
            raise ConnectionError("Need to be connected to wire guard.")

        valid_proxy_list: List[dict] = self.proxy_manager.get_proxy_list(
            force_refresh=proxy_force_refresh, max_cache_age_hours=proxy_max_cache_age
        )

        if (valid_proxy_list is None) or (len(valid_proxy_list) < 1):
            logger.error("Issue with valid proxy list, check get_proxy_list")
            raise ValueError("No suitable proxy list fetched.")
        self.proxy_list = valid_proxy_list

        cfg: DictConfig = factory.load_package_config(config_name=config_name)
        if cfg is None:
            logger.error("Can not get the yaml config")
            raise ValueError("No config file given.")
        self.cfg = cfg

        optionsbuilder: ChromeOptionsBuilder = (
            factory.get_webdrive_chrome_optionbuilder(cfg)
        )

        if optionsbuilder is None:
            logger.error("Can not get the optionbuilder")
            raise ValueError("No optionbuidler.")
        self.optionsbuilder = optionsbuilder

        self.webdrive_list: list[MyWebDriver] = []

    def spawn_webdriver(self) -> MyWebDriver:
        """create a webdriver on the config in __init__"""
        driver: MyWebDriver = MyWebDriver(
            optionsbuilder=self.optionsbuilder,
            config=self.cfg,
            proxy_list=self.proxy_list,
        )
        return driver
