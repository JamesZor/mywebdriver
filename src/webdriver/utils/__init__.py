# src/webdriver/utils/__init__.py

from .validators import is_valid_chrome_webdriver_config

# Export the functions so they're available when importing the package
__all__ = [
    "is_valid_chrome_webdriver_config",
]
