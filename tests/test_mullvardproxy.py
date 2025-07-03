import logging

from omegaconf import OmegaConf

from webdriver import MullvadProxyManager, MyWebDriver

logging.basicConfig(level=logging.INFO)


def test_proxy_fetch():
    """
    mostly to fix the splitting of america country strings as they are in the format
    city, state -> Los Angeles, CA  - Houston, TX
    """
    pm = MullvadProxyManager()
    proxy_list = pm.fetch_proxy_list()

    for p in proxy_list:
        print(p)


def test_basic_setup():
    proxy_manager = MullvadProxyManager()
    proxy_list = proxy_manager.fetch_proxy_list()
    print(proxy_list[0:5])
    cfg = proxy_manager._load_package_config()
    print(OmegaConf.to_yaml(cfg))

    override_socks = proxy_manager._socks_override(proxy_list[0])
    cfg = proxy_manager._load_package_config(overrides=override_socks)
    print("add socks5")
    #    print(OmegaConf.to_yaml(cfg))

    driver = MyWebDriver(config=cfg)
    test_url: str = "https://am.i.mullvad.net/json"

    driver.navigate(test_url)
    print("=" * 20 + f"\nCurrent URL: {driver.current_url}\n" + "=" * 20)
    webpage_data = driver.get_json_content()
    print(webpage_data)
    print("=" * 20 + f"\n{webpage_data =}\n" + "=" * 20)

    assert proxy_manager.check_wg_mullvad_connection(), "Need to run wg"

    driver.close()


def test_check_proxy():
    print("=" * 10 + " Running test check proxy " + "=" * 10)
    proxy_manager = MullvadProxyManager()

    proxy_list = proxy_manager.fetch_proxy_list()
    idx = 19
    # [18, 19, 20, 21]
    p_c = proxy_list[idx]
    proxy_results = proxy_manager.check_proxy(p_c)
    print(f"{proxy_results = }.")
    print(f"checked proxy\n{p_c =}.")

    print("=" * 10 + " End test check proxy " + "=" * 10)


def test_check_proxy_list():
    print("=" * 10 + " Running test check proxy list " + "=" * 10)
    proxy_manager = MullvadProxyManager()

    proxy_list = proxy_manager.fetch_proxy_list()
    idx = len(proxy_list)
    proxy_manager.check_all_proxies_threaded(proxy_list[:idx], max_workers=10)

    for p in proxy_list[:idx]:
        if p.get("valid"):
            print(p.get("country"), p.get("hostname"))


def test_load_save():
    print("=" * 10 + " Running simple save load test " + "=" * 10)
    pm = MullvadProxyManager()
    proxy_list = pm.fetch_proxy_list()

    print("got proxy list, now saving.")
    pm.save_proxy_list(proxy_list=proxy_list)

    print("saved")
    loaded_list = pm.load_latest_proxy_list()
    print(loaded_list[0:5])

    print("=" * 10 + " End of simple save load test " + "=" * 10)


def test_processing():

    pm = MullvadProxyManager()

    latest_file = pm._get_latest_proxy_file()

    print(f"{latest_file =}")

    age_hours = pm._get_file_age_hours(latest_file)

    print(f"{age_hours =}")

    is_fresh = age_hours <= 24.0

    print(f"{is_fresh =}")

    is_fresh, cache_file = pm.is_cache_fresh(24)
    print(f"{is_fresh =}, {cache_file = }")


def test_main_process():
    print("=" * 10 + " Running main process testing " + "=" * 10)
    pm = MullvadProxyManager(max_workers=10)
    fresh_proxies = pm.get_proxy_list(force_refresh=True)
    #    fresh_proxies = pm.get_proxy_list()

    print(fresh_proxies[0:5])
    print("=" * 10 + " Ended of main process testing " + "=" * 10)


if __name__ == "__main__":
    #    test_proxy_fetch()
    # test_load_save()
    #    test_basic_setup()
    #    test_check_proxy()
    #    test_check_proxy_list()
    #    test_processing()
    test_main_process()
