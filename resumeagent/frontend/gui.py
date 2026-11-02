import logging
import ast
import queue
from copy import deepcopy
from uuid import uuid4
from resumeagent.frontend.harness_tools import run_gui_tool, generate_or_resume
import json
from pathlib import Path
import os
import time
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from resumeagent.main import HomepageDesignAgent
from PIL import ImageTk, Image, ImageOps, ImageDraw
from resumeagent.utils import cal_cost
import asyncio
import shutil


from resumeagent.config import config
from resumeagent.llm.client import read_tokens

logger = logging.getLogger(__name__)


class _StudioSurface(tk.Canvas):
    """Cached translucent surface with debounced rendering."""

    def __init__(self, parent, *, tint='#FAF8FD', opacity=210, radius=12,
                 border='#EEE8F7', border_width=1, **kwargs):
        super().__init__(
            parent,
            bg=parent.cget('bg'),
            bd=0,
            highlightthickness=0,
            **kwargs
        )

        self._tint = tint
        self._opacity = opacity
        self._radius = radius
        self._border = border
        self._border_width = border_width

        self._surface_photo = None
        self._paint_after_id = None
        self._last_paint_key = None

        self.bind('<Configure>', self._schedule_paint_surface, add='+')

    def _schedule_paint_surface(self, event=None):
        """Debounce repeated resize events."""
        if self._paint_after_id is not None:
            try:
                self.after_cancel(self._paint_after_id)
            except tk.TclError:
                pass

        try:
            self._paint_after_id = self.after(
                80, self._paint_surface
            )
        except tk.TclError:
            self._paint_after_id = None

    def _paint_surface(self, event=None):
        self._paint_after_id = None

        width = self.winfo_width()
        height = self.winfo_height()

        if width < 3 or height < 3:
            return

        root = self.winfo_toplevel()
        wallpaper = getattr(root, '_wallpaper_body', None)
        origin = getattr(root, 'scrollable_frame', None)

        if wallpaper is not None and origin is not None:
            x = self.winfo_rootx() - origin.winfo_rootx()
            y = self.winfo_rooty() - origin.winfo_rooty()

            if width > wallpaper.width or height > wallpaper.height:
                base = ImageOps.fit(
                    wallpaper, (width, height)
                ).convert('RGBA')
            else:
                x = max(0, min(x, wallpaper.width - width))
                y = max(0, min(y, wallpaper.height - height))

                base = wallpaper.crop(
                    (x, y, x + width, y + height)
                ).convert('RGBA')
        else:
            base = Image.new(
                'RGBA', (width, height), self.cget('bg')
            )

        # 如果尺寸、位置和背景都没有变化，就不重新绘制。
        paint_key = (
            width, height, x if wallpaper is not None else 0,
            y if wallpaper is not None else 0,
            id(wallpaper), self._tint, self._opacity,
            self._radius, self._border, self._border_width
        )

        if paint_key == self._last_paint_key:
            return

        layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        draw.rounded_rectangle(
            (0, 0, width - 1, height - 1),
            radius=self._radius,
            fill=(
                *self.winfo_rgb8(self._tint),
                self._opacity
            ),
            outline=self._border,
            width=self._border_width
        )

        result = Image.alpha_composite(base, layer).convert('RGB')

        self._surface_photo = ImageTk.PhotoImage(result)

        self.delete('surface')
        self.create_image(
            0, 0,
            anchor='nw',
            image=self._surface_photo,
            tags='surface'
        )
        self.tag_lower('surface')

        self._last_paint_key = paint_key

    def winfo_rgb8(self, color):
        return tuple(
            value // 256 for value in self.winfo_rgb(color)
        )


class Application(tk.Tk):
    def __init__(self, agent: HomepageDesignAgent = None):
        super().__init__()

        self.title("ResumeAgent — Homepage Studio · Glass V7")
        self.agent = agent or HomepageDesignAgent()
        self._events = queue.Queue()
        self._worker = None
        self._closing = False
        self._destroyed = False
        self._cancel_requested = False
        self._cancelled_run_ids = set()
        self._cancel_event = threading.Event()
        self._resume_run_id = None
        self._page_states = {}
        self._disabled_widgets = []
        self._preview_attempts = set()
        self.last_error = None

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = min(max(screen_width - 40, 1280), 1800)
        window_height = min(max(screen_height - 80, 820), 1100)
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(1180, 740)

        self.colors = {
            "app": "#EEEAF6",
            # V7: clearer, more liquid glass. These are pre-blended tints that
            # simulate higher translucency while keeping text and controls sharp.
            "white": "#FAF8FD",
            "glass_panel": "#F6F4FB",
            "glass_header": "#F6F3FB",
            "glass_center": "#F4F8FD",
            "paper": "#FFFFFF",
            "ink": "#262236",
            "muted": "#726B85",
            "line": "#EAE4F1",
            "lavender": "#F1EBFE",
            "lavender_deep": "#7962C8",
            "lavender_dark": "#6550B4",
            "pink": "#FBEAF2",
            "pink_deep": "#C879A5",
            "blue": "#E8F2FD",
            "blue_deep": "#668CB9",
            "mint": "#E7F5EC",
            "mint_deep": "#4C886D",
            "peach": "#FCF0E8",
            "peach_deep": "#B9825F",
            "red": "#FBE8EB",
            "red_deep": "#BD6C7B",
            "field": "#FFFFFF",
            "stage": "#FAF8FD",
        }
        self.configure(bg=self.colors["app"])

        self.current_page = 0
        self.pages = []
        self.is_animating = False
        self.img_ref = None
        self.backup_folder_path = None
        self.buttons = []
        self._page_thumb_refs = []
        self._preview_source_image = None
        self._preview_canvas = None
        self._stage_bg_photo = None
        self._preview_photo = None
        self._shared_background_original = None
        self._shared_background_photo = None
        self._shared_background_label = None
        self._header_background_photo = None
        self._header_background_label = None
        # Background rendering cache
        self._background_refresh_after_id = None
        self._wallpaper_cache = None
        self._wallpaper_cache_key = None

        self._last_background_layout = None
        self._last_body_key = None
        self._last_header_key = None
        self._wallpaper_body = None
        self.shared_background_path = (
            Path(__file__).resolve().parents[2] / "gui_assets" / "shared_floral_background.png"
        )

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Studio.TMenubutton",
            background=self.colors["field"],
            foreground=self.colors["ink"],
            bordercolor=self.colors["line"],
            lightcolor=self.colors["line"],
            darkcolor=self.colors["line"],
            arrowcolor=self.colors["muted"],
            padding=(10, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "Studio.TMenubutton",
            background=[("active", "#F1EAFB")],
            foreground=[("active", self.colors["ink"])],
        )
        style.configure(
            "Studio.Vertical.TScrollbar",
            background="#D9CDEB",
            troughcolor="#F8F5FC",
            bordercolor="#F8F5FC",
            arrowcolor="#8D80A7",
            width=10,
        )
        style.configure(
            "Studio.Horizontal.TScrollbar",
            background="#D9CDEB",
            troughcolor="#F8F5FC",
            bordercolor="#F8F5FC",
            arrowcolor="#8D80A7",
        )

        # Top creative toolbar.
        # Draw the toolbar directly on a Canvas so the floral wallpaper remains
        # visible; ordinary Tk Frames/Labels do not support true transparency.
        self.title_frame = tk.Canvas(
            self, height=62, bg=self.colors["app"],
            bd=0, highlightthickness=0
        )
        self.title_frame.pack(side=tk.TOP, fill=tk.X)
        self.title_frame.pack_propagate(False)

        self._header_items = {}
        self._header_items["logo"] = self.title_frame.create_text(
            43, 23, text="✿", fill=self.colors["lavender_deep"],
            font=("Georgia", 22, "bold"), anchor="center",
            tags=("header-content",)
        )
        self._header_items["brand"] = self.title_frame.create_text(
            70, 20, text="ResumeAgent", fill=self.colors["ink"],
            font=("Segoe UI", 14, "bold"), anchor="w",
            tags=("header-content",)
        )
        self._header_items["subtitle"] = self.title_frame.create_text(
            71, 42, text="Homepage Studio", fill=self.colors["muted"],
            font=("Segoe UI", 8), anchor="w",
            tags=("header-content",)
        )

        self._header_items["breadcrumb"] = self.title_frame.create_text(
            0, 31, text="My website", fill=self.colors["muted"],
            font=("Segoe UI", 9), anchor="w",
            tags=("header-content",)
        )
        self._header_items["separator"] = self.title_frame.create_text(
            0, 31, text="›", fill="#C4BDCF",
            font=("Segoe UI", 13), anchor="w",
            tags=("header-content",)
        )
        self.current_page_label = self.title_frame.create_text(
            0, 31, text="Untitled page", fill=self.colors["ink"],
            font=("Segoe UI", 9, "bold"), anchor="w",
            tags=("header-content",)
        )

        self.model_menu_label = self.title_frame.create_text(
            0, 31, text="MODEL", fill=self.colors["muted"],
            font=("Segoe UI", 8, "bold"), anchor="e",
            tags=("header-content",)
        )

        self.css_frame_var = tk.StringVar(value="Tailwind")
        self.agent.css_frame = "Tailwind"

        llm_type = config.get("LLM_TYPE", "openai")
        if llm_type == "openai":
            self.web_design_model_options = ["gpt-4-turbo-2024-04-09", "gpt-4o"]
        elif llm_type == "qwen":
            self.web_design_model_options = ["qwen3.8-flash", "qwen3.8-max", "qwen3.8-2.4t-a95b", "qwen3.8-omni-flash"]
        else:
            self.web_design_model_options = [self.agent.model]

        selected_model = self.agent.model
        if selected_model not in self.web_design_model_options:
            self.web_design_model_options.append(selected_model)

        self.model_var = tk.StringVar(value=selected_model)
        self.model_menu = ttk.OptionMenu(
            self.title_frame, self.model_var, selected_model,
            *self.web_design_model_options, command=self.switch_model
        )
        self.model_menu.config(style="Studio.TMenubutton")
        self._model_menu_window = self.title_frame.create_window(
            0, 31, window=self.model_menu, anchor="e",
            width=260, height=38, tags=("header-content",)
        )
        self.agent.model = selected_model

        # Main three-part studio: pages/settings | large canvas | inspector.
        self.scrollable_frame = tk.Frame(self, bg=self.colors["app"])
        self.scrollable_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True,
            padx=18, pady=(15, 16)
        )
        self._install_shared_background()

        self.begin_time = time.time()
        self.begin_cost = read_tokens()
        self.total_cost = 0
        self.time_cost = 0

        self.web_design_widgets = self.create_web_design_widgets()
        self.model_menu.set_menu(selected_model, *self.web_design_model_options)
        self.agent.model = selected_model
        self.display_web_design_mode()
        self.display_table_page()
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self._poll_id = self.after(50, self._poll_operation)

    def _install_shared_background(self):
        """Install one shared wallpaper with cached rendering."""
        try:
            if not self.shared_background_path.exists():
                logger.warning(
                    "Shared background image not found: %s",
                    self.shared_background_path
                )
                return

            self._shared_background_original = Image.open(
                self.shared_background_path
            ).convert("RGB")

            self._shared_background_label = tk.Label(
                self.scrollable_frame,
                bd=0,
                highlightthickness=0,
                bg=self.colors["app"]
            )

            self._shared_background_label.place(
                x=0, y=0, relwidth=1, relheight=1
            )
            self._shared_background_label.lower()

            self.scrollable_frame.bind(
                "<Configure>",
                self._schedule_shared_background_refresh,
                add="+"
            )

            self.title_frame.bind(
                "<Configure>",
                self._schedule_shared_background_refresh,
                add="+"
            )

            self.bind(
                "<Configure>",
                self._schedule_shared_background_refresh,
                add="+"
            )

            # Paint the initial window once at idle; only later resize events
            # need the debounce, otherwise startup can remain blank until 120ms.
            self.after_idle(self._refresh_shared_background)

        except Exception:
            logger.exception(
                "Unable to install shared floral background"
            )


    def _schedule_shared_background_refresh(self, event=None):
        """Debounce wallpaper refresh during window resizing."""

        if self._background_refresh_after_id is not None:
            try:
                self.after_cancel(
                    self._background_refresh_after_id
                )
            except tk.TclError:
                pass

        try:
            self._background_refresh_after_id = self.after(
                0 if self._shared_background_photo is None else 120,
                self._refresh_shared_background
            )
        except tk.TclError:
            self._background_refresh_after_id = None


    def _refresh_shared_background(self, event=None):
        """Render wallpaper only when window geometry changes."""

        self._background_refresh_after_id = None

        if self._shared_background_original is None:
            return

        try:
            root_width = self.winfo_width()
            root_height = self.winfo_height()

            if root_width < 80 or root_height < 80:
                return

            root_size = (root_width, root_height)

            header_box = (
                self.title_frame.winfo_rootx() - self.winfo_rootx(),
                self.title_frame.winfo_rooty() - self.winfo_rooty(),
                self.title_frame.winfo_width(),
                self.title_frame.winfo_height()
            )

            body_box = (
                self.scrollable_frame.winfo_rootx() - self.winfo_rootx(),
                self.scrollable_frame.winfo_rooty() - self.winfo_rooty(),
                self.scrollable_frame.winfo_width(),
                self.scrollable_frame.winfo_height()
            )

            layout_key = (root_size, header_box, body_box)

            # 完全没有变化：直接返回。
            if layout_key == self._last_background_layout:
                return

            # 1. 整张壁纸只在窗口尺寸改变时重新缩放。
            resampling = getattr(
                Image, "Resampling", Image
            ).LANCZOS

            if self._wallpaper_cache_key != root_size:

                resampling = getattr(
                    Image, "Resampling", Image
                ).LANCZOS

                wallpaper = ImageOps.fit(
                    self._shared_background_original,
                    root_size,
                    method=resampling,
                    centering=(0.5, 0.5)
                )

                white = Image.new(
                    "RGB", wallpaper.size, "#FFFFFF"
                )

                self._wallpaper_cache = Image.blend(
                    white, wallpaper, 0.83
                )

                self._wallpaper_cache_key = root_size

            wallpaper = self._wallpaper_cache

            def crop_for(box):
                x, y, width, height = box

                width = max(1, width)
                height = max(1, height)

                left = max(
                    0, min(x, wallpaper.width - 1)
                )
                top = max(
                    0, min(y, wallpaper.height - 1)
                )

                right = min(
                    wallpaper.width, left + width
                )
                bottom = min(
                    wallpaper.height, top + height
                )

                crop = wallpaper.crop(
                    (left, top, right, bottom)
                )

                if crop.size != (width, height):
                    crop = ImageOps.fit(
                        crop,
                        (width, height),
                        method=resampling,
                        centering=(0.5, 0.5)
                    )

                return crop

            # 2. 主体背景只有发生变化才重新生成。
            body_key = (root_size, body_box)

            body_changed = body_key != self._last_body_key

            if body_changed:
                body = crop_for(body_box)

                self._wallpaper_body = body

                self._shared_background_photo = (
                    ImageTk.PhotoImage(body)
                )

                self._shared_background_label.configure(
                    image=self._shared_background_photo
                )

                self._shared_background_label.lower()

                self._last_body_key = body_key

            # 3. 顶部背景独立缓存，但与主体使用同一张壁纸。
            header_key = (root_size, header_box)

            if header_key != self._last_header_key:
                header = crop_for(header_box)

                self._header_background_photo = (
                    ImageTk.PhotoImage(header)
                )

                self.title_frame.delete("header-background")

                self.title_frame.create_image(
                    0, 0,
                    anchor="nw",
                    image=self._header_background_photo,
                    tags=("header-background",)
                )

                self.title_frame.tag_lower("header-background")

                self._last_header_key = header_key

            # 4. 更新顶部控件位置。
            width = self.title_frame.winfo_width()

            breadcrumb_x = max(
                300, int(width * 0.225)
            )

            self.title_frame.coords(
                self._header_items["breadcrumb"],
                breadcrumb_x, 31
            )

            self.title_frame.coords(
                self._header_items["separator"],
                breadcrumb_x + 94, 31
            )

            self.title_frame.coords(
                self.current_page_label,
                breadcrumb_x + 111, 31
            )

            self.title_frame.coords(
                self.model_menu_label,
                width - 292, 31
            )

            self.title_frame.coords(
                self._model_menu_window,
                width - 18, 31
            )

            # 5. 只有主体背景改变时才重绘玻璃面板。
            if body_changed:

                def repaint(parent):
                    for child in parent.winfo_children():
                        if isinstance(child, _StudioSurface):
                            child._schedule_paint_surface()

                        repaint(child)

                repaint(self.scrollable_frame)

            self._last_background_layout = layout_key

        except Exception:
            logger.exception(
                "Unable to refresh shared floral background"
            )

    def create_web_design_widgets(self):
        web_design_widgets = {}
        c = self.colors

        def make_panel(parent):
            return _StudioSurface(parent,tint='#F5F1FF',opacity=130,radius=14)

        def make_heading(parent, title, subtitle=None, bg=None):
            bg = bg or c["white"]
            holder = tk.Frame(parent, bg=bg)
            tk.Label(
                holder, text=title, bg=bg, fg=c["ink"],
                font=("Segoe UI", 11, "bold")
            ).pack(anchor="w")
            if subtitle:
                tk.Label(
                    holder, text=subtitle, bg=bg, fg=c["muted"],
                    font=("Segoe UI", 8)
                ).pack(anchor="w", pady=(3, 0))
            return holder

        def make_button(parent, text, command, kind="soft"):
            palette = {
                "primary": (c["lavender_deep"], "#FFFFFF", c["lavender_dark"]),
                "soft": (c["lavender"], c["lavender_deep"], "#DED2F5"),
                "mint": (c["mint"], c["mint_deep"], "#D3EBDD"),
                "peach": (c["peach"], c["peach_deep"], "#F6E0D0"),
                "plain": ("#FDFCFF", c["muted"], "#F6F2FB"),
                "danger": (c["red"], c["red_deep"], "#F2D7DC"),
            }
            bg, fg, active = palette[kind]
            button = tk.Button(
                parent, text=text, command=command,
                bg=bg, fg=fg, activebackground=active,
                activeforeground=fg, relief=tk.FLAT, bd=0,
                padx=7, pady=5, width=1, height=2, font=("Segoe UI", 8, "bold"),
                cursor="hand2", highlightthickness=0
            )
            button.bind('<Configure>',lambda event: event.widget.configure(wraplength=max(40,event.width-16)),add='+')
            return button

        # LEFT: page thumbnails and project details.
        input_frame = make_panel(self.scrollable_frame)
        web_design_widgets["input_frame"] = input_frame
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(4, weight=1)

        pages_header = tk.Frame(input_frame, bg=c["white"])
        pages_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 7))
        tk.Label(
            pages_header, text="Your pages",
            bg=c["white"], fg=c["ink"], font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)
        tk.Label(
            pages_header, text="STORY",
            bg=c["white"], fg=c["pink_deep"], font=("Segoe UI", 7, "bold")
        ).pack(side=tk.RIGHT)

        page_list_holder = tk.Frame(input_frame, bg=c["glass_panel"], height=240)
        page_list_holder.grid(row=1, column=0, sticky="ew", padx=10)
        page_list_holder.grid_propagate(False)
        page_list_holder.pack_propagate(False)
        input_frame.bind('<Configure>',lambda event: page_list_holder.configure(
            height=max(150,min(360,int(event.height*.34)))),add='+')

        page_nav_canvas = tk.Canvas(
            page_list_holder, bg=c["white"],
            highlightthickness=0, bd=0
        )
        page_nav_scrollbar = ttk.Scrollbar(
            page_list_holder, orient=tk.VERTICAL,
            command=page_nav_canvas.yview,
            style="Studio.Vertical.TScrollbar"
        )
        page_nav_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        page_nav_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        page_nav_frame = _StudioSurface(page_nav_canvas,tint='#F5F1FF',opacity=120,radius=0)
        page_nav_window = page_nav_canvas.create_window(
            (0, 0), window=page_nav_frame, anchor="nw"
        )
        page_nav_canvas.configure(yscrollcommand=page_nav_scrollbar.set)
        page_nav_frame.bind(
            "<Configure>",
            lambda event: page_nav_canvas.configure(
                scrollregion=page_nav_canvas.bbox("all")
            )
        )
        page_nav_canvas.bind(
            "<Configure>",
            lambda event: page_nav_canvas.itemconfigure(
                page_nav_window, width=event.width
            )
        )
        web_design_widgets["page_nav_frame"] = page_nav_frame

        separator = tk.Frame(input_frame, bg=c["line"], height=1)
        separator.grid(row=2, column=0, sticky="ew", padx=14, pady=(10, 9))

        details_header = make_heading(
            input_frame, "Your details",
            "A little context helps shape your site"
        )
        details_header.grid(row=3, column=0, sticky="new", padx=15, pady=(0, 7))

        settings_holder = tk.Frame(input_frame, bg=c["white"])
        settings_holder.grid(row=4, column=0, sticky="nsew", padx=10)
        settings_holder.grid_columnconfigure(0, weight=1)
        settings_holder.grid_rowconfigure(0, weight=1)

        settings_canvas = tk.Canvas(
            settings_holder, bg=c["white"],
            highlightthickness=0, bd=0
        )
        settings_scrollbar = ttk.Scrollbar(
            settings_holder, orient=tk.VERTICAL,
            command=settings_canvas.yview,
            style="Studio.Vertical.TScrollbar"
        )
        settings_canvas.grid(row=0, column=0, sticky="nsew")
        settings_scrollbar.grid(row=0, column=1, sticky="ns")
        settings_inner = _StudioSurface(settings_canvas,tint='#F5F1FF',opacity=140,radius=0)
        settings_window = settings_canvas.create_window(
            (0, 0), window=settings_inner, anchor="nw"
        )
        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)
        settings_inner.bind(
            "<Configure>",
            lambda event: settings_canvas.configure(
                scrollregion=settings_canvas.bbox("all")
            )
        )
        settings_canvas.bind(
            "<Configure>",
            lambda event: settings_canvas.itemconfigure(
                settings_window, width=event.width
            )
        )

        def field_label(parent, text):
            return tk.Label(
                parent, text=text, bg=c["white"], fg=c["muted"],
                font=("Segoe UI", 8), anchor="w"
            )

        form = _StudioSurface(settings_inner,tint='#F5F1FF',opacity=140,radius=0)
        form.pack(fill=tk.X, padx=7, pady=(2, 7))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=0, minsize=38)

        language_options = ["en", "zh"]
        self.language_var = tk.StringVar(value="en")
        language_menu = ttk.OptionMenu(
            form, self.language_var, language_options[0],
            *language_options, command=self.change_language
        )
        language_menu.config(style="Studio.TMenubutton")
        field_label(form, "Language").grid(row=0, column=0, columnspan=2, sticky="w", pady=(6,3))
        language_menu.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,7))

        css_frame_options = ["Tailwind", "Bootstrap", "Materialize", "Bulma", "None"]
        self.css_frame_var = tk.StringVar(value="Tailwind")
        css_frame_menu = ttk.OptionMenu(
            form, self.css_frame_var, css_frame_options[0],
            *css_frame_options, command=self.on_css_frame_change
        )
        css_frame_menu.config(style="Studio.TMenubutton")
        field_label(form, "CSS framework").grid(row=2, column=0, columnspan=2, sticky="w", pady=(4,3))
        css_frame_menu.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,7))

        status_options = ["student", "graduate", "entry_level", "mid_level", "expert"]
        self.status_var = tk.StringVar(value="student")
        status_menu = ttk.OptionMenu(
            form, self.status_var, status_options[0],
            *status_options, command=self.change_status
        )
        status_menu.config(style="Studio.TMenubutton")
        field_label(form, "Status").grid(row=4, column=0, columnspan=2, sticky="w", pady=(4,3))
        status_menu.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0,7))

        industry_options = [
            "tech", "creative", "finance", "healthcare", "education",
            "legal", "manufacturing", "public_service", "other"
        ]
        self.industry_var = tk.StringVar(value="tech")
        industry_menu = ttk.OptionMenu(
            form, self.industry_var, industry_options[0],
            *industry_options, command=self.on_industry_change
        )
        industry_menu.config(style="Studio.TMenubutton")
        field_label(form, "Industry").grid(row=6, column=0, columnspan=2, sticky="w", pady=(4,3))
        industry_menu.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0,7))

        input_labels = [
            "save_file", "basic_information", "academic_achievements",
            "experience", "professional_skills", "website_template_path",
            "feedback", "each refine times", "local_img_storage_path"
        ]
        visible_labels = [
            "Save folder", "About you", "Education & awards",
            "Experience", "Skills", "Website reference",
            "Design feedback", "Refinement rounds", "Local image folder"
        ]
        web_design_widgets["input_labels"] = []
        web_design_widgets["input_entries"] = []

        for idx, original_label in enumerate(input_labels):
            row = 8 + idx * 2
            label = field_label(form, visible_labels[idx])
            entry = tk.Entry(
                form, bg=c["field"], fg=c["ink"],
                insertbackground=c["lavender_deep"],
                relief=tk.FLAT, bd=0, width=1, font=("Segoe UI", 8),
                highlightthickness=1, highlightbackground="#F0ECF5",
                highlightcolor="#B29BE6"
            )
            label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(6,3))
            entry.grid(row=row+1, column=0, sticky="ew", padx=(0,5), pady=(0,5), ipady=6)

            if idx != 8:
                clear_button = tk.Button(
                    form, text="Clear",
                    command=lambda widget=entry: widget.delete(0, tk.END),
                    bg=c["white"], fg=c["muted"],
                    activebackground=c["lavender"], activeforeground=c["lavender_deep"],
                    relief=tk.FLAT, bd=0, padx=3,
                    font=("Segoe UI", 7), cursor="hand2"
                )
                clear_button.grid(row=row+1, column=1, sticky='e', padx=(0,1), pady=(0,5))

            web_design_widgets["input_labels"].append(label)
            web_design_widgets["input_entries"].append(entry)

        local_img_storage_button = tk.Button(
            form, text="Load",
            command=self.upload_local_img_storage,
            bg=c["lavender"], fg=c["lavender_deep"],
            activebackground="#DED2F5", activeforeground=c["lavender_deep"],
            relief=tk.FLAT, bd=0, padx=5,
            font=("Segoe UI", 7, "bold"), cursor="hand2"
        )
        local_img_storage_button.grid(row=25, column=1, padx=(0,1), pady=(0,5))

        gen_img_options = ["Gen", "Local", "None"]
        self.gen_img_var = tk.StringVar(value="Gen")
        gen_img_menu = ttk.OptionMenu(
            form, self.gen_img_var, gen_img_options[0],
            *gen_img_options, command=self.change_gen_img
        )
        gen_img_menu.config(style="Studio.TMenubutton")
        field_label(form, "Image source").grid(row=26, column=0, columnspan=2, sticky="w", pady=(6,3))
        gen_img_menu.grid(row=27, column=0, columnspan=2, sticky="ew", pady=(0,7))
        self.gen_img_menu = gen_img_menu
        self.agent.gen_img = gen_img_options[0]
        self._bind_studio_scroll(settings_inner,settings_canvas)

        # Run status and existing generation controls.
        runtime = tk.Frame(input_frame, bg=c["white"])
        runtime.grid(row=5, column=0, sticky="ew", padx=13, pady=(8, 5))
        runtime.grid_columnconfigure(1, weight=1)

        self.animation_idx = 0
        tk.Label(
            runtime, text="●", bg=c["white"], fg=c["mint_deep"],
            font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=0, sticky="w", padx=(1, 5))
        tk.Label(
            runtime, text="Agent status", bg=c["white"], fg=c["muted"],
            font=("Segoe UI", 8)
        ).grid(row=0, column=1, sticky="w")
        self.animation_label = tk.Label(
            runtime, text="Idle", bg=c["white"], fg=c["mint_deep"],
            font=("Segoe UI", 8, "bold")
        )
        self.animation_label.grid(row=0, column=2, sticky="e")

        self.token_cost_label = tk.Label(
            runtime, text="$0.00", bg=c["white"], fg=c["ink"],
            font=("Segoe UI", 8)
        )
        self.token_img_label = tk.Label(
            runtime, text="$0.00", bg=c["white"], fg=c["ink"],
            font=("Segoe UI", 8)
        )
        self.time_label = tk.Label(
            runtime, text="0 s", bg=c["white"], fg=c["ink"],
            font=("Segoe UI", 8)
        )
        for row, (label_text, value_label) in enumerate([
            ("Token cost", self.token_cost_label),
            ("Image cost", self.token_img_label),
            ("Time cost", self.time_label),
        ], start=1):
            tk.Label(
                runtime, text=label_text, bg=c["white"], fg=c["muted"],
                font=("Segoe UI", 7)
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=1)
            value_label.grid(row=row, column=2, sticky="e", pady=1)

        left_actions = tk.Frame(input_frame, bg=c["white"])
        left_actions.grid(row=6, column=0, sticky="ew", padx=10, pady=(4, 12))
        left_actions.grid_columnconfigure(0, weight=1)
        left_actions.grid_columnconfigure(1, weight=1)

        plan_button = make_button(left_actions, "Plan", self.plan, "primary")
        auto_gen_button = make_button(left_actions, "Auto Generate", self.auto_gen_website, "mint")
        clean_useless_imgs_button = make_button(
            left_actions, "Clean Useless IMG", self.clean, "plain"
        )
        cancel_button = make_button(left_actions, "Cancel", self.cancel, "peach")

        plan_button.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        auto_gen_button.grid(row=0, column=1, sticky="ew", padx=3, pady=3)
        clean_useless_imgs_button.grid(row=1, column=0, sticky="ew", padx=3, pady=3)
        cancel_button.grid(row=1, column=1, sticky="ew", padx=3, pady=3)

        web_design_widgets["plan_button"] = plan_button
        web_design_widgets["auto_gen_button"] = auto_gen_button
        web_design_widgets["clean_useless_imgs_button"] = clean_useless_imgs_button
        web_design_widgets["cancel"] = cancel_button
        web_design_widgets["cancel_button"] = cancel_button

        # CENTER: large, presentation-like preview canvas.
        preview_card = _StudioSurface(self.scrollable_frame,tint='#F8F6FF',opacity=150,radius=14)
        preview_card.grid_columnconfigure(0, weight=1)
        preview_card.grid_rowconfigure(1, weight=1)
        web_design_widgets["preview_card"] = preview_card

        preview_header = tk.Frame(preview_card, bg=c["white"])
        preview_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(15, 9))
        tk.Label(
            preview_header, text="Canvas",
            bg=c["white"], fg=c["ink"], font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)
        tk.Label(
            preview_header, text="A live look at your website",
            bg=c["white"], fg=c["muted"], font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=(11, 0), pady=(3, 0))
        self.preview_page_label = tk.Label(
            preview_header, text="PREVIEW",
            bg=c["lavender"], fg=c["lavender_deep"],
            font=("Segoe UI", 7, "bold"), padx=9, pady=4
        )
        self.preview_page_label.pack(side=tk.RIGHT)

        web_design_widgets["output_image_frame"] = tk.Frame(
            preview_card, bg=c["white"], bd=0,
            highlightthickness=0
        )
        web_design_widgets["output_image_frame"].grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 8)
        )

        preview_actions = tk.Frame(preview_card, bg=c["white"])
        preview_actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(3, 12))
        for column in range(4):
            preview_actions.grid_columnconfigure(column, weight=1)

        restore_backup_html_button = make_button(
            preview_actions, "Restore Backup", self.restore_backup_html, "plain"
        )
        create_button = make_button(
            preview_actions, "Create Website", self.create_website, "primary"
        )
        refine_button = make_button(
            preview_actions, "Refine Website", self.refine_website, "mint"
        )
        open_website_button = make_button(
            preview_actions, "Open Website", self.open_website, "soft"
        )

        for col, button in enumerate([
            restore_backup_html_button, create_button, refine_button, open_website_button
        ]):
            button.grid(row=0, column=col, sticky="ew", padx=3)

        web_design_widgets["restore_backup_html_button"] = restore_backup_html_button
        web_design_widgets["create_button"] = create_button
        web_design_widgets["refine_button"] = refine_button
        web_design_widgets["open_website_button"] = open_website_button

        # RIGHT: page inspector / editable page specification.
        editor_card = make_panel(self.scrollable_frame)
        editor_card.grid_columnconfigure(0, weight=1)
        editor_card.grid_rowconfigure(1, weight=1)
        web_design_widgets["editor_card"] = editor_card

        editor_header = make_heading(
            editor_card, "Page settings",
            "Fine-tune the selected page"
        )
        editor_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(15, 10))

        web_design_widgets["output_text"] = tk.Frame(
            editor_card, bg=c["white"], bd=0
        )
        web_design_widgets["output_text"].grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 7)
        )

        editor_actions = tk.Frame(editor_card, bg=c["white"])
        editor_actions.grid(row=2, column=0, sticky="ew", padx=10, pady=(3, 12))
        for column in range(2):
            editor_actions.grid_columnconfigure(column, weight=1)

        delete_page_button = make_button(
            editor_actions, "Delete Page", self.delete_page, "plain"
        )
        add_page_button = make_button(
            editor_actions, "Add Page", self.add_page, "soft"
        )
        complete_page_button = make_button(
            editor_actions, "Complete Page", self.complete_page, "soft"
        )
        refine_page_button = make_button(
            editor_actions, "Refine Page", self.refine_page, "mint"
        )

        delete_page_button.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        add_page_button.grid(row=0, column=1, sticky="ew", padx=3, pady=3)
        complete_page_button.grid(row=1, column=0, sticky="ew", padx=3, pady=3)
        refine_page_button.grid(row=1, column=1, sticky="ew", padx=3, pady=3)

        web_design_widgets["delete_page_button"] = delete_page_button
        web_design_widgets["add_page_button"] = add_page_button
        web_design_widgets["complete_page_button"] = complete_page_button
        web_design_widgets["refine_page_button"] = refine_page_button

        return web_design_widgets

    def cancel(self):
        self._cancel_requested = True
        self._cancel_event.set()
        self.agent.cancel_run()

    def on_css_frame_change(self, css_frame):
        if css_frame == "None":
            self.agent.css_frame = None
        else:
            self.agent.css_frame = css_frame
        logger.info(f"Change CSS Frame to: {css_frame}")

    def switch_model(self,model):
        self.agent.model = model
        logger.info(f"Switched to {model}")

    def upload_local_img_storage(self):
        if not self._prepare_operation():
            return
        if not self.agent.vision:
            messagebox.showerror('Input','Enable vision before loading images')
            return
        agent = self.agent
        self._start_operation('Loading images...',lambda:agent.managed_action('load_local_img_storage'))

    def change_gen_img(self,gen_img):
        if gen_img == "None":
            self.agent.gen_img = False
            self.agent.local_img_storage_copy = self.agent.local_img_storage.copy()
            self.agent.local_img_storage = []
        elif gen_img == "Local":
            if not self.agent.local_img_storage:
                messagebox.showerror("Please upload the local_img_storage, current is empty")
            self.agent.gen_img = gen_img
            if self.agent.local_img_storage_copy:
                self.agent.local_img_storage = self.agent.local_img_storage_copy.copy()
            logger.info("Local image entries: %s", len(self.agent.local_img_storage))
        else:
            self.agent.gen_img = gen_img
            self.agent.local_img_storage_copy = self.agent.local_img_storage.copy()
            self.agent.local_img_storage = []
        logger.info(f"Change Gen IMG to: {gen_img}")

    def change_language(self,language):
        self.agent.language = language
        logger.info(f"Change language to: {language}")

    def change_status(self,status):
        self.agent.status = status
        logger.info(f"Change your status: {status}")

    def on_industry_change(self,industry):
        self.agent.industry = industry
        logger.info(f"Change industry to: {industry}")

    def clear_widgets(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.grid_forget()

    def display_web_design_mode(self):
        self.scrollable_frame.grid_rowconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(0, weight=0, minsize=260)
        self.scrollable_frame.grid_columnconfigure(1, weight=1, minsize=400)
        self.scrollable_frame.grid_columnconfigure(2, weight=0, minsize=300)
        self.scrollable_frame.bind('<Configure>',self._resize_studio_columns,add='+')

        self.web_design_widgets["input_frame"].grid(
            row=0, column=0, sticky="nsew", padx=(0,8), pady=1
        )
        self.web_design_widgets["preview_card"].grid(
            row=0, column=1, sticky="nsew", padx=8, pady=1
        )
        self.web_design_widgets["editor_card"].grid(
            row=0, column=2, sticky="nsew", padx=(8,0), pady=1
        )

        self.web_design_widgets["input_frame"].configure(width=280)
        self.web_design_widgets["input_frame"].grid_propagate(False)
        self.web_design_widgets["editor_card"].configure(width=310)
        self.web_design_widgets["editor_card"].grid_propagate(False)

    def _resize_studio_columns(self,event=None):
        width=self.scrollable_frame.winfo_width()
        if width<500:
            return
        left=max(260,min(340,round(width*.18)))
        right=max(300,min(430,round(width*.24)))
        self.scrollable_frame.grid_columnconfigure(0,minsize=left)
        self.scrollable_frame.grid_columnconfigure(2,minsize=right)
        self.web_design_widgets['input_frame'].configure(width=left)
        self.web_design_widgets['editor_card'].configure(width=right)

    def _bind_studio_scroll(self,parent,canvas):
        def scroll(event):
            canvas.yview_scroll(-int(event.delta/120),'units')
            return 'break'
        if not isinstance(parent,tk.Text):
            parent.bind('<MouseWheel>',scroll,add='+')
        for child in parent.winfo_children():
            self._bind_studio_scroll(child,canvas)

    def read_input_entries(self):
        entries = self.web_design_widgets['input_entries']
        values = [entry.get().strip() for entry in entries]
        rounds = int(values[7]) if values[7] else 2
        if rounds < 0:
            raise ValueError('Refinement rounds must be a nonnegative integer')
        directory = str(Path(values[0] or self.agent.save_file).expanduser().resolve())
        self.agent.change_save_file(directory)
        for index,key in enumerate(('basic_information','academic_achievements','experience','professional_skills'),1):
            self.agent.task[key] = values[index]
        self.agent.task['img'] = values[5] if self.agent.vision and values[5] else None
        self.agent.user_feedback = values[6]
        self.agent.refine_times = rounds
        self.agent.local_img_storage_path = values[8]


    def plan(self):
        if not self._prepare_operation():
            return
        agent = self.agent
        if not any(agent.task.get(k) for k in ('basic_information','academic_achievements','experience','professional_skills','img')):
            messagebox.showerror('Input', 'Provide a profile or a website reference first')
            return
        def work():
            reference = agent.task.get('img')
            if reference and str(reference).startswith(('https://','http://')):
                target = str(Path(agent.save_file)/('reference-'+uuid4().hex[:8]+'.png'))
                agent.task['img'] = run_gui_tool(agent,'browser.reference',url=reference,screenshot_path=target)
            if self._cancel_event.is_set():
                return None
            return agent.managed_action('plan')
        self._start_operation('Planning...',work,self._apply_pages)

    def display_table_page(self):
        table_frame = self.web_design_widgets["output_text"]
        for widget in table_frame.winfo_children():
            widget.destroy()

        c = self.colors
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(1, weight=1)

        self.create_blocks(self.web_design_widgets["page_nav_frame"])

        has_page = bool(self.pages)
        self.current_page = max(0, min(self.current_page, len(self.pages) - 1))
        item = self.pages[self.current_page] if has_page else dict.fromkeys(
            ('html_name','js_description','description','relationship','practice_features',
             'additional_features','page_style','is_main_page'),'Plan or add a page to edit')
        html_name = item.get("html_name", f"page_{self.current_page + 1}.html") if has_page else 'Untitled page'

        if hasattr(self, "current_page_label"):
            self.title_frame.itemconfigure(self.current_page_label, text=html_name)
        if hasattr(self, "preview_page_label"):
            self.preview_page_label.config(text=html_name.upper())

        page_heading = tk.Frame(table_frame, bg=c["white"])
        page_heading.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 8))
        tk.Label(
            page_heading, text=html_name,
            bg=c["white"], fg=c["ink"], font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")
        tk.Label(
            page_heading, text=f"Page {self.current_page + 1} of {len(self.pages)}" if has_page else 'No page selected',
            bg=c["white"], fg=c["muted"], font=("Segoe UI", 7)
        ).pack(anchor="w", pady=(2, 0))

        editor_holder = tk.Frame(table_frame, bg=c["white"])
        editor_holder.grid(row=1, column=0, sticky="nsew")
        editor_holder.grid_columnconfigure(0, weight=1)
        editor_holder.grid_rowconfigure(0, weight=1)

        editor_canvas = tk.Canvas(
            editor_holder, bg=c["white"], highlightthickness=0, bd=0
        )
        editor_scrollbar = ttk.Scrollbar(
            editor_holder, orient=tk.VERTICAL,
            command=editor_canvas.yview,
            style="Studio.Vertical.TScrollbar"
        )
        editor_canvas.grid(row=0, column=0, sticky="nsew")
        editor_scrollbar.grid(row=0, column=1, sticky="ns")

        inner_frame = _StudioSurface(editor_canvas,tint='#F5F1FF',opacity=140,radius=0)
        inner_window = editor_canvas.create_window(
            (0, 0), window=inner_frame, anchor="nw"
        )
        inner_frame.grid_columnconfigure(0, weight=1)
        editor_canvas.configure(yscrollcommand=editor_scrollbar.set)

        for row, (key, value) in enumerate(item.items()):
            field = _StudioSurface(inner_frame,tint='#FFFFFF',opacity=246,radius=10,height=90,width=1)
            field.grid(row=row, column=0, sticky="ew", padx=3, pady=(0,9))
            field.grid_propagate(False)
            field.grid_columnconfigure(0, weight=1)
            field.grid_rowconfigure(1, weight=1)

            label_text = key.replace("_", " ").strip().title()
            tk.Label(
                field, text=label_text,
                bg=c["white"], fg=c["muted"],
                font=("Segoe UI", 8, "bold"), anchor="w"
            ).grid(row=0, column=0, sticky="ew", padx=9, pady=(7, 2))

            height = 2

            text_widget = tk.Text(
                field, wrap=tk.WORD, height=height, width=1,
                bg="#FEFDFF", fg=c["ink"],
                insertbackground=c["lavender_deep"],
                selectbackground="#E8DFFC",
                selectforeground=c["ink"],
                relief=tk.FLAT, bd=0,
                padx=8, pady=6,
                font=("Segoe UI", 8),
                highlightthickness=1,
                highlightbackground="#EEE9F4",
                highlightcolor="#B29BE6"
            )
            text_widget.insert(tk.END, str(value))
            text_widget.grid(row=1, column=0, sticky="nsew", padx=9, pady=(0,9))
            text_widget.bind(
                "<FocusIn>",
                lambda event: event.widget.config(state=tk.NORMAL)
            )
            text_widget.bind(
                "<FocusOut>",
                lambda event, k=key, idx=self.current_page:
                    self.save_value(event, k, idx)
            )
            if not has_page:
                text_widget.config(state=tk.DISABLED,fg=c['muted'])

        inner_frame.bind(
            "<Configure>",
            lambda event: editor_canvas.configure(
                scrollregion=editor_canvas.bbox("all")
            )
        )
        editor_canvas.bind(
            "<Configure>",
            lambda event: editor_canvas.itemconfigure(
                inner_window, width=event.width
            )
        )

        html_path = os.path.join(self.agent.save_file, html_name)
        page_name = Path(html_name).stem
        page_img_path = os.path.join(self.agent.save_file, f"{page_name}.png")
        self.update_ui_after_refine_website()
        self._bind_studio_scroll(inner_frame,editor_canvas)

    def create_blocks(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

        self.buttons = []
        self._page_thumb_refs = []
        c = self.colors

        if not self.pages:
            empty_card=_StudioSurface(frame,tint='#FFFFFF',opacity=235,radius=10,height=78,width=1)
            empty_card.pack(fill=tk.X,padx=5,pady=8)
            empty_card.pack_propagate(False)
            tk.Label(
                empty_card, text="Your first page starts here\nChoose Plan or Add Page",
                bg=c["white"], fg=c["muted"],
                font=("Segoe UI", 8),justify='left'
            ).pack(fill=tk.X, padx=12, pady=15)
            return

        for idx, value in enumerate(self.pages):
            html_name = value.get("html_name", f"page_{idx + 1}.html")
            page_name = Path(html_name).stem
            page_img_path = os.path.join(
                self.agent.save_file, f"{page_name}.png"
            )
            is_current = idx == self.current_page

            thumb = None
            if os.path.exists(page_img_path):
                try:
                    image = Image.open(page_img_path).convert("RGB")
                    image.thumbnail((52, 42))
                    tile = Image.new("RGB", (56, 44), "#F4EFFA")
                    tile.paste(
                        image,
                        ((56 - image.width) // 2, (44 - image.height) // 2)
                    )
                    thumb = ImageTk.PhotoImage(tile)
                except Exception:
                    logger.exception("Unable to load page thumbnail")

            if thumb is None:
                placeholder = Image.new(
                    "RGB", (56, 44),
                    ["#EEE7FA", "#F8E9F0", "#E7F0FA", "#E6F3EB"][idx % 4]
                )
                draw=ImageDraw.Draw(placeholder)
                for line,length in enumerate((38,32,25)):
                    draw.line((8,13+line*8,length+8,13+line*8),fill='#C5B5DE',width=2)
                thumb = ImageTk.PhotoImage(placeholder)

            self._page_thumb_refs.append(thumb)

            card=_StudioSurface(frame,tint='#FFFFFF',opacity=248,radius=10,
                                border=c['lavender_deep'] if is_current else '#ECE6F3',
                                border_width=2 if is_current else 1,height=76,width=1)
            card.pack(fill=tk.X,padx=5,pady=(0,10))
            card.pack_propagate(False)
            button = tk.Button(
                card,
                text=f"{idx + 1:02d}   {html_name}\n       {self._page_states.get(html_name,'Page')}",
                image=thumb,
                compound=tk.LEFT,
                anchor="w",
                command=lambda page_idx=idx: self.on_block_click(page_idx),
                bg="#FAF7FF" if is_current else "#FFFFFF",
                fg=c["lavender_deep"] if is_current else c["ink"],
                activebackground="#E9DFFC",
                activeforeground=c["lavender_deep"],
                relief=tk.FLAT,
                bd=0,
                padx=7, width=1, justify='left',
                pady=4,
                font=("Segoe UI", 8, "bold" if is_current else "normal"),
                cursor="hand2",
                highlightthickness=0,
                highlightbackground=c["lavender_deep"] if is_current else c["line"]
            )
            button.pack(fill=tk.BOTH,expand=True,padx=5,pady=5)
            self.buttons.append(button)
        self._bind_studio_scroll(frame,frame.master)

    def on_frame_resize(self, event):
        canvas_width = event.width
        self.nametowidget(self.block_canvas).itemconfig(self.inner_frame_id, width=canvas_width)

        self.nametowidget(self.block_canvas).config(scrollregion=self.nametowidget(self.block_canvas).bbox("all"))


    def on_block_click(self, idx):
        if not self.is_animating and 0<=idx<len(self.pages):
            self.current_page=idx
            self.display_table_page()


    def prev_page(self):
        self.on_block_click(self.current_page-1)

    def next_page(self):
        self.on_block_click(self.current_page+1)

    def delete_page(self):
        if self.is_animating or not self.pages:
            return
        name=self.pages.pop(self.current_page)['html_name']
        for page in self.pages:
            for key in ('buttons','links'):
                relation=page.get('relationship',{})
                relation[key]=[item for item in relation.get(key,[]) if item.get('jump_page','').split('#')[0]!=name]
        self.current_page=max(0,min(self.current_page,len(self.pages)-1))
        self._save_pages(self.agent.save_file)
        self.display_table_page()

    def refine_page(self):
        if not self._prepare_operation(require_page=True):
            return
        index,agent = self.current_page,self.agent
        page,feedback = deepcopy(self.pages[index]),agent.user_feedback
        def applied(value):
            if value is not None:
                self.pages[index] = value
                self._save_pages(agent.save_file)
            self.display_table_page()
        self._start_operation('Refining specification...',lambda:agent.managed_action('refine_page',page,feedback),applied)

    def restore_backup_html(self):
        if not self._prepare_operation(require_page=True):
            return
        agent,page = self.agent,deepcopy(self.pages[self.current_page])
        self._start_operation('Restoring backup...',lambda:run_gui_tool(agent,'gui.restore',page_info=page),
                              lambda value:self.display_table_page())

    def complete_page(self):
        if not self._prepare_operation(require_page=True):
            return
        pages,index,agent = deepcopy(self.pages),self.current_page,self.agent
        self._start_operation('Completing page...',lambda:agent.managed_action('complete_page',pages,index),self._apply_pages)

    def add_page(self):
        if self.is_animating:
            return
        names={page.get('html_name') for page in self.pages}
        number=1
        while f'page_{number}.html' in names:
            number+=1
        self.pages.append({'html_name':f'page_{number}.html','css_name':f'page_{number}.css',
                           'description':'','page_style':'','is_main_page':False,
                           'relationship':{'buttons':[],'links':[{'link_name':'Home','jump_page':self.pages[0]['html_name'] if self.pages else 'index.html'}]}})
        if len(self.pages)==1:
            self.pages[0]['html_name']='index.html'
            self.pages[0]['is_main_page']=True
        self.current_page=len(self.pages)-1
        self._save_pages(self.agent.save_file)
        self.display_table_page()


    def save_backup(self, current_path, backup_path):
        if os.path.exists(current_path):
            shutil.copy(current_path, backup_path)
            logger.info(f"备份已保存: {backup_path}")
        else:
            logger.info(f"当前文件 {current_path} 不存在，无法备份。")

    def open_website(self):
        if not self._prepare_operation(require_page=True):
            return
        agent,page = self.agent,deepcopy(self.pages[self.current_page])
        html_path = agent.page_paths(page)['html']
        if not Path(html_path).is_file():
            messagebox.showerror('Preview','Create this website page first')
            return
        self._start_operation('Opening website...',lambda:run_gui_tool(agent,'browser.preview',html_path=html_path))


    def save_value(self, event, key, idx):
        if self.is_animating or self._closing or idx>=len(self.pages):
            return
        widget=event.widget
        value=widget.get('1.0',tk.END).strip()
        try:
            if key=='relationship':
                try:
                    value=json.loads(value)
                except ValueError:
                    value=ast.literal_eval(value)
                if not isinstance(value,dict) or any(not isinstance(value.get(k,[]),list) for k in ('buttons','links','imgs')):
                    raise ValueError('Relationship must be an object with list entries')
            elif key=='is_main_page':
                if value.lower() not in ('true','false'):
                    raise ValueError('is_main_page must be true or false')
                value=value.lower()=='true'
            candidate=dict(self.pages[idx],**{key:value})
            self.agent.validate_page_spec(candidate)
            self.pages[idx]=candidate
            self._save_pages(self.agent.save_file)
        except (ValueError,TypeError,SyntaxError) as exc:
            messagebox.showerror('Page settings',str(exc))
        widget.config(state=tk.DISABLED)

    def _save_pages(self, directory):
        directory=Path(directory or self.agent.save_file).resolve()
        self.agent.tools.call('filesystem.write_json',path=str(directory/'pages.json'),data=self.pages)
        self.agent.task_queue=deepcopy(self.pages)

    def update_cost(self):
        tokens = read_tokens()
        llm_name = self.agent.model
        current_prompt_cost = tokens.get(llm_name, [0, 0])[0]
        current_completion_cost = tokens.get(llm_name, [0, 0])[1]
        total_prompt_cost = current_prompt_cost - self.begin_cost.get(llm_name, [0, 0])[0]
        total_completion_cost = current_completion_cost - self.begin_cost.get(llm_name, [0, 0])[1]
        self.total_cost = cal_cost(total_prompt_cost, total_completion_cost,self.agent.model)
        self.time_cost += time.time() - self.begin_time
        self.token_cost_label.config(text=f"${self.total_cost:.4f}")
        self.time_label.config(text=f"{self.time_cost:.1f} s")

    def create_website(self):
        if not self._prepare_operation(require_page=True):
            return
        page,agent = deepcopy(self.pages[self.current_page]),self.agent
        def work():
            run_gui_tool(agent,'gui.backup',page_info=page)
            if not self._cancel_event.is_set():
                agent.managed_action('write_original_website',page)
        self._start_operation('Creating...',work,lambda value:self.display_table_page())

    def refine_website(self):
        if not self._prepare_operation(require_page=True):
            return
        page,agent = deepcopy(self.pages[self.current_page]),self.agent
        if not Path(agent.page_paths(page)['html']).is_file():
            messagebox.showerror('Input','Create this website page first')
            return
        def work():
            run_gui_tool(agent,'gui.backup',page_info=page)
            if not self._cancel_event.is_set():
                agent.managed_action('refine',page)
        self._start_operation('Refining...',work,lambda value:self.display_table_page())

    def update_ui_after_refine_website(self):
        page = self.pages[self.current_page] if self.pages else {}
        html_name = page.get("html_name", "")
        frame = self.web_design_widgets["output_image_frame"]

        for widget in frame.winfo_children():
            widget.destroy()

        html_path = os.path.join(self.agent.save_file, html_name)
        page_name = Path(html_name).stem if html_name else ""
        page_img_path = os.path.join(self.agent.save_file, f"{page_name}.png")

        if html_name and os.path.exists(html_path) and not os.path.exists(page_img_path):
            signature = (html_path, Path(html_path).stat().st_mtime_ns)
            if not self.is_animating and signature not in self._preview_attempts:
                self._preview_attempts.add(signature)
                agent = self.agent
                self._start_operation('Rendering preview...',
                    lambda: run_gui_tool(agent,'browser.render',html_path=html_path,screenshot_path=page_img_path),
                    lambda value:self.update_ui_after_refine_website())

        stage = tk.Frame(frame, bg="#FEFDFF")
        stage.pack(fill=tk.BOTH, expand=True)

        stage_canvas = tk.Canvas(
            stage, bg="#FEFDFF",
            highlightthickness=0, bd=0
        )
        stage_scrollbar = ttk.Scrollbar(
            stage, orient=tk.VERTICAL,
            command=stage_canvas.yview,
            style="Studio.Vertical.TScrollbar"
        )
        stage_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stage_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        stage_canvas.configure(yscrollcommand=stage_scrollbar.set)

        self._preview_canvas = stage_canvas
        self._preview_source_image = None

        if os.path.exists(page_img_path):
            try:
                self._preview_source_image = Image.open(page_img_path).convert("RGB")
            except Exception:
                logger.exception("Unable to open generated screenshot")

        if self._preview_source_image is None:
            self._draw_empty_creative_stage()
        else:
            self._draw_creative_preview()

        stage_canvas.bind(
            "<Configure>",
            lambda event: self._draw_creative_preview()
            if self._preview_source_image is not None else self._draw_empty_creative_stage()
        )

    def _make_preview_background(self, width, height):
        """The preview canvas is a clean white surface; the floral wallpaper is global."""
        return Image.new("RGB", (max(1, int(width)), max(1, int(height))), "#FFFFFF")

    def _draw_empty_creative_stage(self):
        if self._preview_canvas is None:
            return
        canvas=self._preview_canvas
        canvas.delete('all')
        view_width=max(220,canvas.winfo_width())
        view_height=max(240,canvas.winfo_height())
        floral_stage=self._make_preview_background(view_width,view_height)
        bg_photo=ImageTk.PhotoImage(floral_stage)
        self._stage_bg_photo=bg_photo
        canvas.create_image(0,0,image=bg_photo,anchor='nw')
        x0,y0,x1,y1=12,12,view_width-12,view_height-14
        canvas.create_rectangle(x0,y0,x1,y1,fill='#FFFFFF',outline='#ECE7F3')
        canvas.create_rectangle(x0+1,y0+1,x1-1,y0+42,fill='#FCFAFF',outline='')
        for offset,color in enumerate(('#E9A2A8','#E9C987','#9CCCB1')):
            start_x=x0+16+offset*17
            canvas.create_oval(start_x,y0+17,start_x+9,y0+26,fill=color,outline='')
        canvas.create_rectangle(x0+83,y0+10,x1-14,y0+32,fill='#F4F0FA',outline='')
        canvas.create_text(x0+94,y0+21,text='Generated page preview',anchor='w',fill='#8B8598',font=('Segoe UI',8))
        canvas.create_text(view_width/2,view_height*.51,text='Your generated website appears here',
                           width=max(150,view_width-70),justify='center',fill=self.colors['ink'],font=('Segoe UI',13,'bold'))
        canvas.create_text(view_width/2,view_height*.51+52,text='Create or refine a page to view the actual screenshot.',
                           width=max(150,view_width-85),justify='center',fill=self.colors['muted'],font=('Segoe UI',9))
        canvas.configure(scrollregion=(0,0,view_width,view_height))

    def _draw_creative_preview(self):
        if self._preview_canvas is None or self._preview_source_image is None:
            return
        canvas=self._preview_canvas
        canvas.delete('all')
        view_width=max(220,canvas.winfo_width())
        view_height=max(240,canvas.winfo_height())
        source_image=self._preview_source_image.copy()
        target_width=max(150,view_width-48)
        target_height=max(1,round(source_image.height*target_width/source_image.width))
        source_image=source_image.resize((target_width,target_height),getattr(Image,'Resampling',Image).LANCZOS)
        stage_height=max(view_height,source_image.height+90)
        floral_stage=self._make_preview_background(view_width,stage_height)
        bg_photo=ImageTk.PhotoImage(floral_stage)
        self._stage_bg_photo=bg_photo
        canvas.create_image(0,0,image=bg_photo,anchor='nw')
        image_x,image_y=24,62
        frame_left,frame_top,frame_right,frame_bottom=12,12,view_width-12,max(view_height-14,image_y+source_image.height+12)
        canvas.create_rectangle(frame_left,frame_top,frame_right,frame_bottom,fill='#FFFFFF',outline='#ECE7F3')
        canvas.create_rectangle(frame_left+1,frame_top+1,frame_right-1,image_y-10,fill='#FCFAFF',outline='')
        for offset,color in enumerate(('#E9A2A8','#E9C987','#9CCCB1')):
            x=frame_left+16+offset*17
            canvas.create_oval(x,frame_top+17,x+9,frame_top+26,fill=color,outline='')
        canvas.create_rectangle(frame_left+83,frame_top+10,frame_right-14,frame_top+32,fill='#F4F0FA',outline='')
        canvas.create_text(frame_left+94,frame_top+21,text='Live website preview',anchor='w',fill='#8D8799',font=('Segoe UI',8))
        preview_photo=ImageTk.PhotoImage(source_image)
        self._preview_photo=preview_photo
        self.img_ref=preview_photo
        canvas.create_image(image_x,image_y,image=preview_photo,anchor='nw')
        canvas.configure(scrollregion=(0,0,view_width,frame_bottom+14))


    def auto_gen_website(self):
        if not self._prepare_operation():
            return
        agent,pages,resume_id = self.agent,deepcopy(self.pages),self._resume_run_id
        self._start_operation('Generating through Harness Runtime...',
                              lambda:generate_or_resume(agent,pages,resume_id),self._apply_pages)

    def clean(self):
        if not self._prepare_operation():
            return
        agent=self.agent
        self._start_operation('Cleaning unused images...',lambda:run_gui_tool(agent,'gui.clean'),
                              lambda value:self.display_table_page())

    def create_backup_folder(self, save_file):
        backup_folder = os.path.join(save_file, "backup")
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
            logger.info(f"Backup 文件夹已创建: {backup_folder}")
        else:
            logger.info(f"Backup 文件夹已存在: {backup_folder}")
        return backup_folder

    def animate(self,animation_sequence):
        pending = getattr(self, '_animation_after_id', None)
        if pending:
            self.after_cancel(pending)
            self._animation_after_id = None
        if self.is_animating and animation_sequence:
            # A previous action may have used a longer animation sequence.
            self.animation_idx %= len(animation_sequence)
            self.animation_label.config(text=animation_sequence[self.animation_idx], fg=self.colors["lavender_deep"])
            self.animation_idx = (self.animation_idx + 1) % len(animation_sequence)
            self._animation_after_id = self.after(300, lambda: self.animate(animation_sequence))
        else:
            self.animation_label.config(text="Idle", fg=self.colors["mint_deep"])


    def _prepare_operation(self, require_page=False):
        if self.is_animating or self._closing:
            return False
        try:
            self.read_input_entries()
            if require_page:
                if not self.pages:
                    raise ValueError('Plan or add a page first')
                self.agent.validate_page_spec(self.pages[self.current_page])
            return True
        except (ValueError, TypeError, OSError) as exc:
            messagebox.showerror('Input', str(exc))
            return False

    def _set_busy(self, busy):
        self.is_animating = busy
        if not busy:
            for widget, state in self._disabled_widgets:
                if widget.winfo_exists():
                    widget.configure(state=state)
            self._disabled_widgets = []
            return
        cancel = self.web_design_widgets.get('cancel_button')
        def walk(parent):
            for widget in parent.winfo_children():
                if widget is not cancel and isinstance(widget,(tk.Button,tk.Entry,tk.Text,ttk.Menubutton)):
                    self._disabled_widgets.append((widget,widget.cget('state')))
                    widget.configure(state=tk.DISABLED)
                walk(widget)
        walk(self)

    def _start_operation(self, label, work, on_success=None):
        if self.is_animating or self._closing:
            return False
        self._cancel_requested = False
        self._cancel_event.clear()
        self._cancelled_run_ids = set()
        self._on_success = on_success
        self.last_error = None
        self.begin_time = time.time()
        self._set_busy(True)
        self.animate([label])
        events,agent = self._events,self.agent
        prior_run = agent.last_run_id
        # Neither the worker nor completion delivery calls Tcl/after/messagebox.
        self._worker = threading.Thread(target=self._operation_worker,
                                        args=(events,agent,prior_run,work),daemon=True)
        self._worker.start()
        return True

    @staticmethod
    def _operation_worker(events, agent, prior_run, work):
        value, failure, record, states = None, None, None, {}
        try:
            value = work()
        except Exception as exc:
            failure = {'type':type(exc).__name__, 'message':type(exc).__name__}
            if isinstance(exc,(ValueError,FileNotFoundError)):
                failure['message'] = str(exc)
            result = getattr(exc,'result',None)
            if result:
                record = result
        try:
            if agent.last_run_id and (agent.last_run_id != prior_run or record):
                runtime = agent._runtime()
                record = record or runtime.state.get_run(agent.last_run_id)
                states = {p['spec']['html_name']:p['status'] for p in runtime.state.pages(record['id'])}
                if failure:
                    path = runtime.tracer.diagnostic_path(record['id'])
                    details = []
                    if path.is_file():
                        details = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
                    specific = next((d for d in reversed(details) if d.get('error_type') not in ('RuntimeError','RunStopped')),None)
                    failure.update(run_id=record['id'],stage=(specific or {}).get('stage',record['stage']),
                                   type=(specific or {}).get('error_type',record.get('error') or failure['type']),
                                   message=(specific or {}).get('message',failure['message']),
                                   diagnostic=str(path),task_id=(specific or {}).get('task_id',''))
        except Exception:
            logger.error('Could not read GUI operation diagnostic metadata')
        events.put((value,failure,record,states))

    def _poll_operation(self):
        if self._destroyed:
            return
        if self._cancel_requested or self._closing:
            runtime = self.agent.active_runtime
            if runtime is not None and runtime.run_id not in self._cancelled_run_ids:
                runtime.cancel(runtime.run_id)
                self._cancelled_run_ids.add(runtime.run_id)
        # A worker posts just before returning: wait for its actual exit, so a
        # success callback cannot overwrite the still-running worker reference.
        if self._worker is None or not self._worker.is_alive():
            try:
                value,failure,record,states = self._events.get_nowait()
            except queue.Empty:
                pass
            else:
                self._worker = None
                self._set_busy(False)
                self._page_states.update(states)
                if record:
                    self.title(f'ResumeAgent — Homepage Studio · Glass V7 | Run {record["id"]} · {record["status"]}')
                    if not record['context']['settings'].get('action'):
                        self._resume_run_id = record['id'] if record['status'] != 'completed' else None
                if not self._closing:
                    try:
                        if failure:
                            self.last_error = failure
                            text = (f'The operation could not finish.\nRun ID: {failure.get("run_id","not created")}\n'
                                    f'Stage: {failure.get("stage","input")}\nTask ID: {failure.get("task_id","")}\n'
                                    f'{failure["type"]}: {failure["message"]}\n'
                                    f'Developer diagnostics: {failure.get("diagnostic","not available")}')
                            logger.error('GUI operation failed: %s, Run %s',failure['type'],failure.get('run_id'))
                            messagebox.showerror('Runtime',text)
                        elif self._on_success:
                            self._on_success(value)
                    except Exception as exc:
                        self.last_error = {'type':type(exc).__name__,'message':'Unable to update the GUI; generated artifacts are preserved'}
                        logger.error('GUI completion callback failed: %s',type(exc).__name__)
                        messagebox.showerror('GUI',self.last_error['message']+' ('+type(exc).__name__+')')
                    finally:
                        self.update_cost()
                        if not self.is_animating:
                            self.animate([])
        if self._closing and (self._worker is None or not self._worker.is_alive()):
            if not getattr(self,'_cleanup_started',False):
                self._cleanup_started = True
                agent = self.agent
                self._worker = threading.Thread(target=agent.close,daemon=True)
                self._worker.start()
            elif not self._worker.is_alive():
                self._final_destroy()
                return
        self._poll_id = self.after(50,self._poll_operation)

    def _apply_pages(self, pages):
        if pages is not None:
            self.pages = deepcopy(pages)
            self.current_page = max(0,min(self.current_page,len(self.pages)-1))
            self._save_pages(self.agent.save_file)
        self.display_table_page()

    def _on_close(self):
        if self._closing:
            return
        self._closing = True
        self._cancel_requested = True
        self._cancel_event.set()
        self.withdraw()

    def _final_destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        for pending in self.tk.call('after','info'):
            # Cancel Tcl events without deleting another widget's registered
            # Python command. Each owning widget releases it during destroy().
            self.tk.call('after','cancel',pending)
        super().destroy()

    def destroy(self):
        if self._worker is not None and self._worker.is_alive():
            self._on_close()
        else:
            self._final_destroy()


def main():
    from resumeagent.main import main as run
    run(['--gui'])


if __name__ == '__main__':
    main()
