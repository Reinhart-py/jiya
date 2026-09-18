from typing import TypeAlias

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

NoSuchElement: TypeAlias = NoSuchElementException

XPATHS = {
    "result_count": "(//span[@class='_1xhlznaa'])[1]",
    "scroll_container_primary": "(//div[@class='_15gu4wr'])[3]",
    "scroll_container_fallback": "(//div[@class='_15gu4wr'])[2]",
    "next_page_btn": "//div[@class='_5ocwns']//div[2] | //div[contains(@class, 'pagination')]//div[last()]",
    "close_drawer_btn": "//div[@class='_121p9rc'] | //button[@aria-label='Close'] | //div[contains(@class, 'close')]",
}


def get_default_chrome_options() -> Options:
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-background-networking")
    options.add_argument("--mute-audio")
    options.add_argument("--js-flags=--expose-gc")
    options.add_argument("--disk-cache-size=52428800")
    options.add_argument("--media-cache-size=52428800")
    return options


def create_session(
    options: Options = None,
    service: Service = None,
) -> WebDriver:
    if options is None:
        options = get_default_chrome_options()
    if service is None:
        service = webdriver.ChromeService()
    driver = webdriver.Chrome(options=options, service=service)
    driver.set_page_load_timeout(60)
    driver.maximize_window()
    return driver


def clean_dom_memory(driver: WebDriver) -> None:
    try:
        driver.execute_script("""
            if (window.gc) {
                window.gc();
            }
            const ghost_canvases = document.querySelectorAll('canvas:not([width])');
            ghost_canvases.forEach(c => c.remove());
        """)
    except Exception:
        pass


def quit_session(driver: WebDriver | None) -> None:
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass


def navigate(url: str, driver: WebDriver) -> None:
    driver.get(url)


def find(driver: WebDriver, xpath: str) -> WebElement:
    return driver.find_element(By.XPATH, xpath)


def scroll_into_view(driver: WebDriver, el: WebElement | None) -> None:
    if el:
        driver.execute_script("arguments[0].scrollIntoView(false);", el)


def wait(time: float, driver: WebDriver) -> None:
    driver.implicitly_wait(time)


def click_element(element: WebElement) -> None:
    element.click()
