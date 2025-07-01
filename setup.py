from setuptools import find_packages, setup

setup(
    name="webdriver-proxy-package",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "selenium>=4.0.0",
        "hydra-core>=1.3.0",
        "omegaconf>=2.3.0",
        "requests>=2.28.0",
    ],
    package_data={
        "webdriver": ["conf/**/*.yaml"],
    },
    include_package_data=True,
    author="James",
    description="WebDriver package with proxy rotation and Hydra configuration",
)
