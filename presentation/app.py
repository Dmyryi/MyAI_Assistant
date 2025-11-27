"""
Presentation layer: Главное приложение GUI
Использует dependency injection для всех сервисов
"""
import os
import threading
import io
import sys
import customtkinter as ctk
from typing import Optional
import subprocess
import platform
from PIL import Image, ImageTk

from application.document_analysis_service import DocumentAnalysisService
from application.video_indexing_service import VideoIndexingService
# Импорт нового сервиса
from application.storage_service import StorageService
from infrastructure.google import OAuthService
from downloader import download_links

# Импортируем функцию локализации И сам менеджер i18n
from infrastructure.localization import _, i18n

# Импортируем компоненты GUI
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
    """Single Responsibility: Отображение одного результата поиска"""
    
    def __init__(self, master, text_snippet, tags, filename, timecode, accuracy, meta, on_feedback, frame_path=None, **kwargs):
        # Инициализация CTkFrame (внешний вид карточки)
        super().__init__(
            master,
            corner_radius=14,
            border_width=1,
            border_color=PALETTE["border"],
            fg_color=PALETTE["card"],
            **kwargs
        )
        # Сохранение данных, специфичных для этой карточки
        self.meta = meta or {}
        self.on_feedback = on_feedback
        self.feedback_sent = False
        self.frame_path = frame_path
        
        # Построение внутреннего UI карточки с использованием переданных данных
        self._build_ui(text_snippet, tags, filename, timecode, accuracy)
    
    def _build_ui(self, text_snippet, tags, filename, timecode, accuracy):
        """Строит UI компонента"""
        # Левая часть: Таймкод и точность
        self.info_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=PALETTE["primary"], width=90)
        self.info_frame.pack(side="left", fill="y", padx=(5, 10), pady=5)
        
        self.lbl_time = ctk.CTkLabel(self.info_frame, text=timecode, font=("Inter", 18, "bold"), text_color="white")
        self.lbl_time.pack(pady=(15, 5))
        self.lbl_acc = ctk.CTkLabel(self.info_frame, text=f"{accuracy}%", font=("Inter", 12), text_color="#e2e8f0")
        self.lbl_acc.pack()

        # Средняя часть: Превью кадра (если есть)
        if self.frame_path:
            self.preview_frame = ctk.CTkFrame(self, corner_radius=8, fg_color=PALETTE["surface_alt"], width=160)
            self.preview_frame.pack(side="left", fill="y", padx=(0, 10), pady=5)
            self.preview_frame.pack_propagate(False)
            
            # Загружаем и отображаем изображение
            self._load_preview_image()
        else:
            self.preview_frame = None

        # Правая часть: Контент
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

        # Локализация тегов
        tags_str = f"[{tags}]" if tags else f"[{_('card_no_tags')}]"
        self.lbl_tags = ctk.CTkLabel(
            self.content_frame,
            # Використовуємо локалізований заголовок + теги
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
            # Використовуємо локалізований заголовок + ім'я файлу
            text=f"{_('card_file')} {filename}",
            font=MONO_FONT,
            text_color=PALETTE["muted"],
            anchor="w"
        )
        self.lbl_file.pack(fill="x")

        # Кнопки отзывов
        self.actions_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.actions_frame.pack(fill="x", pady=(8, 4))
        self.actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.feedback_label = ctk.CTkLabel(
            self.actions_frame,
            text=_("card_feedback_q"), # Локализация вопроса
            font=("Inter", 11),
            text_color=PALETTE["muted"],
            anchor="w"
        )
        self.feedback_label.grid(row=0, column=0, sticky="w")

        self.btn_group = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        self.btn_group.grid(row=0, column=1, sticky="e")

        self.btn_like = ctk.CTkButton(
            self.btn_group,
            text=_("btn_like"), # Локализация кнопки лайк
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
            text=_("btn_dislike"), # Локализация кнопки дизлайк
            font=("Inter", 11, "bold"),
            width=100,
            height=30,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=lambda: self._send_feedback("negative")
        )
        self.btn_dislike.grid(row=0, column=1)
    
    def _load_preview_image(self):
        """Загружает и отображает превью кадра"""
        if not self.frame_path or not self.preview_frame:
            return
        
        if not os.path.exists(self.frame_path):
            # Если файл не найден, показываем заглушку
            placeholder = ctk.CTkLabel(
                self.preview_frame,
                text=_("preview_placeholder"), # Локализация заглушки
                font=("Inter", 11),
                text_color=PALETTE["muted"],
                justify="center"
            )
            placeholder.pack(expand=True, fill="both", padx=5, pady=5)
            return
        
        try:
            # Загружаем изображение
            img = Image.open(self.frame_path)
            
            # Вычисляем размеры для превью (максимум 160x120)
            max_width, max_height = 160, 120
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Конвертируем в формат для CTkLabel
            ctk_image = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(img.width, img.height)
            )
            
            # Создаем label с изображением
            self.preview_label = ctk.CTkLabel(
                self.preview_frame,
                image=ctk_image,
                text="",
                corner_radius=6
            )
            self.preview_label.pack(expand=True, fill="both", padx=5, pady=5)
            
            # Добавляем подпись с размером
            size_label = ctk.CTkLabel(
                self.preview_frame,
                text=f"{img.width}×{img.height}",
                font=("Inter", 9),
                text_color=PALETTE["muted"]
            )
            size_label.pack(pady=(0, 5))
            
            # Добавляем кнопку для открытия в полном размере
            self.btn_view_full = ctk.CTkButton(
                self.preview_frame,
                text=_("btn_view_full"), # Локализация кнопки просмотра
                font=("Inter", 10),
                height=24,
                width=140,
                fg_color=PALETTE["surface"],
                hover_color=PALETTE["border"],
                command=self._open_full_image
            )
            self.btn_view_full.pack(pady=(0, 5))
            
        except Exception as e:
            # Если не удалось загрузить изображение
            error_label = ctk.CTkLabel(
                self.preview_frame,
                # Локализация ошибки с параметром
                text=_("preview_error", error=str(e)[:20]),
                font=("Inter", 10),
                text_color="#f87171",
                justify="center"
            )
            error_label.pack(expand=True, fill="both", padx=5, pady=5)
    
    def _open_full_image(self):
        """Открывает изображение в полном размере"""
        if not self.frame_path:
            return
        
        if not os.path.exists(self.frame_path):
            return
        
        try:
            # Открываем изображение системным просмотрщиком
            if platform.system() == 'Windows':
                os.startfile(self.frame_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', self.frame_path])
            else:  # Linux
                subprocess.run(['xdg-open', self.frame_path])
        except Exception:
            pass  # Игнорируем ошибки открытия

    def _send_feedback(self, value: str):
        """Отправляет обратную связь"""
        if self.feedback_sent:
            return
        if self.on_feedback and self.on_feedback(self.meta, value):
            self.feedback_sent = True
            self.btn_like.configure(state="disabled")
            self.btn_dislike.configure(state="disabled")
            # Локализация сообщения "Спасибо"
            self.feedback_label.configure(text=_("feedback_thanks"), text_color=PALETTE["text"])


class App(ctk.CTk):
    """
    Dependency Inversion: GUI зависит от абстракций (сервисов)
    Single Responsibility: Управление UI и координация действий пользователя
    """
    
    def __init__(
        self,
        analysis_service: Optional[DocumentAnalysisService] = None,
        indexing_service: Optional[VideoIndexingService] = None,
        auth_service: Optional[OAuthService] = None,
        storage_service: Optional[StorageService] = None # <-- Новый сервис
    ):
        super().__init__()
        
        # Dependency Injection: Сохраняем сервисы
        self.analysis_service = analysis_service
        self.indexing_service = indexing_service
        self.auth_service = auth_service
        self.storage_service = storage_service # <-- Сохраняем
        
        # 1. Настройка базового окна
        self._setup_window()
        
        # 2. ВАЖНО: Инициализация данных (статистика и т.д.) ДО построения UI
        # Именно здесь создается self.stats_data
        self._initialize_state()
        
        # 3. Установка коллбеков
        if self.auth_service:
            self._setup_auth_callback()
            
        # 4. Построение интерфейса (который использует инициализированные данные)
        self._build_ui()
        
        # 5. Обновляем информацию о хранилище после запуска
        self.update_storage_info()

    
    def _setup_window(self):
        """Настройка окна"""
        # Локализация заголовка окна
        self.title(_("app_title"))
        self.geometry("1024x768")  # Немного увеличил высоту
        self.configure(fg_color=PALETTE["bg"])
        
        try:
            self.state("zoomed")
        except Exception:
            self.attributes("-zoomed", True)
        
        # Настройка сетки главного окна
        self.grid_columnconfigure(1, weight=1) # Основная область растягивается
        self.grid_rowconfigure(0, weight=1)    # Высота растягивается
        
        # Устанавливаем минимальный размер окна
        self.minsize(1200, 768)
    
    def _initialize_state(self):
        """Инициализация состояния"""
        self.stats_data = {"downloads": 0, "results": 0}
        self.total_results = 0
        self.total_downloads = 0
        self.token_file = "token.enc"  # Зашифрованный файл
        self.download_progress_total = 0
        self._auth_thread_running = False
        # Сохраняем ID документа, чтобы не терять при смене языка
        self._current_doc_id = ""

    
    def _setup_auth_callback(self):
        """Устанавливает callback для получения сообщений от OAuthService"""
        if not self.auth_service:
            return
        
        def auth_callback(msg_type: str, message: str):
            """Callback для получения сообщений от OAuthService"""
            if msg_type == "status":
                self.after(0, lambda: self._set_status(message, PALETTE["text"]))
            elif msg_type == "log":
                self.after(0, lambda: self.log_message(message))
            elif msg_type == "error":
                self.after(0, lambda: self._set_status(f"❌ {message}", "#f87171"))
        
        # Устанавливаем callback
        self.auth_service.status_callback = auth_callback
    
    def change_language(self, new_lang_code: str):
        """Змінює мову інтерфейсу та перебудовує GUI"""
        if new_lang_code == i18n.current_language:
            return

        # 1. Зберігаємо важливий стан
        self._current_doc_id = self.doc_entry.get()
        
        # 2. Змінюємо мову в бекенді
        i18n.load_language(new_lang_code)
        
        # 3. Оновлюємо заголовок вікна
        self.title(_("app_title"))

        # 4. Очищаємо основні контейнери (сайдбар і головну область)
        for widget in self.sidebar.winfo_children():
            widget.destroy()
        for widget in self.main_panel_scroll.winfo_children():
            widget.destroy()

        # 5. Перебудовуємо інтерфейс
        self._build_sidebar()
        self._build_main_area(self.main_panel_scroll)

        # 6. Відновлюємо стан та оновлюємо динамічні елементи
        self.doc_entry.insert(0, self._current_doc_id)
        self.update_auth_state_label()
        # Відновлюємо статистику
        self._set_stat("downloads", self.total_downloads)
        self._set_stat("results", self.total_results)
        self.update_storage_info()


    def _build_ui(self):
        """Построение UI"""
        # Sidebar (левая колонка)
        self.sidebar = ctk.CTkScrollableFrame(self, fg_color=PALETTE["surface"], corner_radius=0, width=320)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        
        # Main panel (правая колонка)
        self.main_panel_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=700)
        self.main_panel_scroll.grid(row=0, column=1, sticky="nsew", padx=(12, 12), pady=(12, 12))
        self.main_panel_scroll.grid_columnconfigure(0, weight=1)
        self.main_panel_scroll.grid_rowconfigure(2, weight=1)  # Tab view будет растягиваться
        
        self._build_sidebar()
        self._build_main_area(self.main_panel_scroll)
    
    def _build_sidebar(self):
        """Построение боковой панели"""
        # Branding
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
        brand.grid_columnconfigure(0, weight=1)
        # Локализация бренда
        ctk.CTkLabel(brand, text=_("sidebar_brand"), font=("Inter", 22, "bold"), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text=_("sidebar_brand_sub"), font=("Inter", 12), text_color=PALETTE["muted"]).grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        # Document block
        doc_block = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=12)
        doc_block.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        doc_block.grid_columnconfigure(0, weight=1)
        
        id_header_frame = ctk.CTkFrame(doc_block, fg_color="transparent")
        id_header_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 4))
        id_header_frame.grid_columnconfigure(0, weight=1)

        # Локализация заголовка Doc ID
        ctk.CTkLabel(doc_block, text=_("doc_block_title"), font=("Inter", 12, "bold"), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 4))
        
        btn_paste_id = ctk.CTkButton(
            id_header_frame,
            text="📋",
            width=30,
            height=24,
            font=("Inter", 12),
            fg_color=PALETTE["surface"],
            hover_color=PALETTE["border"],
            # Ця команда вставить текст із буфера в self.doc_entry
            command=lambda: self._paste_to_entry(self.doc_entry)
        )
        btn_paste_id.grid(row=0, column=1, sticky="e")
        # Локализация плейсхолдера
        self.doc_entry = ctk.CTkEntry(doc_block, placeholder_text=_("doc_entry_placeholder"), font=("Inter", 13))
        self.doc_entry.grid(row=1, column=0, sticky="ew", padx=14)
        
        
        oauth_row = ctk.CTkFrame(doc_block, fg_color="transparent")
        oauth_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(8, 0))
        oauth_row.grid_columnconfigure(0, weight=1)
        
        # Локализация начального статуса Google
        self.lbl_auth_state = ctk.CTkLabel(oauth_row, text=_("google_not_connected"), font=("Inter", 11), text_color="#f87171", anchor="w")
        self.lbl_auth_state.grid(row=0, column=0, sticky="w")
        
        # Локализация кнопки подключения
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
        
        # Локализация кнопки запуска анализа
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
        
        # Status chip
        status_chip = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=12)
        status_chip.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        status_chip.grid_columnconfigure(1, weight=1)
        
        # Локализация заголовка статуса
        ctk.CTkLabel(status_chip, text=_("status_title"), font=("Inter", 12, "bold"), text_color=PALETTE["muted"]).grid(row=0, column=0, padx=14, pady=(10, 0), sticky="w")
        
        # Локализация начального статуса
        self.lbl_status = ctk.CTkLabel(status_chip, text=_("status_ready"), font=("Inter", 12), text_color=PALETTE["text"], wraplength=250, justify="left")
        self.lbl_status.grid(row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 12))
        
        # Links section
        # Локализация заголовка ссылок
        links_title = ctk.CTkLabel(self.sidebar, text=_("links_title"), font=HEADING_FONT, text_color=PALETTE["text"])
        links_title.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 6))
        
        # Локализация подсказки для ссылок
        links_hint = ctk.CTkLabel(self.sidebar, text=_("links_hint"), font=("Inter", 12), text_color=PALETTE["muted"])
        links_hint.grid(row=4, column=0, sticky="w", padx=18, pady=(0, 8))
        
        self.links_box = ctk.CTkTextbox(self.sidebar, height=140, font=MONO_FONT, fg_color=PALETTE["surface_alt"], border_color=PALETTE["border"], border_width=1)
        self.links_box.grid(row=5, column=0, sticky="ew", padx=18)
        
        self.download_actions = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.download_actions.grid(row=6, column=0, sticky="ew", padx=18, pady=(10, 6))
        self.download_actions.grid_columnconfigure(0, weight=1)
        
        # Локализация кнопки вставки
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
        
        # Локализация кнопки загрузки
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
        
        # Progress cards
        self.progress_card = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=12)
        self.progress_card.grid(row=7, column=0, sticky="ew", padx=18, pady=(4, 6))
        self.progress_card.grid_columnconfigure(0, weight=1)
        
        # Локализация заголовка прогресса загрузки
        ctk.CTkLabel(self.progress_card, text=_("progress_download_title"), font=("Inter", 12, "bold"), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        self.download_progress_label = ctk.CTkLabel(self.progress_card, text="0 / 0", font=("Inter", 11), text_color=PALETTE["muted"])
        self.download_progress_label.grid(row=1, column=0, sticky="w", padx=14)
        self.download_progress_bar = ctk.CTkProgressBar(self.progress_card, height=10)
        self.download_progress_bar.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 10))
        self.download_progress_bar.set(0)
        
        # Локализация заголовка прогресса индексации
        ctk.CTkLabel(self.progress_card, text=_("progress_index_title"), font=("Inter", 12, "bold"), text_color=PALETTE["text"]).grid(row=3, column=0, sticky="w", padx=14, pady=(4, 2))
        # Локализация начального статуса индексации
        self.index_progress_label = ctk.CTkLabel(self.progress_card, text=_("index_not_started"), font=("Inter", 11), text_color=PALETTE["muted"])
        self.index_progress_label.grid(row=4, column=0, sticky="w", padx=14)
        self.index_progress_bar = ctk.CTkProgressBar(self.progress_card, height=10)
        self.index_progress_bar.grid(row=5, column=0, sticky="ew", padx=14, pady=(4, 12))
        self.index_progress_bar.set(0)
        
        # Stats
        self.stats_frame = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=14)
        self.stats_frame.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.stats_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.stat_cards = {
            # Локализация заголовков статистики
            "downloads": self._create_stat_chip(self.stats_frame, 0, _("stat_downloads"), self.stats_data["downloads"]),
            "results": self._create_stat_chip(self.stats_frame, 1, _("stat_results"), self.stats_data["results"]),
        }
        
        # --- Storage Block (New) ---
        storage_block = ctk.CTkFrame(self.sidebar, fg_color=PALETTE["surface_alt"], corner_radius=12)
        storage_block.grid(row=10, column=0, sticky="ew", padx=18, pady=(0, 18))
        storage_block.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(storage_block, text=_("storage_block_title"), font=("Inter", 12, "bold"), text_color=PALETTE["muted"]).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        # Лейбл для размера (будет обновляться)
        self.lbl_storage_size = ctk.CTkLabel(storage_block, text=_("storage_size_label", size="..."), font=("Inter", 12), text_color=PALETTE["text"])
        self.lbl_storage_size.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        # Кнопка очистки (красная)
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
        # ---------------------------

    
    def _build_main_area(self, parent):
        """Построение основной области"""
        hero = ctk.CTkFrame(parent, fg_color=PALETTE["surface"], corner_radius=18)
        hero.grid(row=0, column=0, sticky="ew")
        
        # Настройка сетки Hero:
        # Column 0: Заголовки (растягивается)
        # Column 1: Переключатель языка (фиксированный размер, прижат вправо)
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)
        
        # --- Language Selection (Top Right) ---
        available_langs = i18n.get_available_languages()
        self.lang_menu = ctk.CTkOptionMenu(
            hero, # Вставляем в Hero фрейм
            values=available_langs,
            command=self.change_language,
            font=BODY_FONT,
            width=80, # Делаем чуть компактнее
            height=28,
            fg_color=PALETTE["surface_alt"],
            button_color=PALETTE["primary"],
            button_hover_color=PALETTE["primary_dark"],
            dropdown_fg_color=PALETTE["card"],
            dropdown_hover_color=PALETTE["surface_alt"],
            dropdown_text_color=PALETTE["text"]
        )
        # Размещаем в правом верхнем углу (row=0, col=1, sticky="ne")
        self.lang_menu.grid(row=0, column=1, sticky="ne", padx=(0, 24), pady=(20, 0))
        self.lang_menu.set(i18n.current_language)

        
        # Локализация главного заголовка и подзаголовка
        # Заголовок в колонке 0
        ctk.CTkLabel(hero, text=_("hero_title"), font=("Inter", 28, "bold"), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        # Подзаголовок растягивается на обе колонки
        ctk.CTkLabel(hero, text=_("hero_subtitle"), font=("Inter", 14), text_color=PALETTE["muted"], wraplength=700, justify="left").grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 18))
        
        steps_frame = ctk.CTkFrame(parent, fg_color=PALETTE["surface_alt"], corner_radius=16)
        steps_frame.grid(row=1, column=0, sticky="ew", pady=(18, 12))  # Уменьшен нижний отступ для большего места
        steps_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Локализация шагов пайплайна
        self._build_pipeline_step(steps_frame, 0, _("step1_title"), _("step1_desc"), "⬇")
        self._build_pipeline_step(steps_frame, 1, _("step2_title"), _("step2_desc"), "🧠")
        self._build_pipeline_step(steps_frame, 2, _("step3_title"), _("step3_desc"), "🎬")
        
        # Tab view - растягивается по всей доступной высоте (weight=1 в grid_rowconfigure)
        self.tab_view = ctk.CTkTabview(parent, fg_color=PALETTE["surface"], corner_radius=18)
        self.tab_view.grid(row=2, column=0, sticky="nsew", pady=(0, 0))
        
        # Локализация названий вкладок
        self.tab_results = self.tab_view.add(_("tab_results"))
        # Область результатов растягивается на всю доступную высоту tab_view
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
        """Создает карточку этапа пайплайна"""
        card = ctk.CTkFrame(parent, fg_color=PALETTE["card"], corner_radius=12, border_color=PALETTE["border"], border_width=1)
        card.grid(row=0, column=column, sticky="nsew", padx=12, pady=16)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=icon, font=("Inter", 22), text_color=PALETTE["text"]).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 0))
        ctk.CTkLabel(card, text=title, font=("Inter", 14, "bold"), text_color=PALETTE["text"]).grid(row=1, column=0, sticky="w", padx=12, pady=(4, 0))
        ctk.CTkLabel(card, text=descr, font=("Inter", 11), text_color=PALETTE["muted"], wraplength=250, justify="left").grid(row=2, column=0, sticky="w", padx=12, pady=(2, 12))
    
    def _create_stat_chip(self, parent, column: int, title: str, initial_value: int):
        """Создает карточку статистики"""
        card = ctk.CTkFrame(parent, fg_color=PALETTE["card"], corner_radius=12, border_width=1, border_color=PALETTE["border"])
        card.grid(row=0, column=column, sticky="ew", padx=12, pady=12)
        card.grid_columnconfigure(0, weight=1)
        
        title_lbl = ctk.CTkLabel(card, text=title, font=("Inter", 13), text_color=PALETTE["muted"])
        title_lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))
        
        value_lbl = ctk.CTkLabel(card, text=str(initial_value), font=("Inter", 28, "bold"), text_color=PALETTE["text"])
        value_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(4, 12))
        
        return value_lbl
    
    def update_auth_state_label(self):
        """Обновляет статус авторизации"""
        if self.auth_service and self.auth_service.is_authenticated():
            # Локализация статуса подключено
            self.lbl_auth_state.configure(text=_("google_connected"), text_color="#22c55e")
            self.btn_auth.configure(text=_("btn_reconnect_google"), state="normal")
        else:
            # Локализация статуса не подключено
            self.lbl_auth_state.configure(text=_("google_not_connected"), text_color="#f87171")
            self.btn_auth.configure(text=_("btn_connect_google"), state="normal")
    
    def _auto_connect_if_needed(self):
        """Автоматическое подключение если нужно"""
        # Проверяем через auth_service, а не через файл
        if self.auth_service and self.auth_service.is_authenticated():
            self.update_auth_state_label()
            return
        from oauth_config import has_client_secret_source
        if not has_client_secret_source():
            # Локализация ошибки отсутствия ключа
            self._set_status(_("status_no_oauth"), "#f87171")
            return
        # Не автоподключаем, просто обновляем статус
        self.update_auth_state_label()
    
    def connect_google_account(self):
        """Подключение Google аккаунта"""
        if self._auth_thread_running:
            return
        from oauth_config import has_client_secret_source
        if not has_client_secret_source():
            # Локализация критической ошибки отсутствия ключа
            self._set_status(_("status_no_oauth_crit"), "#f87171")
            return
        
        if not self.auth_service:
            # Локализация ошибки неинициализированного сервиса
            self._set_status(_("status_service_not_init"), "#f87171")
            return
        
        self._auth_thread_running = True
        # Локализация текста кнопки при подключении
        self.btn_auth.configure(state="disabled", text=_("btn_connecting_google"))
        # Локализация статуса инициализации
        self._set_status(_("status_auth_init"), PALETTE["text"])
        
        def worker():
            try:
                # Callback уже установлен в _setup_auth_callback
                success = self.auth_service.authenticate()
                
                if success:
                    # Локализация успеха авторизации
                    self.after(0, lambda: self._set_status(_("status_auth_success"), "#22c55e"))
                else:
                    # Локализация неудачи авторизации
                    self.after(0, lambda: self._set_status(_("status_auth_fail"), "#f87171"))
                
                self.after(0, self.update_auth_state_label)
                    
            except Exception as e:
                # Локализация ошибки авторизации с параметром
                self.after(0, lambda: self._set_status(_("status_auth_error", error=e), "#f87171"))
                self.after(0, self.update_auth_state_label)
            finally:
                self._auth_thread_running = False
                self.after(0, lambda: self.btn_auth.configure(state="normal"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def start_process(self):
        """Запуск процесса анализа"""
        doc_id = self.doc_entry.get().strip()
        if not doc_id:
            # Локализация ошибки отсутствия ID
            self._set_status(_("status_no_doc_id"), "#f87171")
            return
        if not self.auth_service or not self.auth_service.is_authenticated():
            # Локализация подсказки о подключении
            self._set_status(_("status_connect_first"), "#f87171")
            return
        
        if not self.analysis_service:
            # Локализация ошибки неинициализированного сервиса
            self._set_status(_("status_service_not_init"), "#f87171")
            return
        
        # Очистка результатов
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        self._set_stat("results", 0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        
        # Локализация текста кнопки при запуске
        self.btn_run.configure(state="disabled", text=_("btn_running_analysis"))
        # Локализация переключения вкладки (ВАЖЛИВО: має співпадати з назвою при додаванні)
        self.tab_view.set(_("tab_results"))
        # Локализация статуса старта анализа
        self._set_status(_("status_starting_analysis"), PALETTE["text"])
        
        def callback(msg_type: str, data):
            """Callback для сервиса анализа"""
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
                # Цей код виконається, коли бекенд скаже "Я все"
                # Ми використовуємо self.after(0, ...), щоб безпечно оновити кнопку з головного потоку
                # Локализация текста кнопки после завершения
                self.after(0, lambda: self.btn_run.configure(state="normal", text=_("btn_run_analysis")))
                # Локализация статуса завершения
                self.after(0, lambda: self._set_status(_("status_analysis_finished"), "#22c55e"))
        
        threading.Thread(
            target=lambda: self.analysis_service.analyze_document(doc_id, callback),
            daemon=True
        ).start()
    
    def start_download_flow(self):
        """Запуск загрузки видео"""
        raw_links = self.links_box.get("1.0", "end").strip()

# --- ДОДАЙ ЦЕЙ БЛОК ТУТ ---
        print("\n" + "="*30)
        print("[DEBUG] ДІАГНОСТИКА ПОСИЛАНЬ")
        print(f"[DEBUG] Сирий текст з поля (в лапках): '{raw_links}'")
        # ---------------------------

        urls = [line.strip() for line in raw_links.splitlines() if line.strip()]

        # --- І ЦЕЙ БЛОК ТУТ ---
        print(f"[DEBUG] Знайдено окремих посилань: {len(urls)}")
        print(f"[DEBUG] Список для завантажувача: {urls}")
        print("="*30 + "\n")
        # ---------------------------
        if not urls:
            # Локализация ошибки отсутствия ссылок
            self._set_status(_("status_no_links"), "#f87171")
            print("[DEBUG] ❌ Помилка: список URL порожній, зупиняємося.")
            return
        
        self.reset_download_progress(len(urls))
        # Локализация текста кнопки при загрузке
        self.btn_download.configure(state="disabled", text=_("btn_downloading"))
        # Локализация статуса старта загрузки
        self._set_status(_("status_starting_download"), PALETTE["text"])
        threading.Thread(target=self.download_and_index_thread, args=(urls,), daemon=True).start()
    
    def download_and_index_thread(self, urls: list[str]):
        """Поток для загрузки и индексации"""
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
            # --- ДОДАЙ ЦЕЙ РЯДОК ТУТ ---
            print(f"\n[DEBUG] === ВІДПОВІДЬ ЗАВАНТАЖУВАЧА ===\n{results}\n=================================\n")
            # ---------------------------
            success_count = len([r for r in results if r.get("status") == "success"])
            
            if success_count:
                # Локализация статуса начала индексации
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
                
                # Локализация статуса завершения импорта с параметром
                self._set_status(_("status_import_finished", count=success_count))
                self.after(0, lambda: self.links_box.delete("1.0", "end"))
                self.after(0, lambda count=success_count: self._bump_stat("downloads", count))
                # Обновляем размер хранилища
                self.after(0, self.update_storage_info)
            else:
                # Локализация статуса "нет новых файлов"
                self._set_status(_("status_download_no_new"))
        except Exception as e:
            # Локализация ошибки загрузки с параметром
            self._set_status(_("status_download_error", error=e), "#f87171")
        finally:
            self.after(0, lambda count=success_count: self.set_indexing_state(False, count))
            # Локализация текста кнопки после завершения
            self.after(0, lambda: self.btn_download.configure(state="normal", text=_("btn_download_index")))
    
    def add_result_card(self, data):
        """Добавляет карточку результата"""
        meta = {
            "filename": data.get("filename"),
            "timestamp": data.get("timestamp"),
            "frame_path": data.get("frame_path"),
            "timecode": data.get("timecode"),
            "text_snippet": data.get("text_snippet"),
        }
        card = ResultCard(
            self.results_scroll,
            text_snippet=data['text_snippet'],
            tags=data.get('tags', ''),
            filename=data['filename'],
            timecode=data['timecode'],
            accuracy=data['accuracy'],
            meta=meta,
            on_feedback=self.handle_feedback,
            frame_path=data.get('frame_path')  # Передаем путь к кадру для превью
        )
        card.pack(fill="x", pady=5)
        # self.results_scroll._parent_canvas.yview_moveto(1.0)
        self._bump_stat("results", 1)
    
    def handle_feedback(self, meta: dict, value: str) -> bool:
        """Обработка обратной связи"""
        if not meta or not self.analysis_service:
            return False
        
        def worker():
            success = self.analysis_service.record_feedback(meta, value == "positive")
            if success:
                # Локализация успеха фидбека
                self._set_status(_("status_feedback_saved"), PALETTE["text"])
            else:
                # Локализация неудачи фидбека
                self._set_status(_("status_feedback_fail"), "#f87171")
        
        threading.Thread(target=worker, daemon=True).start()
        return True
    
    def reset_download_progress(self, total: int):
        """Сброс прогресса загрузки"""
        self.download_progress_total = total
        self.update_download_progress(0, total)
    
    def update_download_progress(self, current: int, total: int | None = None):
        """Обновление прогресса загрузки"""
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
        """Установка состояния индексации"""
        if running:
            # Локализация статуса индексации с параметром
            self.index_progress_label.configure(text=_("index_running", total=total))
            self.index_progress_bar.configure(mode="indeterminate")
            self.index_progress_bar.start()
        else:
            self.index_progress_bar.stop()
            self.index_progress_bar.configure(mode="determinate")
            self.index_progress_bar.set(1 if total else 0)
            # Локализация статуса завершения индексации
            self.index_progress_label.configure(text=_("index_finished") if total else _("index_not_started"))
    
    def _set_stat(self, key: str, value: int):
        """Установка статистики"""
        self.stats_data[key] = max(0, value)
        lbl = self.stat_cards.get(key)
        if lbl:
            lbl.configure(text=str(self.stats_data[key]))
        if key == "results":
            self.total_results = self.stats_data[key]
        if key == "downloads":
            self.total_downloads = self.stats_data[key]
    
    def _bump_stat(self, key: str, delta: int = 1):
        """Увеличение статистики"""
        current = self.stats_data.get(key, 0)
        self._set_stat(key, current + delta)
    
    def _set_status(self, text: str, color: str | None = None):
        """Установка статуса"""
        if color is None:
            color = PALETTE["muted"]
        self.lbl_status.configure(text=text, text_color=color)
    

    # Додайте цей метод у клас App в presentation/app.py

    def _paste_to_entry(self, entry_widget: ctk.CTkEntry):
        """Вставка тексту з буфера обміну в вказане поле"""
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                # Очищаємо поле і вставляємо новий текст
                entry_widget.delete(0, "end")
                entry_widget.insert(0, clipboard_text.strip())
        except Exception:
            # Локализация ошибки буфера обмена
            self._set_status(_("status_clipboard_empty"), "#f87171")

            
    def paste_links_from_clipboard(self):
        """Вставка ссылок из буфера обмена"""
        try:
            clipboard_text = self.clipboard_get()
        except Exception:
            # Локализация ошибки буфера обмена
            self._set_status(_("status_clipboard_empty"), "#f87171")
            return
        
        clipboard_text = clipboard_text.strip()
        if not clipboard_text:
            # Локализация ошибки пустого буфера
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
        # Локализация успеха вставки
        self._set_status(_("status_links_pasted"), PALETTE["text"])
    
    def log_message(self, text):
        """Добавление сообщения в лог"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # --- Новые методы для работы с хранилищем ---
    def _format_bytes(self, size: int) -> str:
        """Форматирует байты в человекочитаемый вид"""
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.1f} {power_labels.get(n, '')}B"

    def update_storage_info(self):
        """Обновляет информацию о размере хранилища"""
        if self.storage_service:
            size_bytes = self.storage_service.get_total_size_bytes()
            formatted_size = self._format_bytes(size_bytes)
            self.lbl_storage_size.configure(text=_("storage_size_label", size=formatted_size))

    def confirm_clear_storage(self):
        """Показывает диалог подтверждения очистки"""
        # Простой способ создать модальное окно подтверждения в CTk
        dialog = ctk.CTkToplevel(self)
        dialog.title(_("confirm_clear_title"))
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True) # Поверх основного окна
        
        # Центрируем окно
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # Контент диалога
        ctk.CTkLabel(dialog, text=_("confirm_clear_title"), font=("Inter", 16, "bold"), text_color=PALETTE["text"]).pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text=_("confirm_clear_text"), font=("Inter", 12), text_color=PALETTE["muted"], wraplength=350).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        def on_confirm():
            dialog.destroy()
            self._run_clear_storage()

        ctk.CTkButton(btn_frame, text="Отмена", fg_color=PALETTE["surface"], hover_color=PALETTE["border"], command=dialog.destroy, width=100).pack(side="left", expand=True, padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Удалить", fg_color=PALETTE["danger"], hover_color=PALETTE["danger_hover"], command=on_confirm, width=100).pack(side="left", expand=True)

        dialog.grab_set() # Модальный режим

    def _run_clear_storage(self):
        """Запускает процесс очистки в фоне"""
        if not self.storage_service:
            return

        self.btn_clear_storage.configure(state="disabled")
        self._set_status(_("status_clearing_started"), PALETTE["text"])

        def worker():
            success = self.storage_service.clear_project_storage()
            if success:
                self.after(0, lambda: self._set_status(_("status_clearing_finished"), "#22c55e"))
                # Сбрасываем статистику и результаты
                self.after(0, lambda: self._set_stat("downloads", 0))
                self.after(0, lambda: self._set_stat("results", 0))
                self.after(0, self.update_storage_info)
                # Очищаем список результатов в GUI
                self.after(0, lambda: [widget.destroy() for widget in self.results_scroll.winfo_children()])
            else:
                self.after(0, lambda: self._set_status(_("status_clearing_error"), "#f87171"))
            
            self.after(0, lambda: self.btn_clear_storage.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


__all__ = ['App']