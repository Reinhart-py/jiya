import random
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

class GoogleMapsEngine:
    def __init__(self, headless: bool = False):
        self.driver = self._init_driver(headless)

    def _init_driver(self, headless: bool) -> webdriver.Chrome:
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--start-maximized")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        service = Service()
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(35)
        return driver

    def human_delay(self, a: float = 0.4, b: float = 0.9) -> None:
        time.sleep(random.uniform(a, b))

    def wait_for_search_results(self, timeout: int = 15) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                if "/maps/place/" in self.driver.current_url:
                    return True

                cards = self.driver.find_elements(
                    By.XPATH,
                    "//div[@role='feed']//a[contains(@href, '/maps/place/')] | //a[contains(@href, '/maps/place/')]"
                )
                if len(cards) > 0:
                    return True

                if self.is_end_of_list() or self.is_partial_match():
                    return True
            except Exception:
                pass
            time.sleep(0.3)
        return False

    def search_query(self, query_or_url: str) -> bool:
        if query_or_url.startswith("http://") or query_or_url.startswith("https://"):
            url = query_or_url
        else:
            encoded = quote(query_or_url.strip())
            url = f"https://www.google.com/maps/search/{encoded}?hl=en"

        try:
            self.driver.get(url)
        except Exception:
            pass

        try:
            for btn_xpath in [
                "//button[contains(@aria-label, 'Accept')]",
                "//button[contains(., 'Accept all')]",
                "//form//button"
            ]:
                btns = self.driver.find_elements(By.XPATH, btn_xpath)
                if btns:
                    btns[0].click()
                    break
        except Exception:
            pass

        return self.wait_for_search_results(timeout=15)

    def is_end_of_list(self) -> bool:
        try:
            end_markers = self.driver.find_elements(
                By.XPATH,
                "//span[contains(text(), \"You've reached the end of the list\")] | "
                "//div[contains(text(), \"You've reached the end of the list\")] | "
                "//span[contains(text(), 'No more results')] | "
                "//div[contains(@class, 'HlvSq')]"
            )
            return len(end_markers) > 0
        except Exception:
            return False

    def is_partial_match(self) -> bool:
        try:
            partial_markers = self.driver.find_elements(
                By.XPATH,
                "//div[contains(text(), 'Partial match')] | //span[contains(text(), 'Partial match')] | "
                "//div[contains(text(), 'Did you mean')] | //div[contains(text(), 'No results found')] | "
                "//div[contains(text(), \"Don't see what you're looking for?\")]"
            )
            return len(partial_markers) > 0
        except Exception:
            return False

    def is_single_place_view(self) -> bool:
        return "/maps/place/" in self.driver.current_url

    def close_place_view(self) -> None:
        try:
            back_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@aria-label, 'Back')] | //button[@jsaction*='pane.back'] | "
                "//button[@aria-label='Close'] | //button[contains(@class, 'hArJGc')]"
            )
            if back_buttons and back_buttons[0].is_displayed():
                self.driver.execute_script("arguments[0].click();", back_buttons[0])
                time.sleep(0.6)
                return
        except Exception:
            pass

        try:
            self.driver.back()
            time.sleep(0.6)
        except Exception:
            pass

    def scroll_results_pane(self) -> Tuple[bool, int]:
        try:
            feed = self.driver.find_element(
                By.XPATH,
                "//div[@role='feed'] | //div[contains(@aria-label, 'Results for')]"
            )
            old_top = self.driver.execute_script("return arguments[0].scrollTop;", feed)
            scroll_amt = random.randint(700, 1100)
            self.driver.execute_script("arguments[0].scrollTop += arguments[1];", feed, scroll_amt)
            self.human_delay(0.7, 1.2)
            new_top = self.driver.execute_script("return arguments[0].scrollTop;", feed)
            return (new_top > old_top, new_top)
        except Exception:
            try:
                self.driver.execute_script(f"window.scrollBy(0, {random.randint(500, 800)});")
                self.human_delay(0.5, 0.9)
                return (True, 0)
            except Exception:
                return (False, 0)

    def extract_visible_cards(self) -> List:
        return self.driver.find_elements(
            By.XPATH,
            "//div[@role='feed']//a[contains(@href, '/maps/place/')] | //a[contains(@href, '/maps/place/')]"
        )

    def _rank_phones(self, phones: List[str]) -> List[str]:
        def score(p: str) -> int:
            clean = re.sub(r"[^\d+]", "", p)
            if clean.startswith("+9715") or clean.startswith("009715") or clean.startswith("05") or clean.startswith("9715"):
                return 0
            if re.match(r"^(\+91|91|0)?[6-9]\d{9}$", clean):
                return 1
            if clean.startswith("+447") or clean.startswith("07"):
                return 2
            if any(clean.startswith(tf) for tf in ["800", "+971800", "1800", "+1800"]):
                return 10
            if re.search(r"(\+?\d{1,3})?[5-9]\d{7,10}", clean):
                return 3
            return 5

        unique = list(dict.fromkeys([p.strip() for p in phones if p.strip()]))
        return sorted(unique, key=score)

    def parse_card_details(self, card) -> Optional[Dict[str, str]]:
        try:
            link = card.get_attribute("href")
            if not link:
                return None

            title = card.get_attribute("aria-label")
            if not title:
                title = card.text.split("\n")[0] if card.text else "null"

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
            self.human_delay(0.1, 0.2)
            self.driver.execute_script("arguments[0].click();", card)

            start_pane = time.time()
            pane_loaded = False
            while time.time() - start_pane < 7:
                if len(self.driver.find_elements(By.XPATH, "//h1[contains(@class, 'DUwDvf')] | //button[@data-item-id='address']")) > 0:
                    pane_loaded = True
                    break
                time.sleep(0.2)

            if not pane_loaded:
                return None

            data = self.parse_active_place_pane(link, title)
            self.close_place_view()
            return data
        except Exception:
            self.close_place_view()
            return None

    def parse_active_place_pane(self, link: str = "", title: str = "") -> Optional[Dict[str, str]]:
        try:
            if not link:
                link = self.driver.current_url
            if not title:
                try:
                    title = self.driver.find_element(By.XPATH, "//h1[contains(@class, 'DUwDvf')]").text.strip()
                except Exception:
                    title = "null"

            data = {
                "link": link,
                "title": title.strip(),
                "category": "null",
                "phone_1": "null",
                "phone_2": "null",
                "website": "null",
                "address": "null",
                "rating": "null",
                "reviews": "null",
            }

            raw_phones = []
            phone_nodes = self.driver.find_elements(
                By.XPATH,
                "//button[starts-with(@data-item-id, 'phone:')] | //button[contains(@aria-label, 'Phone')] | //a[starts-with(@href, 'tel:')]"
            )
            for node in phone_nodes:
                text = node.text.replace("Phone:", "").strip()
                href = node.get_attribute("href") or ""
                tel = href.replace("tel:", "").strip()
                if text:
                    raw_phones.append(text)
                if tel:
                    raw_phones.append(tel)

            ranked = self._rank_phones(raw_phones)
            if len(ranked) > 0:
                data["phone_1"] = ranked[0]
            if len(ranked) > 1:
                data["phone_2"] = ranked[1]

            try:
                addr_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[@data-item-id='address'] | //button[contains(@aria-label, 'Address')]"
                )
                data["address"] = addr_btn.text.replace("Address:", "").strip()
            except Exception:
                pass

            try:
                web_btn = self.driver.find_element(
                    By.XPATH,
                    "//a[@data-item-id='authority'] | //a[contains(@aria-label, 'Website')]"
                )
                data["website"] = web_btn.get_attribute("href")
            except Exception:
                pass

            try:
                stars_el = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'F7nice')]//span[@aria-hidden='true']"
                )
                data["rating"] = stars_el.text.strip()
                revs_el = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'F7nice')]//span[contains(@aria-label, 'reviews')]"
                )
                data["reviews"] = "".join(filter(str.isdigit, revs_el.text))
            except Exception:
                pass

            try:
                cat_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@jsaction, 'pane.rating.category')]"
                )
                data["category"] = cat_btn.text.strip()
            except Exception:
                pass

            return data
        except Exception:
            return None

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass
