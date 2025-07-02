import logging

from omegaconf import OmegaConf

from webdriver import MullvadProxyManager, MyWebDriver

logging.basicConfig(level=logging.DEBUG)


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
    idx = 0
    p_c = proxy_list[idx]
    proxy_results = proxy_manager.check_proxy(p_c)
    print(f"{proxy_results = }.")
    print(f"checked proxy\n{p_c =}.")

    print("=" * 10 + " End test check proxy " + "=" * 10)


if __name__ == "__main__":
    #    test_basic_setup()
    test_check_proxy()
