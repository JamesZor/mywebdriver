"""
Test Hydra config loading and composition.
"""

import logging

from webdriver.core.factory import create_webdriver_with_hydra, load_package_config

# Configure logging
logging.basicConfig(level=logging.INFO)


def test_config_loading():
    """Test that Hydra correctly loads and composes package configs."""

    print("=== Testing Config Loading ===")

    # Load the default config
    cfg = load_package_config()

    print("Loaded config structure:")
    from omegaconf import OmegaConf

    print(OmegaConf.to_yaml(cfg))

    # Test expected values
    print("\n=== Validating Expected Values ===")

    # Check proxy config
    assert (
        not cfg.proxy.enabled
    ), f"Expected proxy.enabled=False, got {cfg.proxy.enabled}"
    assert (
        not cfg.proxy.rotation.enabled
    ), f"Expected proxy.rotation.enabled=False, got {cfg.proxy.rotation.enabled}"
    assert (
        cfg.proxy.rotation.interval == 10
    ), f"Expected proxy.rotation.interval=10, got {cfg.proxy.rotation.interval}"
    print("✅ Proxy config loaded correctly")

    # Check webdriver config
    assert (
        cfg.webdriver.browser.type == "chrome"
    ), f"Expected webdriver.browser.type=chrome, got {cfg.webdriver.browser.type}"
    assert (
        not cfg.webdriver.browser.headless
    ), f"Expected webdriver.browser.headless=False, got {cfg.webdriver.browser.headless}"
    assert (
        cfg.webdriver.browser.timeout == 30
    ), f"Expected webdriver.browser.timeout=30, got {cfg.webdriver.browser.timeout}"
    print("✅ WebDriver config loaded correctly")

    # Check package info
    assert (
        cfg.package.name == "webdriver_proxy"
    ), f"Expected package.name=webdriver_proxy, got {cfg.package.name}"
    print("✅ Package config loaded correctly")

    print("\n🎉 All config tests passed!")
    return cfg


def test_config_overrides():
    """Test that config overrides work correctly."""

    print("\n=== Testing Config Overrides ===")

    # Test with overrides
    cfg = load_package_config(
        overrides=[
            "proxy.enabled=true",
            "webdriver.browser.headless=true",
            "proxy.rotation.interval=5",
        ]
    )

    print("Config with overrides:")
    from omegaconf import OmegaConf

    print(OmegaConf.to_yaml(cfg))

    # Validate overrides worked
    assert cfg.proxy.enabled, "Override proxy.enabled=true failed"
    assert (
        cfg.webdriver.browser.headless
    ), "Override webdriver.browser.headless=true failed"
    assert cfg.proxy.rotation.interval == 5, "Override proxy.rotation.interval=5 failed"

    print("✅ All overrides applied correctly!")


def test_webdriver_with_config():
    """Test creating WebDriver with loaded config."""

    print("\n=== Testing WebDriver Creation with Config ===")

    # Create WebDriver using factory
    driver = create_webdriver_with_hydra(session_id="config_test")

    # Print the config that was used
    driver._print_config()

    # Test basic functionality
    driver.navigate("https://example.com")
    print(f"Navigation successful: {driver.current_url}")

    driver.close()
    print("✅ WebDriver with config test passed!")


if __name__ == "__main__":
    # Run all tests
    cfg = test_config_loading()
    test_config_overrides()
    test_webdriver_with_config()

    print("\n🚀 All tests completed successfully!")
