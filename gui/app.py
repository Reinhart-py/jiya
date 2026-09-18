import os
import threading
import urllib.request
import webbrowser
from io import BytesIO
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageDraw

from gmaps.runner import GMapsRunner
from runner.runner import Runner as TwoGISRunner
from utils.state_manager import load_all_history

ctk.set_appearance_mode("dark")

BG_VOID = "#070303"
SIDEBAR_GLASS = "#0F0505"
CARD_GLASS = "#170707"
ACCENT_BLOOD = "#B91C1C"
ACCENT_HOVER = "#991B1B"
BORDER_HIGHLIGHT = "#3A1010"
TEXT_PRIMARY = "#F8DFDF"
TEXT_MUTED = "#8B5A5A"

class JiyaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Jiya")
        self.geometry("850x550")
        self.resizable(False, False)
        self.configure(fg_color=BG_VOID)

        self.current_thread = None
        self.is_running = False
        self.resume_state = {}

        self._build_layout()
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

        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=SIDEBAR_GLASS)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=20, fg_color=BG_VOID)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frames = {}

    def _get_rounded_avatar(self, size=(60, 60)):
        try:
            url = "https://ik.imagekit.io/Reinhart/reinhart.png?updatedAt=1747593545727"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            raw_data = urllib.request.urlopen(req).read()
            img = Image.open(BytesIO(raw_data)).convert("RGBA")
        except Exception:
            img = Image.new("RGBA", size, (185, 28, 28, 255))
        
        img = img.resize(size, Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        
        output = Image.new("RGBA", size, (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)
        return ctk.CTkImage(light_image=output, dark_image=output, size=size)

    def _build_sidebar(self):
        self.avatar_img = self._get_rounded_avatar((50, 50))
        avatar_lbl = ctk.CTkLabel(self.sidebar_frame, image=self.avatar_img, text="")
        avatar_lbl.grid(row=0, column=0, pady=(25, 5))

        title_lbl = ctk.CTkLabel(self.sidebar_frame, text="JIYA SUITE", font=ctk.CTkFont(size=14, weight="bold", tracking=2), text_color=ACCENT_BLOOD)
        title_lbl.grid(row=1, column=0, pady=(0, 25))

        nav_buttons = [
            ("dashboard", "✦ Dashboard"),
            ("gmaps", "❖ Google Maps"),
            ("2gis", "❖ 2GIS Global"),
            ("history", "⟲ Vault / Resume"),
            ("profile", "◈ Developer"),
        ]

        self.nav_btns = {}
        for i, (key, text) in enumerate(nav_buttons):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                fg_color="transparent",
                text_color=TEXT_PRIMARY,
                hover_color=CARD_GLASS,
                anchor="w",
                corner_radius=8,
                font=ctk.CTkFont(size=13),
                command=lambda k=key: self.select_frame(k)
            )
            btn.grid(row=i+2, column=0, padx=15, pady=4, sticky="ew")
            self.nav_btns[key] = btn

    def _build_dashboard(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["dashboard"] = frame

        title = ctk.CTkLabel(frame, text="Command Center", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_PRIMARY)
        title.grid(row=0, column=0, sticky="w", pady=(5, 15))

        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew")
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        history = load_all_history()
        total_leads = sum(h.get("total_saved", 0) for h in history)

        self._create_stat_card(stats_frame, "Sessions", str(len(history)), 0)
        self._create_stat_card(stats_frame, "Total Leads", f"{total_leads:,}", 1)

        log_frame = ctk.CTkFrame(frame, fg_color=CARD_GLASS, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=15)
        log_frame.grid(row=2, column=0, sticky="nsew", pady=15)
        frame.grid_rowconfigure(2, weight=1)

        lbl = ctk.CTkLabel(log_frame, text="Terminal Output", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        lbl.pack(anchor="w", padx=15, pady=(10, 0))

        self.sys_log = ctk.CTkTextbox(log_frame, fg_color="transparent", text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Consolas", size=11))
        self.sys_log.pack(expand=True, fill="both", padx=10, pady=10)
        self.sys_log.configure(state="disabled")

    def _create_stat_card(self, parent, title, value, col):
        card = ctk.CTkFrame(parent, fg_color=CARD_GLASS, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=15, height=90)
        card.grid(row=0, column=col, sticky="ew", padx=5)
        card.pack_propagate(False)

        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color=ACCENT_BLOOD)
        lbl_val.pack(anchor="w", padx=15, pady=(10, 0))
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_title.pack(anchor="w", padx=15)

    def _build_gmaps_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["gmaps"] = frame

        title = ctk.CTkLabel(frame, text="Google Maps Intelligence", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_PRIMARY)
        title.pack(anchor="w", pady=(5, 15))

        form = ctk.CTkFrame(frame, fg_color=CARD_GLASS, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=15)
        form.pack(fill="x", ipady=10)

        ctk.CTkLabel(form, text="Search Query / Maps URL / Batch File", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=20)
        self.gmaps_input = ctk.CTkEntry(row, width=320, fg_color=BG_VOID, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.gmaps_input.pack(side="left")
        self.gmaps_input.insert(0, "Software in Business Bay")
        
        ctk.CTkButton(row, text="Browse", width=80, fg_color=BG_VOID, border_color=ACCENT_BLOOD, border_width=1, hover_color=SIDEBAR_GLASS, command=self._browse_file).pack(side="left", padx=10)

        ctk.CTkLabel(form, text="Target Leads Cap (0 for unlimited)", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.gmaps_cap = ctk.CTkEntry(form, width=150, fg_color=BG_VOID, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.gmaps_cap.pack(anchor="w", padx=20)
        self.gmaps_cap.insert(0, "1000")

        self.gmaps_btn = ctk.CTkButton(frame, text="Initiate Extraction", fg_color=ACCENT_BLOOD, hover_color=ACCENT_HOVER, corner_radius=8, command=self._start_gmaps)
        self.gmaps_btn.pack(anchor="w", pady=20)

    def _browse_file(self):
        filepath = ctk.filedialog.askopenfilename(filetypes=[("Data Files", "*.csv *.xlsx *.txt")])
        if filepath:
            self.gmaps_input.delete(0, "end")
            self.gmaps_input.insert(0, filepath)

    def _build_2gis_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["2gis"] = frame

        title = ctk.CTkLabel(frame, text="2GIS Directory Mining", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_PRIMARY)
        title.pack(anchor="w", pady=(5, 15))

        form = ctk.CTkFrame(frame, fg_color=CARD_GLASS, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=15)
        form.pack(fill="x", ipady=10)

        ctk.CTkLabel(form, text="Target Region", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_city = ctk.CTkEntry(form, width=320, fg_color=BG_VOID, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.twogis_city.pack(anchor="w", padx=20)
        self.twogis_city.insert(0, "Dubai")

        ctk.CTkLabel(form, text="Search Keyword", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_query = ctk.CTkEntry(form, width=320, fg_color=BG_VOID, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.twogis_query.pack(anchor="w", padx=20)
        self.twogis_query.insert(0, "Software")

        ctk.CTkLabel(form, text="Target Leads Cap", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_cap = ctk.CTkEntry(form, width=150, fg_color=BG_VOID, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.twogis_cap.pack(anchor="w", padx=20)
        self.twogis_cap.insert(0, "2000")

        self.twogis_btn = ctk.CTkButton(frame, text="Initiate Extraction", fg_color=ACCENT_BLOOD, hover_color=ACCENT_HOVER, corner_radius=8, command=self._start_twogis)
        self.twogis_btn.pack(anchor="w", pady=20)

    def _build_history_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["history"] = frame

        title = ctk.CTkLabel(frame, text="Vault Checkpoints", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_PRIMARY)
        title.pack(anchor="w", pady=(5, 15))

        self.scroll_hist = ctk.CTkScrollableFrame(frame, fg_color="transparent", corner_radius=0)
        self.scroll_hist.pack(expand=True, fill="both")
        self.refresh_history()

    def refresh_history(self):
        for widget in self.scroll_hist.winfo_children():
            widget.destroy()

        history = load_all_history()
        if not history:
            ctk.CTkLabel(self.scroll_hist, text="No checkpoints found.", text_color=TEXT_MUTED).pack(pady=20)
            return

        for idx, item in enumerate(history):
            card = ctk.CTkFrame(self.scroll_hist, fg_color=CARD_GLASS, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=12)
            card.pack(fill="x", pady=5)
            
            eng = str(item.get("engine", "")).upper()
            tgt = str(item.get("target", ""))[:40]
            svd = item.get("total_saved", 0)
            step = item.get("last_step", 1)

            info = ctk.CTkLabel(card, text=f"[{eng}] {tgt}  |  {svd} Leads  |  Step {step}", font=ctk.CTkFont(size=12), text_color=TEXT_PRIMARY)
            info.pack(side="left", padx=15, pady=15)

            btn = ctk.CTkButton(card, text="Resume", width=80, fg_color=BG_VOID, border_width=1, border_color=ACCENT_BLOOD, hover_color=SIDEBAR_GLASS, command=lambda i=item: self._resume_task(i))
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
        
        self.write_log("Checkpoint loaded. Ready for initiation.")

    def _build_profile_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["profile"] = frame

        title = ctk.CTkLabel(frame, text="Architect Protocol", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_PRIMARY)
        title.pack(anchor="w", pady=(5, 15))

        card = ctk.CTkFrame(frame, fg_color=CARD_GLASS, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=15)
        card.pack(fill="x", ipady=10)

        header = ctk.CTkLabel(card, text="Reinhart aka Kiri", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_PRIMARY)
        header.pack(anchor="w", padx=20, pady=(15, 2))
        
        sub = ctk.CTkLabel(card, text="Lead Architect & Systems Engineer", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED)
        sub.pack(anchor="w", padx=20, pady=(0, 15))

        self.open_in_browser = ctk.BooleanVar(value=True)
        toggle = ctk.CTkSwitch(card, text="Open links externally", variable=self.open_in_browser, progress_color=ACCENT_BLOOD, button_color=TEXT_PRIMARY, button_hover_color=TEXT_MUTED)
        toggle.pack(anchor="w", padx=20, pady=(0, 15))

        links = [
            ("Portfolio", "@reinhart.dev", "https://reinhart.pages.dev"),
            ("Telegram", "@kiri0507", "https://t.me/kiri0507?text=Hello%20%2C%20i%20just%20saw%20your%20resume%20and%20came%20to%20ask%20about%20it"),
            ("WhatsApp", "+1 (315) 370-1897", "https://wa.me/13153701897?text=Hi%2C%20saw%20your%20resume%20Have%20a%20proposal%20for%20you"),
            ("GitHub", "Reinhart-py", "https://github.com/Reinhart-py"),
            ("X / Twitter", "@reinhartDev", "https://x.com/reinhartDev"),
        ]

        for platform, handle, url in links:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(anchor="w", padx=20, pady=2, fill="x")
            lbl_plat = ctk.CTkLabel(row, text=platform, width=90, anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
            lbl_plat.pack(side="left")
            lbl_link = ctk.CTkLabel(row, text=handle, text_color=ACCENT_BLOOD, cursor="hand2", font=ctk.CTkFont(size=12))
            lbl_link.pack(side="left")
            lbl_link.bind("<Button-1>", lambda e, u=url: self._handle_link(u))

    def _handle_link(self, url: str):
        if self.open_in_browser.get():
            webbrowser.open(url)
        else:
            self.write_log(f"Hyperlink intercepted: {url}")
            self.select_frame("dashboard")

    def select_frame(self, name: str):
        for key, frame in self.frames.items():
            frame.pack_forget()
        self.frames[name].pack(expand=True, fill="both")

        for key, btn in self.nav_btns.items():
            btn.configure(fg_color=CARD_GLASS if key == name else "transparent")
            
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
        
        out_path = os.path.join(os.path.expanduser("~"), "Downloads", f"gmaps_{target.replace(' ', '_')[:20]}.csv")
        out_path = self.resume_state.get("output_path", out_path)
        start_idx = self.resume_state.get("last_step", 0)
        
        self.write_log(f"❖ GMAPS ENGINE IGNITED ❖ Target: {target}")
        self.resume_state = {}
        
        def run_task():
            runner = GMapsRunner(target_input=target, output_path=out_path, start_index=start_idx, target_count=cap, ui_logger=self.write_log)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.after(0, lambda: self.gmaps_btn.configure(state="normal"))
                self.write_log("Task complete or terminated.")

        threading.Thread(target=run_task, daemon=True).start()

    def _start_twogis(self):
        if self.is_running: return
        self.is_running = True
        self.twogis_btn.configure(state="disabled")
        self.select_frame("dashboard")
        
        city = self.twogis_city.get().strip().lower()
        query = self.twogis_query.get().strip()
        cap = int(self.twogis_cap.get()) if self.twogis_cap.get().isdigit() else 0
        
        out_path = os.path.join(os.path.expanduser("~"), "Downloads", f"2gis_{city}_{query.replace(' ', '_')[:20]}.csv")
        out_path = self.resume_state.get("output_path", out_path)
        start_page = self.resume_state.get("last_step", 1)
        init_saved = self.resume_state.get("total_saved", 0)
        
        self.write_log(f"❖ 2GIS ENGINE IGNITED ❖ Region: {city.upper()} | Query: {query}")
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
                self.write_log("Task complete or terminated.")

        threading.Thread(target=run_task, daemon=True).start()
