import csv
import os
import pandas as pd
from typing import List, Callable

from .scraper import GoogleMapsEngine
from utils.state_manager import update_latest_progress

HEADERS = ["keyword", "title", "category", "primary_mobile", "secondary_phone", "website", "address", "rating", "reviews"]

class GMapsRunner:
    def __init__(self, target_input: str, output_path: str, start_index: int = 0, target_count: int = 0, ui_logger: Callable[[str], None] = print):
        self.target_input = target_input.strip('\'" \t\r\n')
        self.output_path = output_path.strip('\'" \t\r\n')
        self.current_idx = start_index
        self.target_count = target_count
        self.total_saved = 0
        self.log = ui_logger

    def _load_keywords(self) -> List[str]:
        raw_path = os.path.abspath(os.path.expanduser(self.target_input))
        if os.path.isfile(raw_path):
            ext = os.path.splitext(raw_path)[1].lower()
            try:
                if ext in [".xlsx", ".xls"]:
                    df = pd.read_excel(raw_path)
                elif ext == ".csv":
                    df = pd.read_csv(raw_path)
                else:
                    with open(raw_path, "r", encoding="utf-8") as f:
                        return [line.strip() for line in f if line.strip()]

                if df.shape[1] > 1:
                    return df.apply(lambda row: " ".join(row.dropna().astype(str)), axis=1).tolist()
                else:
                    return [str(val).strip() for val in df.iloc[:, 0].dropna().tolist()]
            except Exception as e:
                self.log(f"✖ Error parsing file: {e}")
                return [self.target_input]

        return [self.target_input]

    def _init_csv(self) -> None:
        abs_output = os.path.abspath(os.path.expanduser(self.output_path))
        os.makedirs(os.path.dirname(abs_output), exist_ok=True)
        if not os.path.exists(abs_output) or os.path.getsize(abs_output) == 0:
            with open(abs_output, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)

    def run(self) -> None:
        self._init_csv()
        keywords = self._load_keywords()

        self.log(f"Target Source: {self.target_input}")
        self.log(f"Queued Tasks: {len(keywords)} items")
        self.log(f"Export Dest: {self.output_path}")

        engine = GoogleMapsEngine(headless=False)

        try:
            for idx in range(self.current_idx, len(keywords)):
                kw = keywords[idx]
                self.log(f"\n--- TASK [{idx+1}/{len(keywords)}]: {kw.upper()} ---")
                self.log("Connecting & awaiting Google response (Max 20s sentry)...")
                
                is_loaded = engine.search_query(kw)

                if not is_loaded:
                    self.log(f"⚠ Sentry Alert: Network stalled or no response after 20s for '{kw}'. Skipping.")
                    update_latest_progress("gmaps", self.target_input, idx + 1, self.total_saved)
                    continue

                seen_links = set()
                doom_scroll_count = 0
                max_scrolls = 25

                if engine.is_single_place_view():
                    self.log("↳ Single company entity resolved directly")
                    details = engine.parse_active_place_pane()
                    if details and details["title"] != "null":
                        row = [
                            kw, details["title"], details["category"], details["phone_1"],
                            details["phone_2"], details["website"], details["address"],
                            details["rating"], details["reviews"]
                        ]
                        with open(self.output_path, "a", encoding="utf-8", newline="") as f:
                            csv.writer(f).writerow(row)
                        self.total_saved += 1
                        self.log(f" [#{self.total_saved}] {details['title'][:25]} | {details['phone_1']} | {details['website'][:24]}")

                    update_latest_progress("gmaps", self.target_input, idx + 1, self.total_saved)
                    continue

                for _ in range(max_scrolls):
                    if self.target_count > 0 and self.total_saved >= self.target_count:
                        break

                    cards = engine.extract_visible_cards()
                    fresh_meat = 0

                    for card in cards:
                        if self.target_count > 0 and self.total_saved >= self.target_count:
                            break

                        try:
                            href = card.get_attribute("href")
                            if not href or href in seen_links:
                                continue

                            details = engine.parse_card_details(card)
                            if details and details.get("link"):
                                seen_links.add(details["link"])
                                row = [
                                    kw, details["title"], details["category"], details["phone_1"],
                                    details["phone_2"], details["website"], details["address"],
                                    details["rating"], details["reviews"]
                                ]
                                with open(self.output_path, "a", encoding="utf-8", newline="") as f:
                                    csv.writer(f).writerow(row)

                                self.total_saved += 1
                                fresh_meat += 1
                                
                                mob_badge = "📱" if ("+9715" in details["phone_1"] or "+91" in details["phone_1"]) else "☎"
                                self.log(f" [#{self.total_saved:<4}] {details['title'][:24]:<24} | {mob_badge} {details['phone_1']:<16} | {details['website'][:22]}")
                        except Exception:
                            continue

                    if engine.is_end_of_list():
                        self.log("↳ End of directory reached for this search term.")
                        break

                    has_moved, _ = engine.scroll_results_pane()
                    if fresh_meat == 0 and not has_moved:
                        doom_scroll_count += 1
                    else:
                        doom_scroll_count = 0

                    if doom_scroll_count >= 2:
                        self.log("↳ Directory scroll threshold satisfied. Proceeding...")
                        break

                update_latest_progress("gmaps", self.target_input, idx + 1, self.total_saved)

                if self.target_count > 0 and self.total_saved >= self.target_count:
                    self.log(f"\n✔ Target lead threshold of {self.target_count} successfully collected!")
                    break

        except Exception as e:
            self.log(f"Pipeline error: {e}")
        finally:
            engine.close()
