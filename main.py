import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import os
import urllib.request
import urllib.error
import io
import sys
import json
import ctypes
import uuid
from datetime import datetime as dt

# Fix for Windows taskbar icon grouping (forces separate taskbar button per window)
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(str(uuid.uuid4()))
except (AttributeError, OSError):
    pass

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

# ─── Palette ────────────────────────────────────────────────────────────────────
BG          = "#5ea8a7"
SURFACE     = "#161616"
CARD        = "#1e1e1e"
CARD_HOVER  = "#252525"
BORDER      = "#2a2a2a"
ACCENT      = "#ff3333"
ACCENT_DARK = "#cc2222"
ACCENT_LITE = "#ff5555"
TEXT        = "#f0f0f0"
TEXT_MID    = "#a0a0a0"
TEXT_DIM    = "#555555"
SUCCESS     = "#00cc66"
WARNING     = "#ffaa00"
INPUT_BG    = "#111111"
CANVAS_BG   = "#0a0a0a"

# ─── History persistence ────────────────────────────────────────────────────────
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")
MAX_HISTORY  = 200

def load_history():
    if os.path.isfile(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[-MAX_HISTORY:]
        except Exception:
            pass
    return []

def save_history(entries):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(entries[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

_history = load_history()

# ─── Helpers ───────────────────────────────────────────────────────────────────
def hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return r, g, b, alpha

def rgba_to_hex(r, g, b, a=255):
    return f"#{r:02x}{g:02x}{b:02x}"

def lighten(hex_color, amount=0.15):
    r, g, b, a = hex_to_rgba(hex_color)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02x}{g:02x}{b:02x}"

def darken(hex_color, amount=0.1):
    r, g, b, a = hex_to_rgba(hex_color)
    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))
    return f"#{r:02x}{g:02x}{b:02x}"

def tag(widget, **kwargs):
    for key, val in kwargs.items():
        widget.tag_configure(key, **val)

# ─── Window ────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("YT-DLP Video Downloader")
root.geometry("1100x680")
root.minsize(900, 560)
root.configure(bg=BG)

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
win_w, win_h = 1100, 680
root.geometry(f"{win_w}x{win_h}+{(screen_w-win_w)//2}+{(screen_h-win_h)//2}")

# ─── App Icon ──────────────────────────────────────────────────────────────────
_ico_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "1486485559-118arrow-down-download-downloads-downloading-save_81191.ico"
)
try:
    from PIL import Image, ImageTk
    _img = Image.open(_ico_path)
    _icon_img = ImageTk.PhotoImage(_img)
    root.iconphoto(True, _icon_img)
except Exception:
    try:
        root.iconbitmap(_ico_path)
    except Exception:
        pass

# ─── Custom TFrame ─────────────────────────────────────────────────────────────
def make_card(parent, **kw):
    f = tk.Frame(parent, bg=CARD, bd=0, highlightthickness=0, **kw)
    return f

def make_sunken(parent, **kw):
    f = tk.Frame(parent, bg=INPUT_BG, bd=0, highlightthickness=0, **kw)
    return f

# ─── Modern Entry ──────────────────────────────────────────────────────────────
class ModernEntry:
    def __init__(self, parent, placeholder="", width=40):
        self.var = tk.StringVar()
        self.placeholder = placeholder
        self._showing_placeholder = True
        self._placeholder_text = placeholder

        self.frame = make_sunken(parent, width=width)
        self.entry = tk.Entry(
            self.frame, textvariable=self.var, bg=INPUT_BG, fg=TEXT,
            font=("Segoe UI", 10), bd=0, insertbackground=TEXT,
            highlightthickness=0, width=width
        )
        self.entry.pack(fill="both", expand=True, padx=10, pady=8)

        if not self.var.get():
            self._show_placeholder()
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.var.trace_add("write", self._on_var_change)

    def _show_placeholder(self):
        if not self._showing_placeholder:
            return
        self._showing_placeholder = True
        self.entry.configure(fg=TEXT_DIM)

    def _on_var_change(self, *a):
        if not self._showing_placeholder and self.var.get() == "":
            self._show_placeholder()

    def _on_focus_in(self, e):
        if self._showing_placeholder:
            self._showing_placeholder = False
            self.var.set("")
        self.entry.configure(fg=TEXT)

    def _on_focus_out(self, e):
        if self.var.get() == "":
            self._show_placeholder()

    def get(self):
        v = self.var.get()
        return "" if v == self.placeholder else v

    def set(self, value):
        self._showing_placeholder = False
        self.var.set(value)
        self.entry.configure(fg=TEXT)

    def clear(self):
        self.var.set("")
        self._show_placeholder()

    def bind_key(self, seq, func):
        self.entry.bind(seq, func)

    @property
    def widget(self):
        return self.frame

# ─── Modern Button ──────────────────────────────────────────────────────────────
class ModernButton:
    def __init__(self, parent, text="", icon="", command=None,
                 bg=ACCENT, fg=TEXT, w=14, h=1, font_size=10,
                 radius=True, **kw):
        self._bg = bg
        self._fg = fg
        self._hover_bg = lighten(bg, 0.12)
        self._active_bg = darken(bg, 0.1)
        self._command = command
        self._enabled = True

        label = f"  {icon}  {text}" if icon else f"  {text}  "
        self.btn = tk.Button(
            parent, text=label, bg=bg, fg=fg,
            font=("Segoe UI", font_size, "bold"),
            activebackground=self._active_bg, activeforeground=fg,
            bd=0, highlightthickness=0, relief="flat",
            cursor="hand2", command=command, **kw
        )
        self.btn.bind("<Enter>", self._on_enter)
        self.btn.bind("<Leave>", self._on_leave)
        self.btn.bind("<ButtonPress-1>", self._on_press)
        self.btn.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, e):
        if self._enabled:
            self.btn.configure(bg=self._hover_bg)

    def _on_leave(self, e):
        if self._enabled:
            self.btn.configure(bg=self._bg)

    def _on_press(self, e):
        if self._enabled:
            self.btn.configure(bg=self._active_bg)

    def _on_release(self, e):
        if self._enabled:
            self.btn.configure(bg=self._hover_bg)
            if self._command:
                self._command()

    def enable(self):
        self._enabled = True
        self.btn.configure(bg=self._bg, fg=self._fg, state="normal")

    def disable(self):
        self._enabled = False
        self.btn.configure(bg="#1a1a1a", fg=TEXT_DIM, state="disabled")

    def configure_command(self, command):
        self._command = command
        self.btn.configure(command=command)

    @property
    def widget(self):
        return self.btn

# ─── Progress Bar ──────────────────────────────────────────────────────────────
class ModernProgress:
    def __init__(self, parent, height=8):
        self.value = 0
        self.max = 100
        self.height = height

        self.canvas = tk.Canvas(
            parent, bg=SURFACE, height=height, highlightthickness=0
        )
        self.track = self.canvas.create_rectangle(
            0, 0, 3000, height, fill="#1f1f1f", width=0
        )
        self.bar = self.canvas.create_rectangle(
            0, 0, 0, height, fill=ACCENT, width=0
        )
        self._track_id = self.track
        self._bar_id = self.bar

    def set(self, val):
        self.value = max(0, min(val, self.max))
        self._draw()

    def _draw(self):
        self.canvas.delete(self._bar_id)
        w = self.canvas.winfo_width() or 600
        pct = self.value / self.max
        bw = int(w * pct)
        self._bar_id = self.canvas.create_rectangle(
            0, 0, bw, self.height, fill=ACCENT, width=0
        )
        self.canvas.tag_lower(self._track_id)
        self.canvas.tag_raise(self._bar_id)

    def pack(self, **kw):
        self.canvas.pack(**kw)
        self.canvas.after(50, self._draw)

    def grid(self, **kw):
        self.canvas.grid(**kw)
        self.canvas.after(50, self._draw)

    @property
    def widget(self):
        return self.canvas

# ─── Pill Selector ─────────────────────────────────────────────────────────────
class PillSelector:
    def __init__(self, parent, options, command=None, default=0):
        self.options = list(options)
        self.command = command
        self.selection = tk.IntVar(value=default)

        self.frame = tk.Frame(parent, bg=SURFACE)

        self.pills = []
        for i, opt in enumerate(self.options):
            lbl = tk.Label(
                self.frame, text=opt, bg=SURFACE, fg=TEXT_DIM,
                font=("Segoe UI", 8, "bold"),
                highlightthickness=0, bd=0, cursor="hand2"
            )
            lbl.pack(side="left", padx=(0, 4))
            lbl.bind("<Button-1>", lambda e, idx=i: self._select(idx))
            self.pills.append(lbl)

        self._select(default)

    def _select(self, idx):
        self.selection.set(idx)
        for i, lbl in enumerate(self.pills):
            if i == idx:
                lbl.configure(bg=ACCENT, fg=TEXT)
            else:
                lbl.configure(bg="#222222", fg=TEXT_DIM)
        if self.command:
            self.command(idx)

    @property
    def widget(self):
        return self.frame

# ─── State ─────────────────────────────────────────────────────────────────────
_state = {
    "video_info": None,
    "formats": [],
    "format_labels": [],
    "selected_format": 0,
    "output_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
    "cancel_event": threading.Event(),
    "busy": False,
    "queue": queue.Queue(),
}

# ─── Widget references ─────────────────────────────────────────────────────────
url_entry   = None
fetch_btn  = None
dl_btn     = None
cancel_btn = None
progress_w = None
status_lbl = None
thumb_canv = None
title_lbl  = None
meta_lbl   = None
format_combo = None
history_tree = None
output_entry = None

# ─── Dispatch queue ─────────────────────────────────────────────────────────────
def _dispatch(fn):
    _state["queue"].put(fn)

def _poll_queue():
    while True:
        try:
            fn = _state["queue"].get_nowait()
        except queue.Empty:
            break
        try:
            fn()
        except Exception:
            import traceback; traceback.print_exc()
    root.after(60, _poll_queue)

# ─── Utilities ─────────────────────────────────────────────────────────────────
def set_status(msg, color=TEXT_MID):
    status_lbl.configure(text=msg, fg=color)

def set_busy(busy, msg=""):
    _state["busy"] = busy
    if msg:
        set_status(msg, TEXT_DIM)
    if busy:
        fetch_btn.disable()
        url_entry.entry.configure(state="disabled")
    else:
        fetch_btn.enable()
        url_entry.entry.configure(state="normal")

def enable_dl(enable):
    if enable:
        dl_btn.enable()
    else:
        dl_btn.disable()

def update_progress(pct):
    progress_w.set(pct)
    root.update_idletasks()

def _human_size(n):
    if not n:
        return "—"
    for u in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024:
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TiB"

def _fmt_duration(s):
    if not s:
        return ""
    m, s = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

def add_history_row(time_str, title, quality, status, status_tag):
    """Insert a row into the history Treeview and persist to JSON."""
    history_tree.insert("", "end",
                        values=(time_str, title, quality, status),
                        tags=(status_tag,))
    global _history
    _history.append({"time": time_str, "title": title,
                     "quality": quality, "status": status})
    save_history(_history)

# ─── Thumbnail ─────────────────────────────────────────────────────────────────
_thumb_photo = None

def show_thumb_placeholder():
    thumb_canv.delete("all")
    thumb_canv.configure(bg="#0a0a0a")
    thumb_canv.create_text(
        140, 80, text="No preview", fill=TEXT_DIM,
        font=("Segoe UI", 9), anchor="center"
    )

def set_thumbnail(data):
    global _thumb_photo
    if not data:
        show_thumb_placeholder()
        return
    try:
        from PIL import Image, ImageTk
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img.thumbnail((280, 158), Image.LANCZOS)
        _thumb_photo = ImageTk.PhotoImage(img)
        thumb_canv.delete("all")
        thumb_canv.create_image(140, 79, image=_thumb_photo, anchor="center")
    except Exception:
        show_thumb_placeholder()

# ─── Format list ───────────────────────────────────────────────────────────────
def build_format_list(info):
    formats = []
    for f in info.get("formats", []):
        vc = f.get("vcodec") or ""
        ac = f.get("acodec") or ""
        if vc != "none" and ac != "none":
            res = f.get("resolution") or ""
            ext = (f.get("ext") or "").upper()
            fps = f.get("fps")
            size = _human_size(f.get("filesize") or f.get("filesize_approx") or 0)
            parts = [p for p in [res, ext, fps and f"{fps}fps", size] if p and p != "—"]
            label = " ".join(parts) if parts else "Unknown"
            formats.append((label, f.get("format_id")))
    if not formats:
        for f in info.get("formats", []):
            vc = f.get("vcodec") or ""
            ac = f.get("acodec") or ""
            if vc == "none" and ac != "none":
                ext = (f.get("ext") or "MP3").upper()
                tbr = f.get("tbr")
                tbr_str = f", ~{int(tbr)}kbps" if tbr else ""
                label = f"Audio only ({ext}{tbr_str})"
                formats.append((label, "bestaudio"))
    return formats

# ─── Download worker ────────────────────────────────────────────────────────────
def do_fetch(url):
    try:
        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        _state["video_info"] = info
        formats = build_format_list(info)
        _state["formats"] = formats
        _state["format_labels"] = [f[0] for f in formats]
        title = info.get("title", "")
        dur = _fmt_duration(info.get("duration") or 0)
        uploader = info.get("uploader", "") or info.get("creator", "")
        views = info.get("view_count") or 0
        view_str = f"{views/1_000_000:.1f}M views" if views >= 1_000_000 else (
                   f"{views/1000:.0f}K views" if views >= 1000 else f"{views} views" if views else "")
        thumb_url = info.get("thumbnail")
        thumb_data = None
        if thumb_url:
            try:
                req = urllib.request.Request(
                    thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                thumb_data = urllib.request.urlopen(req, timeout=10).read()
            except Exception:
                thumb_data = None

        def on_ready():
            set_busy(False)
            format_combo["values"] = _state["format_labels"]
            if _state["format_labels"]:
                format_combo.current(0)
            set_thumbnail(thumb_data)
            title_lbl.configure(text=title or "(untitled)", fg=TEXT)
            meta_lbl.configure(text=f"{dur}  •  {uploader}  •  {view_str}", fg=TEXT_MID)
            set_status("Ready. Choose quality and download.", SUCCESS)
            enable_dl(True)

        _dispatch(on_ready)

    except Exception as exc:
        def on_err():
            set_busy(False)
            _state["video_info"] = None
            _state["formats"] = []
            _state["format_labels"] = []
            format_combo["values"] = []
            show_thumb_placeholder()
            title_lbl.configure(text="(no video selected)", fg=TEXT_DIM)
            meta_lbl.configure(text="", fg=TEXT_DIM)
            enable_dl(False)
            set_status(f"Error: {exc}", WARNING)
            messagebox.showerror("Fetch Error", f"Could not fetch video info:\n{exc}")

        _dispatch(on_err)

def do_download(url, fmt_id, out_dir, video_title=""):
    _state["cancel_event"].clear()

    def hook(d):
        if _state["cancel_event"].is_set():
            raise yt_dlp.utils.DownloadError("cancelled")
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done  = d.get("downloaded_bytes") or 0
            if total:
                pct = done / total * 100
                _dispatch(lambda p=pct: update_progress(p))
            else:
                _dispatch(lambda d_=done: set_status(
                    f"Downloading... {_human_size(d_)}", TEXT_MID))
        elif d["status"] == "finished":
            _dispatch(lambda: set_status("Finalizing...", TEXT_MID))

    try:
        opts = {
            "format": fmt_id or "best",
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "quiet": True, "no_warnings": True, "noprogress": True,
            "progress_hooks": [hook], "restrict_filenames": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        def on_ok():
            update_progress(100)
            ts = dt.now().strftime("%H:%M:%S")
            title_short = (video_title or url)[:60]
            add_history_row(ts, title_short, fmt_id or "best", "Done", "done")
            set_status(f"Download complete!  {ts}", SUCCESS)
            enable_dl(True)
            cancel_btn.disable()

        _dispatch(on_ok)

    except yt_dlp.utils.DownloadError as e:
        if _state["cancel_event"].is_set():
            def on_cancel():
                ts = dt.now().strftime("%H:%M:%S")
                add_history_row(ts, (video_title or url)[:60],
                                fmt_id or "best", "Cancelled", "warn")
                set_status("Download cancelled.", WARNING)
                enable_dl(True)
                cancel_btn.disable()
            _dispatch(on_cancel)
        else:
            def on_dl_err():
                set_status(f"Download failed: {e}", WARNING)
                enable_dl(True)
                cancel_btn.disable()
                messagebox.showerror("Download Error", str(e))
            _dispatch(on_dl_err)

    except Exception as e:
        def on_dl_err():
            set_status(f"Download failed: {e}", WARNING)
            enable_dl(True)
            cancel_btn.disable()
            messagebox.showerror("Download Error", str(e))
        _dispatch(on_dl_err)

# ─── Callbacks ─────────────────────────────────────────────────────────────────
def on_fetch():
    url = url_entry.get().strip()
    if not url:
        set_status("Enter a URL first.", WARNING)
        return
    if not YTDLP_AVAILABLE:
        set_status("yt-dlp is not installed.", WARNING)
        messagebox.showerror("Missing Dependency", "yt-dlp is not installed.\nRun: pip install yt-dlp")
        return
    set_busy(True, "Fetching video info...")
    enable_dl(False)
    threading.Thread(target=do_fetch, args=(url,), daemon=True).start()

def on_download():
    url = url_entry.get().strip()
    if not url or not _state["video_info"]:
        set_status("Fetch a video first.", WARNING)
        return
    d = _state["output_dir"]
    if not os.path.isdir(d):
        set_status("Invalid download folder.", WARNING)
        return
    sel = format_combo.current()
    fmt_id = _state["formats"][sel][1] if sel < len(_state["formats"]) else "best"
    set_busy(True, "Downloading...")
    enable_dl(False)
    cancel_btn.enable()
    progress_w.set(0)
    threading.Thread(target=do_download,
                    args=(url, fmt_id, d,
                          _state["video_info"].get("title", "")),
                    daemon=True).start()

def on_cancel():
    _state["cancel_event"].set()
    cancel_btn.disable()
    set_status("Cancelling...", TEXT_MID)

def on_browse():
    d = filedialog.askdirectory(title="Choose download folder",
                                initialdir=_state["output_dir"])
    if d:
        _state["output_dir"] = d
        output_entry.configure(state="normal")
        output_entry.delete(0, tk.END)
        output_entry.insert(0, d)
        output_entry.configure(state="readonly")

def on_paste(e=None):
    try:
        clip = root.clipboard_get()
        cur = url_entry.get().strip()
        if not cur or cur == url_entry.placeholder:
            url_entry.set(clip)
    except Exception:
        pass

def on_entry_key(e):
    if e.keysym == "Return":
        on_fetch()

# ─── Build UI ──────────────────────────────────────────────────────────────────
# ═══ OUTER SHELL ════════════════════════════════════════════════════════════════
shell = tk.Frame(root, bg=BG)
shell.pack(fill="both", expand=True)

# Top bar
topbar = tk.Frame(shell, bg=BG, height=48)
topbar.pack(fill="x")
topbar.propagate(False)

tk.Frame(topbar, bg=ACCENT, width=4).pack(side="left", fill="y", pady=10, padx=(16, 0))

tk.Label(topbar, text="YT", bg=BG, fg=ACCENT,
         font=("Segoe UI", 20, "bold"), anchor="w"
).pack(side="left", padx=(12, 2))

tk.Label(topbar, text="-DLP", bg=BG, fg=TEXT,
         font=("Segoe UI", 20, "bold"), anchor="w"
).pack(side="left")

tk.Label(topbar, text="Video Downloader",
         bg=BG, fg=TEXT_DIM, font=("Segoe UI", 9),
         anchor="e"
).pack(side="right", padx=20)

# ═══ MAIN CONTENT ════════════════════════════════════════════════════════════════
content = tk.Frame(shell, bg=BG)
content.pack(fill="both", expand=True, padx=16, pady=(4, 8))

# ─── LEFT PANEL ───────────────────────────────────────────────────────────────
left = tk.Frame(content, bg=BG)
left.pack(side="left", fill="both", expand=True, padx=(0, 12))

# URL card
url_card = make_card(left)
url_card.pack(fill="x", pady=(0, 10))

tk.Label(url_card, text="VIDEO URL",
         bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 8, "bold"),
         anchor="w"
).pack(fill="x", padx=14, pady=(12, 0))

url_row = tk.Frame(url_card, bg=CARD)
url_row.pack(fill="x", padx=14, pady=(8, 10))
url_row.pack(fill="x")

url_entry = ModernEntry(url_row, placeholder="Paste YouTube / video URL here...", width=52)
url_entry.widget.pack(side="left", fill="x", expand=True)
url_entry.bind_key("<Control-v>", on_paste)
url_entry.bind_key("<Return>", on_entry_key)

paste_btn_wrap = tk.Frame(url_row, bg=CARD, width=4)
paste_btn_wrap.pack(side="right", padx=(8, 0))

btn_paste = ModernButton(paste_btn_wrap, text="PASTE", icon="",
                         bg="#2a2a2a", fg=TEXT, font_size=8,
                         command=on_paste)
btn_paste.widget.pack()

# Preview card
preview_card = make_card(left)
preview_card.pack(fill="x", pady=(0, 10))

tk.Label(preview_card, text="PREVIEW",
         bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 8, "bold"),
         anchor="w"
).pack(fill="x", padx=14, pady=(12, 0))

thumb_canv = tk.Canvas(preview_card, bg=CANVAS_BG,
                        width=280, height=158,
                        highlightthickness=0, bd=0)
thumb_canv.pack(padx=14, pady=10)
show_thumb_placeholder()

meta_row = tk.Frame(preview_card, bg=CARD)
meta_row.pack(fill="x", padx=14, pady=(0, 10))
meta_row.pack(fill="x")

title_lbl = tk.Label(meta_row, text="(no video selected)",
                     bg=CARD, fg=TEXT_DIM,
                     font=("Segoe UI", 9, "bold"), anchor="w",
                      justify="left")
title_lbl.pack(fill="x")

meta_lbl = tk.Label(meta_row, text="",
                     bg=CARD, fg=TEXT_DIM,
                     font=("Segoe UI", 8), anchor="w")
meta_lbl.pack(fill="x", pady=(2, 0))

# Quality card
quality_card = make_card(left)
quality_card.pack(fill="x", pady=(0, 10))

tk.Label(quality_card, text="QUALITY",
         bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 8, "bold"),
         anchor="w"
).pack(fill="x", padx=14, pady=(12, 0))

combo_frame = tk.Frame(quality_card, bg=CARD)
combo_frame.pack(fill="x", padx=14, pady=(8, 10))

format_combo = ttk.Combobox(combo_frame, values=[],
                            state="readonly", font=("Segoe UI", 9),
                            background=INPUT_BG, foreground=TEXT)
format_combo.pack(fill="x")
if format_combo["values"]:
    format_combo.current(0)

# Output card
output_card = make_card(left)
output_card.pack(fill="x", pady=(0, 14))

tk.Label(output_card, text="SAVE TO",
         bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 8, "bold"),
         anchor="w"
).pack(fill="x", padx=14, pady=(12, 0))

out_row = tk.Frame(output_card, bg=CARD)
out_row.pack(fill="x", padx=14, pady=(8, 12))

output_entry = tk.Entry(out_row, bg=INPUT_BG, fg=TEXT,
                         font=("Segoe UI", 9), bd=0, insertbackground=TEXT,
                         highlightthickness=0, readonlybackground=INPUT_BG)
output_entry.insert(0, _state["output_dir"])
output_entry.configure(state="readonly")
output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

btn_browse = ModernButton(out_row, text="BROWSE", icon="",
                           bg="#2a2a2a", fg=TEXT, font_size=8,
                           command=on_browse)
btn_browse.widget.pack(side="right")

# Progress card
prog_card = make_card(left)
prog_card.pack(fill="x", pady=(0, 14))

tk.Label(prog_card, text="PROGRESS",
         bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 8, "bold"),
         anchor="w"
).pack(fill="x", padx=14, pady=(12, 0))

progress_w = ModernProgress(prog_card, height=6)
progress_w.pack(fill="x", padx=14, pady=(10, 6))

status_lbl = tk.Label(prog_card, text="Paste a URL and click Fetch to begin.",
                       bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 8),
                       anchor="w")
status_lbl.pack(fill="x", padx=14, pady=(0, 10))

# Action buttons
action_row = tk.Frame(left, bg=BG)
action_row.pack(fill="x", pady=(0, 0))

dl_btn = ModernButton(action_row, text="DOWNLOAD", icon="▼",
                        bg=ACCENT, fg=TEXT, w=18, font_size=10,
                        command=on_download)
dl_btn.widget.pack(side="left", fill="x", expand=True, padx=(0, 8))
dl_btn.disable()

cancel_btn = ModernButton(action_row, text="CANCEL", icon="✕",
                           bg="#2a2a2a", fg=TEXT, w=10, font_size=9,
                           command=on_cancel)
cancel_btn.widget.pack(side="right", fill="x", padx=(8, 0))
cancel_btn.disable()

fetch_btn = ModernButton(action_row, text="FETCH INFO", icon="ℹ",
                          bg="#2563eb", fg=TEXT, w=14, font_size=9,
                          command=on_fetch)
fetch_btn.widget.pack(fill="x", expand=True)

# ─── SEPARATOR ────────────────────────────────────────────────────────────────
sep = tk.Frame(content, bg=BG, width=1)
sep.pack(side="left", fill="y", padx=0)

# ─── RIGHT PANEL ──────────────────────────────────────────────────────────────
right = tk.Frame(content, bg=BG)
right.pack(side="right", fill="both", expand=True, padx=(12, 0))

history_card = make_card(right)
history_card.pack(fill="both", expand=True)

tk.Label(history_card, text="DOWNLOAD HISTORY",
         bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 8, "bold"),
         anchor="w"
).pack(fill="x", padx=14, pady=(12, 6))

# Scrollable history list
list_frame = tk.Frame(history_card, bg=CARD)
list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

# Pre-populate history from disk on startup
for entry in _history:
    _tag = "done" if entry["status"] == "Done" else "warn"

columns = ("time", "url", "quality", "status")
history_tree = ttk.Treeview(list_frame, columns=columns,
                             show="tree headings", height=20,
                             style="Modern.Treeview")

history_tree.heading("#0", text="")
history_tree.heading("time",    text="TIME")
history_tree.heading("url",     text="URL / TITLE")
history_tree.heading("quality",  text="QUALITY")
history_tree.heading("status",  text="STATUS")

history_tree.column("#0",       width=0,  stretch=False)
history_tree.column("time",     width=65, anchor="center")
history_tree.column("url",      width=260, anchor="w")
history_tree.column("quality",  width=80,  anchor="center")
history_tree.column("status",   width=80,  anchor="center")

vsb = ttk.Scrollbar(list_frame, orient="vertical", command=history_tree.yview)
history_tree.configure(yscrollcommand=vsb.set)

history_tree.pack(side="left", fill="both", expand=True)
vsb.pack(side="right", fill="y")

tag(history_tree, done={"foreground": SUCCESS})
tag(history_tree, warn={"foreground": WARNING})

# Populate history from disk on startup
for entry in _history:
    _tag = "done" if entry["status"] == "Done" else "warn"
    history_tree.insert("", "end",
                        values=(entry["time"], entry["title"],
                                entry["quality"], entry["status"]),
                        tags=(_tag,))

# ═══ STATUS BAR ════════════════════════════════════════════════════════════════
statusbar = tk.Frame(shell, bg=SURFACE, height=28)
statusbar.pack(fill="x", side="bottom")
statusbar.propagate(False)

tk.Frame(statusbar, bg=ACCENT, width=3).pack(side="left", fill="y", pady=5)

statusbar_lbl = tk.Label(statusbar, text="Ready",
                          bg=SURFACE, fg=TEXT_DIM,
                          font=("Segoe UI", 8), anchor="w")
statusbar_lbl.pack(side="left", fill="both", expand=True, padx=12)

def _update_statusbar():
    try:
        statusbar_lbl.configure(text=status_lbl.cget("text"),
                                fg=status_lbl.cget("fg"))
    except tk.TclError:
        return
    root.after(200, _update_statusbar)

# Override set_status to also update statusbar
_orig_set_status = set_status
def set_status(msg, color=TEXT_MID):
    _orig_set_status(msg, color)
    statusbar_lbl.configure(text=msg, fg=color)

# ─── Configure ttk style for Combobox ─────────────────────────────────────────
style = ttk.Style(root)
style.theme_use("clam")
style.configure("Modern.Treeview",
                background=INPUT_BG, foreground=TEXT,
                fieldbackground=INPUT_BG, borderwidth=0,
                rowheight=24, font=("Segoe UI", 8))
style.configure("Modern.Treeview.Heading",
                background=SURFACE, foreground=TEXT_DIM,
                font=("Segoe UI", 8, "bold"), borderwidth=0)
style.map("Modern.Treeview",
          background=[("selected", "#2a2a2a")],
          foreground=[("selected", TEXT)])
history_tree.configure(style="Modern.Treeview")

# ─── Kick off queue poller ─────────────────────────────────────────────────────
root.after(100, _poll_queue)
root.after(200, _update_statusbar)
# ─── App Icon ──────────────────────────────────────────────────────────────────
_icon_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "w3", "1486485559-118arrow-down-download-downloads-downloading-save_81191.ico"
)
try:
    root.iconbitmap(_icon_path)
except Exception:
    pass  # icon is optional; no crash if file is missing

# ─── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    #root.iconbitmap(_icon_path)
    root.mainloop()
