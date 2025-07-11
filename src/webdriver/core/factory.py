"""
Factory functions for creating WebDriver instances with Hydra configs.
"""

import logging
import os
from typing import Optional

import pkg_resources
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf

from webdriver.core.options import ChromeOptionsBuilder
from webdriver.utils.validators import is_valid_chrome_webdriver_config

from .mywebdriver import MyWebDriver

logger = logging.getLogger(__name__)


def get_package_config_path():
    """Get path to package's default configs."""
    return pkg_resources.resource_filename("webdriver", "conf")


def create_webdriver_with_hydra(
    config_name: str = "config",
    overrides: Optional[list] = None,
    session_id: Optional[str] = None,
) -> MyWebDriver:
    """
    Create WebDriver using Hydra config composition.

    Args:
        config_name: Name of the config file (without .yaml)
        overrides: List of config overrides (e.g., ["proxy.enabled=true"])
        session_id: Unique session identifier

    Returns:
        MyWebDriver instance with composed configuration
    """
    logger.debug(f"Getting hydra config: {config_name=}.")
    cfg = load_package_config(config_name, overrides)
    logger.debug(f"print cfg:\n{OmegaConf.to_yaml(cfg)}\n.")
    return MyWebDriver(config=cfg, session_id=session_id)


def load_package_config(
    config_name: str = "config", overrides: Optional[list] = None
) -> DictConfig:
    """
    Load and return the composed config without creating WebDriver.
    Useful for testing config composition.
    """
    config_path = get_package_config_path()

    # Clear any existing Hydra instance
    GlobalHydra.instance().clear()

    try:
        # Initialize Hydra with the package config directory
        with initialize_config_dir(config_dir=config_path, version_base=None):
            cfg = compose(config_name=config_name, overrides=overrides or [])
        return cfg
    finally:
        # Clean up
        GlobalHydra.instance().clear()


def get_webdrive_chrome_optionbuilder(config: DictConfig) -> ChromeOptionsBuilder:
    """
    sets up a chromeoptions class with the stated config.
    ? Creates a copy thus it can be changed by the threading process.

    Returns:
        ChromeOptionsBuilder. set up as state in conf/
    """

    if config:
        if is_valid_chrome_webdriver_config(config):
            options_builder: ChromeOptionsBuilder = instantiate(
                config.webdriver.browser.options
            )

            return options_builder
    else:
        logger.error("Error getting the chrome options options_builder.")
        raise ValueError
