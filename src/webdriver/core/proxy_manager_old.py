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

import requests
from tqdm import tqdm  # Import tqdm for progress bars

# Notice: We removed the circular import from webdriver

##############################
###  Proxy / IP rotation.
##############################


class OldMullvadProxyManager:
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

    DATA_RAW_DIR = Path("./data/proxy/raw")
    DATA_CLEAN_DIR = Path("./data/proxy/clean")
    TEST_URL = "https://api.sofascore.com/api/v1/tournament/1"
    TEST_EMPTY_URL = "https://api.sofascore.com/api/v1/tournament/{tournamentID}"
    VALID_TOURNAMENT_IDS = [
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

    def __init__(
        self,
        proxy_list_url: str = PROXY_LIST_URL,
        max_proxies: int = 500,
        countries: Optional[List[str]] = None,
        max_threads: int = 4,
    ):
        """
        Initialize the Mullvad proxy manager.

        Args:
            proxy_list_url: URL to fetch the list of Mullvad SOCKS5 proxies
            max_proxies: Maximum number of proxies to keep in the list
            countries: Optional list of country codes to filter proxies by
            max_threads: Maximum number of threads to use for proxy checking
        """
        self.proxy_list_url = proxy_list_url
        self.max_proxies = max_proxies
        self.countries = countries
        self.max_threads = max_threads
        self.proxies = []
        self.current_proxy = None
        self.current_ip = None
        self.logger = logging.getLogger(__name__)

        # Ensure data directories exist
        self.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_proxy_list(self) -> List[Dict]:
        """
        Fetch and parse the list of available Mullvad SOCKS5 proxies.

        Returns:
            List of proxy dictionaries with relevant information
        """
        try:
            response = requests.get(self.proxy_list_url)
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

                        # Filter by countries if specified
                        if self.countries and country.lower() not in [
                            c.lower() for c in self.countries
                        ]:
                            continue

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

                    if len(proxy_list) >= self.max_proxies:
                        break

            self.logger.info(f"Fetched {len(proxy_list)} Mullvad SOCKS5 proxies")
            return proxy_list

        except Exception as e:
            self.logger.error(f"Error fetching proxy list: {str(e)}")
            return []

    def update_proxy_list(self) -> None:
        """Update the internal list of available proxies."""
        self.proxies = self.fetch_proxy_list()

    ##############################
    ###  check proxies
    ##############################

    def check_proxy(self, proxy: Dict) -> Tuple[bool, Dict]:
        """
        Check if a proxy works with the Sofascore API.

        Tests a single proxy by attempting to access the Sofascore API
        and checking if the response is valid or blocked.

        Args:
            proxy: Dictionary containing proxy information

        Returns:
            Tuple of (is_valid, proxy_info)
            - is_valid: Boolean indicating if the proxy works with Sofascore
            - proxy_info: The original proxy dict, potentially with additional info
        """
        self.logger.info(
            f"Testing proxy: {proxy.get('country')} - {proxy.get('hostname')}"
        )

        try:
            # Lazy import to avoid circular dependencies
            from src.sofascore.infrastructure.webdriver import MyWebDriver

            # Initialize a WebDriver with the specific proxy directly
            proxy_url = proxy.get("proxy_url")
            if not proxy_url:
                self.logger.warning(f"No proxy URL found for {proxy.get('hostname')}")
                proxy["valid"] = False
                proxy["checked_at"] = datetime.datetime.utcnow().isoformat()
                proxy["error"] = "Missing proxy URL"
                return False, proxy

            # Create a driver with the specific proxy
            driver = MyWebDriver(
                headless=True,
                proxy=proxy_url,  # Direct proxy configuration
                enable_rotation=False,  # Disable rotation since we're testing one proxy
            )

            # Navigate to the test URL
            try:
                random_tournament_id = random.choice(self.VALID_TOURNAMENT_IDS)
                test_url = self.TEST_EMPTY_URL.format(tournamentID=random_tournament_id)
                driver.navigate(test_url)
                page_data = driver.get_json_content()

                # Check if we got valid data
                if page_data:
                    # Success case: We got tournament data
                    if page_data.get("tournament"):
                        self.logger.info(f"Proxy valid: {proxy.get('hostname')}")
                        # Add validation status to proxy info
                        proxy["valid"] = True
                        proxy["checked_at"] = datetime.datetime.utcnow().isoformat()
                        driver.close()
                        return True, proxy
                    # Error case: We got an error response
                    elif page_data.get("error"):
                        error_code = page_data.get("error", {}).get("code")
                        error_reason = page_data.get("error", {}).get("reason")
                        self.logger.warning(
                            f"Proxy blocked: {proxy.get('hostname')} - Error: {error_code} ({error_reason})"
                        )
                        proxy["error_code"] = error_code
                        proxy["error_reason"] = error_reason
            except Exception as nav_error:
                self.logger.warning(
                    f"Navigation error with proxy {proxy.get('hostname')}: {str(nav_error)}"
                )
                proxy["error"] = f"Navigation error: {str(nav_error)}"

            # Clean up driver resources
            driver.close()

            # If we reach here, the proxy didn't work
            proxy["valid"] = False
            proxy["checked_at"] = datetime.datetime.utcnow().isoformat()
            return False, proxy

        except Exception as e:
            self.logger.error(f"Error testing proxy {proxy.get('hostname')}: {str(e)}")
            proxy["valid"] = False
            proxy["checked_at"] = datetime.datetime.utcnow().isoformat()
            proxy["error"] = str(e)
            return False, proxy

    def check_proxy_list(
        self, proxy_list: List[Dict], use_threading: bool = True
    ) -> List[Dict]:
        """
        Check multiple proxies against the Sofascore API.

        Tests a list of proxies, optionally using multiple threads for efficiency.

        Args:
            proxy_list: List of proxy dictionaries to check
            use_threading: Whether to use threading to speed up the process

        Returns:
            List of valid proxy dictionaries that work with Sofascore
        """
        if not proxy_list:
            self.logger.warning("Empty proxy list provided for checking")
            return []

        self.logger.info(
            f"Checking {len(proxy_list)} proxies for Sofascore compatibility"
        )

        valid_proxies = []
        checked_proxies = []

        if use_threading and self.max_threads > 1:
            # Use ThreadPoolExecutor for parallel checking
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                # Submit all proxy checks to the executor
                future_to_proxy = {
                    executor.submit(self.check_proxy, proxy): proxy
                    for proxy in proxy_list
                }

                # Process results as they complete with a progress bar
                with tqdm(
                    total=len(proxy_list), desc="Testing proxies", unit="proxy"
                ) as pbar:
                    for future in as_completed(future_to_proxy):
                        proxy = future_to_proxy[future]
                        try:
                            is_valid, checked_proxy = future.result()
                            checked_proxies.append(checked_proxy)
                            if is_valid:
                                valid_proxies.append(checked_proxy)
                        except Exception as exc:
                            self.logger.error(
                                f"Proxy check failed for {proxy.get('hostname')}: {exc}"
                            )
                        finally:
                            pbar.update(1)
        else:
            # Sequential checking (no threading) with progress bar
            with tqdm(
                total=len(proxy_list), desc="Testing proxies", unit="proxy"
            ) as pbar:
                for proxy in proxy_list:
                    try:
                        is_valid, checked_proxy = self.check_proxy(proxy)
                        checked_proxies.append(checked_proxy)
                        if is_valid:
                            valid_proxies.append(checked_proxy)
                    except Exception as exc:
                        self.logger.error(
                            f"Proxy check failed for {proxy.get('hostname')}: {exc}"
                        )
                    finally:
                        pbar.update(1)

        # Save all checked proxies for reference
        self.save_proxy_list(checked_proxies, self.DATA_RAW_DIR, "checked_proxies")

        self.logger.info(
            f"Found {len(valid_proxies)} valid proxies out of {len(proxy_list)} checked"
        )
        return valid_proxies

    def save_proxy_list(
        self, proxy_list: List[Dict], directory: Path, prefix: str = ""
    ) -> str:
        """
        Save a proxy list to disk as JSON.

        Args:
            proxy_list: List of proxy dictionaries to save
            directory: Directory to save the file in
            prefix: Optional prefix for the filename

        Returns:
            Path to the saved file
        """
        if not proxy_list:
            self.logger.warning(f"Empty proxy list, not saving to {directory}")
            return ""

        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if prefix:
            filename = f"{prefix}_{timestamp}.json"
        else:
            filename = f"proxies_{timestamp}.json"

        filepath = directory / filename

        # Save proxies as JSON
        try:
            with open(filepath, "w") as f:
                json.dump(proxy_list, f, indent=2)

            self.logger.info(f"Saved {len(proxy_list)} proxies to {filepath}")
            return str(filepath)
        except Exception as e:
            self.logger.error(f"Error saving proxy list to {filepath}: {str(e)}")
            return ""

    def load_proxy_list(self, filepath: Union[str, Path]) -> List[Dict]:
        """
        Load a proxy list from a JSON file.

        Args:
            filepath: Path to the JSON file containing proxies

        Returns:
            List of proxy dictionaries
        """
        filepath = Path(filepath)

        if not filepath.exists():
            self.logger.warning(f"Proxy file does not exist: {filepath}")
            return []

        try:
            with open(filepath, "r") as f:
                proxy_list = json.load(f)

            self.logger.info(f"Loaded {len(proxy_list)} proxies from {filepath}")
            return proxy_list
        except Exception as e:
            self.logger.error(f"Error loading proxy list from {filepath}: {str(e)}")
            return []

    def get_latest_proxy_file(
        self, directory: Path, prefix: str = ""
    ) -> Optional[Path]:
        """
        Get the most recent proxy file in a directory.

        Args:
            directory: Directory to search for proxy files
            prefix: Optional prefix to filter files by

        Returns:
            Path to the most recent file, or None if no files found
        """
        if not directory.exists():
            return None

        files = list(directory.glob(f"{prefix}*.json"))
        if not files:
            return None

        # Return the most recent file (by modification time)
        return max(files, key=os.path.getmtime)

    def diff_proxy_lists(self, old_list: List[Dict], new_list: List[Dict]) -> Dict:
        """
        Compare two proxy lists and identify differences.

        Args:
            old_list: Previous list of proxies
            new_list: New list of proxies

        Returns:
            Dictionary with 'added', 'removed', and 'unchanged' keys containing lists of proxies
        """
        # Extract unique identifiers (hostnames) from each list
        old_hostnames = {
            proxy.get("hostname") for proxy in old_list if proxy.get("hostname")
        }
        new_hostnames = {
            proxy.get("hostname") for proxy in new_list if proxy.get("hostname")
        }

        # Find added and removed hostnames
        added_hostnames = new_hostnames - old_hostnames
        removed_hostnames = old_hostnames - new_hostnames
        unchanged_hostnames = old_hostnames.intersection(new_hostnames)

        # Create lists of actual proxy objects
        added = [p for p in new_list if p.get("hostname") in added_hostnames]
        removed = [p for p in old_list if p.get("hostname") in removed_hostnames]
        unchanged = [p for p in new_list if p.get("hostname") in unchanged_hostnames]

        self.logger.info(
            f"Proxy diff: {len(added)} added, {len(removed)} removed, {len(unchanged)} unchanged"
        )

        return {"added": added, "removed": removed, "unchanged": unchanged}

    def process_proxies(self, force_check: bool = False) -> None:
        """
        Process proxies by fetching, checking, and updating the proxy list.

        This is the main orchestration method that:
        1. Fetches the latest available proxies
        2. Checks if we have already validated proxies available
        3. Tests proxies against Sofascore if needed or requested
        4. Saves the results
        5. Updates the internal proxy list

        Args:
            force_check: If True, force checking all proxies even if we have recent validation data
        """
        # Step 1: Fetch the current list of available proxies
        self.logger.info("Fetching current list of Mullvad proxies")
        with tqdm(total=1, desc="Fetching proxies", unit="batch") as pbar:
            unchecked_proxies = self.fetch_proxy_list()
            pbar.update(1)

        # Initialize the proxies list with unchecked proxies so it's not empty during testing
        # This addresses the "No proxies available" error
        self.proxies = unchecked_proxies

        # get the previous unchecked_proxies
        unchecked_proxies_previous_save = self.get_latest_proxy_file(
            self.DATA_RAW_DIR, "raw_proxies"
        )
        if unchecked_proxies_previous_save:
            unchecked_proxies_previous = self.load_proxy_list(
                unchecked_proxies_previous_save
            )

        # Step 2: Check if we have recent valid proxies
        latest_valid_file = self.get_latest_proxy_file(
            self.DATA_CLEAN_DIR, "valid_proxies"
        )

        valid_proxies = []
        if latest_valid_file and not force_check:
            # Load previously validated proxies
            self.logger.info(
                f"Loading previously validated proxies from {latest_valid_file}"
            )
            with tqdm(total=1, desc="Loading cached proxies", unit="file") as pbar:
                valid_proxies = self.load_proxy_list(latest_valid_file)
                pbar.update(1)

            # Check if the file is recent enough (e.g., less than 24 hours old)
            file_age = time.time() - os.path.getmtime(latest_valid_file)
            if file_age > 86400:  # 24 hours in seconds
                self.logger.info(
                    "Validated proxy list is older than 24 hours, checking proxies"
                )
                force_check = True

            # Compare with current proxies to identify changes
            if valid_proxies:
                with tqdm(
                    total=1, desc="Comparing proxy lists", unit="comparison"
                ) as pbar:
                    diff = self.diff_proxy_lists(
                        unchecked_proxies_previous, unchecked_proxies
                    )
                    pbar.update(1)

                # If there are significant changes, force a recheck
                if len(diff["added"]) > 10 or len(diff["removed"]) > 10:
                    self.logger.info(
                        "Significant changes in proxy list detected, forcing recheck"
                    )
                    self.save_proxy_list(
                        unchecked_proxies, self.DATA_RAW_DIR, f"raw_proxies"
                    )
                    force_check = True
        else:
            # No valid proxy file found
            self.logger.info(
                "No recent validated proxy list found, checking all proxies"
            )
            force_check = True

        # Step 3: Check proxies if needed
        if force_check:
            self.logger.info("Checking proxies for Sofascore compatibility")
            valid_proxies = self.check_proxy_list(unchecked_proxies)

            # Save the validated proxies
            if valid_proxies:
                with tqdm(total=1, desc="Saving valid proxies", unit="file") as pbar:
                    self.save_proxy_list(
                        valid_proxies, self.DATA_CLEAN_DIR, "valid_proxies"
                    )
                    pbar.update(1)

        # Step 4: Update the internal proxy list
        if valid_proxies:
            self.logger.info(f"Setting {len(valid_proxies)} valid proxies for use")
            self.define_proxy_list(valid_proxies)
        else:
            self.logger.warning("No valid proxies found, using unchecked proxies")
            # We already set this earlier, but want to keep the log message
            # self.proxies = unchecked_proxies

    def define_proxy_list(self, proxy_list: List[Dict]) -> None:
        """Set a new proxy list, after checking them"""
        if not proxy_list:
            raise ValueError("Empty proxies list")
        self.proxies = proxy_list

    def get_random_proxy(self) -> Dict:
        """
        Get a random proxy from the available list.

        Returns:
            Dictionary with proxy information
        """
        if not self.proxies:
            raise ValueError("No proxies available")

        return random.choice(self.proxies)

    def verify_ip_change(self, previous_ip: Optional[str] = None) -> Tuple[bool, str]:
        """
        Verify that the IP has changed by checking Mullvad's IP verification service.

        Args:
            previous_ip: Previous IP address to compare against

        Returns:
            Tuple of (success, current_ip)
        """
        try:
            # Use requests instead of curl to check the current IP through Mullvad
            response = requests.get("https://am.i.mullvad.net/json", timeout=10)
            response.raise_for_status()

            data = response.json()
            current_ip = data.get("ip", "")
            is_mullvad = data.get("mullvad_exit_ip", False)

            if not is_mullvad:
                self.logger.warning("Not connected through Mullvad VPN")
                return False, current_ip

            # Check if IP has changed
            if previous_ip and current_ip == previous_ip:
                self.logger.warning(f"IP has not changed: {current_ip}")
                return False, current_ip

            self.logger.info(f"Current IP: {current_ip}")
            return True, current_ip

        except Exception as e:
            self.logger.error(f"Error verifying IP change: {str(e)}")
            return False, ""


################################################################################
############################## Testing area                 ####################
################################################################################
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    mv = MullvadProxyManager()
    #### some leading tests

    #
    raw_dir = mv.DATA_RAW_DIR
    clean_dir = mv.DATA_CLEAN_DIR
    print(f"{raw_dir=} \n{clean_dir=}")

    lates_raw = mv.get_latest_proxy_file(raw_dir)
    lates_raw
    lates_clean = mv.get_latest_proxy_file(clean_dir)
    lates_clean

    loaded_raw = mv.load_proxy_list(lates_raw)
    loaded_raw
    loaded_clean = mv.load_proxy_list(lates_clean)
    loaded_clean
    len(loaded_clean)

    lates_valid_file = mv.get_latest_proxy_file(mv.DATA_CLEAN_DIR, "valid_proxies")
    lates_valid_file
    valid_proxies = mv.load_proxy_list(lates_valid_file)
    valid_proxies
    t = time.time()
    t
    file_t = os.path.getmtime(lates_valid_file)
    file_t
    t - file_t
    diff = mv.diff_proxy_lists(loaded_raw, valid_proxies)
    diff

    fetch = mv.fetch_proxy_list()

    diff = mv.diff_proxy_lists(loaded_raw, fetch)
    ######
    # Test basic proxy fetching
    print("Testing proxy fetching...")
    proxies = mv.fetch_proxy_list()
    print(f"Fetched {len(proxies)} proxies")

    # Test proxy checking
    print("\nTesting proxy checking...")
    # Check just a few proxies for testing
    test_proxies = proxies[:5]
    valid_proxies = mv.check_proxy_list(test_proxies)
    print(f"Found {len(valid_proxies)} valid proxies")

    # Test the full process_proxies function
    print("\nTesting full proxy processing...")
    mv.process_proxies(force_check=True)

    # Get a random proxy
    print("\nGetting a random proxy...")
    random_proxy = mv.get_random_proxy()
    print(
        f"Random proxy: {random_proxy.get('country')} - {random_proxy.get('hostname')}"
    )

    len(mv.proxies)
    mv = MullvadProxyManager(max_threads=1)
    mv.process_proxies()

    mv.process_proxies()
    ####
