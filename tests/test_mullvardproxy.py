import logging

from omegaconf import OmegaConf

from webdriver import MullvadProxyManager, MyWebDriver

logging.basicConfig(level=logging.DEBUG)


def test_basic_setup():
    proxy_manager = MullvadProxyManager()
    proxy_list = proxy_manager.fetch_proxy_list()
    print(proxy_list[1])
    cfg = proxy_manager._load_package_config()
    print(OmegaConf.to_yaml(cfg))

    override_socks = proxy_manager.socks_override(proxy_list[0])
    cfg = proxy_manager._load_package_config(overrides=override_socks)
    print("add socks5")
    print(OmegaConf.to_yaml(cfg))

    driver = MyWebDriver(config=cfg)
    test_url: str = "https://am.i.mullvad.net/json"

    driver.navigate(test_url)
    print(f"==================================\nCurrent URL: {driver.current_url}")
    print("=" * 10)
    webpage_data = driver.get_json_content()
    print(webpage_data)


if __name__ == "__main__":
    test_basic_setup()
