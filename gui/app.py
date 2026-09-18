import os
import threading
import urllib.request
import webbrowser
from io import BytesIO

import customtkinter as ctk
from PIL import Image, ImageDraw

from gmaps.runner import GMapsRunner
from runner.runner import Runner as TwoGISRunner
from utils.state_manager import load_all_history

ctk.set_appearance_mode("dark")

# ◈ NEON GLOSSY COLOR PALETTE ◈
BG_COLOR = "#050505"           # Pitch black background
CARD_COLOR = "#0D0D0D"         # Slightly raised black for cards
NEON_PURPLE = "#A855F7"        # Glowing shiny purple edge
HOVER_PURPLE = "#7E22CE"       # Darker purple for button hovers
TEXT_WHITE = "#FFFFFF"
TEXT_GRAY = "#9CA3AF"

class KiriApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kiri")
        self.geometry("820x520")
        self.minsize(750, 480)
        self.configure(fg_color=BG_COLOR)

        self.current_thread = None
        self.is_running = False
        self.resume_state = {}
        self.icons = {}

        self._build_layout()
        self._load_ui_icons()
        self._build_sidebar()
        self._build_dashboard()
        self._build_gmaps_view()
        self._build_2gis_view()
        self._build_history_view()
        self._build_profile_view()

        self.select_frame("dashboard")

    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=180, corner_radius=0, fg_color=BG_COLOR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=20, fg_color=BG_COLOR)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frames = {}

    def _load_ui_icons(self):
        """Fetches proper sleek white icons in the background so the app boots instantly"""
        icon_urls = {
            "dashboard": "https://img.icons8.com/ios-filled/50/ffffff/dashboard.png",
            "gmaps": "https://img.icons8.com/ios-filled/50/ffffff/google-maps.png",
            "2gis": "https://img.icons8.com/ios-filled/50/ffffff/globe.png",
            "history": "https://img.icons8.com/ios-filled/50/ffffff/time-machine.png",
            "profile": "https://img.icons8.com/ios-filled/50/ffffff/user.png"
        }

        def fetch():
            for name, url in icon_urls.items():
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    raw_data = urllib.request.urlopen(req, timeout=3).read()
                    img = Image.open(BytesIO(raw_data)).convert("RGBA")
                    self.icons[name] = ctk.CTkImage(light_image=img, dark_image=img, size=(18, 18))
                    
                    # Update buttons if they are already drawn
                    if hasattr(self, 'nav_btns') and name in self.nav_btns:
                        self.after(0, lambda n=name: self.nav_btns[n].configure(image=self.icons[n]))
                except Exception:
                    pass
        threading.Thread(target=fetch, daemon=True).start()

    def _build_sidebar(self):
        # Load the local logo1.png
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "logo1.png")
            if not os.path.exists(logo_path): logo_path = "images/logo1.png"
            logo_img = Image.open(logo_path).convert("RGBA")
            self.logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(70, 70))
        except Exception:
            # Fallback if image folder is missing
            logo_img = Image.new("RGBA", (70, 70), (0, 0, 0, 0))
            self.logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(70, 70))

        logo_lbl = ctk.CTkLabel(self.sidebar_frame, image=self.logo_ctk, text="")
        logo_lbl.grid(row=0, column=0, pady=(20, 5))

        title_lbl = ctk.CTkLabel(self.sidebar_frame, text="K I R I", font=ctk.CTkFont(size=18, weight="bold"), text_color=NEON_PURPLE)
        title_lbl.grid(row=1, column=0, pady=(0, 25))

        nav_buttons = [
            ("dashboard", " Dashboard"),
            ("gmaps", " Google Maps"),
            ("2gis", " 2GIS Global"),
            ("history", " History"),
            ("profile", " Developer"),
        ]

        self.nav_btns = {}
        for i, (key, text) in enumerate(nav_buttons):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                image=self.icons.get(key, None),
                fg_color="transparent",
                text_color=TEXT_WHITE,
                hover_color=CARD_COLOR,
                anchor="w",
                corner_radius=12,
                font=ctk.CTkFont(size=13),
                command=lambda k=key: self.select_frame(k)
            )
            btn.grid(row=i+2, column=0, padx=15, pady=4, sticky="ew")
            self.nav_btns[key] = btn

    def _build_dashboard(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["dashboard"] = frame

        title = ctk.CTkLabel(frame, text="Dashboard", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_WHITE)
        title.grid(row=0, column=0, sticky="w", pady=(5, 15))

        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew")
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        history = load_all_history()
        total_leads = sum(h.get("total_saved", 0) for h in history)

        self._create_stat_card(stats_frame, "Total Sessions", str(len(history)), 0)
        self._create_stat_card(stats_frame, "Leads Saved", f"{total_leads:,}", 1)

        log_frame = ctk.CTkFrame(frame, fg_color=CARD_COLOR, border_width=2, border_color=NEON_PURPLE, corner_radius=15)
        log_frame.grid(row=2, column=0, sticky="nsew", pady=15)
        frame.grid_rowconfigure(2, weight=1)

        lbl = ctk.CTkLabel(log_frame, text="Log Output", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_GRAY)
        lbl.pack(anchor="w", padx=15, pady=(10, 0))

        self.sys_log = ctk.CTkTextbox(log_frame, fg_color="transparent", text_color=TEXT_WHITE, font=ctk.CTkFont(size=12))
        self.sys_log.pack(expand=True, fill="both", padx=10, pady=10)
        self.sys_log.configure(state="disabled")

    def _create_stat_card(self, parent, title, value, col):
        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, border_width=2, border_color=NEON_PURPLE, corner_radius=15, height=90)
        card.grid(row=0, column=col, sticky="ew", padx=8)
        card.pack_propagate(False)

        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color=NEON_PURPLE)
        lbl_val.pack(anchor="w", padx=15, pady=(10, 0))
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color=TEXT_GRAY)
        lbl_title.pack(anchor="w", padx=15)

    def _build_gmaps_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["gmaps"] = frame

        title = ctk.CTkLabel(frame, text="Google Maps", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(5, 15))

        form = ctk.CTkFrame(frame, fg_color=CARD_COLOR, border_width=2, border_color=NEON_PURPLE, corner_radius=15)
        form.pack(fill="x", ipady=10)

        ctk.CTkLabel(form, text="Search Query / Maps URL / Batch File", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=20)
        self.gmaps_input = ctk.CTkEntry(row, width=320, fg_color=BG_COLOR, border_color=NEON_PURPLE, corner_radius=8)
        self.gmaps_input.pack(side="left")
        self.gmaps_input.insert(0, "Software in Business Bay")
        
        ctk.CTkButton(row, text="Browse", width=80, fg_color=BG_COLOR, border_color=NEON_PURPLE, border_width=1, hover_color=HOVER_PURPLE, command=self._browse_file).pack(side="left", padx=10)

        ctk.CTkLabel(form, text="Total Leads to Save (0 for unlimited)", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.gmaps_cap = ctk.CTkEntry(form, width=150, fg_color=BG_COLOR, border_color=NEON_PURPLE, corner_radius=8)
        self.gmaps_cap.pack(anchor="w", padx=20)
        self.gmaps_cap.insert(0, "1000")

        self.gmaps_btn = ctk.CTkButton(frame, text="Start Scraping", fg_color=NEON_PURPLE, hover_color=HOVER_PURPLE, corner_radius=10, command=self._start_gmaps)
        self.gmaps_btn.pack(anchor="w", pady=20)

    def _browse_file(self):
        filepath = ctk.filedialog.askopenfilename(filetypes=[("Data Files", "*.csv *.xlsx *.txt")])
        if filepath:
            self.gmaps_input.delete(0, "end")
            self.gmaps_input.insert(0, filepath)

    def _build_2gis_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["2gis"] = frame

        title = ctk.CTkLabel(frame, text="2GIS Scraper", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(5, 15))

        form = ctk.CTkFrame(frame, fg_color=CARD_COLOR, border_width=2, border_color=NEON_PURPLE, corner_radius=15)
        form.pack(fill="x", ipady=10)

        ctk.CTkLabel(form, text="City Name", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_city = ctk.CTkEntry(form, width=320, fg_color=BG_COLOR, border_color=NEON_PURPLE, corner_radius=8)
        self.twogis_city.pack(anchor="w", padx=20)
        self.twogis_city.insert(0, "Dubai")

        ctk.CTkLabel(form, text="Search Keyword", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_query = ctk.CTkEntry(form, width=320, fg_color=BG_COLOR, border_color=NEON_PURPLE, corner_radius=8)
        self.twogis_query.pack(anchor="w", padx=20)
        self.twogis_query.insert(0, "Software")

        ctk.CTkLabel(form, text="Total Leads to Save", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_cap = ctk.CTkEntry(form, width=150, fg_color=BG_COLOR, border_color=NEON_PURPLE, corner_radius=8)
        self.twogis_cap.pack(anchor="w", padx=20)
        self.twogis_cap.insert(0, "2000")

        self.twogis_btn = ctk.CTkButton(frame, text="Start Scraping", fg_color=NEON_PURPLE, hover_color=HOVER_PURPLE, corner_radius=10, command=self._start_twogis)
        self.twogis_btn.pack(anchor="w", pady=20)

    def _build_history_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["history"] = frame

        title = ctk.CTkLabel(frame, text="History & Resume", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(5, 15))

        self.scroll_hist = ctk.CTkScrollableFrame(frame, fg_color="transparent", corner_radius=0)
        self.scroll_hist.pack(expand=True, fill="both")
        self.refresh_history()

    def refresh_history(self):
        for widget in self.scroll_hist.winfo_children():
            widget.destroy()

        history = load_all_history()
        if not history:
            ctk.CTkLabel(self.scroll_hist, text="No history found.", text_color=TEXT_GRAY).pack(pady=20)
            return

        for idx, item in enumerate(history):
            card = ctk.CTkFrame(self.scroll_hist, fg_color=CARD_COLOR, border_width=1, border_color=NEON_PURPLE, corner_radius=12)
            card.pack(fill="x", pady=5)
            
            eng = str(item.get("engine", "")).upper()
            tgt = str(item.get("target", ""))[:35]
            svd = item.get("total_saved", 0)
            step = item.get("last_step", 1)

            info = ctk.CTkLabel(card, text=f"[{eng}] {tgt}  |  {svd} Leads  |  Step {step}", font=ctk.CTkFont(size=12), text_color=TEXT_WHITE)
            info.pack(side="left", padx=15, pady=15)

            btn = ctk.CTkButton(card, text="Resume", width=70, fg_color=BG_COLOR, border_width=1, border_color=NEON_PURPLE, hover_color=HOVER_PURPLE, command=lambda i=item: self._resume_task(i))
            btn.pack(side="right", padx=15)

    def _resume_task(self, item):
        self.resume_state = item
        engine = item.get("engine")
        
        if engine == "gmaps":
            self.gmaps_input.delete(0, "end")
            self.gmaps_input.insert(0, item.get("target", ""))
            self.gmaps_cap.delete(0, "end")
            self.gmaps_cap.insert(0, str(item.get("target_count", 0)))
            self.select_frame("gmaps")
        elif engine == "2gis":
            self.twogis_city.delete(0, "end")
            self.twogis_city.insert(0, item.get("city_name", ""))
            self.twogis_query.delete(0, "end")
            self.twogis_query.insert(0, item.get("query_string", ""))
            self.twogis_cap.delete(0, "end")
            self.twogis_cap.insert(0, str(item.get("target_count", 0)))
            self.select_frame("2gis")
        
        self.write_log("Loaded from history. Ready to resume.")

    def _build_profile_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["profile"] = frame

        title = ctk.CTkLabel(frame, text="Developer", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(5, 10))

        card = ctk.CTkFrame(frame, fg_color=CARD_COLOR, border_width=2, border_color=NEON_PURPLE, corner_radius=15)
        card.pack(fill="both", expand=True, pady=10)

        # Profile Picture & Intro Row
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=20, pady=20)

        self.dev_avatar_lbl = ctk.CTkLabel(top_row, text="")
        self.dev_avatar_lbl.pack(side="left", padx=(0, 20))
        
        # Fetch the round avatar safely
        def fetch_dev_avatar():
            try:
                url = "https://ik.imagekit.io/Reinhart/reinhart.png?updatedAt=1747593545727"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                raw_data = urllib.request.urlopen(req, timeout=5).read()
                img = Image.open(BytesIO(raw_data)).convert("RGBA")
                size = (80, 80)
                img = img.resize(size, Image.Resampling.LANCZOS)
                
                mask = Image.new("L", size, 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0) + size, fill=255)
                
                output = Image.new("RGBA", size, (0, 0, 0, 0))
                output.paste(img, (0, 0), mask)
                
                new_img = ctk.CTkImage(light_image=output, dark_image=output, size=size)
                self.after(0, lambda: self.dev_avatar_lbl.configure(image=new_img))
            except Exception:
                pass
        threading.Thread(target=fetch_dev_avatar, daemon=True).start()

        info_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(info_frame, text="Reinhart aka Kiri", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w")
        ctk.CTkLabel(info_frame, text="Lead Developer", font=ctk.CTkFont(size=14), text_color=TEXT_GRAY).pack(anchor="w")
        
        quote = '"We do not do it because it\'s easy. We do it because we thought it would be easy."'
        ctk.CTkLabel(info_frame, text=quote, font=ctk.CTkFont(size=12, slant="italic"), text_color=NEON_PURPLE).pack(anchor="w", pady=(10, 0))

        # Links Section
        links_frame = ctk.CTkFrame(card, fg_color="transparent")
        links_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(links_frame, text="Connect & Portfolio", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", pady=(0, 10))

        links = [
            ("Portfolio", "reinhart.pages.dev", "https://reinhart.pages.dev"),
            ("Telegram", "@kiri0507", "https://t.me/kiri0507"),
            ("WhatsApp", "+1 (315) 370-1897", "https://wa.me/13153701897"),
            ("GitHub", "Reinhart-py", "https://github.com/Reinhart-py"),
            ("Twitter", "@reinhartDev", "https://x.com/reinhartDev"),
            ("Instagram", "@reinhart.dev", "https://www.instagram.com/reinhart.dev/"),
        ]

        for platform, handle, url in links:
            row = ctk.CTkFrame(links_frame, fg_color="transparent")
            row.pack(anchor="w", pady=4, fill="x")
            ctk.CTkLabel(row, text=platform, width=100, anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_GRAY).pack(side="left")
            lbl_link = ctk.CTkLabel(row, text=handle, text_color=NEON_PURPLE, cursor="hand2", font=ctk.CTkFont(size=12))
            lbl_link.pack(side="left")
            lbl_link.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

    def select_frame(self, name: str):
        for key, frame in self.frames.items():
            frame.pack_forget()
        self.frames[name].pack(expand=True, fill="both")

        for key, btn in self.nav_btns.items():
            btn.configure(fg_color=CARD_COLOR if key == name else "transparent")
            
        if name == "history":
            self.refresh_history()

    def write_log(self, message: str):
        self.after(0, self._thread_safe_log, message)

    def _thread_safe_log(self, message: str):
        self.sys_log.configure(state="normal")
        self.sys_log.insert("end", message + "\n")
        self.sys_log.see("end")
        self.sys_log.configure(state="disabled")

    def _start_gmaps(self):
        if self.is_running: return
        self.is_running = True
        self.gmaps_btn.configure(state="disabled")
        self.select_frame("dashboard")
        
        target = self.gmaps_input.get()
        cap = int(self.gmaps_cap.get()) if self.gmaps_cap.get().isdigit() else 0
        
        out_path = os.path.join(os.path.expanduser("~"), "Downloads", f"gmaps_leads.csv")
        out_path = self.resume_state.get("output_path", out_path)
        start_idx = self.resume_state.get("last_step", 0)
        
        self.write_log(f"Starting Google Maps scraper for: {target}")
        self.resume_state = {}
        
        def run_task():
            runner = GMapsRunner(target_input=target, output_path=out_path, start_index=start_idx, target_count=cap, ui_logger=self.write_log)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.after(0, lambda: self.gmaps_btn.configure(state="normal"))
                self.write_log("Finished.")

        threading.Thread(target=run_task, daemon=True).start()

    def _start_twogis(self):
        if self.is_running: return
        self.is_running = True
        self.twogis_btn.configure(state="disabled")
        self.select_frame("dashboard")
        
        city = self.twogis_city.get().strip().lower()
        query = self.twogis_query.get().strip()
        cap = int(self.twogis_cap.get()) if self.twogis_cap.get().isdigit() else 0
        
        out_path = os.path.join(os.path.expanduser("~"), "Downloads", f"2gis_leads.csv")
        out_path = self.resume_state.get("output_path", out_path)
        start_page = self.resume_state.get("last_step", 1)
        init_saved = self.resume_state.get("total_saved", 0)
        
        self.write_log(f"Starting 2GIS scraper for: {city} - {query}")
        self.resume_state = {}
        
        def run_task():
            class Config:
                engine = "2gis"
                city_name = city
                query_string = query
                country = "ae"
                output_path = out_path
                start_page = start_page
                initial_saved = init_saved
                target_count = cap
            
            runner = TwoGISRunner(config=Config(), ui_logger=self.write_log)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.after(0, lambda: self.twogis_btn.configure(state="normal"))
                self.write_log("Finished.")

        threading.Thread(target=run_task, daemon=True).start()
