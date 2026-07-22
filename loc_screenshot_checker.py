"""
Localization Screenshot Checker
================================
Compare screenshots across two language folders.
Uses one folder as source of truth, another as target.

Usage:
    py loc_screenshot_checker.py

Requirements:
    pip install Pillow
"""

import os
import sys
import platform
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk
import shutil

IS_MAC = platform.system() == "Darwin"

# ── Constants ──────────────────────────────────────────────────────────────────

BG_DARK = "#1a1a2e"
BG_PANEL = "#16213e"
BG_CARD = "#0f3460"
BG_SELECTED = "#1a3a6e"
BG_HOVER = "#12294e"
FG_TEXT = "#e0e0e0"
FG_DIM = "#8899aa"
FG_ACCENT = "#e94560"
FG_GREEN = "#4ecca3"
FG_YELLOW = "#f0c040"
FG_BLUE = "#4a9ff5"
FG_RED = "#e74c3c"
FONT_FAMILY = "SF Pro" if IS_MAC else "Segoe UI"
FONT_MONO_FAMILY = "Menlo" if IS_MAC else "Consolas"
FONT_TITLE = (FONT_FAMILY, 13, "bold")
FONT_NORMAL = (FONT_FAMILY, 11)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_MONO = (FONT_MONO_FAMILY, 10)
FONT_BIG = (FONT_FAMILY, 22, "bold")
FONT_LIST = (FONT_FAMILY, 10)
FONT_PLACEHOLDER = (FONT_FAMILY, 14)

SIDEBAR_WIDTH = 300
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

# Status constants
STATUS_BOTH = "both"
STATUS_SOURCE_ONLY = "source_only"
STATUS_TARGET_ONLY = "target_only"

STATUS_CONFIG = {
    STATUS_BOTH:        {"icon": "●", "color": FG_GREEN,  "label": "Both"},
    STATUS_SOURCE_ONLY: {"icon": "◑", "color": FG_YELLOW, "label": "Missing in target"},
    STATUS_TARGET_ONLY: {"icon": "◐", "color": FG_BLUE,   "label": "Extra in target"},
}


class LocChecker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Loc Screenshot Checker")
        self.configure(bg=BG_DARK)
        self.geometry("1400x850")
        self.minsize(1000, 600)

        # State
        self.source_dir: Path | None = None
        self.target_dir: Path | None = None
        self.all_images: list[tuple[str, str]] = []  # (filename, status)
        self.current_index = 0
        self.filter_status: str | None = None  # None = all
        self._photo_refs: list[ImageTk.PhotoImage] = []
        self._list_items: list[tk.Frame] = []

        self._build_ui()
        self._bind_keys()

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg=BG_PANEL, pady=8, padx=12)
        top.pack(fill="x")

        # Source folder
        tk.Button(
            top, text="📁 Source Folder", command=self._pick_source,
            bg=FG_GREEN, fg="#111", font=FONT_NORMAL, relief="flat",
            padx=10, pady=3, cursor="hand2", activebackground="#3ba884"
        ).pack(side="left")

        self.lbl_source = tk.Label(
            top, text="not selected", bg=BG_PANEL, fg=FG_DIM,
            font=FONT_SMALL, anchor="w"
        )
        self.lbl_source.pack(side="left", padx=(6, 18))

        # Target folder
        tk.Button(
            top, text="📁 Target Folder", command=self._pick_target,
            bg=FG_BLUE, fg="#111", font=FONT_NORMAL, relief="flat",
            padx=10, pady=3, cursor="hand2", activebackground="#3580cc"
        ).pack(side="left")

        self.lbl_target = tk.Label(
            top, text="not selected", bg=BG_PANEL, fg=FG_DIM,
            font=FONT_SMALL, anchor="w"
        )
        self.lbl_target.pack(side="left", padx=(6, 0))

        # Position label (right side)
        self.lbl_position = tk.Label(
            top, text="", bg=BG_PANEL, fg=FG_DIM, font=FONT_MONO
        )
        self.lbl_position.pack(side="right")

        # Main split: sidebar + content
        self.main = tk.Frame(self, bg=BG_DARK)
        self.main.pack(fill="both", expand=True)

        # ── Sidebar ──
        sidebar = tk.Frame(self.main, bg=BG_PANEL, width=SIDEBAR_WIDTH)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Filter buttons
        filter_bar = tk.Frame(sidebar, bg=BG_PANEL, pady=6, padx=8)
        filter_bar.pack(fill="x")

        self.filter_btns = {}
        self._make_filter_btn(filter_bar, "All", None, FG_TEXT, first=True)
        self._make_filter_btn(filter_bar, "●", STATUS_BOTH, FG_GREEN)
        self._make_filter_btn(filter_bar, "◑", STATUS_SOURCE_ONLY, FG_YELLOW)
        self._make_filter_btn(filter_bar, "◐", STATUS_TARGET_ONLY, FG_BLUE)

        # Count labels
        self.lbl_counts = tk.Label(
            sidebar, text="", bg=BG_PANEL, fg=FG_DIM, font=FONT_SMALL,
            anchor="w", padx=10
        )
        self.lbl_counts.pack(fill="x")

        # Separator
        tk.Frame(sidebar, bg=BG_CARD, height=1).pack(fill="x", pady=(4, 0))

        # Scrollable file list
        list_container = tk.Frame(sidebar, bg=BG_PANEL)
        list_container.pack(fill="both", expand=True)

        self.list_canvas = tk.Canvas(list_container, bg=BG_PANEL, highlightthickness=0, bd=0)
        self.list_scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.list_canvas.yview)
        self.list_frame = tk.Frame(self.list_canvas, bg=BG_PANEL)

        self.list_frame.bind("<Configure>", lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_canvas.configure(yscrollcommand=self.list_scrollbar.set)

        self.list_scrollbar.pack(side="right", fill="y")
        self.list_canvas.pack(side="left", fill="both", expand=True)

        # Mouse wheel scrolling (cross-platform)
        self.list_canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.list_canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        # ── Content area ──
        self.content = tk.Frame(self.main, bg=BG_DARK)
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self._show_welcome()

    def _make_filter_btn(self, parent, text, status, color, first=False):
        btn = tk.Button(
            parent, text=text, bg=BG_PANEL, fg=color,
            font=(FONT_FAMILY, 10, "bold"), relief="flat",
            padx=8, pady=1, cursor="hand2",
            activebackground=BG_CARD, activeforeground=color,
            command=lambda: self._set_filter(status)
        )
        btn.pack(side="left", padx=(0 if first else 4, 0))
        self.filter_btns[status] = btn

    def _show_welcome(self):
        for w in self.content.winfo_children():
            w.destroy()
        self._photo_refs.clear()

        frame = tk.Frame(self.content, bg=BG_DARK)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="📸", font=(FONT_FAMILY, 48), bg=BG_DARK, fg=FG_ACCENT).pack()
        tk.Label(
            frame, text="Loc Screenshot Checker", font=FONT_BIG, bg=BG_DARK, fg=FG_TEXT
        ).pack(pady=(4, 8))
        tk.Label(
            frame,
            text="Select a Source folder and a Target folder\nto compare localization screenshots.",
            font=FONT_NORMAL, bg=BG_DARK, fg=FG_DIM, justify="center"
        ).pack()

        # Legend
        legend = tk.Frame(frame, bg=BG_DARK)
        legend.pack(pady=(20, 0))
        for status, cfg in STATUS_CONFIG.items():
            row = tk.Frame(legend, bg=BG_DARK)
            row.pack(anchor="w", pady=1)
            tk.Label(row, text=cfg["icon"], fg=cfg["color"], bg=BG_DARK, font=(FONT_FAMILY, 12)).pack(side="left", padx=(0, 6))
            tk.Label(row, text=cfg["label"], fg=FG_DIM, bg=BG_DARK, font=FONT_SMALL).pack(side="left")

        tk.Label(
            frame,
            text="\n⌨  ↑↓: navigate list  •  Delete: remove target  •  Home/End: jump",
            font=FONT_SMALL, bg=BG_DARK, fg=FG_DIM, justify="center"
        ).pack(pady=(12, 0))

    # ── Key Bindings ───────────────────────────────────────────────────────

    def _bind_keys(self):
        self.bind("<Down>", lambda e: self._navigate(1))
        self.bind("<Up>", lambda e: self._navigate(-1))
        self.bind("<Right>", lambda e: self._navigate(1))
        self.bind("<Left>", lambda e: self._navigate(-1))
        self.bind("<Home>", lambda e: self._jump(0))
        self.bind("<End>", lambda e: self._jump(-1))
        self.bind("<Delete>", lambda e: self._delete_current())
        self.bind("<BackSpace>", lambda e: self._delete_current())  # macOS delete key
        self.bind("<space>", lambda e: self._navigate(1))

    def _bind_mousewheel(self):
        self.list_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        if IS_MAC:
            self.list_canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.list_canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self):
        self.list_canvas.unbind_all("<MouseWheel>")
        if IS_MAC:
            self.list_canvas.unbind_all("<Button-4>")
            self.list_canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if IS_MAC:
            if event.num == 4:
                self.list_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.list_canvas.yview_scroll(1, "units")
            else:
                self.list_canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            self.list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Folder Selection ───────────────────────────────────────────────────

    def _pick_source(self):
        path = filedialog.askdirectory(title="Select SOURCE folder (e.g. en/)")
        if not path:
            return
        self.source_dir = Path(path)
        self.lbl_source.config(text=self._short_path(self.source_dir), fg=FG_GREEN)
        self._refresh()

    def _pick_target(self):
        path = filedialog.askdirectory(title="Select TARGET folder (e.g. es/)")
        if not path:
            return
        self.target_dir = Path(path)
        self.lbl_target.config(text=self._short_path(self.target_dir), fg=FG_BLUE)
        self._refresh()

    def _short_path(self, p: Path) -> str:
        """Show parent/name for brevity."""
        return f"{p.parent.name}/{p.name}" if p.parent.name else p.name

    # ── Data Refresh ───────────────────────────────────────────────────────

    def _get_images(self, folder: Path) -> set[str]:
        if not folder or not folder.exists():
            return set()
        return {f.name for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS}

    def _refresh(self):
        if not self.source_dir or not self.target_dir:
            return

        src_files = self._get_images(self.source_dir)
        tgt_files = self._get_images(self.target_dir)

        # Build unified sorted list with statuses
        all_names = sorted(src_files | tgt_files)
        self.all_images = []
        for name in all_names:
            in_src = name in src_files
            in_tgt = name in tgt_files
            if in_src and in_tgt:
                status = STATUS_BOTH
            elif in_src:
                status = STATUS_SOURCE_ONLY
            else:
                status = STATUS_TARGET_ONLY
            self.all_images.append((name, status))

        # Update counts
        c_both = sum(1 for _, s in self.all_images if s == STATUS_BOTH)
        c_src = sum(1 for _, s in self.all_images if s == STATUS_SOURCE_ONLY)
        c_tgt = sum(1 for _, s in self.all_images if s == STATUS_TARGET_ONLY)
        self.lbl_counts.config(
            text=f"  {c_both} matched  •  {c_src} missing  •  {c_tgt} extra"
        )

        self.current_index = 0
        self._rebuild_list()
        self._render_preview()

    # ── Sidebar List ───────────────────────────────────────────────────────

    def _filtered_images(self) -> list[tuple[int, str, str]]:
        """Returns list of (original_index, name, status) matching current filter."""
        result = []
        for i, (name, status) in enumerate(self.all_images):
            if self.filter_status is None or status == self.filter_status:
                result.append((i, name, status))
        return result

    def _rebuild_list(self):
        # Clear old items
        for w in self.list_frame.winfo_children():
            w.destroy()
        self._list_items.clear()

        filtered = self._filtered_images()

        if not filtered:
            tk.Label(
                self.list_frame, text="No images", bg=BG_PANEL, fg=FG_DIM,
                font=FONT_SMALL, pady=20
            ).pack()
            return

        for orig_idx, name, status in filtered:
            cfg = STATUS_CONFIG[status]
            item = tk.Frame(self.list_frame, bg=BG_PANEL, cursor="hand2", padx=8, pady=4)
            item.pack(fill="x")

            icon_lbl = tk.Label(
                item, text=cfg["icon"], fg=cfg["color"], bg=BG_PANEL,
                font=(FONT_FAMILY, 11)
            )
            icon_lbl.pack(side="left", padx=(0, 6))

            name_lbl = tk.Label(
                item, text=name, fg=FG_TEXT, bg=BG_PANEL,
                font=FONT_LIST, anchor="w"
            )
            name_lbl.pack(side="left", fill="x", expand=True)

            # Store the original index in the item
            item._orig_index = orig_idx
            item._icon_lbl = icon_lbl
            item._name_lbl = name_lbl

            # Click handler
            for widget in (item, icon_lbl, name_lbl):
                widget.bind("<Button-1>", lambda e, idx=orig_idx: self._select(idx))

            # Hover effects
            def on_enter(e, f=item, il=icon_lbl, nl=name_lbl):
                if f._orig_index != self.current_index:
                    for w in (f, il, nl):
                        w.config(bg=BG_HOVER)

            def on_leave(e, f=item, il=icon_lbl, nl=name_lbl):
                if f._orig_index != self.current_index:
                    for w in (f, il, nl):
                        w.config(bg=BG_PANEL)

            for widget in (item, icon_lbl, name_lbl):
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)

            self._list_items.append(item)

        self._highlight_selected()

    def _highlight_selected(self):
        for item in self._list_items:
            is_sel = item._orig_index == self.current_index
            bg = BG_SELECTED if is_sel else BG_PANEL
            for w in (item, item._icon_lbl, item._name_lbl):
                w.config(bg=bg)

    def _scroll_to_selected(self):
        """Scroll the list so the selected item is visible."""
        filtered = self._filtered_images()
        # Find position of current_index in filtered list
        pos = None
        for i, (orig_idx, _, _) in enumerate(filtered):
            if orig_idx == self.current_index:
                pos = i
                break
        if pos is None or not self._list_items:
            return

        self.list_frame.update_idletasks()
        total_height = self.list_frame.winfo_reqheight()
        if total_height == 0:
            return
        item_y = self._list_items[pos].winfo_y()
        item_h = self._list_items[pos].winfo_reqheight()
        canvas_h = self.list_canvas.winfo_height()

        # Scroll so item is centered
        target = (item_y - canvas_h // 2 + item_h // 2) / total_height
        target = max(0.0, min(1.0, target))
        self.list_canvas.yview_moveto(target)

    # ── Filter ─────────────────────────────────────────────────────────────

    def _set_filter(self, status: str | None):
        self.filter_status = status

        # Update button highlights
        for s, btn in self.filter_btns.items():
            if s == status:
                btn.config(relief="sunken", bg=BG_CARD)
            else:
                btn.config(relief="flat", bg=BG_PANEL)

        # Try to keep the same image selected after filter change
        filtered = self._filtered_images()
        if filtered:
            # Find closest filtered item to current_index
            best = min(filtered, key=lambda x: abs(x[0] - self.current_index))
            self.current_index = best[0]
        self._rebuild_list()
        self._render_preview()

    # ── Selection & Navigation ─────────────────────────────────────────────

    def _select(self, orig_index: int):
        self.current_index = orig_index
        self._highlight_selected()
        self._render_preview()

    def _navigate(self, delta: int):
        filtered = self._filtered_images()
        if not filtered:
            return

        # Find current position in filtered list
        current_pos = None
        for i, (orig_idx, _, _) in enumerate(filtered):
            if orig_idx == self.current_index:
                current_pos = i
                break

        if current_pos is None:
            new_pos = 0
        else:
            new_pos = (current_pos + delta) % len(filtered)

        self.current_index = filtered[new_pos][0]
        self._highlight_selected()
        self._scroll_to_selected()
        self._render_preview()

    def _jump(self, pos: int):
        filtered = self._filtered_images()
        if not filtered:
            return
        if pos == -1:
            pos = len(filtered) - 1
        pos = max(0, min(pos, len(filtered) - 1))
        self.current_index = filtered[pos][0]
        self._highlight_selected()
        self._scroll_to_selected()
        self._render_preview()

    # ── Preview Rendering ──────────────────────────────────────────────────

    def _render_preview(self):
        for w in self.content.winfo_children():
            w.destroy()
        self._photo_refs.clear()

        if not self.all_images:
            self._show_welcome()
            self.lbl_position.config(text="")
            return

        filtered = self._filtered_images()
        # Find position in filtered list
        fpos = None
        for i, (orig_idx, _, _) in enumerate(filtered):
            if orig_idx == self.current_index:
                fpos = i
                break
        if fpos is None and filtered:
            self.current_index = filtered[0][0]
            fpos = 0

        if fpos is None:
            self.lbl_position.config(text="")
            self._show_empty()
            return

        name, status = self.all_images[self.current_index]
        self.lbl_position.config(text=f"  {fpos + 1} / {len(filtered)}  •  {name}")

        self._render_side_by_side(name, status)

    def _show_empty(self):
        frame = tk.Frame(self.content, bg=BG_DARK)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(frame, text="No images match this filter", font=FONT_TITLE,
                 bg=BG_DARK, fg=FG_DIM).pack()

    def _render_side_by_side(self, name: str, status: str):
        has_source = status in (STATUS_BOTH, STATUS_SOURCE_ONLY)
        has_target = status in (STATUS_BOTH, STATUS_TARGET_ONLY)

        # Header
        header = tk.Frame(self.content, bg=BG_DARK)
        header.pack(fill="x", pady=(0, 6))

        tk.Label(header, text=f"📄 {name}", font=FONT_TITLE, bg=BG_DARK, fg=FG_TEXT).pack(side="left")

        # Status badge
        cfg = STATUS_CONFIG[status]
        tk.Label(
            header, text=f"  {cfg['icon']} {cfg['label']}",
            font=FONT_SMALL, bg=BG_DARK, fg=cfg["color"]
        ).pack(side="left", padx=(8, 0))

        if has_target:
            tk.Button(
                header, text="🗑 Delete target copy",
                bg=FG_RED, fg="white", font=FONT_SMALL, relief="flat",
                padx=8, pady=2, cursor="hand2",
                command=lambda: self._delete_file(name, self.target_dir)
            ).pack(side="right", padx=4)

        # Panels
        panels = tk.Frame(self.content, bg=BG_DARK)
        panels.pack(fill="both", expand=True)
        panels.columnconfigure(0, weight=1, uniform="col")
        panels.columnconfigure(1, weight=1, uniform="col")
        panels.rowconfigure(1, weight=1)

        src_name = self._short_path(self.source_dir)
        tgt_name = self._short_path(self.target_dir)

        tk.Label(
            panels, text=f"Source  ({src_name})", font=FONT_NORMAL,
            bg=BG_CARD, fg=FG_GREEN, padx=8, pady=4
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))

        tk.Label(
            panels, text=f"Target  ({tgt_name})", font=FONT_NORMAL,
            bg=BG_CARD, fg=FG_BLUE, padx=8, pady=4
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # Source panel
        src_frame = tk.Frame(panels, bg=BG_PANEL)
        src_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 3), pady=(3, 0))
        if has_source:
            self._place_image(src_frame, self.source_dir / name)
        else:
            self._place_placeholder(src_frame, "No source image")

        # Target panel
        tgt_frame = tk.Frame(panels, bg=BG_PANEL)
        tgt_frame.grid(row=1, column=1, sticky="nsew", padx=(3, 0), pady=(3, 0))
        if has_target:
            self._place_image(tgt_frame, self.target_dir / name)
        else:
            self._place_placeholder(tgt_frame, "No target image")

    def _place_placeholder(self, parent: tk.Frame, text: str):
        """Show a centered placeholder message instead of an image."""
        canvas = tk.Canvas(parent, bg=BG_PANEL, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        def _draw(event=None):
            canvas.delete("all")
            cw = max(canvas.winfo_width(), 100)
            ch = max(canvas.winfo_height(), 100)
            # Dashed border rectangle
            pad = 30
            canvas.create_rectangle(
                pad, pad, cw - pad, ch - pad,
                outline=FG_DIM, width=2, dash=(6, 4)
            )
            canvas.create_text(
                cw // 2, ch // 2 - 14,
                text="✕", fill=FG_DIM, font=(FONT_FAMILY, 28)
            )
            canvas.create_text(
                cw // 2, ch // 2 + 20,
                text=text, fill=FG_DIM, font=FONT_PLACEHOLDER, justify="center"
            )

        canvas.bind("<Configure>", _draw)

    def _place_image(self, parent: tk.Frame, path: Path):
        canvas = tk.Canvas(parent, bg=BG_PANEL, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        def _load(event=None):
            canvas.delete("all")
            cw = max(canvas.winfo_width(), 100)
            ch = max(canvas.winfo_height(), 100)

            try:
                img = Image.open(path)
            except Exception as e:
                canvas.create_text(
                    cw // 2, ch // 2,
                    text=f"Error loading:\n{path.name}\n{e}",
                    fill=FG_ACCENT, font=FONT_SMALL, justify="center"
                )
                return

            iw, ih = img.size
            scale = min(cw / iw, ch / ih, 1.0)
            new_w, new_h = int(iw * scale), int(ih * scale)

            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img_resized)
            self._photo_refs.append(photo)
            canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center")

        canvas.bind("<Configure>", _load)

    # ── Delete ─────────────────────────────────────────────────────────────

    def _delete_current(self):
        if not self.all_images:
            return
        name, status = self.all_images[self.current_index]
        if status == STATUS_SOURCE_ONLY:
            messagebox.showinfo("Info", "This image only exists in source.\nNothing to delete from target.")
            return
        if status == STATUS_TARGET_ONLY:
            self._delete_file(name, self.target_dir)
        else:
            self._delete_file(name, self.target_dir)

    def _delete_file(self, name: str, folder: Path):
        path = folder / name
        if not path.exists():
            messagebox.showwarning("Not found", f"File already deleted:\n{path}")
            self._refresh()
            return

        if not messagebox.askyesno("Confirm Delete", f"Delete this file?\n\n{path}"):
            return

        try:
            try:
                import send2trash as s2t
                s2t.send2trash(str(path))
            except ImportError:
                path.unlink()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete:\n{e}")
            return

        self._refresh()


if __name__ == "__main__":
    app = LocChecker()
    app.mainloop()
