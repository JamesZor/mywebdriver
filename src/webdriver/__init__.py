# src.webdriver.__init__.py

"""
WebDriver Proxy Package

Provides WebDriver instances with proxy rotation and configuration management.
"""

from .core.factory import create_webdriver_with_hydra, load_package_config
from .core.manager_webdriver import ManagerWebdriver
from .core.mywebdriver import MyWebDriver
from .core.proxy_manager import MullvadProxyManager

__version__ = "0.1.0"
__all__ = [
    "MyWebDriver",
    "create_webdriver_with_hydra",
    "load_package_config",
    "MullvadProxyManager",
    "ManagerWebdriver",
]
