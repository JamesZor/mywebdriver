import logging

from webdriver import ManagerWebdriver

logging.basicConfig(level=logging.INFO)


def test_manager_webdriver():
    mw = ManagerWebdriver()

    d1 = mw.spawn_webdriver()
    test_url: str = "https://am.i.mullvad.net/json"
    test_url = "https://api.sofascore.com/api/v1/tournament/1"

    page_data = d1.get_page(test_url)

    print(page_data)


if __name__ == "__main__":
    test_manager_webdriver()
