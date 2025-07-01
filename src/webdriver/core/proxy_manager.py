"""
Will be using wire guard + mullvad vpn (sock5), in order to do ip rotation.

1. Get the up socks5 details.
    - There is a list that gets updated here:
        https://raw.githubusercontent.com/maximko/mullvad-socks-list/refs/heads/list/mullvad-socks-list.txt
    - head looks like:
    Date: 2025-04-04 06-51-44 UTC
        Total active proxies: 479
         flag  country         city                socks5        ipv4             ipv6                                  speed  multihop  owned  provider       stboot  hostname
         🇦🇱    Albania         Tirana              10.124.0.155  31.171.153.66    2a04:27c0:0:3::f001                   10     3155      ❌     iRegister      ✔️      al-tia-wg-001
         🇦🇱    Albania         Tirana              10.124.0.212  31.171.154.50    2a04:27c0:0:4::f001                   10     3212      ❌     iRegister      ✔️      al-tia-wg-002
         🇦🇹    Austria         Vienna              10.124.2.35   146.70.116.98    2001:ac8:29:84::a01f                  10     3543      ❌     M247           ✔️      at-vie-wg-001
         🇦🇹    Austria         Vienna              10.124.2.36   146.70.116.130   2001:ac8:29:85::a02f                  10     3544      ❌     M247           ✔️      at-vie-wg-002
         🇦🇹    Austria         Vienna              10.124.2.37   146.70.116.162   2001:ac8:29:86::a03f                  10     3545      ❌     M247           ✔️      at-vie-wg-003
    - Need to process this to get the details
    - store this socks5 information to be used.

2. Set up socks5
    - method to add the a sock5 to be used by the driver.
    - a choice to randoism it.
    - then check curl
        curl https://am.i.mullvad.net
        has change the ip, so before then after to ensure we have rotated the ip.

3. set up a counter as an attribute of MyWebDriver class,
    - every navigate adds/ reduces to the counter, once a randoism limit is reached we rotate the sock5, ( using set up socks5 so we test it changes it)


"""

import datetime
import json
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import pkg_resources
import requests
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf
from tqdm import tqdm  # Import tqdm for progress bars

from .mywebdriver import MyWebDriver

logger = logging.getLogger(__name__)


class MullvadProxyManager:
    """
    Manages Mullvad SOCKS5 proxy connections for IP rotation.

    This class handles:
    1. Fetching available Mullvad SOCKS5 proxies
    2. Testing proxies against the Sofascore API
    3. Managing proxy selection for WebDriver
    4. Verifying IP changes
    5. Saving and loading proxy lists
    """

    PROXY_LIST_URL: str = (
        "https://raw.githubusercontent.com/maximko/mullvad-socks-list/refs/heads/list/mullvad-socks-list.txt"
    )

    def __init__(self) -> None:
        logger.debug("running")

    def fetch_proxy_list(self) -> List[Dict]:
        """
        Fetch and parse the list of available Mullvad SOCKS5 proxies.

        Returns:
            List of proxy dictionaries with relevant information
        """
        try:
            response = requests.get(self.PROXY_LIST_URL)
            response.raise_for_status()

            proxy_list = []
            lines = response.text.split("\n")

            # Skip header lines
            data_lines = [
                line
                for line in lines
                if line.strip()
                and not line.startswith("Date:")
                and not line.startswith("Total")
                and not line.startswith(" flag")
            ]

            for line in data_lines:
                # Parse each line
                parts = line.split()
                if len(parts) >= 6:
                    # Extract the relevant fields
                    try:
                        country = parts[1]
                        city = parts[2]
                        socks5_address = parts[3]  # This is the Mullvad SOCKS5 address
                        hostname = parts[-1]

                        proxy_list.append(
                            {
                                "country": country,
                                "city": city,
                                "socks5": socks5_address,
                                "hostname": hostname,
                                "proxy_url": f"socks5://{socks5_address}:1080",
                            }
                        )
                    except IndexError:
                        continue

            logger.info(f"Fetched {len(proxy_list)} Mullvad SOCKS5 proxies")
            return proxy_list

        except Exception as e:
            logger.error(f"Error fetching proxy list: {str(e)}")
            return []

    def socks_override(self, socks5_dict: dict[str, str]) -> List[str]:
        return [f"+socks5.{key}={value}" for key, value in socks5_dict.items()]

    def _load_package_config(
        self, config_name: str = "config", overrides: Optional[list] = None
    ) -> DictConfig:
        """
        Load and return the composed config without creating WebDriver.
        Useful for testing config composition.
        """
        config_path = pkg_resources.resource_filename("webdriver", "conf")

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
