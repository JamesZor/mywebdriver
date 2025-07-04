import logging

from omegaconf import DictConfig, OmegaConf

logger = logging.getLogger(__name__)


def is_valid_chrome_webdriver_config(config: DictConfig) -> bool:
    """
    Validate config structure using OmegaConf's safe access methods.
    """
    logger.debug("=== Config Validation ===")
    logger.debug(f"Config type: {type(config)}")
    logger.debug(f"Config keys: {list(config.keys()) if config else 'None'}")

    try:
        # Check required top-level sections exist
        webdriver_section = OmegaConf.select(config, "webdriver")
        logger.debug(f"Webdriver section found: {webdriver_section is not None}")

        if webdriver_section is None:
            logger.error("Missing 'webdriver' section in config")
            return False

        # Check webdriver.browser section
        browser_section = OmegaConf.select(config, "webdriver.browser")
        logger.debug(f"Browser section found: {browser_section is not None}")

        if browser_section is None:
            logger.error("Missing 'webdriver.browser' section in config")
            return False

        # Check for Hydra _target_ structure
        target = OmegaConf.select(config, "webdriver.browser._target_")
        if target:
            logger.debug(f"Found _target_: {target}")

            # Check required Hydra fields
            service_target = OmegaConf.select(
                config, "webdriver.browser.service._target_"
            )
            options_target = OmegaConf.select(
                config, "webdriver.browser.options._target_"
            )

            logger.debug(f"Service _target_: {service_target}")
            logger.debug(f"Options _target_: {options_target}")

            if not service_target or not options_target:
                logger.error("Hydra config missing service or options _target_")
                return False

        # Check optional sections (don't fail if missing)
        socks5_section = OmegaConf.select(config, "socks5")
        timeouts_section = OmegaConf.select(config, "timeouts")

        logger.debug(f"SOCKS5 section found: {socks5_section is not None}")
        logger.debug(f"Timeouts section found: {timeouts_section is not None}")

        # Validate timeouts structure if present
        if timeouts_section:
            page_load_timeout = OmegaConf.select(config, "timeouts.page_load")
            if page_load_timeout is None:
                logger.warning("timeouts.page_load not found, using default")

        logger.debug("✅ Config validation passed")
        return True

    except Exception as e:
        logger.error(f"Config validation failed: {e}")
        logger.debug("Validation error details:", exc_info=True)
        return False
