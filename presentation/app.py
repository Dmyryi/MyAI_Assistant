"""Main application GUI"""
import os
import threading
import io
import sys
import customtkinter as ctk
from typing import Optional
import subprocess
import platform
from PIL import Image, ImageTk
import cv2

from application.document_analysis_service import DocumentAnalysisService
from application.video_indexing_service import VideoIndexingService
from application.storage_service import StorageService
from infrastructure.google import OAuthService
from downloader import download_links
from infrastructure.localization import _, i18n

PALETTE = {
    "bg": "#0f1115",
    "surface": "#181b22",
    "surface_alt": "#1f232c",
    "card": "#242936",
    "primary": "#3b82f6",
    "primary_dark": "#2563eb",
    "accent": "#a855f7",
    "text": "#f5f7fb",
    "muted": "#9ba1b6",
    "border": "#2f3442",
    "danger": "#ef4444",
    "danger_hover": "#dc2626",
}

HEADING_FONT = ("Inter", 20, "bold")
BODY_FONT = ("Inter", 13)
MONO_FONT = ("JetBrains Mono", 11)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class ResultCard(ctk.CTkFrame):
    """Displays single search result"""
    
    def __init__(self, master, text_snippet, tags, filename, timecode, accuracy, meta, on_feedback, frame_path=None, video_segment=None, **kwargs):
        super().__init__(
            master,
            corner_radius=14,
            border_width=1,
            border_color=PALETTE["border"],
            fg_color=PALETTE["card"],
            **kwargs
        )
        self.meta = meta or {}
        self.on_feedback = on_feedback
        self.feedback_sent = False
        self.frame_path = frame_path
        self.video_segment = video_segment or {}
        
        self._build_ui(text_snippet, tags, filename, timecode, accuracy)
    
    def _build_ui(self, text_snippet, tags, filename, timecode, accuracy):
        """Builds UI component"""
        self.info_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=PALETTE["primary"], width=90)
        self.info_frame.pack(side="left", fill="y", padx=(5, 10), pady=5)
        
        self.lbl_time = ctk.CTkLabel(self.info_frame, text=timecode, font=("Inter", 18, "bold"), text_color="white")
        self.lbl_time.pack(pady=(15, 5))
        self.lbl_acc = ctk.CTkLabel(self.info_frame, text=f"{accuracy}%", font=("Inter", 12), text_color="#e2e8f0")
        self.lbl_acc.pack()

        if self.frame_path or self.video_segment:
            self.preview_frame = ctk.CTkFrame(self, corner_radius=8, fg_color=PALETTE["surface_alt"], width=160)
            self.preview_frame.pack(side="left", fill="y", padx=(0, 10), pady=5)
            self.preview_frame.pack_propagate(False)
            
            if self.video_segment.get("is_segment"):
                self._load_preview_video()
            else:
                self._load_preview_image()
        else:
            self.preview_frame = None

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        self.lbl_text = ctk.CTkLabel(
            self.content_frame,
            text=f"📜 \"{text_snippet}\"",
            font=("Inter", 13),
            text_color=PALETTE["text"],
            wraplength=520,
            justify="left",
            anchor="w"
        )
        self.lbl_text.pack(fill="x", pady=(5, 2))

        tags_str = f"[{tags}]" if tags else f"[{_('card_no_tags')}]"
        self.lbl_tags = ctk.CTkLabel(
            self.content_frame,
            text=f"{_('card_tags')} {tags_str}",
            font=MONO_FONT,
            text_color=PALETTE["accent"],
            wraplength=520,
            justify="left",
            anchor="w"
        )
        self.lbl_tags.pack(fill="x", pady=(0, 5))
        
        self.lbl_file = ctk.CTkLabel(
            self.content_frame,
            text=f"{_('card_file')} {filename}",
            font=MONO_FONT,
            text_color=PALETTE["muted"],
            anchor="w"
        )
        self.lbl_file.pack(fill="x")

        self.actions_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.actions_frame.pack(fill="x", pady=(8, 4))
        self.actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.feedback_label = ctk.CTkLabel(
            self.actions_frame,
            text=_("card_feedback_q"),
            font=("Inter", 11),
            text_color=PALETTE["muted"],
            anchor="w"
        )
        self.feedback_label.grid(row=0, column=0, sticky="w")

        self.btn_group = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        self.btn_group.grid(row=0, column=1, sticky="e")

        self.btn_like = ctk.CTkButton(
            self.btn_group,
            text=_("btn_like"),
            font=("Inter", 11, "bold"),
            width=110,
            height=30,
            fg_color="#22c55e",
            hover_color="#16a34a",
            command=lambda: self._send_feedback("positive")
        )
        self.btn_like.grid(row=0, column=0, padx=(0, 6))

        self.btn_dislike = ctk.CTkButton(
            self.btn_group,
            text=_("btn_dislike"),
            font=("Inter", 11, "bold"),
            width=100,
            height=30,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=lambda: self._send_feedback("negative")
        )
        self.btn_dislike.grid(row=0, column=1)
    
    def _load_preview_image(self):
        """Loads and displays frame preview"""
        if not self.frame_path or not self.preview_frame:
            return
        
        if not os.path.exists(self.frame_path):
            placeholder = ctk.CTkLabel(
                self.preview_frame,
                text=_("preview_placeholder"),
                font=("Inter", 11),
                text_color=PALETTE["muted"],
                justify="center"
            )
            placeholder.pack(expand=True, fill="both", padx=5, pady=5)
            return
        
        try:
            img = Image.open(self.frame_path)
            
            max_width, max_height = 160, 120
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            ctk_image = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(img.width, img.height)
            )
            
            self.preview_label = ctk.CTkLabel(
                self.preview_frame,
                image=ctk_image,
                text="",
                corner_radius=6
            )
            self.preview_label.pack(expand=True, fill="both", padx=5, pady=5)
            
            size_label = ctk.CTkLabel(
                self.preview_frame,
                text=f"{img.width}×{img.height}",
                font=("Inter", 9),
                text_color=PALETTE["muted"]
            )
            size_label.pack(pady=(0, 5))
            
            self.btn_view_full = ctk.CTkButton(
                self.preview_frame,
                text=_("btn_view_full"),
                font=("Inter", 10),
                height=24,
                width=140,
                fg_color=PALETTE["surface"],
                hover_color=PALETTE["border"],
                command=self._open_full_image
            )
            self.btn_view_full.pack(pady=(0, 5))
            
        except Exception as e:
            error_label = ctk.CTkLabel(
                self.preview_frame,
                text=_("preview_error", error=str(e)[:20]),
                font=("Inter", 10),
                text_color="#f87171",
                justify="center"
            )
            error_label.pack(expand=True, fill="both", padx=5, pady=5)
    
    def _load_preview_video(self):
        """Loads and displays video segment preview"""
        if not self.video_segment or not self.preview_frame:
            return
        
        video_filename = self.video_segment.get("filename")
        start_time = self.video_segment.get("start_time")
        end_time = self.video_segment.get("end_time")
        
        if not video_filename or start_time is None or end_time is None:
            if self.frame_path:
                self._load_preview_image()
            return
        
        video_path = None
        video_folder = "source_videos"
        possible_paths = [
            os.path.join(video_folder, video_filename),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), video_folder, video_filename),
            video_filename
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                video_path = path
                break
        
        if not video_path:
            if self.frame_path:
                self._load_preview_image()
            else:
                placeholder = ctk.CTkLabel(
                    self.preview_frame,
                    text=_("preview_placeholder"),
                    font=("Inter", 11),
                    text_color=PALETTE["muted"],
                    justify="center"
                )
                placeholder.pack(expand=True, fill="both", padx=5, pady=5)
            return
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise IOError("Не удалось открыть видео")
            
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            start_frame = int(start_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                raise ValueError("Не удалось прочитать кадр")
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            max_width, max_height = 160, 120
            h, w = frame_rgb.shape[:2]
            aspect_ratio = w / h
            if w > h:
                new_width = min(max_width, w)
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = min(max_height, h)
                new_width = int(new_height * aspect_ratio)
            
            frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
            
            img = Image.fromarray(frame_resized)
            
            ctk_image = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(new_width, new_height)
            )
            
            self.preview_label = ctk.CTkLabel(
                self.preview_frame,
                image=ctk_image,
                text="",
                corner_radius=6
            )
            self.preview_label.pack(expand=True, fill="both", padx=5, pady=5)
            
            video_indicator = ctk.CTkLabel(
                self.preview_frame,
                text="▶ Видео",
                font=("Inter", 9),
                text_color=PALETTE["primary"]
            )
            video_indicator.pack(pady=(0, 2))
            
            self.btn_play_video = ctk.CTkButton(
                self.preview_frame,
                text=_("btn_play_segment"),
                font=("Inter", 10),
                height=24,
                width=140,
                fg_color=PALETTE["primary"],
                hover_color=PALETTE["primary_dark"],
                command=self._play_video_segment
            )
            self.btn_play_video.pack(pady=(0, 5))
            
        except Exception as e:
            if self.frame_path:
                self._load_preview_image()
            else:
                error_label = ctk.CTkLabel(
                    self.preview_frame,
                    text=_("preview_error", error=str(e)[:20]),
                    font=("Inter", 10),
                    text_color="#f87171",
                    justify="center"
                )
                error_label.pack(expand=True, fill="both", padx=5, pady=5)
    
    def _play_video_segment(self):
        """Plays video segment in system video player"""
        if not self.video_segment:
            return
        
        video_filename = self.video_segment.get("filename")
        start_time = self.video_segment.get("start_time")
        end_time = self.video_segment.get("end_time")
        
        if not video_filename or start_time is None or end_time is None:
            return
        
        video_path = None
        video_folder = "source_videos"
        possible_paths = [
            os.path.join(video_folder, video_filename),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), video_folder, video_filename),
            video_filename
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                video_path = path
                break
        
        if not video_path:
            return
        
        try:
            vlc_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
                "vlc"
            ]
            
            vlc_found = False
            for vlc_path in vlc_paths:
                if os.path.exists(vlc_path) or vlc_path == "vlc":
                    try:
                        subprocess.Popen([
                            vlc_path,
                            f"--start-time={int(start_time)}",
                            f"--stop-time={int(end_time)}",
                            video_path
                        ])
                        vlc_found = True
                        break
                    except Exception:
                        continue
            
            if not vlc_found:
                try:
                    subprocess.Popen([
                        "mpv",
                        f"--start={start_time}",
                        f"--end={end_time}",
                        video_path
                    ])
                except Exception:
                    if platform.system() == 'Windows':
                        os.startfile(video_path)
                    elif platform.system() == 'Darwin':
                        subprocess.run(['open', video_path])
                    else:
                        subprocess.run(['xdg-open', video_path])
        except Exception:
            pass
    
    def _open_full_image(self):
        """Opens image in full size"""
        if not self.frame_path:
            return
        
        if not os.path.exists(self.frame_path):
            return
        
        try:
            if platform.system() == 'Windows':
                os.startfile(self.frame_path)
            elif platform.system() == 'Darwin':
                subprocess.run(['open', self.frame_path])
            else:
                subprocess.run(['xdg-open', self.frame_path])
        except Exception:
            pass

    def _send_feedback(self, value: str):
        """Sends feedback"""
        if self.feedback_sent:
            return
        if self.on_feedback and self.on_feedback(self.meta, value):
            self.feedback_sent = True
            self.btn_like.configure(state="disabled")
            self.btn_dislike.configure(state="disabled")
            self.feedback_label.configure(text=_("feedback_thanks"), text_color=PALETTE["text"])


class App(ctk.CTk):
    """Main application GUI"""
    
    def __init__(
        self,
        analysis_service: Optional[DocumentAnalysisService] = None,
        indexing_service: Optional[VideoIndexingService] = None,
        auth_service: Optional[OAuthService] = None,
        storage_service: Optional[StorageService] = None
    ):
        super().__init__()
        
        self.analysis_service = analysis_service
        self.indexing_service = indexing_service
        self.auth_service = auth_service
        self.storage_service = storage_service
        
        self._setup_window()
        self._initialize_state()
        
        if self.auth_service:
            self._setup_auth_callback()
            
        self._build_ui()
        self.update_storage_info()

    
    def _setup_window(self):
        """Window setup"""
        self.title(_("app_title"))
        self.geometry("1024x768")
        self.configure(fg_color=PALETTE["bg"])
        
        try:
            self.state("zoomed")
        except Exception:
            self.attributes("-zoomed", True)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.minsize(1200, 768)
    
    def _initialize_state(self):
        """State initialization"""
        self.stats_data = {"downloads": 0, "results": 0}
        self.total_results = 0
        self.total_downloads = 0
        self.token_file = "token.enc"
        self.download_progress_total = 0
        self._auth_thread_running = False
        self._current_doc_id = ""

    
    def _setup_auth_callback(self):
        """Sets up callback for receiving messages from OAuthService"""
        if not self.auth_service:
            return
        
        def auth_callback(msg_type: str, message: str):
            """Callback for receiving messages from OAuthService"""
            if msg_type == "status":
                self.after(0, lambda: self._set_status(message, PALETTE["text"]))
            elif msg_type == "log":
                self.after(0, lambda: self.log_message(message))
            elif msg_type == "error":
                self.after(0, lambda: self._set_status(f"❌ {message}", "#f87171"))
        
        self.auth_service.status_callback = auth_callback
    
    def change_language(self, new_lang_code: str):
        """Changes interface language and rebuilds GUI"""
        if new_lang_code == i18n.current_language:
            return

        self._current_doc_id = self.doc_entry.get()
        i18n.load_language(new_lang_code)
        self.title(_("app_title"))

        for widget in self.sidebar.winfo_children():
            widget.destroy()
        for widget in self.main_panel_scroll.winfo_children():
            widget.destroy()

        self._build_sidebar()
        self._build_main_area(self.main_panel_scroll)

        self.doc_entry.insert(0, self._current_doc_id)
        self.update_auth_state_label()
        self._set_stat("downloads", self.total_downloads)
        self._set_stat("results", self.total_results)
        self.update_storage_info()


    def _build_ui(self):
        """UI construction"""
        self.sidebar = ctk.CTkScrollableFrame(self, fg_color=PALETTE["surface"], corner_radius=0, width=320)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        
        self.main_panel_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=700)
        self.main_panel_scroll.grid(row=0, column=1, sticky="nsew", padx=(12, 12), pady=(12, 12))
        self.main_panel_scroll.grid_columnconfigure(0, weight=1)
        self.main_panel_scroll.grid_rowconfigure(2, weight=1)
        
        self._build_sidebar()
        self._build_main_area(self.main_panel_scroll)
    
    def _build_sidebar(self):
        """Sidebar construction"""
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
        brand.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(brand, text=_("sidebar_brand"), font=("Inter", 22, "bold"), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text=_("sidebar_brand_sub"), font=("Inter", 12), text_color=PALETTE["muted"]).grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        doc_block = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=12)
        doc_block.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        doc_block.grid_columnconfigure(0, weight=1)
        
        id_header_frame = ctk.CTkFrame(doc_block, fg_color="transparent")
        id_header_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 4))
        id_header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(doc_block, text=_("doc_block_title"), font=("Inter", 12, "bold"), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 4))
        
        btn_paste_id = ctk.CTkButton(
            id_header_frame,
            text="📋",
            width=30,
            height=24,
            font=("Inter", 12),
            fg_color=PALETTE["surface"],
            hover_color=PALETTE["border"],
            command=lambda: self._paste_to_entry(self.doc_entry)
        )
        btn_paste_id.grid(row=0, column=1, sticky="e")
        self.doc_entry = ctk.CTkEntry(doc_block, placeholder_text=_("doc_entry_placeholder"), font=("Inter", 13))
        self.doc_entry.grid(row=1, column=0, sticky="ew", padx=14)
        
        
        oauth_row = ctk.CTkFrame(doc_block, fg_color="transparent")
        oauth_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(8, 0))
        oauth_row.grid_columnconfigure(0, weight=1)
        
        self.lbl_auth_state = ctk.CTkLabel(oauth_row, text=_("google_not_connected"), font=("Inter", 11), text_color="#f87171", anchor="w")
        self.lbl_auth_state.grid(row=0, column=0, sticky="w")
        
        self.btn_auth = ctk.CTkButton(
            oauth_row,
            text=_("btn_connect_google"),
            font=("Inter", 11, "bold"),
            height=30,
            fg_color=PALETTE["surface"],
            hover_color=PALETTE["border"],
            command=self.connect_google_account
        )
        self.btn_auth.grid(row=0, column=1, padx=(6, 0))
        
        self.btn_run = ctk.CTkButton(
            doc_block,
            text=_("btn_run_analysis"),
            font=("Inter", 13, "bold"),
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_dark"],
            height=36,
            command=self.start_process
        )
        self.btn_run.grid(row=3, column=0, sticky="ew", padx=14, pady=(10, 14))
        
        status_chip = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=12)
        status_chip.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        status_chip.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(status_chip, text=_("status_title"), font=("Inter", 12, "bold"), text_color=PALETTE["muted"]).grid(row=0, column=0, padx=14, pady=(10, 0), sticky="w")
        
        self.lbl_status = ctk.CTkLabel(status_chip, text=_("status_ready"), font=("Inter", 12), text_color=PALETTE["text"], wraplength=250, justify="left")
        self.lbl_status.grid(row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 12))
        
        links_title = ctk.CTkLabel(self.sidebar, text=_("links_title"), font=HEADING_FONT, text_color=PALETTE["text"])
        links_title.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 6))
        
        links_hint = ctk.CTkLabel(self.sidebar, text=_("links_hint"), font=("Inter", 12), text_color=PALETTE["muted"])
        links_hint.grid(row=4, column=0, sticky="w", padx=18, pady=(0, 8))
        
        self.links_box = ctk.CTkTextbox(self.sidebar, height=140, font=MONO_FONT, fg_color=PALETTE["surface_alt"], border_color=PALETTE["border"], border_width=1)
        self.links_box.grid(row=5, column=0, sticky="ew", padx=18)
        
        self.download_actions = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.download_actions.grid(row=6, column=0, sticky="ew", padx=18, pady=(10, 6))
        self.download_actions.grid_columnconfigure(0, weight=1)
        
        self.paste_btn = ctk.CTkButton(
            self.download_actions,
            text=_("btn_paste_links"),
            font=("Inter", 11, "bold"),
            fg_color=PALETTE["surface_alt"],
            hover_color=PALETTE["border"],
            text_color=PALETTE["text"],
            height=34,
            command=self.paste_links_from_clipboard
        )
        self.paste_btn.grid(row=0, column=0, sticky="ew")
        
        self.btn_download = ctk.CTkButton(
            self.download_actions,
            text=_("btn_download_index"),
            font=("Inter", 12, "bold"),
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_dark"],
            height=36,
            command=self.start_download_flow
        )
        self.btn_download.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        
        self.progress_card = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=12)
        self.progress_card.grid(row=7, column=0, sticky="ew", padx=18, pady=(4, 6))
        self.progress_card.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.progress_card, text=_("progress_download_title"), font=("Inter", 12, "bold"), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        self.download_progress_label = ctk.CTkLabel(self.progress_card, text="0 / 0", font=("Inter", 11), text_color=PALETTE["muted"])
        self.download_progress_label.grid(row=1, column=0, sticky="w", padx=14)
        self.download_progress_bar = ctk.CTkProgressBar(self.progress_card, height=10)
        self.download_progress_bar.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 10))
        self.download_progress_bar.set(0)
        
        ctk.CTkLabel(self.progress_card, text=_("progress_index_title"), font=("Inter", 12, "bold"), text_color=PALETTE["text"]).grid(row=3, column=0, sticky="w", padx=14, pady=(4, 2))
        self.index_progress_label = ctk.CTkLabel(self.progress_card, text=_("index_not_started"), font=("Inter", 11), text_color=PALETTE["muted"])
        self.index_progress_label.grid(row=4, column=0, sticky="w", padx=14)
        self.index_progress_bar = ctk.CTkProgressBar(self.progress_card, height=10)
        self.index_progress_bar.grid(row=5, column=0, sticky="ew", padx=14, pady=(4, 12))
        self.index_progress_bar.set(0)
        
        self.stats_frame = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=14)
        self.stats_frame.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.stats_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.stat_cards = {
            "downloads": self._create_stat_chip(self.stats_frame, 0, _("stat_downloads"), self.stats_data["downloads"]),
            "results": self._create_stat_chip(self.stats_frame, 1, _("stat_results"), self.stats_data["results"]),
        }
        
        storage_block = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=12)
        storage_block.grid(row=10, column=0, sticky="ew", padx=18, pady=(0, 18))
        storage_block.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(storage_block, text=_("storage_block_title"), font=("Inter", 12, "bold"), text_color=PALETTE["muted"]).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        self.lbl_storage_size = ctk.CTkLabel(storage_block, text=_("storage_size_label", size="..."), font=("Inter", 12), text_color=PALETTE["text"])
        self.lbl_storage_size.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        self.btn_clear_storage = ctk.CTkButton(
            storage_block,
            text=_("btn_clear_storage"),
            font=("Inter", 12, "bold"),
            fg_color=PALETTE["danger"],
            hover_color=PALETTE["danger_hover"],
            height=32,
            command=self.confirm_clear_storage
        )
        self.btn_clear_storage.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

    
    def _build_main_area(self, parent):
        """Main area construction"""
        hero = ctk.CTkFrame(parent, fg_color=PALETTE["surface"], corner_radius=18)
        hero.grid(row=0, column=0, sticky="ew")
        
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)
        
        available_langs = i18n.get_available_languages()
        self.lang_menu = ctk.CTkOptionMenu(
            hero,
            values=available_langs,
            command=self.change_language,
            font=BODY_FONT,
            width=80,
            height=28,
            fg_color=PALETTE["surface_alt"],
            button_color=PALETTE["primary"],
            button_hover_color=PALETTE["primary_dark"],
            dropdown_fg_color=PALETTE["card"],
            dropdown_hover_color=PALETTE["surface_alt"],
            dropdown_text_color=PALETTE["text"]
        )
        self.lang_menu.grid(row=0, column=1, sticky="ne", padx=(0, 24), pady=(20, 0))
        self.lang_menu.set(i18n.current_language)

        
        ctk.CTkLabel(hero, text=_("hero_title"), font=("Inter", 28, "bold"), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(hero, text=_("hero_subtitle"), font=("Inter", 14), text_color=PALETTE["muted"], wraplength=700, justify="left").grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 18))
        
        steps_frame = ctk.CTkFrame(parent, fg_color=PALETTE["surface_alt"], corner_radius=16)
        steps_frame.grid(row=1, column=0, sticky="ew", pady=(18, 12))
        steps_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self._build_pipeline_step(steps_frame, 0, _("step1_title"), _("step1_desc"), "⬇")
        self._build_pipeline_step(steps_frame, 1, _("step2_title"), _("step2_desc"), "🧠")
        self._build_pipeline_step(steps_frame, 2, _("step3_title"), _("step3_desc"), "🎬")
        
        self.tab_view = ctk.CTkTabview(parent, fg_color=PALETTE["surface"], corner_radius=18)
        self.tab_view.grid(row=2, column=0, sticky="nsew", pady=(0, 0))
        
        self.tab_results = self.tab_view.add(_("tab_results"))
        self.results_scroll = ctk.CTkScrollableFrame(
            self.tab_results, 
            fg_color=PALETTE["surface"],
            height=500
        )
        self.results_scroll.pack(fill="both", expand=True, padx=8, pady=16)
        
        self.tab_logs = self.tab_view.add(_("tab_logs"))
        self.log_box = ctk.CTkTextbox(self.tab_logs, font=MONO_FONT, fg_color=PALETTE["surface_alt"], border_color=PALETTE["border"], border_width=1)
        self.log_box.pack(fill="both", expand=True, padx=8, pady=50)
        self.log_box.configure(state="disabled")
    
    def _build_pipeline_step(self, parent, column, title, descr, icon):
        """Creates pipeline stage card"""
        card = ctk.CTkFrame(parent, fg_color=PALETTE["card"], corner_radius=12, border_color=PALETTE["border"], border_width=1)
        card.grid(row=0, column=column, sticky="nsew", padx=12, pady=16)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=icon, font=("Inter", 22), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 0))
        ctk.CTkLabel(card, text=title, font=("Inter", 14, "bold"), text_color=PALETTE["text"]).grid(row=1, column=0, sticky="w", padx=12, pady=(4, 0))
        ctk.CTkLabel(card, text=descr, font=("Inter", 11), text_color=PALETTE["muted"], wraplength=250, justify="left").grid(row=2, column=0, sticky="w", padx=12, pady=(2, 12))
    
    def _create_stat_chip(self, parent, column: int, title: str, initial_value: int):
        """Creates statistics card"""
        card = ctk.CTkFrame(parent, fg_color=PALETTE["card"], corner_radius=12, border_width=1, border_color=PALETTE["border"])
        card.grid(row=0, column=column, sticky="ew", padx=12, pady=12)
        card.grid_columnconfigure(0, weight=1)
        
        title_lbl = ctk.CTkLabel(card, text=title, font=("Inter", 13), text_color=PALETTE["muted"])
        title_lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))
        
        value_lbl = ctk.CTkLabel(card, text=str(initial_value), font=("Inter", 28, "bold"), text_color=PALETTE["text"])
        value_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(4, 12))
        
        return value_lbl
    
    def update_auth_state_label(self):
        """Updates authorization status"""
        if self.auth_service and self.auth_service.is_authenticated():
            self.lbl_auth_state.configure(text=_("google_connected"), text_color="#22c55e")
            self.btn_auth.configure(text=_("btn_reconnect_google"), state="normal")
        else:
            self.lbl_auth_state.configure(text=_("google_not_connected"), text_color="#f87171")
            self.btn_auth.configure(text=_("btn_connect_google"), state="normal")
    
    def _auto_connect_if_needed(self):
        """Automatic connection if needed"""
        if self.auth_service and self.auth_service.is_authenticated():
            self.update_auth_state_label()
            return
        from oauth_config import has_client_secret_source
        if not has_client_secret_source():
            self._set_status(_("status_no_oauth"), "#f87171")
            return
        self.update_auth_state_label()
    
    def connect_google_account(self):
        """Google account connection"""
        if self._auth_thread_running:
            return
        from oauth_config import has_client_secret_source
        if not has_client_secret_source():
            self._set_status(_("status_no_oauth_crit"), "#f87171")
            return
        
        if not self.auth_service:
            self._set_status(_("status_service_not_init"), "#f87171")
            return
        
        self._auth_thread_running = True
        self.btn_auth.configure(state="disabled", text=_("btn_connecting_google"))
        self._set_status(_("status_auth_init"), PALETTE["text"])
        
        def worker():
            try:
                success = self.auth_service.authenticate()
                
                if success:
                    self.after(0, lambda: self._set_status(_("status_auth_success"), "#22c55e"))
                else:
                    self.after(0, lambda: self._set_status(_("status_auth_fail"), "#f87171"))
                
                self.after(0, self.update_auth_state_label)
                    
            except Exception as e:
                self.after(0, lambda: self._set_status(_("status_auth_error", error=e), "#f87171"))
                self.after(0, self.update_auth_state_label)
            finally:
                self._auth_thread_running = False
                self.after(0, lambda: self.btn_auth.configure(state="normal"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def start_process(self):
        """Starts analysis process"""
        doc_id = self.doc_entry.get().strip()
        if not doc_id:
            self._set_status(_("status_no_doc_id"), "#f87171")
            return
        if not self.auth_service or not self.auth_service.is_authenticated():
            self._set_status(_("status_connect_first"), "#f87171")
            return
        
        if not self.analysis_service:
            self._set_status(_("status_service_not_init"), "#f87171")
            return
        
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        self._set_stat("results", 0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        
        self.btn_run.configure(state="disabled", text=_("btn_running_analysis"))
        self.tab_view.set(_("tab_results"))
        self._set_status(_("status_starting_analysis"), PALETTE["text"])
        
        def callback(msg_type: str, data):
            """Callback for analysis service"""
            if msg_type == "status":
                self.after(0, lambda: self._set_status(data, PALETTE["text"]))
            elif msg_type == "log":
                self.after(0, lambda: self.log_message(data))
            elif msg_type == "error":
                self.after(0, lambda: self._set_status(f"❌ {data}", "#f87171"))
                self.after(0, lambda: self.log_message(f"❌ ERROR: {data}"))
            elif msg_type == "result_found":
                self.after(0, lambda: self.add_result_card(data))
            elif msg_type == "finished":
                self.after(0, lambda: self.btn_run.configure(state="normal", text=_("btn_run_analysis")))
                self.after(0, lambda: self._set_status(_("status_analysis_finished"), "#22c55e"))
        
        threading.Thread(
            target=lambda: self.analysis_service.analyze_document(doc_id, callback),
            daemon=True
        ).start()
    
    def start_download_flow(self):
        """Starts video download"""
        raw_links = self.links_box.get("1.0", "end").strip()

        print("\n" + "="*30)
        print("[DEBUG] ДІАГНОСТИКА ПОСИЛАНЬ")
        print(f"[DEBUG] Сирий текст з поля (в лапках): '{raw_links}'")

        urls = [line.strip() for line in raw_links.splitlines() if line.strip()]

        print(f"[DEBUG] Знайдено окремих посилань: {len(urls)}")
        print(f"[DEBUG] Список для завантажувача: {urls}")
        print("="*30 + "\n")
        if not urls:
            self._set_status(_("status_no_links"), "#f87171")
            print("[DEBUG] ❌ Помилка: список URL порожній, зупиняємося.")
            return
        
        self.reset_download_progress(len(urls))
        self.btn_download.configure(state="disabled", text=_("btn_downloading"))
        self._set_status(_("status_starting_download"), PALETTE["text"])
        threading.Thread(target=self.download_and_index_thread, args=(urls,), daemon=True).start()
    
    def download_and_index_thread(self, urls: list[str]):
        """Thread for downloading and indexing"""
        success_count = 0
        try:
            def progress_callback(msg_type: str, data):
                if msg_type == "download_progress":
                    if isinstance(data, dict):
                        current = data.get("current", 0)
                        total = data.get("total", 0)
                        self.after(0, lambda c=current, t=total: self.update_download_progress(c, t))
                elif msg_type == "status":
                    self.after(0, lambda: self._set_status(data, PALETTE["text"]))
                elif msg_type == "log":
                    self.after(0, lambda: self.log_message(data))
                elif msg_type == "error":
                    self.after(0, lambda: self._set_status(f"❌ {data}", "#f87171"))
            
            results = download_links(urls, progress_callback)
            print(f"\n[DEBUG] === ВІДПОВІДЬ ЗАВАНТАЖУВАЧА ===\n{results}\n=================================\n")
            success_count = len([r for r in results if r.get("status") == "success"])
            
            if success_count:
                self._set_status(_("status_indexing_started"))
                self.after(0, lambda count=success_count: self.set_indexing_state(True, count))
                
                if self.indexing_service:
                    old_stdout = sys.stdout
                    buffer = io.StringIO()
                    sys.stdout = buffer
                    try:
                        self.indexing_service.index_new_videos()
                    finally:
                        sys.stdout = old_stdout
                        log_text = buffer.getvalue()
                        if log_text.strip():
                            self.log_message(log_text)
                
                self._set_status(_("status_import_finished", count=success_count))
                self.after(0, lambda: self.links_box.delete("1.0", "end"))
                self.after(0, lambda count=success_count: self._bump_stat("downloads", count))
                self.after(0, self.update_storage_info)
            else:
                self._set_status(_("status_download_no_new"))
        except Exception as e:
            self._set_status(_("status_download_error", error=e), "#f87171")
        finally:
            self.after(0, lambda count=success_count: self.set_indexing_state(False, count))
            self.after(0, lambda: self.btn_download.configure(state="normal", text=_("btn_download_index")))
    
    def add_result_card(self, data):
        """Adds result card"""
        meta = {
            "filename": data.get("filename"),
            "timestamp": data.get("timestamp"),
            "frame_path": data.get("frame_path"),
            "timecode": data.get("timecode"),
            "text_snippet": data.get("text_snippet"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "segment_id": data.get("segment_id"),
        }
        
        video_segment = None
        if data.get("is_segment"):
            video_segment = {
                "filename": data.get("filename"),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "is_segment": True
            }
        
        card = ResultCard(
            self.results_scroll,
            text_snippet=data['text_snippet'],
            tags=data.get('tags', ''),
            filename=data['filename'],
            timecode=data.get('timecode', ''),
            accuracy=data['accuracy'],
            meta=meta,
            on_feedback=self.handle_feedback,
            frame_path=data.get('frame_path'),
            video_segment=video_segment
        )
        card.pack(fill="x", pady=5)
        self._bump_stat("results", 1)
    
    def handle_feedback(self, meta: dict, value: str) -> bool:
        """Handles feedback"""
        if not meta or not self.analysis_service:
            return False
        
        def worker():
            success = self.analysis_service.record_feedback(meta, value == "positive")
            if success:
                self._set_status(_("status_feedback_saved"), PALETTE["text"])
            else:
                self._set_status(_("status_feedback_fail"), "#f87171")
        
        threading.Thread(target=worker, daemon=True).start()
        return True
    
    def reset_download_progress(self, total: int):
        """Resets download progress"""
        self.download_progress_total = total
        self.update_download_progress(0, total)
    
    def update_download_progress(self, current: int, total: int | None = None):
        """Updates download progress"""
        if total is None or total <= 0:
            total = self.download_progress_total
        if total <= 0:
            self.download_progress_bar.set(0)
            self.download_progress_label.configure(text="0 / 0")
            return
        ratio = min(max(current / total, 0.0), 1.0)
        self.download_progress_bar.set(ratio)
        self.download_progress_label.configure(text=f"{current} / {total}")
    
    def set_indexing_state(self, running: bool, total: int = 0):
        """Sets indexing state"""
        if running:
            self.index_progress_label.configure(text=_("index_running", total=total))
            self.index_progress_bar.configure(mode="indeterminate")
            self.index_progress_bar.start()
        else:
            self.index_progress_bar.stop()
            self.index_progress_bar.configure(mode="determinate")
            self.index_progress_bar.set(1 if total else 0)
            self.index_progress_label.configure(text=_("index_finished") if total else _("index_not_started"))
    
    def _set_stat(self, key: str, value: int):
        """Sets statistics"""
        self.stats_data[key] = max(0, value)
        lbl = self.stat_cards.get(key)
        if lbl:
            lbl.configure(text=str(self.stats_data[key]))
        if key == "results":
            self.total_results = self.stats_data[key]
        if key == "downloads":
            self.total_downloads = self.stats_data[key]
    
    def _bump_stat(self, key: str, delta: int = 1):
        """Increments statistics"""
        current = self.stats_data.get(key, 0)
        self._set_stat(key, current + delta)
    
    def _set_status(self, text: str, color: str | None = None):
        """Sets status"""
        if color is None:
            color = PALETTE["muted"]
        self.lbl_status.configure(text=text, text_color=color)
    
    def _paste_to_entry(self, entry_widget: ctk.CTkEntry):
        """Pastes text from clipboard to specified field"""
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                entry_widget.delete(0, "end")
                entry_widget.insert(0, clipboard_text.strip())
        except Exception:
            self._set_status(_("status_clipboard_empty"), "#f87171")

            
    def paste_links_from_clipboard(self):
        """Pastes links from clipboard"""
        try:
            clipboard_text = self.clipboard_get()
        except Exception:
            self._set_status(_("status_clipboard_empty"), "#f87171")
            return
        
        clipboard_text = clipboard_text.strip()
        if not clipboard_text:
            self._set_status(_("status_clipboard_no_text"), "#f87171")
            return
        
        current = self.links_box.get("1.0", "end").strip()
        insertion = clipboard_text if clipboard_text.endswith("\n") else clipboard_text + "\n"
        if current:
            if not current.endswith("\n"):
                self.links_box.insert("end", "\n")
            self.links_box.insert("end", insertion)
        else:
            self.links_box.delete("1.0", "end")
            self.links_box.insert("1.0", insertion)
        self.links_box.focus_set()
        self._set_status(_("status_links_pasted"), PALETTE["text"])
    
    def log_message(self, text):
        """Adds message to log"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _format_bytes(self, size: int) -> str:
        """Formats bytes into human-readable format"""
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.1f} {power_labels.get(n, '')}B"

    def update_storage_info(self):
        """Updates storage size information"""
        if self.storage_service:
            size_bytes = self.storage_service.get_total_size_bytes()
            formatted_size = self._format_bytes(size_bytes)
            self.lbl_storage_size.configure(text=_("storage_size_label", size=formatted_size))

    def confirm_clear_storage(self):
        """Shows confirmation dialog for clearing"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(_("confirm_clear_title"))
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text=_("confirm_clear_title"), font=("Inter", 16, "bold"), text_color=PALETTE["text"]).pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text=_("confirm_clear_text"), font=("Inter", 12), text_color=PALETTE["muted"], wraplength=350).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        def on_confirm():
            dialog.destroy()
            self._run_clear_storage()

        ctk.CTkButton(btn_frame, text="Отмена", fg_color=PALETTE["surface"], hover_color=PALETTE["border"], command=dialog.destroy, width=100).pack(side="left", expand=True, padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Удалить", fg_color=PALETTE["danger"], hover_color=PALETTE["danger_hover"], command=on_confirm, width=100).pack(side="left", expand=True)

        dialog.grab_set()

    def _run_clear_storage(self):
        """Runs clearing process in background"""
        if not self.storage_service:
            return

        self.btn_clear_storage.configure(state="disabled")
        self._set_status(_("status_clearing_started"), PALETTE["text"])

        def worker():
            success = self.storage_service.clear_project_storage()
            if success:
                self.after(0, lambda: self._set_status(_("status_clearing_finished"), "#22c55e"))
                self.after(0, lambda: self._set_stat("downloads", 0))
                self.after(0, lambda: self._set_stat("results", 0))
                self.after(0, self.update_storage_info)
                self.after(0, lambda: [widget.destroy() for widget in self.results_scroll.winfo_children()])
            else:
                self.after(0, lambda: self._set_status(_("status_clearing_error"), "#f87171"))
            
            self.after(0, lambda: self.btn_clear_storage.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


__all__ = ['App']