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
import random
import re
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pkg_resources
import requests
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf
from tqdm import tqdm  # Import tqdm for progress bars

from webdriver.core.options import ChromeOptionsBuilder
from webdriver.utils import is_valid_chrome_webdriver_config

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

    def __init__(self, max_workers: int = 8) -> None:
        logger.debug("running")
        self.max_workers = max_workers

        self.project_root = Path(__file__).parent.parent.parent.parent
        self.data_dir = self.project_root / "data" / "proxies"

        if not self.check_wg_mullvad_connection():
            logger.warning(
                f"Wireguard not running/ connected to Mullvad. {self.check_wg_mullvad_connection()}."
            )

    def _parse_proxy_line(self, line: str) -> Optional[Tuple[str, str, str, str]]:
        """
        handle the parsing of the proxy lines, mostly to deal with USA states - extra spaces.

        Returns:
            None - If issue parsing the line, else
            country, city, socks5_address, hostnames as str.
        """

        # TODO unicode casting
        # "city": "Malm\u00f6",

        try:
            # split for spaces greater than 2
            parts: list[str] = re.split(r" {2,}", line.strip())
            # remove empty parts
            parts = [part for part in parts if part]
            num_parts: int = len(parts)

            if (num_parts < 20) and (num_parts >= 4):
                flag: str = parts[0]
                country: str = parts[1].replace(" ", "_")
                city: str = parts[2].replace(", ", "_").replace(" ", "_")
                socks5_address: str = parts[3]
                hostname = parts[-1]

                return country, city, socks5_address, hostname
            logger.debug(f"Warning processing\n{line=}.")
            return None

        except Exception as e:
            logger.debug(f"Warning processing: {str(e)}\n{line=}.")
            return None

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
                parse_line_results = self._parse_proxy_line(line)
                # check for good return aka not none.
                if parse_line_results:
                    country, city, socks5_address, hostname = parse_line_results
                    proxy_list.append(
                        {
                            "country": country,
                            "city": city,
                            "socks5": socks5_address,
                            "hostname": hostname,
                            "proxy_url": f"socks5://{socks5_address}:1080",
                        }
                    )
                else:
                    continue

            logger.info(f"Fetched {len(proxy_list)} Mullvad SOCKS5 proxies")
            return proxy_list

        except Exception as e:
            logger.error(f"Error fetching proxy list: {str(e)}")
            return []

    def _socks_override(self, socks5_dict: dict[str, Union[str, bool]]) -> List[str]:
        return [f"+socks5.{key}={value}" for key, value in socks5_dict.items()]

    def _load_mywebdrive_config(
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

    def _get_webdrive_chrome_optionsbuilder(
        self, config: DictConfig
    ) -> ChromeOptionsBuilder:
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
    def check_proxy(
        self, options_builder: ChromeOptionsBuilder, proxy: Dict[str, Union[str, bool]]
    ) -> bool:
        """
        Check if a proxy works with the Sofascore API.

        Tests a single proxy by attempting to access the Sofascore API
        and checking if the response is valid or blocked.

        Args:
            proxy: Dictionary containing proxy information

        Returns:
            Boolean indicating if the proxy works with Sofascore
        """
        logger.debug("-" * 10 + "checking proxy")

        logger.debug(
            f"Checking proxy: country={proxy.get('country')}, hostname={proxy.get('hostname')}."
        )

        try:
            webdriver_options = options_builder.add_proxy_and_build(proxy)

            driver: MyWebDriver = MyWebDriver(options=webdriver_options)

            try:
                test_sofascore_url: str = self.SOFA_EMPTY_TOUR.format(
                    tournamentID=random.choice(self.VALID_TOURNAMENT_IDS)
                )
                logger.debug(f"Checking via {test_sofascore_url =}.")

                page_data = driver.go_get_json(test_sofascore_url)

                logger.debug("-" * 25 + f"\n{page_data = }\n" + "-" * 25)

                driver.close()

                proxy["checked_at"] = datetime.datetime.now().isoformat()

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
                logger.warning(f"Navigation error with proxy {proxy.get('hostname')}.")
                logger.debug(
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
        options_builder: ChromeOptionsBuilder = (
            self._get_webdrive_chrome_optionsbuilder(
                config=self._load_mywebdrive_config()
            )
        )

        with ThreadPoolExecutor(max_workers=max_workers) as excutor:

            futures_to_proxy: dict[Future, dict] = {
                excutor.submit(self.check_proxy, options_builder, proxy): proxy
                for proxy in proxy_list
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

    def save_proxy_list(
        self,
        proxy_list: list[dict],
        unfiltered: bool = False,
        custom_dir: Optional[str] = None,
    ) -> None:
        """
        Save a proxy list to disk as JSON.
        Args:
            proxy_list: List of proxy dictionaries to save
            custom_dir: Optional custom directory (if None, uses default data/proxies)
        Returns:
            None
        """
        # Use custom dir if provided, otherwise use default
        if custom_dir:
            save_dir = Path(custom_dir)

        else:
            if unfiltered:
                save_dir = self.data_dir / "raw"
            else:
                save_dir = self.data_dir

        timestamp: str = datetime.datetime.now().strftime("%Y_%m_%d")
        file_path: Path = save_dir / f"{timestamp}.json"

        try:
            with open(file_path, "w") as f:
                json.dump(proxy_list, f, indent=2)
                logger.info(
                    f"File saved: {file_path} - number of proxies: {len(proxy_list)}"
                )
        except Exception as e:
            logger.error(f"Error saving proxy list to {file_path}: {str(e)}")

    def load_latest_proxy_list(self) -> list[dict]:
        """Load the most recent proxy list"""
        try:
            json_files = list(self.data_dir.glob("*.json"))
            if not json_files:
                logger.warning("No proxy files found")
                return []

            # Get the most recent file
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)

            with open(latest_file, "r") as f:
                proxy_list = json.load(f)
                logger.info(f"Loaded {len(proxy_list)} proxies from {latest_file}")
                return proxy_list

        except Exception as e:
            logger.error(f"Error loading proxy list: {str(e)}")
            return []

    def _get_latest_proxy_file(self) -> Optional[Path]:
        """
        Internal method to get the latest proxy file.
        Returns:
            Path to the latest file or None if no files exist
        """
        try:
            json_files = list(self.data_dir.glob("*.json"))
            if not json_files:
                logger.debug("No proxy files found in data directory")
                return None

            # Get the most recent file by modification time
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            return latest_file

        except Exception as e:
            logger.error(f"Error finding latest proxy file: {str(e)}")
            return None

    def _get_file_age_hours(self, file_path: Path) -> float:
        """
        Internal method to get file age in hours.
        Args:
            file_path: Path to the file
        Returns:
            Age of file in hours
        """
        try:
            file_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            current_time = datetime.datetime.now()
            time_diff = current_time - file_time
            return time_diff.total_seconds() / 3600  # Convert to hours
        except Exception as e:
            logger.error(f"Error calculating file age: {str(e)}")
            return float("inf")  # Return very large number if error

    def is_cache_fresh(
        self, max_age_hours: float = 24.0
    ) -> Tuple[bool, Optional[Path]]:
        """
        Check if cached proxy list is still fresh.
        Args:
            max_age_hours: Maximum age in hours before cache is considered stale
        Returns:
            (is_fresh: bool, file_path: Optional[Path])
        """
        latest_file = self._get_latest_proxy_file()

        if not latest_file:
            logger.info("No cached proxy file found")
            return False, None

        age_hours = self._get_file_age_hours(latest_file)
        is_fresh = age_hours <= max_age_hours

        logger.info(
            f"Cache file: {latest_file.name}, Age: {age_hours:.1f}h, Fresh: {is_fresh}"
        )
        return is_fresh, latest_file

    def load_proxy_list_from_file(self, file_path: Path) -> List[Dict]:
        """Load proxy list from specific file"""
        try:
            with open(file_path, "r") as f:
                proxy_list = json.load(f)
                logger.info(f"Loaded {len(proxy_list)} proxies from {file_path.name}")
                return proxy_list
        except Exception as e:
            logger.error(f"Error loading proxy list from {file_path}: {str(e)}")
            return []

    def fetch_and_process_proxies(self, skip_testing: bool = False) -> List[Dict]:
        """
        Fetch proxy list from URL and process/check them for Sofascore compatibility.
        This is the "heavy lifting" method that actually fetches and tests.

        Args:
            skip_testing: If True, just fetch proxies without testing them

        Returns:
            List of proxy dictionaries (with 'valid' field if tested)
        """

        # Step 1: Fetch new proxy list from URL
        logger.info("Fetching new proxy list from API")
        proxy_list = self.fetch_proxy_list()

        if not proxy_list:
            logger.warning("No proxies found from API")
            return []

        logger.info(f"Fetched {len(proxy_list)} proxies")

        # Step 2: Test proxies (unless skipped)
        if not skip_testing:
            logger.info("Testing proxies for Sofascore compatibility...")
            self.check_all_proxies_threaded(
                proxy_list=proxy_list, max_workers=self.max_workers
            )

            # Count valid proxies
            valid_proxies = [p for p in proxy_list if p.get("valid", False)]
            logger.info(
                f"Found {len(valid_proxies)} valid proxies out of {len(proxy_list)}"
            )

        # Step 3: Save the processed proxy list
        try:
            self.save_proxy_list(valid_proxies)
            self.save_proxy_list(proxy_list, unfiltered=True)  # saved for debugging
            logger.info("Saved processed proxy list to cache")
        except Exception as e:
            logger.error(f"Failed to save proxy list: {str(e)}")

        return valid_proxies

    def get_proxy_list(
        self, force_refresh: bool = False, max_cache_age_hours: float = 24.0
    ) -> List[Dict]:
        """
        Get proxy list - either from cache (if fresh) or fetch and process new data.
        This is the main entry point for getting proxies.

        Args:
            force_refresh: If True, always fetch new data
            max_cache_age_hours: Maximum age for cache validity
        Returns:
            List of proxy dictionaries
        """

        # Step 1: Check cache first (unless force refresh)
        if not force_refresh:
            is_fresh, cache_file = self.is_cache_fresh(max_cache_age_hours)

            if is_fresh and cache_file:
                logger.info("Using fresh cached proxy list")
                return self.load_proxy_list_from_file(cache_file)

        # Step 2: Cache is stale or force refresh - fetch and process new data
        logger.info("Cache stale or force refresh - fetching new proxy data")
        return self.fetch_and_process_proxies()  # This does the heavy lifting

    ### TODO

    # save proxy list
    # load proxy list
