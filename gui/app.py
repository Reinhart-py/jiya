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

BG_OBSIDIAN = "#07090E"
SIDEBAR_BG = "#0B0E17"
CARD_SLATE = "#101623"
CARD_INNER = "#151C2C"
CYAN_ACCENT = "#00F0FF"
CYAN_HOVER = "#00B8D4"
CYAN_BORDER = "#005566"
TEXT_WHITE = "#F8FAFC"
TEXT_SLATE = "#94A3B8"
ERROR_ROSE = "#F43F5E"

class KiriApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kiri")
        self.geometry("900x560")
        self.minsize(820, 500)
        self.configure(fg_color=BG_OBSIDIAN)

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

    def _create_cyan_container(self, parent, border_glow=CYAN_BORDER, inner_bg=CARD_INNER, padding=1):
        outer = ctk.CTkFrame(parent, fg_color=border_glow, corner_radius=14)
        inner = ctk.CTkFrame(outer, fg_color=inner_bg, corner_radius=13)
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
            self.after(0, lambda: self.auth_status.configure(text="Validating license signature...", text_color=TEXT_SLATE))
            res = verify_key_payload(saved)
            if res["passed"]:
                self.license_info = {"owner": res["owner"], "expires": res["expires"]}
                self.after(0, self._unlock_application)
                threading.Thread(target=self._license_guard_loop, args=(saved,), daemon=True).start()
            else:
                self.after(0, lambda: self.auth_status.configure(text=res["msg"], text_color=ERROR_ROSE))
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
                self.after(0, lambda: self.dash_exp_lbl.configure(text=f"Valid: {res['expires']}"))

    def _unlock_application(self):
        self.frames["auth"].grid_forget()
        self.sidebar_frame.grid()
        self.main_frame.grid()
        self.select_frame("dashboard")

        owner_tag = self.license_info["owner"].upper()
        self.user_display_lbl.configure(text=owner_tag)
        self.dash_owner_lbl.configure(text=owner_tag)
        self.dash_exp_lbl.configure(text=f"{self.license_info['expires']}")
        self.dev_user_lbl.configure(text=f"Licensee: {self.license_info['owner']}")
        self.dev_exp_lbl.configure(text=f"Term: {self.license_info['expires']}")

        self._prompt_unfinished_recovery()

    def _lock_application(self):
        self.sidebar_frame.grid_remove()
        self.main_frame.grid_remove()
        self.select_frame("auth")
        self.auth_status.configure(text="License session revoked or expired.", text_color=ERROR_ROSE)
        self.auth_btn.configure(state="normal")

    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=SIDEBAR_BG)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=16, fg_color=BG_OBSIDIAN)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frames = {}

    def _build_auth_view(self):
        frame = ctk.CTkFrame(self, fg_color=BG_OBSIDIAN)
        self.frames["auth"] = frame
        frame.grid_rowconfigure((0, 2), weight=1)
        frame.grid_columnconfigure((0, 2), weight=1)

        outer, inner = self._create_cyan_container(frame, border_glow=CYAN_ACCENT, inner_bg=CARD_SLATE, padding=2)
        outer.grid(row=1, column=1, ipadx=24, ipady=18)

        ctk.CTkLabel(inner, text="K I R I", font=ctk.CTkFont(size=26, weight="bold"), text_color=CYAN_ACCENT).pack(pady=(18, 4))
        ctk.CTkLabel(inner, text="Lead Mining Core Architecture", font=ctk.CTkFont(size=12), text_color=TEXT_SLATE).pack(pady=(0, 18))

        self.auth_input = ctk.CTkEntry(inner, width=300, height=36, justify="center", show="•", fg_color=CARD_INNER, border_color=CYAN_BORDER, border_width=1, corner_radius=8)
        self.auth_input.pack(pady=4)

        self.auth_status = ctk.CTkLabel(inner, text="", font=ctk.CTkFont(size=11), text_color=ERROR_ROSE)
        self.auth_status.pack(pady=3)

        self.auth_btn = ctk.CTkButton(inner, text="Authorize System", width=300, height=36, fg_color=CYAN_ACCENT, hover_color=CYAN_HOVER, text_color=BG_OBSIDIAN, font=ctk.CTkFont(weight="bold"), corner_radius=8, command=self._do_login)
        self.auth_btn.pack(pady=(6, 18))

        c_bar = ctk.CTkFrame(inner, fg_color="transparent")
        c_bar.pack(pady=(0, 8))
        ctk.CTkLabel(c_bar, text="Direct Registration:", font=ctk.CTkFont(size=11), text_color=TEXT_SLATE).pack(side="left", padx=6)

        self.contact_btns = {}
        tb = ctk.CTkButton(c_bar, text="", width=30, height=30, fg_color=CARD_INNER, hover_color=CYAN_BORDER, corner_radius=6, command=lambda: webbrowser.open("https://t.me/kiri0507"))
        tb.pack(side="left", padx=3)
        wb = ctk.CTkButton(c_bar, text="", width=30, height=30, fg_color=CARD_INNER, hover_color=CYAN_BORDER, corner_radius=6, command=lambda: webbrowser.open("https://wa.me/13153701897"))
        wb.pack(side="left", padx=3)

        self.contact_btns["telegram"] = tb
        self.contact_btns["whatsapp"] = wb

    def _do_login(self):
        key = self.auth_input.get().strip()
        if not key:
            return
        self.auth_btn.configure(state="disabled")
        self.auth_status.configure(text="Authenticating...", text_color=TEXT_SLATE)

        def verify_task():
            res = verify_key_payload(key)
            if res["passed"]:
                save_key(key)
                self.license_info = {"owner": res["owner"], "expires": res["expires"]}
                self.after(0, self._unlock_application)
                threading.Thread(target=self._license_guard_loop, args=(key,), daemon=True).start()
            else:
                self.after(0, lambda: self.auth_status.configure(text=res["msg"], text_color=ERROR_ROSE))
                self.after(0, lambda: self.auth_btn.configure(state="normal"))

        threading.Thread(target=verify_task, daemon=True).start()

    def _build_sidebar(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logo_path = os.path.join(base_dir, "images", "logo1.png")
            logo_img = Image.open(logo_path).convert("RGBA")
            self.logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(56, 56))
        except Exception:
            empty = Image.new("RGBA", (56, 56), (0, 0, 0, 0))
            self.logo_ctk = ctk.CTkImage(light_image=empty, dark_image=empty, size=(56, 56))

        ctk.CTkLabel(self.sidebar_frame, image=self.logo_ctk, text="").grid(row=0, column=0, pady=(16, 2))

        self.user_display_lbl = ctk.CTkLabel(self.sidebar_frame, text="...", font=ctk.CTkFont(size=12, weight="bold"), text_color=CYAN_ACCENT)
        self.user_display_lbl.grid(row=1, column=0, pady=(0, 16))

        nav_buttons = [
            ("dashboard", " Dashboard"),
            ("gmaps", " Google Maps"),
            ("2gis", " 2GIS Global"),
            ("history", " Checkpoints"),
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
                hover_color=CARD_SLATE,
                anchor="w",
                corner_radius=8,
                font=ctk.CTkFont(size=12),
                command=lambda k=key: self.select_frame(k),
            )
            btn.grid(row=i + 2, column=0, padx=10, pady=3, sticky="ew")
            self.nav_btns[key] = btn

    def _build_dashboard(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["dashboard"] = frame

        title = ctk.CTkLabel(frame, text="Operations Console", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_WHITE)
        title.grid(row=0, column=0, sticky="w", pady=(2, 10))

        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew")
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        history = load_all_history()
        total_leads = sum(h.get("total_saved", 0) for h in history)

        self._render_stat_metric(stats_frame, "Sessions", str(len(history)), 0)
        self._render_stat_metric(stats_frame, "Leads Saved", f"{total_leads:,}", 1)

        lic_outer, lic_inner = self._create_cyan_container(stats_frame, border_glow=CYAN_BORDER, inner_bg=CARD_SLATE, padding=1)
        lic_outer.grid(row=0, column=2, sticky="ew", padx=5)
        lic_inner.pack_propagate(False)
        ctk.CTkLabel(lic_inner, text="KEY REGISTRATION", font=ctk.CTkFont(size=9, weight="bold"), text_color=TEXT_SLATE).pack(anchor="w", padx=12, pady=(8, 0))
        self.dash_owner_lbl = ctk.CTkLabel(lic_inner, text="...", font=ctk.CTkFont(size=13, weight="bold"), text_color=CYAN_ACCENT)
        self.dash_owner_lbl.pack(anchor="w", padx=12)
        self.dash_exp_lbl = ctk.CTkLabel(lic_inner, text="Validating...", font=ctk.CTkFont(size=10), text_color=TEXT_SLATE)
        self.dash_exp_lbl.pack(anchor="w", padx=12)

        self.resume_banner_outer, self.resume_banner_inner = self._create_cyan_container(frame, border_glow=CYAN_ACCENT, inner_bg=CARD_SLATE, padding=1)
        self.resume_banner_lbl = ctk.CTkLabel(self.resume_banner_inner, text="Active Checkpoint: Interrupted session available.", font=ctk.CTkFont(size=11), text_color=TEXT_WHITE)
        self.resume_banner_lbl.pack(side="left", padx=12, pady=6)
        self.resume_banner_btn = ctk.CTkButton(self.resume_banner_inner, text="Resume Immediately", width=130, height=26, fg_color=CYAN_ACCENT, hover_color=CYAN_HOVER, text_color=BG_OBSIDIAN, font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6, command=self._resume_active_checkpoint)
        self.resume_banner_btn.pack(side="right", padx=8, pady=5)
        self.resume_banner_dismiss = ctk.CTkButton(self.resume_banner_inner, text="Dismiss", width=50, height=26, fg_color=CARD_INNER, hover_color=CYAN_BORDER, font=ctk.CTkFont(size=11), corner_radius=6, command=self._dismiss_active_checkpoint)
        self.resume_banner_dismiss.pack(side="right", padx=(0, 4), pady=5)

        log_outer, log_inner = self._create_cyan_container(frame, border_glow=CYAN_BORDER, inner_bg=CARD_SLATE, padding=1)
        log_outer.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        frame.grid_rowconfigure(3, weight=1)

        header_row = ctk.CTkFrame(log_inner, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(header_row, text="Realtime Execution Terminal", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_SLATE).pack(side="left")

        self.sys_log = ctk.CTkTextbox(log_inner, fg_color="transparent", text_color=TEXT_WHITE, font=ctk.CTkFont(family="Consolas", size=11))
        self.sys_log.pack(expand=True, fill="both", padx=6, pady=6)
        self.sys_log.configure(state="disabled")

    def _render_stat_metric(self, parent, title, value, col):
        outer, inner = self._create_cyan_container(parent, border_glow=CYAN_BORDER, inner_bg=CARD_SLATE, padding=1)
        outer.grid(row=0, column=col, sticky="ew", padx=5)
        inner.pack_propagate(False)

        lbl_val = ctk.CTkLabel(inner, text=value, font=ctk.CTkFont(size=22, weight="bold"), text_color=CYAN_ACCENT)
        lbl_val.pack(anchor="w", padx=12, pady=(6, 0))
        lbl_title = ctk.CTkLabel(inner, text=title.upper(), font=ctk.CTkFont(size=9, weight="bold"), text_color=TEXT_SLATE)
        lbl_title.pack(anchor="w", padx=12)

    def _prompt_unfinished_recovery(self):
        active = get_active_checkpoint()
        if active and active.get("target"):
            tgt = str(active.get("target"))[:25]
            eng = str(active.get("engine", "SYS")).upper()
            step = active.get("last_step", 1)
            self.resume_banner_lbl.configure(text=f"Interrupted Session: [{eng}] {tgt}... (Step {step})")
            self.resume_banner_outer.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        else:
            self.resume_banner_outer.grid_remove()

    def _dismiss_active_checkpoint(self):
        clear_active_checkpoint()
        self.resume_banner_outer.grid_remove()
        self.write_log("Active checkpoint purged.")

    def _resume_active_checkpoint(self):
        active = get_active_checkpoint()
        if active:
            self.resume_banner_outer.grid_remove()
            self._execute_restored_session(active)

    def _execute_restored_session(self, item):
        self.resume_state = item
        engine = item.get("engine")
        self.select_frame("dashboard")

        if engine == "gmaps":
            self.write_log(f"Resuming Google Maps run: {item.get('target')} from Step {item.get('last_step', 0)}")
            self.gmaps_input.delete(0, "end")
            self.gmaps_input.insert(0, item.get("target", ""))
            self.gmaps_cap.delete(0, "end")
            self.gmaps_cap.insert(0, str(item.get("target_count", 0)))
            self._execute_gmaps_pipeline()
        elif engine == "2gis":
            self.write_log(f"Resuming 2GIS run: {item.get('city_name')} - {item.get('query_string')} from Page {item.get('last_step', 1)}")
            self.twogis_city.delete(0, "end")
            self.twogis_city.insert(0, item.get("city_name", ""))
            self.twogis_query.delete(0, "end")
            self.twogis_query.insert(0, item.get("query_string", ""))
            self.twogis_cap.delete(0, "end")
            self.twogis_cap.insert(0, str(item.get("target_count", 0)))
            self._execute_twogis_pipeline()

    def _build_gmaps_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["gmaps"] = frame

        title = ctk.CTkLabel(frame, text="Google Maps Intelligence", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(2, 12))

        outer, inner = self._create_cyan_container(frame, border_glow=CYAN_BORDER, inner_bg=CARD_SLATE, padding=1)
        outer.pack(fill="x")

        ctk.CTkLabel(inner, text="Target Search, Maps Web URL, or File Dataset", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=16, pady=(14, 4))

        input_box = ctk.CTkFrame(inner, fg_color="transparent")
        input_box.pack(fill="x", padx=16)
        self.gmaps_input = ctk.CTkEntry(input_box, width=360, height=34, fg_color=CARD_INNER, border_color=CYAN_BORDER, border_width=1, corner_radius=6)
        self.gmaps_input.pack(side="left", fill="x", expand=True)
        self.gmaps_input.insert(0, "Software in Business Bay")

        ctk.CTkButton(input_box, text="Browse", width=70, height=34, fg_color=CARD_INNER, border_color=CYAN_ACCENT, border_width=1, hover_color=CYAN_HOVER, text_color=TEXT_WHITE, corner_radius=6, command=self._select_batch_file).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(inner, text="Target Extraction Cap (0 = Continuous / Unlimited)", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=16, pady=(12, 4))
        self.gmaps_cap = ctk.CTkEntry(inner, width=150, height=34, fg_color=CARD_INNER, border_color=CYAN_BORDER, border_width=1, corner_radius=6)
        self.gmaps_cap.pack(anchor="w", padx=16, pady=(0, 16))
        self.gmaps_cap.insert(0, "1000")

        self.gmaps_btn = ctk.CTkButton(frame, text="Execute Target Run", height=38, fg_color=CYAN_ACCENT, hover_color=CYAN_HOVER, text_color=BG_OBSIDIAN, font=ctk.CTkFont(weight="bold"), corner_radius=8, command=self._execute_gmaps_pipeline)
        self.gmaps_btn.pack(anchor="w", pady=16)

    def _select_batch_file(self):
        selected = ctk.filedialog.askopenfilename(filetypes=[("Data Files", "*.csv *.xlsx *.txt")])
        if selected:
            self.gmaps_input.delete(0, "end")
            self.gmaps_input.insert(0, selected)

    def _build_2gis_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["2gis"] = frame

        title = ctk.CTkLabel(frame, text="2GIS Global Scraper", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(2, 12))

        outer, inner = self._create_cyan_container(frame, border_glow=CYAN_BORDER, inner_bg=CARD_SLATE, padding=1)
        outer.pack(fill="x")

        ctk.CTkLabel(inner, text="Target Emirate or Municipality", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=16, pady=(14, 4))
        self.twogis_city = ctk.CTkEntry(inner, width=360, height=34, fg_color=CARD_INNER, border_color=CYAN_BORDER, border_width=1, corner_radius=6)
        self.twogis_city.pack(anchor="w", padx=16)
        self.twogis_city.insert(0, "Dubai")

        ctk.CTkLabel(inner, text="Category Query Keyword", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=16, pady=(12, 4))
        self.twogis_query = ctk.CTkEntry(inner, width=360, height=34, fg_color=CARD_INNER, border_color=CYAN_BORDER, border_width=1, corner_radius=6)
        self.twogis_query.pack(anchor="w", padx=16)
        self.twogis_query.insert(0, "Software")

        ctk.CTkLabel(inner, text="Target Extraction Cap", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=16, pady=(12, 4))
        self.twogis_cap = ctk.CTkEntry(inner, width=150, height=34, fg_color=CARD_INNER, border_color=CYAN_BORDER, border_width=1, corner_radius=6)
        self.twogis_cap.pack(anchor="w", padx=16, pady=(0, 16))
        self.twogis_cap.insert(0, "2000")

        self.twogis_btn = ctk.CTkButton(frame, text="Execute Regional Run", height=38, fg_color=CYAN_ACCENT, hover_color=CYAN_HOVER, text_color=BG_OBSIDIAN, font=ctk.CTkFont(weight="bold"), corner_radius=8, command=self._execute_twogis_pipeline)
        self.twogis_btn.pack(anchor="w", pady=16)

    def _build_history_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["history"] = frame

        title = ctk.CTkLabel(frame, text="Extraction Checkpoints", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(2, 12))

        self.scroll_hist = ctk.CTkScrollableFrame(frame, fg_color="transparent", corner_radius=0)
        self.scroll_hist.pack(expand=True, fill="both")

    def refresh_history(self):
        for widget in self.scroll_hist.winfo_children():
            widget.destroy()

        history = load_all_history()
        if not history:
            ctk.CTkLabel(self.scroll_hist, text="No historic checkpoints recorded.", text_color=TEXT_SLATE).pack(pady=18)
            return

        for item in history:
            outer, inner = self._create_cyan_container(self.scroll_hist, border_glow=CYAN_BORDER, inner_bg=CARD_SLATE, padding=1)
            outer.pack(fill="x", pady=3)

            eng = str(item.get("engine", "SYS")).upper()
            tgt = str(item.get("target", ""))[:38]
            svd = item.get("total_saved", 0)
            step = item.get("last_step", 1)

            info = ctk.CTkLabel(inner, text=f"[{eng}] {tgt} | Yield: {svd} | Step: {step}", font=ctk.CTkFont(size=11), text_color=TEXT_WHITE)
            info.pack(side="left", padx=12, pady=10)

            btn = ctk.CTkButton(inner, text="Resume Run", width=90, height=26, fg_color=CARD_INNER, border_width=1, border_color=CYAN_ACCENT, hover_color=CYAN_HOVER, font=ctk.CTkFont(size=11), corner_radius=6, command=lambda i=item: self._execute_restored_session(i))
            btn.pack(side="right", padx=10)

    def _build_developer_view(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frames["developer"] = frame

        title = ctk.CTkLabel(frame, text="Developer Dossier", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_WHITE)
        title.pack(anchor="w", pady=(2, 8))

        outer, inner = self._create_cyan_container(frame, border_glow=CYAN_BORDER, inner_bg=CARD_SLATE, padding=1)
        outer.pack(fill="both", expand=True, pady=4)

        top_profile = ctk.CTkFrame(inner, fg_color="transparent")
        top_profile.pack(fill="x", padx=16, pady=(14, 10))

        self.dev_avatar_lbl = ctk.CTkLabel(top_profile, text="")
        self.dev_avatar_lbl.pack(side="left", padx=(0, 16))

        def fetch_round_avatar():
            try:
                url = "https://ik.imagekit.io/Reinhart/reinhart.png?updatedAt=1747593545727"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                raw = urllib.request.urlopen(req, timeout=5).read()
                img = Image.open(BytesIO(raw)).convert("RGBA")
                size = (68, 68)
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

        ctk.CTkLabel(meta_col, text="Reinhart aka Kiri", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w")
        ctk.CTkLabel(meta_col, text="Lead Systems Architect", font=ctk.CTkFont(size=11), text_color=TEXT_SLATE).pack(anchor="w")

        quote = '"We do not do it because it\'s easy. We do it because we thought it would be easy."'
        ctk.CTkLabel(meta_col, text=quote, font=ctk.CTkFont(size=10, slant="italic"), text_color=CYAN_ACCENT).pack(anchor="w", pady=(4, 0))

        lic_box = ctk.CTkFrame(inner, fg_color=CARD_INNER, corner_radius=8)
        lic_box.pack(fill="x", padx=16, pady=(0, 10))

        self.dev_user_lbl = ctk.CTkLabel(lic_box, text="Licensee: ...", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_WHITE)
        self.dev_user_lbl.pack(anchor="w", padx=12, pady=(6, 1))
        self.dev_exp_lbl = ctk.CTkLabel(lic_box, text="Expiry: ...", font=ctk.CTkFont(size=10), text_color=TEXT_SLATE)
        self.dev_exp_lbl.pack(anchor="w", padx=12, pady=(0, 6))

        ctk.CTkLabel(inner, text="Official Communication Trunks", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", padx=16, pady=(2, 4))

        channels = [
            ("Portfolio Portal", "reinhart.pages.dev", "https://reinhart.pages.dev"),
            ("Direct Channel (Telegram)", "@kiri0507", "https://t.me/kiri0507"),
            ("Priority Channel (WhatsApp)", "+1 (315) 370-1897", "https://wa.me/13153701897"),
            ("Repository (GitHub)", "Reinhart-py", "https://github.com/Reinhart-py"),
            ("Updates (Twitter/X)", "@reinhartDev", "https://x.com/reinhartDev"),
            ("Instagram", "@reinhart.dev", "https://www.instagram.com/reinhart.dev/"),
        ]

        for label, val, link in channels:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(anchor="w", padx=16, pady=1, fill="x")
            ctk.CTkLabel(row, text=label, width=170, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_SLATE).pack(side="left")
            link_lbl = ctk.CTkLabel(row, text=val, text_color=CYAN_ACCENT, cursor="hand2", font=ctk.CTkFont(size=11))
            link_lbl.pack(side="left")
            link_lbl.bind("<Button-1>", lambda e, u=link: webbrowser.open(u))

        bot_ctrl = ctk.CTkFrame(inner, fg_color="transparent")
        bot_ctrl.pack(fill="x", padx=16, pady=(10, 10))
        ctk.CTkButton(bot_ctrl, text="Purge License Token", height=28, fg_color=ERROR_ROSE, hover_color="#BE123C", font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6, command=self._purge_session_keys).pack(side="left")

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
            btn.configure(fg_color=CARD_SLATE if key == name else "transparent")

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

        self.write_log(f"Launching Google Maps worker for: {target}")
        self.resume_state = {}

        def async_worker():
            runner = GMapsRunner(target_input=target, output_path=out_path, start_index=start_idx, target_count=cap, ui_logger=self.write_log)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.after(0, lambda: self.gmaps_btn.configure(state="normal"))
                self.write_log("Execution finished.")
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

        self.write_log(f"Launching 2GIS worker for: {city} -> {query}")
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
                self.write_log("Execution finished.")
                self.after(0, self._prompt_unfinished_recovery)

        threading.Thread(target=async_worker, daemon=True).start()
