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
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

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
    MULLVAD_CHECK_CURL: str = "https://am.i.mullvad.net/json"
    SOFA_EMPTY_TOUR: str = "https://api.sofascore.com/api/v1/tournament/{tournamentID}"
    VALID_TOURNAMENT_IDS: List[int] = [
        1,
        2,
        3,
        16,
        17,
        72,
        84,
        4,
        19,
        77,
        5,
        6,
        65,
        78,
        12,
        13,
        15,
        18,
        23,
        24,
        27,
        28,
        29,
        30,
        69,
        31,
        33,
        34,
        35,
        87,
        88,
        89,
        90,
        91,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
        43,
        44,
        45,
        48,
        49,
        50,
        51,
        52,
        53,
        54,
        55,
        56,
        57,
        73,
        58,
        62,
        63,
        64,
        66,
        86,
        68,
        71,
        79,
        82,
        83,
        92,
        94,
        98,
    ]

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

    def _socks_override(self, socks5_dict: dict[str, str]) -> List[str]:
        return [f"+socks5.{key}={value}" for key, value in socks5_dict.items()]

    def _load_package_config(
        self, config_name: str = "proxy_init_run", overrides: Optional[list] = None
    ) -> DictConfig:
        """
        Load and return the composed config without creating WebDriver.
        Useful for testing config composition.
        """
        config_path: str = pkg_resources.resource_filename("webdriver", "conf")
        # Clear any existing Hydra instance
        GlobalHydra.instance().clear()

        try:
            # Initialize Hydra with the package config directory
            with initialize_config_dir(config_dir=config_path, version_base=None):
                cfg: DictConfig = compose(
                    config_name=config_name, overrides=overrides or []
                )
            return cfg
        finally:
            # Clean up
            GlobalHydra.instance().clear()

    def _get_webdrive(self) -> MyWebDriver:
        """
        Load up a webdriver using the proxy configs.
        returns:
            MyWebDriver
        """

    def check_wg_mullvad_connection(self) -> bool:
        """
        method to check computer is connected via wireguard and to mullvad vpn service.
        """
        try:
            mullvad_response: requests.Response = requests.get(
                self.MULLVAD_CHECK_CURL, timeout=10
            )
            mullvad_response.raise_for_status()
            data: dict[str, Any] = mullvad_response.json()

            return data.get("mullvad_exit_ip", False)

        except Exception as e:
            logger.error(f"Error curling mullvard: {str(e)}.")
            return False

    # Check proxy
    def check_proxy(self, proxy: Dict[str, Union[str, bool]]) -> bool:
        """
        Check if a proxy works with the Sofascore API.

        Tests a single proxy by attempting to access the Sofascore API
        and checking if the response is valid or blocked.

        Args:
            proxy: Dictionary containing proxy information

        Returns:
            Boolean indicating if the proxy works with Sofascore
        """
        logger.debug(
            f"Checking proxy: country={proxy.get('country')}, hostname={proxy.get('hostname')}."
        )

        try:
            driver: MyWebDriver = MyWebDriver(
                config=self._load_package_config(overrides=self._socks_override(proxy))
            )

            try:
                test_sofascore_url: str = self.SOFA_EMPTY_TOUR.format(
                    tournamentID=random.choice(self.VALID_TOURNAMENT_IDS)
                )
                logger.debug(f"Checking via {test_sofascore_url =}.")

                page_data = driver.go_get_json(test_sofascore_url)

                logger.debug("-" * 25 + f"\n{page_data = }\n" + "-" * 25)

                driver.close()

                proxy["checked_at"] = datetime.datetime.utcnow().isoformat()

                if page_data and isinstance(page_data, dict):
                    # Success case:
                    if page_data.get("tournament"):
                        logger.debug(f"Proxy valid: {proxy.get('hostname')}.")
                        proxy["valid"] = True
                        return True
                    # fail case:
                    elif page_data.get("error"):
                        error_code = page_data.get("error", {}).get("code")
                        error_reason = page_data.get("error", {}).get("reason")
                        logger.debug(
                            f"Proxy blocked: {proxy.get('hostname')} - Error: {error_code} ({error_reason})"
                        )
                        proxy["error_code"] = error_code
                        proxy["error_reason"] = error_reason

                return False

            # driver nav error
            except Exception as nav_error:
                logger.warning(
                    f"Navigation error with proxy {proxy.get('hostname')}: {str(nav_error)}"
                )
                proxy["valid"] = False
                proxy["error"] = str(nav_error)
                driver.close()
                return False

        # driver
        except Exception as e:
            logger.error(f"Error testing proxy {proxy.get('hostname')}: {str(e)}")
            proxy["valid"] = False
            proxy["error"] = str(e)
            return False

    def check_all_proxies_threaded(
        self, proxy_list: List[dict], max_workers: int = 5
    ) -> None:
        """
        Check multiple proxies against the Sofascore API.

        Tests a list of proxies, optionally using multiple threads for efficiency.

        Args:
            proxy_list: List of proxy dictionaries to check
            max_workers: Int

        Returns:
            None: references  change / in place.
        """
        num_proxies = len(proxy_list)
        num_good_proxies: int = 0
        logger.info(f"Checking {num_proxies} proxies for Sofascore compatibility.")

        with ThreadPoolExecutor(max_workers=max_workers) as excutor:

            futures_to_proxy: dict[Future, dict] = {
                excutor.submit(self.check_proxy, proxy): proxy for proxy in proxy_list
            }

            with tqdm(total=num_proxies, desc="Testing proxies", unit="proxy") as pbar:
                for future in as_completed(futures_to_proxy):
                    proxy = futures_to_proxy[future]
                    try:
                        num_good_proxies += future.result()
                    except Exception as exc:
                        logger.debug(
                            f"Error: failed for {proxy.get('hostname')} : {str(exc)}."
                        )
                        proxy["valid"] = False
                        proxy["error"] = str(exc)
                    finally:
                        pbar.update(1)
        logger.info(
            f"Found {num_good_proxies} working sock5 proxies, out of {num_proxies}."
        )

    ### TODO

    # process the proxy list
