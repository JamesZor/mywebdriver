import logging
import os

from omegaconf import OmegaConf

import webdriver.core.factory as factory
from webdriver.core.mywebdriver import MyWebDriver

os.environ["DISPLAY"] = ":0"

# 1. Set up basic logging so you can see the debug output in IPython
logging.basicConfig(level=logging.DEBUG)

# 2. Load your test config
cfg = factory.load_package_config(config_name="default")

# 3. Force proxy settings to False (just to guarantee it bypasses the proxy logic)
cfg.proxy.enabled = False
cfg.proxy.rotation.enabled = False

# (Optional) If you are still debugging the Chrome 143 crash, you can inject the headless flag here
# cfg.webdriver.browser.options.arguments.append("--headless=new")

# 4. Build the Chrome options
chrome_optionsbuilder = factory.get_webdrive_chrome_optionbuilder(cfg)

# 5. Instantiate the WebDriver (note the corrected 'optionsbuilder' spelling)
print("Spawning WebDriver...")
driver = MyWebDriver(
    optionsbuilder=chrome_optionsbuilder,  # Fixed typo here
    config=cfg,
    session_id="ipython_test_session",
)

# 6. Run a quick test
try:
    print(f"Navigating... (Current config proxy status: {driver.config.proxy.enabled})")
    driver.navigate(test_url)
    data = driver.get_page(test_url)
    print(data)
    print(f"Success! Reached: {driver.current_url}")
finally:
    # 7. Ensure it closes properly even if it fails
    driver.close()
    print("WebDriver closed.")
