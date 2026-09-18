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
from utils.paths import get_export_dir
from utils.security import get_saved_key, revoke_saved_key, save_key, verify_key_payload
from utils.state_manager import (
    clear_active_checkpoint,
    get_active_checkpoint,
    load_all_history,
)

ctk.set_appearance_mode("dark")

BG_COLOR = "#030204"
CARD_BG = "#08070B"
CARD_INNER = "#0D0B12"
NEON_PURPLE = "#A855F7"
NEON_PURPLE_GLOW = "#C084FC"
BORDER_HIGHLIGHT = "#3B0764"
HOVER_PURPLE = "#7E22CE"
TEXT_WHITE = "#FFFFFF"
TEXT_MUTED = "#9CA3AF"
ERROR_RED = "#EF4444"

class KiriApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kiri")
        self.geometry("860x540")
        self.minsize(800, 500)
        self.configure(fg_color=BG_COLOR)

        self._apply_native_window_icon()

        self.current_thread = None
        self.is_running = False
        self.resume_state = {}
        self.icons = {}
        self.license_info = {"owner": "", "expires": ""}

        self._load_network_icons()
        self._build_layout()
        self._build_auth_view()
        self._build_sidebar()
        self._build_dashboard()
        self._build_gmaps_view()
        self._build_2gis_view()
        self._build_history_view()
        self._build_developer_view()

        self.select_frame("auth")
        threading.Thread(target=self._auto_login, daemon=True).start()

    def _apply_native_window_icon(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_ico = os.path.join(base_dir, "images", "icon.ico")
            logo_png = os.path.join(base_dir, "images", "logo1.png")

            if os.name == "nt" and os.path.exists(icon_ico):
                self.iconbitmap(icon_ico)
            elif os.path.exists(logo_png):
                img = Image.open(logo_png)
                self.wm_iconphoto(True, ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))._light_image)
        except Exception:
            pass

    def _create_glossy_container(self, parent, border_glow=BORDER_HIGHLIGHT, inner_bg=CARD_INNER, padding=1):
        outer = ctk.CTkFrame(parent, fg_color=border_glow, corner_radius=16)
        inner = ctk.CTkFrame(outer, fg_color=inner_bg, corner_radius=15)
        inner.pack(fill="both", expand=True, padx=padding, pady=padding)
        return outer, inner

    def _load_network_icons(self):
        urls = {
            "telegram": "https://img.icons8.com/color/48/telegram-app.png",
            "whatsapp": "https://img.icons8.com/color/48/whatsapp--v1.png",
            "dashboard": "https://img.icons8.com/ios-filled/50/ffffff/dashboard.png",
            "gmaps": "https://img.icons8.com/ios-filled/50/ffffff/google-maps.png",
            "2gis": "https://img.icons8.com/ios-filled/50/ffffff/globe.png",
            "history": "https://img.icons8.com/ios-filled/50/ffffff/time-machine.png",
            "developer": "https://img.icons8.com/ios-filled/50/ffffff/user.png",
        }

        def fetch_payload():
            for name, url in urls.items():
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    raw = urllib.request.urlopen(req, timeout=3).read()
                    img = Image.open(BytesIO(raw)).convert("RGBA")
                    self.icons[name] = ctk.CTkImage(light_image=img, dark_image=img, size=(18, 18))

                    if hasattr(self, "nav_btns") and name in self.nav_btns:
                        self.after(0, lambda n=name: self.nav_btns[n].configure(image=self.icons[n]))
                    if hasattr(self, "contact_btns") and name in self.contact_btns:
                        self.after(0, lambda n=name: self.contact_btns[n].configure(image=self.icons[n]))
                except Exception:
                    pass

        threading.Thread(target=fetch_payload, daemon=True).start()

    def _auto_login(self):
        saved = get_saved_key()
        if saved:
            self.after(0, lambda: self.auth_status.configure(text="Checking license status...", text_color=TEXT_MUTED))
            res = verify_key_payload(saved)
            if res["passed"]:
                self.license_info = {"owner": res["owner"], "expires": res["expires"]}
                self.after(0, self._unlock_application)
                threading.Thread(target=self._license_guard_loop, args=(saved,), daemon=True).start()
            else:
                self.after(0, lambda: self.auth_status.configure(text=res["msg"], text_color=ERROR_RED))
                self.after(0, lambda: self.auth_btn.configure(state="normal"))

    def _license_guard_loop(self, key):
        while True:
            time.sleep(300)
            res = verify_key_payload(key)
            if not res["passed"]:
                self.after(0, self._lock_application)
                break
            else:
                self.license_info["expires"] = res["expires"]
                self.after(0, lambda: self.dash_exp_lbl.configure(text=f"Expires: {res['expires']}"))

    def _unlock_application(self):
        self.frames["auth"].grid_forget()
        self.sidebar_frame.grid()
        self.main_frame.grid()
        self.select_frame("dashboard")

        owner_tag = self.license_info["owner"].upper()
        self.user_display_lbl.configure(text=owner_tag)
        self.dash_owner_lbl.configure(text=owner_tag)
        self.dash_exp_lbl.configure(text=f"Expires: {self.license_info['expires']}")
        self.dev_user_lbl.configure(text=f"Licensed to: {self.license_info['owner']}")
        self.dev_exp_lbl.configure(text=f"Expiry: {self.license_info['expires']}")

        self._prompt_unfinished_recovery()

    def _lock_application(self):
        self.sidebar_frame.grid_remove()
        self.main_frame.grid_remove()
        self.select_frame("auth")
        self.auth_status.configure(text="License deactivated or expired.", text_color=ERROR_RED)
        self.auth_btn.configure(state="normal")

    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=190, corner_radius=0, fg_color=BG_COLOR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=20, fg_color=BG_COLOR)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frames = {}

    def _build_auth_view(self):
        frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.frames["auth"] = frame
        frame.grid_rowconfigure((0, 2), weight=1)
        frame.grid_columnconfigure((0, 2), weight=1)

        outer, inner = self._create_glossy_container(frame, border_glow=NEON_PURPLE, padding=2)
        outer.grid(row=1, column=1, ipadx=25, ipady=20)

        ctk.CTkLabel(inner, text="K I R I", font=ctk.CTkFont(size=28, weight="bold"), text_color=NEON_PURPLE_GLOW).pack(pady=(20, 4))
        ctk.CTkLabel(inner, text="Enterprise System Authentication", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(pady=(0, 20))

        self.auth_input = ctk.CTkEntry(inner, width=320, height=38, justify="center", show="•", fg_color=CARD_BG, border_color=BORDER_HIGHLIGHT, border_width=1, corner_radius=10)
        self.auth_input.pack(pady=5)

        self.auth_status = ctk.CTkLabel(inner, text="", font=ctk.CTkFont(size=11), text_color=ERROR_RED)
        self.auth_status.pack(pady=4)

        self.auth_btn = ctk.CTkButton(inner, text="Unlock Terminal", width=320, height=38, fg_color=NEON_PURPLE, hover_color=HOVER_PURPLE, font=ctk.CTkFont(weight="bold"), corner_radius=10, command=self._do_login)
        self.auth_btn.pack(pady=(8, 20))

        c_bar = ctk.CTkFrame(inner, fg_color="transparent")
        c_bar.pack(pady=(0, 10))
        ctk.CTkLabel(c_bar, text="Acquire verification key:", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(side="left", padx=8)

        self.contact_btns = {}
        tb = ctk.CTkButton(c_bar, text="", width=32, height=32, fg_color=CARD_BG, hover_color=BORDER_HIGHLIGHT, corner_radius=8, command=lambda: webbrowser.open("https://t.me/kiri0507"))
        tb.pack(side="left", padx=4)
        wb = ctk.CTkButton(c_bar, text="", width=32, height=32, fg_color=CARD_BG, hover_color=BORDER_HIGHLIGHT, corner_radius=8, command=lambda: webbrowser.open("https://wa.me/13153701897"))
        wb.pack(side="left", padx=4)

        self.contact_btns["telegram"] = tb
        self.contact_btns["whatsapp"] = wb

    def _do_login(self):
        key = self.auth_input.get().strip()
        if not key:
            return
        self.auth_btn.configure(state="disabled")
        self.auth_status.configure(text="Validating key on server...", text_color=TEXT_MUTED)

        def verify_task():
            res = verify_key_payload(key)
            if res["passed"]:
                save_key(key)
                self.license_info = {"owner": res["owner"], "expires": res["expires"]}
                self.after(0, self._unlock_application)
                threading.Thread(target=self._license_guard_loop, args=(key,), daemon=True).start()
            else:
                self.after(0, lambda: self.auth_status.configure(text=res["msg"], text_color=ERROR_RED))
                self.after(0, lambda: self.auth_btn.configure(state="normal"))

        threading.Thread(target=verify_task, daemon=True).start()

    def _build_sidebar(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logo_path = os.path.join(base_dir, "images", "logo1.png")
            logo_img = Image.open(logo_path).convert("RGBA")
            self.logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(64, 64))
        except Exception:
            empty = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            self.logo_ctk = ctk.CTkImage(light_image=empty, dark_image=empty, size=(64, 64))

        ctk.CTkLabel(self.sidebar_frame, image=self.logo_ctk, text="").grid(row=0, column=0, pady=(20, 2))

        self.user_display_lbl = ctk.CTkLabel(self.sidebar_frame, text="...", font=ctk.CTkFont(size=13, weight="bold"), text_color=NEON_PURPLE_GLOW)
        self.user_display_lbl.grid(row=1, column=0, pady=(0, 20))

        nav_buttons = [
            ("dashboard", " Dashboard"),
            ("gmaps", " Google Maps"),
            ("2gis", " 2GIS Global"),
            ("history", " History"),
            ("developer", " Developer"),
        ]

        self.nav_btns = {}
        for i, (key, text) in enumerate(nav_buttons):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                image=self.icons.get(key, None),
                fg_color="transparent",
                text_color=TEXT_WHITE,
                hover_color=CARD_BG,
                anchor="w",
                corner_radius=10,
                font=ctk.CTkFont(size=13),
                command=lambda k=key: self.select_frame(k),
            )
            btn.grid(row=i + 2, column=0, padx=12, pady=4, sticky="ew")
            self.nav_btns[key] = btn

    def _build_dashboard(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["dashboard"] = frame

        title = ctk.CTkLabel(frame, text="Telemetry & Overview", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_WHITE)
        title.grid(row=0, column=0, sticky="w", pady=(2, 12))

        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew")
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        history = load_all_history()
        total_leads = sum(h.get("total_saved", 0) for h in history)

        self._render_stat_metric(stats_frame, "Sessions", str(len(history)), 0)
        self._render_stat_metric(stats_frame, "Harvested", f"{total_leads:,}", 1)

        lic_outer, lic_inner = self._create_glossy_container(stats_frame, border_glow=BORDER_HIGHLIGHT, inner_bg=CARD_INNER, padding=1)
        lic_outer.grid(row=0, column=2, sticky="ew", padx=6)
        lic_inner.pack_propagate(False)
        ctk.CTkLabel(lic_inner, text="AUTHENTICATED NODE", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 0))
        self.dash_owner_lbl = ctk.CTkLabel(lic_inner, text="...", font=ctk.CTkFont(size=14, weight="bold"), text_color=NEON_PURPLE_GLOW)
        self.dash_owner_lbl.pack(anchor="w", padx=14)
        self.dash_exp_lbl = ctk.CTkLabel(lic_inner, text="Checking...", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.dash_exp_lbl.pack(anchor="w", padx=14)

        self.resume_banner_outer, self.resume_banner_inner = self._create_glossy_container(frame, border_glow=NEON_PURPLE, inner_bg=CARD_BG, padding=1)
        self.resume_banner_lbl = ctk.CTkLabel(self.resume_banner_inner, text="Checkpoint Detected: Interrupted session available.", font=ctk.CTkFont(size=12), text_color=TEXT_WHITE)
        self.resume_banner_lbl.pack(side="left", padx=15, pady=8)
        self.resume_banner_btn = ctk.CTkButton(self.resume_banner_inner, text="Resume Execution", width=120, height=28, fg_color=NEON_PURPLE, hover_color=HOVER_PURPLE, corner_radius=8, command=self._resume_active_checkpoint)
        self.resume_banner_btn.pack(side="right", padx=10, pady=6)
        self.resume_banner_dismiss = ctk.CTkButton(self.resume_banner_inner, text="Discard", width=60, height=28, fg_color=CARD_INNER, hover_color=BORDER_HIGHLIGHT, corner_radius=8, command=self._dismiss_active_checkpoint)
        self.resume_banner_dismiss.pack(side="right", padx=(0, 6), pady=6)

        log_outer, log_inner = self._create_glossy_container(frame, border_glow=BORDER_HIGHLIGHT, inner_bg=CARD_BG, padding=1)
        log_outer.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        frame.grid_rowconfigure(3, weight=1)

        header_row = ctk.CTkFrame(log_inner, fg_color="transparent")
        header_row.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(header_row, text="Console Stream", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(side="left")

        self.sys_log = ctk.CTkTextbox(log_inner, fg_color="transparent", text_color=TEXT_WHITE, font=ctk.CTkFont(family="Consolas", size=11))
        self.sys_log.pack(expand=True, fill="both", padx=8, pady=8)
        self.sys_log.configure(state="disabled")

    def _render_stat_metric(self, parent, title, value, col):
        outer, inner = self._create_glossy_container(parent, border_glow=BORDER_HIGHLIGHT, inner_bg=CARD_INNER, padding=1)
        outer.grid(row=0, column=col, sticky="ew", padx=6)
        inner.pack_propagate(False)

        lbl_val = ctk.CTkLabel(inner, text=value, font=ctk.CTkFont(size=24, weight="bold"), text_color=NEON_PURPLE_GLOW)
        lbl_val.pack(anchor="w", padx=14, pady=(8, 0))
        lbl_title = ctk.CTkLabel(inner, text=title.upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED)
        lbl_title.pack(anchor="w", padx=14)

    def _prompt_unfinished_recovery(self):
        active = get_active_checkpoint()
        if active and active.get("target"):
            target_text = str(active.get("target"))[:30]
            engine = str(active.get("engine", "Task")).upper()
            step = active.get("last_step", 1)
            self.resume_banner_lbl.configure(text=f"Recovery Ready: [{engine}] {target_text}... at step {step}")
            self.resume_banner_outer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        else:
            self.resume_banner_outer.grid_remove()

    def _dismiss_active_checkpoint(self):
        clear_active_checkpoint()
        self.resume_banner_outer.grid_remove()
        self.write_log("Pending recovery checkpoint discarded.")

    def _resume_active_checkpoint(self):
        active = get_active_checkpoint()
        if active:
            self._resume_task_record(active)
            self.resume_banner_outer.grid_remove()

    def _build_gmaps_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["gmaps"] = frame

        title = ctk.CTkLabel(frame, text="Google Maps Intelligence", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(2, 14))

        outer, inner = self._create_glossy_container(frame, border_glow=BORDER_HIGHLIGHT, inner_bg=CARD_BG, padding=1)
        outer.pack(fill="x")

        ctk.CTkLabel(inner, text="Target Query, Maps URL, or Source Dataset", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=18, pady=(16, 4))

        input_box = ctk.CTkFrame(inner, fg_color="transparent")
        input_box.pack(fill="x", padx=18)
        self.gmaps_input = ctk.CTkEntry(input_box, width=380, height=36, fg_color=CARD_INNER, border_color=BORDER_HIGHLIGHT, border_width=1, corner_radius=8)
        self.gmaps_input.pack(side="left", fill="x", expand=True)
        self.gmaps_input.insert(0, "Software in Business Bay")

        ctk.CTkButton(input_box, text="Browse", width=80, height=36, fg_color=CARD_INNER, border_color=NEON_PURPLE, border_width=1, hover_color=HOVER_PURPLE, corner_radius=8, command=self._select_batch_file).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(inner, text="Target Records Limit (0 = Unrestricted Pipeline)", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=18, pady=(14, 4))
        self.gmaps_cap = ctk.CTkEntry(inner, width=160, height=36, fg_color=CARD_INNER, border_color=BORDER_HIGHLIGHT, border_width=1, corner_radius=8)
        self.gmaps_cap.pack(anchor="w", padx=18, pady=(0, 18))
        self.gmaps_cap.insert(0, "1000")

        self.gmaps_btn = ctk.CTkButton(frame, text="Launch Ingestion Matrix", height=40, fg_color=NEON_PURPLE, hover_color=HOVER_PURPLE, font=ctk.CTkFont(weight="bold"), corner_radius=10, command=self._execute_gmaps_pipeline)
        self.gmaps_btn.pack(anchor="w", pady=18)

    def _select_batch_file(self):
        selected = ctk.filedialog.askopenfilename(filetypes=[("Data Files", "*.csv *.xlsx *.txt")])
        if selected:
            self.gmaps_input.delete(0, "end")
            self.gmaps_input.insert(0, selected)

    def _build_2gis_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["2gis"] = frame

        title = ctk.CTkLabel(frame, text="2GIS Regional Scraper", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(2, 14))

        outer, inner = self._create_glossy_container(frame, border_glow=BORDER_HIGHLIGHT, inner_bg=CARD_BG, padding=1)
        outer.pack(fill="x")

        ctk.CTkLabel(inner, text="Target Municipality or Region", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=18, pady=(16, 4))
        self.twogis_city = ctk.CTkEntry(inner, width=380, height=36, fg_color=CARD_INNER, border_color=BORDER_HIGHLIGHT, border_width=1, corner_radius=8)
        self.twogis_city.pack(anchor="w", padx=18)
        self.twogis_city.insert(0, "Dubai")

        ctk.CTkLabel(inner, text="Directory Query Taxonomy", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=18, pady=(14, 4))
        self.twogis_query = ctk.CTkEntry(inner, width=380, height=36, fg_color=CARD_INNER, border_color=BORDER_HIGHLIGHT, border_width=1, corner_radius=8)
        self.twogis_query.pack(anchor="w", padx=18)
        self.twogis_query.insert(0, "Software")

        ctk.CTkLabel(inner, text="Target Records Limit", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=18, pady=(14, 4))
        self.twogis_cap = ctk.CTkEntry(inner, width=160, height=36, fg_color=CARD_INNER, border_color=BORDER_HIGHLIGHT, border_width=1, corner_radius=8)
        self.twogis_cap.pack(anchor="w", padx=18, pady=(0, 18))
        self.twogis_cap.insert(0, "2000")

        self.twogis_btn = ctk.CTkButton(frame, text="Launch Regional Mining", height=40, fg_color=NEON_PURPLE, hover_color=HOVER_PURPLE, font=ctk.CTkFont(weight="bold"), corner_radius=10, command=self._execute_twogis_pipeline)
        self.twogis_btn.pack(anchor="w", pady=18)

    def _build_history_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["history"] = frame

        title = ctk.CTkLabel(frame, text="Session Ledger & Checkpoints", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(2, 14))

        self.scroll_hist = ctk.CTkScrollableFrame(frame, fg_color="transparent", corner_radius=0)
        self.scroll_hist.pack(expand=True, fill="both")

    def refresh_history(self):
        for widget in self.scroll_hist.winfo_children():
            widget.destroy()

        history = load_all_history()
        if not history:
            ctk.CTkLabel(self.scroll_hist, text="No historic sessions logged in memory.", text_color=TEXT_MUTED).pack(pady=20)
            return

        for item in history:
            outer, inner = self._create_glossy_container(self.scroll_hist, border_glow=BORDER_HIGHLIGHT, inner_bg=CARD_BG, padding=1)
            outer.pack(fill="x", pady=4)

            eng = str(item.get("engine", "SYS")).upper()
            tgt = str(item.get("target", ""))[:42]
            svd = item.get("total_saved", 0)
            step = item.get("last_step", 1)

            info = ctk.CTkLabel(inner, text=f"[{eng}] {tgt} | Yield: {svd} | Checkpoint: {step}", font=ctk.CTkFont(size=12), text_color=TEXT_WHITE)
            info.pack(side="left", padx=14, pady=12)

            btn = ctk.CTkButton(inner, text="Restore", width=70, height=28, fg_color=CARD_INNER, border_width=1, border_color=NEON_PURPLE, hover_color=HOVER_PURPLE, corner_radius=6, command=lambda i=item: self._resume_task_record(i))
            btn.pack(side="right", padx=12)

    def _resume_task_record(self, item):
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
        self.write_log(f"Session state loaded: {item.get('target')}")

    def _build_developer_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["developer"] = frame

        title = ctk.CTkLabel(frame, text="Developer Dossier", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(2, 10))

        outer, inner = self._create_glossy_container(frame, border_glow=BORDER_HIGHLIGHT, inner_bg=CARD_BG, padding=1)
        outer.pack(fill="both", expand=True, pady=6)

        top_profile = ctk.CTkFrame(inner, fg_color="transparent")
        top_profile.pack(fill="x", padx=18, pady=(16, 12))

        self.dev_avatar_lbl = ctk.CTkLabel(top_profile, text="")
        self.dev_avatar_lbl.pack(side="left", padx=(0, 18))

        def fetch_round_avatar():
            try:
                url = "https://ik.imagekit.io/Reinhart/reinhart.png?updatedAt=1747593545727"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                raw = urllib.request.urlopen(req, timeout=5).read()
                img = Image.open(BytesIO(raw)).convert("RGBA")
                size = (72, 72)
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
        threading.Thread(target=fetch_round_avatar, daemon=True).start()

        meta_col = ctk.CTkFrame(top_profile, fg_color="transparent")
        meta_col.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(meta_col, text="Reinhart aka Kiri", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w")
        ctk.CTkLabel(meta_col, text="Lead Architect & Systems Engineer", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(anchor="w")

        quote = '"We do not do it because it\'s easy. We do it because we thought it would be easy."'
        ctk.CTkLabel(meta_col, text=quote, font=ctk.CTkFont(size=11, slant="italic"), text_color=NEON_PURPLE_GLOW).pack(anchor="w", pady=(6, 0))

        lic_info_box = ctk.CTkFrame(inner, fg_color=CARD_INNER, corner_radius=10)
        lic_info_box.pack(fill="x", padx=18, pady=(0, 12))

        self.dev_user_lbl = ctk.CTkLabel(lic_info_box, text="Licensed to: ...", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_WHITE)
        self.dev_user_lbl.pack(anchor="w", padx=14, pady=(8, 2))
        self.dev_exp_lbl = ctk.CTkLabel(lic_info_box, text="Expiry: ...", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.dev_exp_lbl.pack(anchor="w", padx=14, pady=(0, 8))

        ctk.CTkLabel(inner, text="Direct Inquiries & Portfolios", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=18, pady=(4, 6))

        channels = [
            ("Portfolio Portal", "reinhart.pages.dev", "https://reinhart.pages.dev"),
            ("Direct Wire (Telegram)", "@kiri0507", "https://t.me/kiri0507"),
            ("Encrypted Trunk (WhatsApp)", "+1 (315) 370-1897", "https://wa.me/13153701897"),
            ("Source Architecture (GitHub)", "Reinhart-py", "https://github.com/Reinhart-py"),
            ("Dispatch (Twitter/X)", "@reinhartDev", "https://x.com/reinhartDev"),
            ("Creative (Instagram)", "@reinhart.dev", "https://www.instagram.com/reinhart.dev/"),
        ]

        for label, val, link in channels:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(anchor="w", padx=18, pady=2, fill="x")
            ctk.CTkLabel(row, text=label, width=170, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(side="left")
            link_lbl = ctk.CTkLabel(row, text=val, text_color=NEON_PURPLE_GLOW, cursor="hand2", font=ctk.CTkFont(size=11))
            link_lbl.pack(side="left")
            link_lbl.bind("<Button-1>", lambda e, u=link: webbrowser.open(u))

        bot_ctrl = ctk.CTkFrame(inner, fg_color="transparent")
        bot_ctrl.pack(fill="x", padx=18, pady=(12, 12))
        ctk.CTkButton(bot_ctrl, text="Purge License & De-authenticate", height=30, fg_color=ERROR_RED, hover_color="#B91C1C", font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8, command=self._purge_session_keys).pack(side="left")

    def _purge_session_keys(self):
        revoke_saved_key()
        self._lock_application()

    def select_frame(self, name: str):
        for key, frame in self.frames.items():
            if name == "auth":
                frame.grid_forget()
            else:
                frame.pack_forget()

        if name == "auth":
            self.sidebar_frame.grid_remove()
            self.main_frame.grid_remove()
            self.frames[name].grid(row=0, column=0, columnspan=2, sticky="nsew")
        else:
            self.sidebar_frame.grid()
            self.main_frame.grid()
            self.frames[name].pack(expand=True, fill="both")

        for key, btn in self.nav_btns.items():
            btn.configure(fg_color=CARD_BG if key == name else "transparent")

        if name == "history":
            self.refresh_history()
        elif name == "dashboard":
            self._prompt_unfinished_recovery()

    def write_log(self, message: str):
        self.after(0, self._thread_safe_log, message)

    def _thread_safe_log(self, message: str):
        self.sys_log.configure(state="normal")
        self.sys_log.insert("end", message + "\n")
        self.sys_log.see("end")
        self.sys_log.configure(state="disabled")

    def _execute_gmaps_pipeline(self):
        if self.is_running:
            return
        self.is_running = True
        self.gmaps_btn.configure(state="disabled")
        self.select_frame("dashboard")

        target = self.gmaps_input.get().strip()
        cap_val = self.gmaps_cap.get().strip()
        cap = int(cap_val) if cap_val.isdigit() else 0

        out_path = str(get_export_dir() / "gmaps_extracted_leads.csv")
        out_path = self.resume_state.get("output_path", out_path)
        start_idx = self.resume_state.get("last_step", 0)

        self.write_log(f"Engaging Google Maps scraper for dataset: {target}")
        self.resume_state = {}

        def async_worker():
            runner = GMapsRunner(target_input=target, output_path=out_path, start_index=start_idx, target_count=cap, ui_logger=self.write_log)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.after(0, lambda: self.gmaps_btn.configure(state="normal"))
                self.write_log("Pipeline cycle completed.")
                self.after(0, self._prompt_unfinished_recovery)

        threading.Thread(target=async_worker, daemon=True).start()

    def _execute_twogis_pipeline(self):
        if self.is_running:
            return
        self.is_running = True
        self.twogis_btn.configure(state="disabled")
        self.select_frame("dashboard")

        city = self.twogis_city.get().strip().lower()
        query = self.twogis_query.get().strip()
        cap_val = self.twogis_cap.get().strip()
        cap = int(cap_val) if cap_val.isdigit() else 0

        out_path = str(get_export_dir() / "2gis_extracted_leads.csv")
        out_path = self.resume_state.get("output_path", out_path)
        start_page = self.resume_state.get("last_step", 1)
        init_saved = self.resume_state.get("total_saved", 0)

        self.write_log(f"Engaging 2GIS regional extractor for: {city} -> {query}")
        self.resume_state = {}

        def async_worker():
            class RuntimeConfig:
                engine = "2gis"
                city_name = city
                query_string = query
                country = "ae"
                output_path = out_path
                start_page = start_page
                initial_saved = init_saved
                target_count = cap

            runner = TwoGISRunner(config=RuntimeConfig(), ui_logger=self.write_log)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.after(0, lambda: self.twogis_btn.configure(state="normal"))
                self.write_log("Pipeline cycle completed.")
                self.after(0, self._prompt_unfinished_recovery)

        threading.Thread(target=async_worker, daemon=True).start()
