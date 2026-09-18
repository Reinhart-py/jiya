import os
import threading
import webbrowser
from pathlib import Path
from typing import Callable

import customtkinter as ctk
from PIL import Image

from gmaps.runner import GMapsRunner
from runner.runner import Runner as TwoGISRunner
from utils.state_manager import load_all_history

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("green")

# UI Colors based on the provided reference
SIDEBAR_COLOR = "#0C1310"
SIDEBAR_HOVER = "#1B2722"
MAIN_BG_COLOR = "#F4F6F8"
CARD_BG_COLOR = "#FFFFFF"
TEXT_DARK = "#1E293B"
TEXT_LIGHT = "#F8FAFC"
ACCENT_COLOR = "#10B981"


def get_default_download_path(filename: str) -> str:
    downloads = Path.home() / "Downloads"
    return str(downloads / filename)


class JiyaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Jiya - B2B Lead Suite")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color=MAIN_BG_COLOR)

        self.current_thread = None
        self.is_running = False

        self._build_layout()
        self._build_sidebar()
        self._build_dashboard()
        self._build_gmaps_view()
        self._build_2gis_view()
        self._build_profile_view()

        self.select_frame("dashboard")

    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=SIDEBAR_COLOR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=MAIN_BG_COLOR)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frames = {}

    def _build_sidebar(self):
        logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text=" Jiya Suite", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color=ACCENT_COLOR
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(30, 30), sticky="w")

        nav_buttons = [
            ("dashboard", "Dashboard"),
            ("gmaps", "Google Maps Module"),
            ("2gis", "2GIS Module"),
            ("profile", "Developer Profile"),
        ]

        self.nav_btns = {}
        for i, (key, text) in enumerate(nav_buttons):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                fg_color="transparent",
                text_color=TEXT_LIGHT,
                hover_color=SIDEBAR_HOVER,
                anchor="w",
                font=ctk.CTkFont(size=14),
                command=lambda k=key: self.select_frame(k)
            )
            btn.grid(row=i+1, column=0, padx=15, pady=5, sticky="ew")
            self.nav_btns[key] = btn

        # Profile miniature at bottom
        self.bot_profile = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.bot_profile.grid(row=7, column=0, padx=15, pady=20, sticky="ew")
        
        user_lbl = ctk.CTkLabel(self.bot_profile, text="Reinhart", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_LIGHT)
        user_lbl.grid(row=0, column=0, sticky="w")
        role_lbl = ctk.CTkLabel(self.bot_profile, text="Lead Architect", font=ctk.CTkFont(size=11), text_color="gray")
        role_lbl.grid(row=1, column=0, sticky="w")

    def _build_dashboard(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["dashboard"] = frame

        title = ctk.CTkLabel(frame, text="Dashboard", font=ctk.CTkFont(size=28, weight="bold"), text_color=TEXT_DARK)
        title.grid(row=0, column=0, sticky="w", pady=(0, 20))

        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew")
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        history = load_all_history()
        total_runs = len(history)
        total_leads = sum(h.get("total_saved", 0) for h in history)

        self._create_stat_card(stats_frame, "Total Sessions", str(total_runs), 0)
        self._create_stat_card(stats_frame, "Leads Harvested", f"{total_leads:,}", 1)
        self._create_stat_card(stats_frame, "System Status", "Idle", 2)

        log_frame = ctk.CTkFrame(frame, fg_color=CARD_BG_COLOR, corner_radius=12)
        log_frame.grid(row=2, column=0, sticky="nsew", pady=20)
        frame.grid_rowconfigure(2, weight=1)

        log_lbl = ctk.CTkLabel(log_frame, text="System Output", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_DARK)
        log_lbl.pack(anchor="w", padx=20, pady=(15, 5))

        self.sys_log = ctk.CTkTextbox(log_frame, fg_color="#F8FAFC", text_color="#334155", font=ctk.CTkFont(family="Consolas", size=12))
        self.sys_log.pack(expand=True, fill="both", padx=20, pady=(0, 20))
        self.sys_log.configure(state="disabled")

    def _create_stat_card(self, parent, title, value, col):
        card = ctk.CTkFrame(parent, fg_color=CARD_BG_COLOR, corner_radius=12, height=120)
        card.grid(row=0, column=col, sticky="ew", padx=10)
        card.pack_propagate(False)

        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=32, weight="bold"), text_color=TEXT_DARK)
        lbl_val.pack(anchor="w", padx=20, pady=(20, 0))
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14), text_color="gray")
        lbl_title.pack(anchor="w", padx=20)

    def _build_gmaps_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["gmaps"] = frame

        title = ctk.CTkLabel(frame, text="Google Maps Extraction", font=ctk.CTkFont(size=28, weight="bold"), text_color=TEXT_DARK)
        title.grid(row=0, column=0, sticky="w", pady=(0, 20))

        form = ctk.CTkFrame(frame, fg_color=CARD_BG_COLOR, corner_radius=12)
        form.grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(form, text="Search Query / Maps URL / Batch File Path", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.gmaps_input = ctk.CTkEntry(form, width=400)
        self.gmaps_input.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.gmaps_input.insert(0, "Software in Business Bay")

        ctk.CTkLabel(form, text="Target Leads Cap (0 for unlimited)", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")
        self.gmaps_cap = ctk.CTkEntry(form, width=150)
        self.gmaps_cap.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.gmaps_cap.insert(0, "1000")

        self.gmaps_btn = ctk.CTkButton(form, text="Initialize Scraper", fg_color=ACCENT_COLOR, hover_color="#059669", command=self._start_gmaps)
        self.gmaps_btn.grid(row=4, column=0, padx=20, pady=30, sticky="w")

    def _build_2gis_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["2gis"] = frame

        title = ctk.CTkLabel(frame, text="2GIS Extraction", font=ctk.CTkFont(size=28, weight="bold"), text_color=TEXT_DARK)
        title.grid(row=0, column=0, sticky="w", pady=(0, 20))

        form = ctk.CTkFrame(frame, fg_color=CARD_BG_COLOR, corner_radius=12)
        form.grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(form, text="Target Region (e.g. Dubai, Abu Dhabi)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.twogis_city = ctk.CTkEntry(form, width=300)
        self.twogis_city.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.twogis_city.insert(0, "Dubai")

        ctk.CTkLabel(form, text="Search Keyword (e.g. Clinics)", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")
        self.twogis_query = ctk.CTkEntry(form, width=300)
        self.twogis_query.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.twogis_query.insert(0, "Software")

        ctk.CTkLabel(form, text="Target Leads Cap", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=20, pady=(20, 5), sticky="w")
        self.twogis_cap = ctk.CTkEntry(form, width=150)
        self.twogis_cap.grid(row=1, column=1, padx=20, pady=5, sticky="w")
        self.twogis_cap.insert(0, "2000")

        self.twogis_btn = ctk.CTkButton(form, text="Initialize Scraper", fg_color=ACCENT_COLOR, hover_color="#059669", command=self._start_twogis)
        self.twogis_btn.grid(row=4, column=0, padx=20, pady=30, sticky="w")

    def _build_profile_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["profile"] = frame

        title = ctk.CTkLabel(frame, text="Developer Profile", font=ctk.CTkFont(size=28, weight="bold"), text_color=TEXT_DARK)
        title.grid(row=0, column=0, sticky="w", pady=(0, 20))

        card = ctk.CTkFrame(frame, fg_color=CARD_BG_COLOR, corner_radius=12)
        card.grid(row=1, column=0, sticky="nsew", ipadx=20, ipady=20)

        header = ctk.CTkLabel(card, text="Reinhart aka Kiri", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_DARK)
        header.pack(anchor="w", padx=20, pady=(20, 5))
        
        sub = ctk.CTkLabel(card, text="Lead Architect & Systems Engineer", font=ctk.CTkFont(size=14), text_color="gray")
        sub.pack(anchor="w", padx=20, pady=(0, 20))

        self.open_in_browser = ctk.BooleanVar(value=True)
        toggle = ctk.CTkSwitch(card, text="Open links directly in default browser", variable=self.open_in_browser, progress_color=ACCENT_COLOR)
        toggle.pack(anchor="w", padx=20, pady=(0, 20))

        links = [
            ("Portfolio", "@reinhart.dev", "https://reinhart.pages.dev"),
            ("Telegram", "@kiri0507", "https://t.me/kiri0507?text=Hello%20%2C%20i%20just%20saw%20your%20resume%20and%20came%20to%20ask%20about%20it"),
            ("WhatsApp", "+1 (315) 370-1897", "https://wa.me/13153701897?text=Hi%2C%20saw%20your%20resume%20Have%20a%20proposal%20for%20you"),
            ("GitHub", "Reinhart-py", "https://github.com/Reinhart-py"),
            ("X / Twitter", "@reinhartDev", "https://x.com/reinhartDev"),
            ("Instagram", "@reinhart.dev", "https://www.instagram.com/reinhart.dev/"),
        ]

        for platform, handle, url in links:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(anchor="w", padx=20, pady=5, fill="x")
            
            lbl_plat = ctk.CTkLabel(row, text=platform, width=100, anchor="w", font=ctk.CTkFont(weight="bold"))
            lbl_plat.pack(side="left")
            
            lbl_link = ctk.CTkLabel(row, text=handle, text_color=ACCENT_COLOR, cursor="hand2")
            lbl_link.pack(side="left")
            lbl_link.bind("<Button-1>", lambda e, u=url: self._handle_link(u))

    def _handle_link(self, url: str):
        if self.open_in_browser.get():
            webbrowser.open(url)
        else:
            self.write_log(f"Link requested: {url}")
            self.select_frame("dashboard")

    def select_frame(self, name: str):
        for key, frame in self.frames.items():
            frame.grid_forget()
        self.frames[name].grid(row=0, column=0, sticky="nsew")

        for key, btn in self.nav_btns.items():
            btn.configure(fg_color=SIDEBAR_HOVER if key == name else "transparent")

    def write_log(self, message: str):
        self.sys_log.configure(state="normal")
        self.sys_log.insert("end", message + "\n")
        self.sys_log.see("end")
        self.sys_log.configure(state="disabled")

    def _start_gmaps(self):
        if self.is_running:
            return
        self.is_running = True
        self.gmaps_btn.configure(state="disabled")
        self.select_frame("dashboard")
        
        target = self.gmaps_input.get()
        cap = int(self.gmaps_cap.get()) if self.gmaps_cap.get().isdigit() else 0
        dest = get_default_download_path(f"gmaps_{target.replace(' ', '_')}.csv")
        
        self.write_log(f"Initializing Google Maps Engine for target: {target}")
        
        def run_task():
            runner = GMapsRunner(target_input=target, output_path=dest, target_count=cap, ui_logger=self.write_log)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.gmaps_btn.configure(state="normal")
                self.write_log("Task complete or terminated.")

        self.current_thread = threading.Thread(target=run_task, daemon=True)
        self.current_thread.start()

    def _start_twogis(self):
        if self.is_running:
            return
        self.is_running = True
        self.twogis_btn.configure(state="disabled")
        self.select_frame("dashboard")
        
        city = self.twogis_city.get().strip().lower()
        query = self.twogis_query.get().strip()
        cap = int(self.twogis_cap.get()) if self.twogis_cap.get().isdigit() else 0
        dest = get_default_download_path(f"2gis_{city}_{query.replace(' ', '_')}.csv")
        
        self.write_log(f"Initializing 2GIS Engine for {city} - {query}")
        
        def run_task():
            class Config:
                engine = "2gis"
                city_name = city
                query_string = query
                country = "ae"
                output_path = dest
                start_page = 1
                initial_saved = 0
                target_count = cap
            
            runner = TwoGISRunner(config=Config(), ui_logger=self.write_log)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.twogis_btn.configure(state="normal")
                self.write_log("Task complete or terminated.")

        self.current_thread = threading.Thread(target=run_task, daemon=True)
        self.current_thread.start()
