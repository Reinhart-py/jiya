import os
import threading
import time
import urllib.request
import webbrowser
from io import BytesIO

import customtkinter as ctk
from PIL import Image, ImageDraw

from gmaps.runner import GMapsRunner
from runner.runner import Runner as TwoGISRunner
from utils.state_manager import load_all_history
from utils.security import get_saved_key, verify_key_payload, save_key

ctk.set_appearance_mode("dark")

# ◈ NEON GLOSSY COLOR PALETTE ◈
BG_COLOR = "#050505"           # Deep pitch black
CARD_COLOR = "#0D0D0D"         # Inner card black
NEON_PURPLE = "#A855F7"        # Glowing shiny edge
HOVER_PURPLE = "#7E22CE"       # Button hovers
TEXT_WHITE = "#FFFFFF"
TEXT_GRAY = "#9CA3AF"
ERROR_RED = "#DC2626"

class KiriApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kiri")
        self.geometry("820x520")
        self.minsize(750, 480)
        self.configure(fg_color=BG_COLOR)
        
        # ◈ FIX: Set the OS Window Icon to your Logo ◈
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "icon.ico")
            if not os.path.exists(logo_path): logo_path = "images/icon.ico"
            self.iconbitmap(logo_path)
        except Exception:
            pass # Fallback if run on Linux/Mac where .ico isn't supported natively

        self.current_thread = None
        self.is_running = False
        self.resume_state = {}
        self.icons = {}
        self.license_info = {"owner": "", "expires": ""}

        self._load_ui_icons()
        self._build_layout()
        
        self._build_auth_view()
        self._build_sidebar()
        self._build_dashboard()
        self._build_gmaps_view()
        self._build_2gis_view()
        self._build_history_view()
        self._build_profile_view()

        # Start by showing the authentication lock screen
        self.sidebar_frame.grid_remove()
        self.main_frame.grid_remove()
        self.select_frame("auth")
        
        # Auto-verify saved key on startup
        threading.Thread(target=self._auto_login, daemon=True).start()

    def _auto_login(self):
        saved = get_saved_key()
        if saved:
            self.after(0, lambda: self.auth_status.configure(text="Verifying key...", text_color=TEXT_GRAY))
            res = verify_key_payload(saved)
            if res["passed"]:
                self.license_info = {"owner": res["owner"], "expires": res.get("expires", "Active")}
                self.after(0, self._unlock_app)
                # Start Heartbeat checking
                threading.Thread(target=self._license_heartbeat, args=(saved,), daemon=True).start()
            else:
                self.after(0, lambda: self.auth_status.configure(text=res["msg"], text_color=ERROR_RED))
                self.after(0, lambda: self.auth_btn.configure(state="normal"))

    def _license_heartbeat(self, key):
        """Continuously checks server every 10 minutes to kill app if key expires"""
        while True:
            time.sleep(600) # 10 mins
            res = verify_key_payload(key)
            if not res["passed"]:
                self.after(0, self._lock_app)
                break

    def _unlock_app(self):
        self.frames["auth"].grid_forget()
        self.sidebar_frame.grid()
        self.main_frame.grid()
        self.select_frame("dashboard")
        
        # Update UI with license owner
        self.user_display_lbl.configure(text=self.license_info["owner"].upper())
        self.dash_owner_lbl.configure(text=self.license_info["owner"])
        self.dash_exp_lbl.configure(text=self.license_info["expires"])

    def _lock_app(self):
        self.sidebar_frame.grid_remove()
        self.main_frame.grid_remove()
        self.select_frame("auth")
        self.auth_status.configure(text="Session expired or key revoked.", text_color=ERROR_RED)
        self.auth_btn.configure(state="normal")

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

    def _create_shiny_card(self, parent, padding=2):
        """Creates a smooth glowing border by stacking frames"""
        outer = ctk.CTkFrame(parent, fg_color=NEON_PURPLE, corner_radius=15)
        inner = ctk.CTkFrame(outer, fg_color=CARD_COLOR, corner_radius=14)
        inner.pack(fill="both", expand=True, padx=padding, pady=padding)
        return outer, inner

    def _load_ui_icons(self):
        urls = {
            "telegram": "https://img.icons8.com/color/48/telegram-app.png",
            "whatsapp": "https://img.icons8.com/color/48/whatsapp--v1.png",
            "dashboard": "https://img.icons8.com/ios-filled/50/ffffff/dashboard.png",
            "gmaps": "https://img.icons8.com/ios-filled/50/ffffff/google-maps.png",
            "2gis": "https://img.icons8.com/ios-filled/50/ffffff/globe.png",
            "history": "https://img.icons8.com/ios-filled/50/ffffff/time-machine.png",
            "profile": "https://img.icons8.com/ios-filled/50/ffffff/user.png"
        }
        def fetch():
            for name, url in urls.items():
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    raw_data = urllib.request.urlopen(req, timeout=3).read()
                    img = Image.open(BytesIO(raw_data)).convert("RGBA")
                    self.icons[name] = ctk.CTkImage(light_image=img, dark_image=img, size=(20, 20))
                    
                    if hasattr(self, 'nav_btns') and name in self.nav_btns:
                        self.after(0, lambda n=name: self.nav_btns[n].configure(image=self.icons[n]))
                    if hasattr(self, 'contact_btns') and name in self.contact_btns:
                        self.after(0, lambda n=name: self.contact_btns[n].configure(image=self.icons[n]))
                except Exception:
                    pass
        threading.Thread(target=fetch, daemon=True).start()

    def _build_auth_view(self):
        frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.frames["auth"] = frame
        frame.grid_rowconfigure((0, 3), weight=1)
        frame.grid_columnconfigure(0, weight=1)

        outer, inner = self._create_shiny_card(frame, padding=2)
        outer.grid(row=1, column=0, ipadx=20, ipady=20)

        ctk.CTkLabel(inner, text="KIRI ENGINE", font=ctk.CTkFont(size=24, weight="bold"), text_color=NEON_PURPLE).pack(pady=(20, 5))
        ctk.CTkLabel(inner, text="Enter License Key to proceed", text_color=TEXT_GRAY).pack(pady=(0, 15))

        self.auth_input = ctk.CTkEntry(inner, width=280, justify="center", show="•", fg_color=BG_COLOR, border_color=NEON_PURPLE)
        self.auth_input.pack(pady=10)

        self.auth_status = ctk.CTkLabel(inner, text="", text_color=ERROR_RED, font=ctk.CTkFont(size=11))
        self.auth_status.pack()

        self.auth_btn = ctk.CTkButton(inner, text="Authenticate", fg_color=NEON_PURPLE, hover_color=HOVER_PURPLE, command=self._do_login)
        self.auth_btn.pack(pady=15)

        # Contact Bar
        c_bar = ctk.CTkFrame(inner, fg_color="transparent")
        c_bar.pack(pady=(10, 5))
        ctk.CTkLabel(c_bar, text="No key?", text_color=TEXT_GRAY, font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
        
        self.contact_btns = {}
        tb = ctk.CTkButton(c_bar, text="", width=30, fg_color="transparent", hover_color=CARD_COLOR, command=lambda: webbrowser.open("https://t.me/kiri0507"))
        tb.pack(side="left", padx=5)
        wb = ctk.CTkButton(c_bar, text="", width=30, fg_color="transparent", hover_color=CARD_COLOR, command=lambda: webbrowser.open("https://wa.me/13153701897"))
        wb.pack(side="left", padx=5)
        
        self.contact_btns["telegram"] = tb
        self.contact_btns["whatsapp"] = wb

    def _do_login(self):
        key = self.auth_input.get().strip()
        if not key: return
        self.auth_btn.configure(state="disabled")
        self.auth_status.configure(text="Connecting to Mothership...", text_color=TEXT_GRAY)
        
        def run_auth():
            res = verify_key_payload(key)
            if res["passed"]:
                save_key(key)
                self.license_info = {"owner": res["owner"], "expires": res.get("expires", "Active")}
                self.after(0, self._unlock_app)
                threading.Thread(target=self._license_heartbeat, args=(key,), daemon=True).start()
            else:
                self.after(0, lambda: self.auth_status.configure(text=res["msg"], text_color=ERROR_RED))
                self.after(0, lambda: self.auth_btn.configure(state="normal"))
        
        threading.Thread(target=run_auth, daemon=True).start()

    def _build_sidebar(self):
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "logo1.png")
            if not os.path.exists(logo_path): logo_path = "images/logo1.png"
            logo_img = Image.open(logo_path).convert("RGBA")
            self.logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(70, 70))
        except Exception:
            logo_img = Image.new("RGBA", (70, 70), (0, 0, 0, 0))
            self.logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(70, 70))

        logo_lbl = ctk.CTkLabel(self.sidebar_frame, image=self.logo_ctk, text="")
        logo_lbl.grid(row=0, column=0, pady=(20, 0))

        # Show License Owner dynamically
        self.user_display_lbl = ctk.CTkLabel(self.sidebar_frame, text="...", font=ctk.CTkFont(size=14, weight="bold"), text_color=NEON_PURPLE)
        self.user_display_lbl.grid(row=1, column=0, pady=(0, 25))

        nav_buttons = [
            ("dashboard", " Dashboard"),
            ("gmaps", " Google Maps"),
            ("2gis", " 2GIS Global"),
            ("history", " History"),
            ("profile", " Settings"),
        ]

        self.nav_btns = {}
        for i, (key, text) in enumerate(nav_buttons):
            btn = ctk.CTkButton(
                self.sidebar_frame, text=text, fg_color="transparent",
                text_color=TEXT_WHITE, hover_color=CARD_COLOR, anchor="w",
                corner_radius=12, font=ctk.CTkFont(size=13),
                command=lambda k=key: self.select_frame(k)
            )
            btn.grid(row=i+2, column=0, padx=15, pady=4, sticky="ew")
            self.nav_btns[key] = btn

    def _build_dashboard(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["dashboard"] = frame

        title = ctk.CTkLabel(frame, text="Dashboard", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_WHITE)
        title.grid(row=0, column=0, sticky="w", pady=(5, 15))

        # Top Stats
        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew")
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        history = load_all_history()
        total_leads = sum(h.get("total_saved", 0) for h in history)

        self._create_stat_card(stats_frame, "Total Sessions", str(len(history)), 0)
        self._create_stat_card(stats_frame, "Leads Saved", f"{total_leads:,}", 1)
        
        # License Card
        lic_outer, lic_inner = self._create_shiny_card(stats_frame, 1)
        lic_outer.grid(row=0, column=2, sticky="ew", padx=8)
        lic_inner.pack_propagate(False)
        ctk.CTkLabel(lic_inner, text="License Info", font=ctk.CTkFont(size=11), text_color=TEXT_GRAY).pack(anchor="w", padx=15, pady=(10, 0))
        self.dash_owner_lbl = ctk.CTkLabel(lic_inner, text="...", font=ctk.CTkFont(size=14, weight="bold"), text_color=NEON_PURPLE)
        self.dash_owner_lbl.pack(anchor="w", padx=15)
        self.dash_exp_lbl = ctk.CTkLabel(lic_inner, text="...", font=ctk.CTkFont(size=11), text_color=TEXT_GRAY)
        self.dash_exp_lbl.pack(anchor="w", padx=15)

        # Log Output (Shiny Border)
        log_outer, log_inner = self._create_shiny_card(frame, 2)
        log_outer.grid(row=2, column=0, sticky="nsew", pady=15)
        frame.grid_rowconfigure(2, weight=1)

        lbl = ctk.CTkLabel(log_inner, text="Log Output", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_GRAY)
        lbl.pack(anchor="w", padx=15, pady=(10, 0))

        self.sys_log = ctk.CTkTextbox(log_inner, fg_color="transparent", text_color=TEXT_WHITE, font=ctk.CTkFont(size=12))
        self.sys_log.pack(expand=True, fill="both", padx=10, pady=10)
        self.sys_log.configure(state="disabled")

    def _create_stat_card(self, parent, title, value, col):
        outer, inner = self._create_shiny_card(parent, 2)
        outer.grid(row=0, column=col, sticky="ew", padx=8)
        inner.pack_propagate(False)

        lbl_val = ctk.CTkLabel(inner, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color=NEON_PURPLE)
        lbl_val.pack(anchor="w", padx=15, pady=(10, 0))
        lbl_title = ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=12), text_color=TEXT_GRAY)
        lbl_title.pack(anchor="w", padx=15)

    def _build_gmaps_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["gmaps"] = frame

        title = ctk.CTkLabel(frame, text="Google Maps", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(5, 15))

        outer, inner = self._create_shiny_card(frame, 2)
        outer.pack(fill="x")

        ctk.CTkLabel(inner, text="Search Query / Maps URL / Batch File", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", padx=20)
        self.gmaps_input = ctk.CTkEntry(row, width=320, fg_color=BG_COLOR, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.gmaps_input.pack(side="left")
        
        ctk.CTkButton(row, text="Browse", width=80, fg_color=BG_COLOR, border_color=NEON_PURPLE, border_width=1, hover_color=HOVER_PURPLE, command=self._browse_file).pack(side="left", padx=10)

        ctk.CTkLabel(inner, text="Total Leads to Save (0 for unlimited)", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.gmaps_cap = ctk.CTkEntry(inner, width=150, fg_color=BG_COLOR, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.gmaps_cap.pack(anchor="w", padx=20, pady=(0, 20))
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

        outer, inner = self._create_shiny_card(frame, 2)
        outer.pack(fill="x")

        ctk.CTkLabel(inner, text="City Name", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_city = ctk.CTkEntry(inner, width=320, fg_color=BG_COLOR, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.twogis_city.pack(anchor="w", padx=20)
        self.twogis_city.insert(0, "Dubai")

        ctk.CTkLabel(inner, text="Search Keyword", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_query = ctk.CTkEntry(inner, width=320, fg_color=BG_COLOR, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.twogis_query.pack(anchor="w", padx=20)
        self.twogis_query.insert(0, "Software")

        ctk.CTkLabel(inner, text="Total Leads to Save", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(15, 5))
        self.twogis_cap = ctk.CTkEntry(inner, width=150, fg_color=BG_COLOR, border_width=1, border_color=BORDER_HIGHLIGHT, corner_radius=8)
        self.twogis_cap.pack(anchor="w", padx=20, pady=(0, 20))
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

    def refresh_history(self):
        for widget in self.scroll_hist.winfo_children():
            widget.destroy()

        history = load_all_history()
        if not history:
            ctk.CTkLabel(self.scroll_hist, text="No history found.", text_color=TEXT_GRAY).pack(pady=20)
            return

        for idx, item in enumerate(history):
            outer, inner = self._create_shiny_card(self.scroll_hist, 1)
            outer.pack(fill="x", pady=5)
            
            eng = str(item.get("engine", "")).upper()
            tgt = str(item.get("target", ""))[:35]
            svd = item.get("total_saved", 0)
            step = item.get("last_step", 1)

            info = ctk.CTkLabel(inner, text=f"[{eng}] {tgt}  |  {svd} Leads  |  Step {step}", font=ctk.CTkFont(size=12), text_color=TEXT_WHITE)
            info.pack(side="left", padx=15, pady=15)

            btn = ctk.CTkButton(inner, text="Resume", width=70, fg_color=BG_COLOR, border_width=1, border_color=NEON_PURPLE, hover_color=HOVER_PURPLE, command=lambda i=item: self._resume_task(i))
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

        title = ctk.CTkLabel(frame, text="Settings & License", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(5, 10))

        outer, inner = self._create_shiny_card(frame, 2)
        outer.pack(fill="both", expand=True, pady=10)

        # Revoke Key Action
        ctk.CTkLabel(inner, text="License Management", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkButton(inner, text="Deactivate & Log Out", fg_color=ERROR_RED, hover_color="#991B1B", command=self._logout).pack(anchor="w", padx=20, pady=(0, 20))

        ctk.CTkLabel(inner, text="Contact Developer", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(10, 10))
        
        links = [
            ("Portfolio", "reinhart.pages.dev", "https://reinhart.pages.dev"),
            ("Telegram", "@kiri0507", "https://t.me/kiri0507"),
            ("WhatsApp", "+1 (315) 370-1897", "https://wa.me/13153701897"),
            ("GitHub", "Reinhart-py", "https://github.com/Reinhart-py"),
        ]

        for platform, handle, url in links:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(anchor="w", padx=20, pady=2, fill="x")
            ctk.CTkLabel(row, text=platform, width=100, anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_GRAY).pack(side="left")
            lbl_link = ctk.CTkLabel(row, text=handle, text_color=NEON_PURPLE, cursor="hand2", font=ctk.CTkFont(size=12))
            lbl_link.pack(side="left")
            lbl_link.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

    def _logout(self):
        try: os.remove("license.key")
        except: pass
        self._lock_app()

    def select_frame(self, name: str):
        for key, frame in self.frames.items():
            frame.grid_forget() if name == "auth" else frame.pack_forget()
        
        if name == "auth":
            self.frames[name].grid(row=0, column=0, sticky="nsew")
        else:
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
            try: runner.run()
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
            try: runner.run()
            finally:
                self.is_running = False
                self.after(0, lambda: self.twogis_btn.configure(state="normal"))
                self.write_log("Finished.")

        threading.Thread(target=run_task, daemon=True).start()
