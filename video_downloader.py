import json
import os
import queue
import socket
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yt_dlp

PORT = 47653
HERE = os.path.dirname(os.path.abspath(__file__))

BG, CARD, FG, MUTED = "#0f172a", "#1e293b", "#e2e8f0", "#94a3b8"
ACC, ACC2, FIELD = "#ef4444", "#dc2626", "#0b1220"

LANG_NAMES = {
    "en": "English", "ur": "Urdu", "hi": "Hindi", "ar": "Arabic", "es": "Spanish",
    "fr": "French", "de": "German", "pt": "Portuguese", "ru": "Russian",
    "ja": "Japanese", "ko": "Korean", "tr": "Turkish", "id": "Indonesian",
    "it": "Italian", "bn": "Bengali", "pa": "Punjabi", "zh": "Chinese",
    "ta": "Tamil", "fa": "Persian", "vi": "Vietnamese", "th": "Thai",
    "nl": "Dutch", "pl": "Polish", "te": "Telugu", "mr": "Marathi",
}

DEFAULT_LANG = "Default (original)"
BEST = "Best available"
MP3 = "Sirf Audio (MP3)"


def app_dir():
    return getattr(sys, "_MEIPASS", HERE)


def lang_label(code):
    name = LANG_NAMES.get(code.split("-")[0].lower())
    return f"{name} ({code})" if name else code


def fmt_duration(sec):
    if not sec:
        return ""
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def analyze(info):
    """Video ki heights, audio languages aur default language nikalta hai."""
    fmts = info.get("formats") or []
    heights = sorted(
        {f["height"] for f in fmts if f.get("vcodec") not in (None, "none") and f.get("height")},
        reverse=True,
    )
    langs, default = [], None
    for f in fmts:
        if f.get("vcodec") != "none" or f.get("acodec") in (None, "none"):
            continue  # sirf audio-only formats
        code = f.get("language")
        if not code:
            continue
        if code not in langs:
            langs.append(code)
        if "default" in (f.get("format_note") or "").lower():
            default = code
    if not default:
        default = info.get("language") or (langs[0] if len(langs) == 1 else None)
    return heights, langs, default


def build_format(height, lang, audio_only=False):
    if audio_only:
        return f"ba[language={lang}]/ba/b" if lang else "bestaudio/best"
    v = f"bv*[height<={height}]" if height else "bv*"
    b = f"b[height<={height}]" if height else "b"
    if lang:
        return f"{v}+ba[language={lang}]/{v}+ba/{b}"
    return f"{v}+ba/{b}"


def send_to_running(url):
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=1) as s:
            s.sendall(json.dumps({"url": url}).encode("utf-8") + b"\n")
        return True
    except OSError:
        return False


class Cancelled(Exception):
    pass


def setup_style(root):
    root.configure(bg=BG)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACC)
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=FG, font=("Segoe UI", 10))
    s.configure("Card.TFrame", background=CARD)
    s.configure("Card.TLabel", background=CARD, foreground=FG)
    s.configure("Muted.TLabel", background=CARD, foreground=MUTED)
    s.configure("Bg.TLabel", background=BG, foreground=MUTED)
    s.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 17, "bold"))
    s.configure("Head.TLabel", background=CARD, foreground=FG, font=("Segoe UI", 11, "bold"))
    s.configure("TEntry", fieldbackground=FIELD, foreground=FG, insertcolor=FG,
                bordercolor="#334155", padding=6)
    s.configure("TCombobox", fieldbackground=FIELD, background=CARD, foreground=FG,
                arrowcolor=FG, bordercolor="#334155", padding=4)
    s.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", FG)])
    s.configure("TButton", background="#334155", foreground=FG, borderwidth=0, padding=(12, 7))
    s.map("TButton", background=[("active", "#475569"), ("disabled", "#1e293b")])
    s.configure("Accent.TButton", background=ACC, foreground="white", padding=(16, 8),
                font=("Segoe UI", 10, "bold"))
    s.map("Accent.TButton", background=[("active", ACC2), ("disabled", "#475569")])
    s.configure("TCheckbutton", background=CARD, foreground=FG)
    s.map("TCheckbutton", background=[("active", CARD)])
    s.configure("Red.Horizontal.TProgressbar", troughcolor=FIELD, background=ACC,
                bordercolor=BG, lightcolor=ACC, darkcolor=ACC)


class App:
    def __init__(self, root, start_url=None, server=None):
        self.root = root
        self.cancel = False
        self.info = None
        self.lang_map = {}
        self.q = queue.Queue()

        root.title("Video Downloader")
        root.geometry("720x720")
        root.minsize(720, 460)
        root.resizable(False, True)
        setup_style(root)
        self.build_ui()
        self.poll()

        if server:
            threading.Thread(target=self.serve, args=(server,), daemon=True).start()
        if start_url:
            self.receive(start_url)

    # ---------- UI ----------
    def build_ui(self):
        # Neeche ka fixed bar (progress + buttons) pehle pack hota hai, taake hamesha nazar aaye
        bottom = ttk.Frame(self.root, padding=(18, 6, 18, 10))
        bottom.pack(side="bottom", fill="x")

        # Upar ka hissa scroll hota hai
        wrap = ttk.Frame(self.root)
        wrap.pack(side="top", fill="both", expand=True)
        canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        main = ttk.Frame(canvas, padding=18)
        win = canvas.create_window((0, 0), window=main, anchor="nw")
        main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        self.root.bind_all(
            "<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        top = ttk.Frame(main)
        top.pack(fill="x")
        ttk.Label(top, text="▶  Video Downloader", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="🧩 Extension", command=self.ext_help).pack(side="right")

        # Link card
        c1 = ttk.Frame(main, style="Card.TFrame", padding=14)
        c1.pack(fill="x", pady=(14, 8))
        ttk.Label(c1, text="Video ya Playlist ka link", style="Head.TLabel").pack(anchor="w")
        row = ttk.Frame(c1, style="Card.TFrame")
        row.pack(fill="x", pady=(8, 0))
        self.url = ttk.Entry(row)
        self.url.pack(side="left", fill="x", expand=True)
        self.url.bind("<Return>", lambda e: self.check())
        self.check_btn = ttk.Button(row, text="Check karein", command=self.check)
        self.check_btn.pack(side="left", padx=(8, 0))

        # Info card
        c2 = ttk.Frame(main, style="Card.TFrame", padding=14)
        c2.pack(fill="x", pady=8)
        self.title_lbl = ttk.Label(c2, text="Pehle link daal kar 'Check karein' dabayen.",
                                   style="Head.TLabel", wraplength=640, justify="left")
        self.title_lbl.pack(anchor="w")
        self.meta_lbl = ttk.Label(c2, text="", style="Muted.TLabel")
        self.meta_lbl.pack(anchor="w", pady=(2, 6))
        self.lang_info = ttk.Label(c2, text="", style="Card.TLabel", wraplength=640, justify="left")
        self.lang_info.pack(anchor="w")

        # Options card
        c3 = ttk.Frame(main, style="Card.TFrame", padding=14)
        c3.pack(fill="x", pady=8)
        g = ttk.Frame(c3, style="Card.TFrame")
        g.pack(fill="x")
        ttk.Label(g, text="Audio language", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(g, text="Quality", style="Card.TLabel").grid(row=0, column=1, sticky="w", padx=(14, 0))
        self.lang = ttk.Combobox(g, values=[DEFAULT_LANG], state="readonly", width=32)
        self.lang.current(0)
        self.lang.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.quality = ttk.Combobox(g, values=[BEST, "1080p", "720p", "480p", MP3],
                                    state="readonly", width=20)
        self.quality.current(0)
        self.quality.grid(row=1, column=1, sticky="w", padx=(14, 0), pady=(4, 0))
        self.playlist = tk.BooleanVar(value=False)
        ttk.Checkbutton(c3, text="Poori playlist download karo",
                        variable=self.playlist).pack(anchor="w", pady=(10, 0))

        # Folder card
        c4 = ttk.Frame(main, style="Card.TFrame", padding=14)
        c4.pack(fill="x", pady=8)
        ttk.Label(c4, text="Save folder", style="Head.TLabel").pack(anchor="w")
        r4 = ttk.Frame(c4, style="Card.TFrame")
        r4.pack(fill="x", pady=(8, 0))
        self.folder = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        ttk.Entry(r4, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(r4, text="Badlein", command=self.pick_folder).pack(side="left", padx=(8, 0))
        ttk.Button(r4, text="Kholein", command=self.open_folder).pack(side="left", padx=(6, 0))

        # Progress
        self.bar = ttk.Progressbar(bottom, maximum=100, style="Red.Horizontal.TProgressbar")
        self.bar.pack(fill="x", pady=(4, 4))
        self.status = ttk.Label(bottom, text="Tayyar", style="Bg.TLabel", wraplength=660)
        self.status.pack(anchor="w")

        row3 = ttk.Frame(bottom)
        row3.pack(pady=8)
        self.btn = ttk.Button(row3, text="⬇  Download", style="Accent.TButton", command=self.start)
        self.btn.pack(side="left", padx=6)
        self.stop = ttk.Button(row3, text="Rokein", command=self.stop_dl, state="disabled")
        self.stop.pack(side="left", padx=6)

        ttk.Label(bottom, text="Sirf apni, Creative Commons ya jis content ki ijazat ho, wohi download karein.",
                  style="Bg.TLabel").pack()

    # ---------- thread-safe UI helpers ----------
    def ui(self, fn):
        self.q.put(fn)

    def poll(self):
        try:
            while True:
                self.q.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def set_status(self, text, pct=None):
        def f():
            self.status.config(text=text)
            if pct is not None:
                self.bar["value"] = pct
        self.ui(f)

    # ---------- misc actions ----------
    def ext_help(self):
        ext = os.path.join(HERE, "extension")
        messagebox.showinfo(
            "Chrome Extension lagane ka tareeqa",
            "1. Chrome me chrome://extensions kholein\n"
            "2. Upar 'Developer mode' ON karein\n"
            "3. 'Load unpacked' dabayen aur ye folder chunein:\n\n" + ext +
            "\n\nIske baad YouTube video par neeche 'Download' button nazar ayega.\n"
            "(Extension lagane se pehle ye app ek dafa start.bat se chal chuki honi chahiye.)",
        )

    def pick_folder(self):
        d = filedialog.askdirectory(initialdir=self.folder.get())
        if d:
            self.folder.set(d)

    def open_folder(self):
        try:
            os.startfile(self.folder.get())
        except Exception:
            pass

    # ---------- link from extension ----------
    def serve(self, srv):
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            try:
                conn.settimeout(2)
                data = b""
                while not data.endswith(b"\n") and len(data) < 65536:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                msg = json.loads(data.decode("utf-8").strip() or "{}")
                url = msg.get("url", "")
                self.ui(lambda u=url: self.receive(u))
            except Exception:
                pass
            finally:
                conn.close()

    def receive(self, url):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(400, lambda: self.root.attributes("-topmost", False))
        if url:
            self.url.delete(0, "end")
            self.url.insert(0, url)
            self.check()

    # ---------- check (info + languages) ----------
    def check(self):
        link = self.url.get().strip()
        if not link.startswith("http"):
            messagebox.showwarning("Link", "Pehle sahi link paste karein.")
            return
        self.check_btn.config(state="disabled")
        self.title_lbl.config(text="Maloomat li ja rahi hain...")
        self.meta_lbl.config(text="")
        self.lang_info.config(text="")
        self.set_status("Video ki language aur quality check ho rahi hai...", 0)
        threading.Thread(target=self._fetch, args=(link,), daemon=True).start()

    def _fetch(self, link):
        opts = {"quiet": True, "no_warnings": True, "noplaylist": True,
                "skip_download": True, "extract_flat": "in_playlist"}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False)
            self.ui(lambda: self.show_info(info))
        except Exception as e:
            msg = str(e)[:300]
            self.ui(lambda: self.fetch_failed(msg))

    def fetch_failed(self, msg):
        self.check_btn.config(state="normal")
        self.title_lbl.config(text="Maloomat nahi mil saki.")
        self.set_status("Error: " + msg, 0)

    def show_info(self, info):
        self.info = info
        self.check_btn.config(state="normal")
        self.lang_map = {}
        if info.get("_type") == "playlist":
            n = len(info.get("entries") or [])
            self.title_lbl.config(text="Playlist: " + str(info.get("title") or ""))
            self.meta_lbl.config(text=f"{n} videos")
            self.lang_info.config(text="Playlist me har video ki language alag ho sakti hai (default use hogi).")
            self.playlist.set(True)
            heights, langs, default = [1080, 720, 480], [], None
        else:
            heights, langs, default = analyze(info)
            self.title_lbl.config(text=info.get("title") or "")
            meta = " • ".join(x for x in (info.get("uploader"), fmt_duration(info.get("duration"))) if x)
            self.meta_lbl.config(text=meta)
            if langs:
                names = ", ".join(lang_label(c) for c in langs)
                d = lang_label(default) if default else "maloom nahi"
                self.lang_info.config(
                    text=f"Default audio: {d}\nDownload ho sakti hai ({len(langs)}): {names}")
            else:
                d = lang_label(default) if default else "original"
                self.lang_info.config(
                    text=f"Is video me sirf ek audio track hai.\nAudio language: {d}")
        # language dropdown
        values = [DEFAULT_LANG]
        for c in langs:
            label = lang_label(c) + ("  ★ default" if c == default else "")
            self.lang_map[label] = c
            values.append(label)
        self.lang.config(values=values)
        self.lang.current(0)
        # quality dropdown
        hs = heights or [1080, 720, 480]
        self.quality.config(values=[BEST] + [f"{h}p" for h in hs] + [MP3])
        self.quality.current(0)
        self.set_status("Check mukammal. Language/quality chun kar Download dabayen.", 0)

    # ---------- download ----------
    def hook(self, d):
        if self.cancel:
            raise Cancelled()
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = done / total * 100 if total else 0
            speed = d.get("speed")
            sp = f"{speed / 1024 / 1024:.2f} MB/s" if speed else ""
            self.set_status(f"Download ho raha hai... {pct:.1f}%  {sp}", pct)
        elif d["status"] == "finished":
            self.set_status("Process ho raha hai (merge/convert)...", 100)

    def start(self):
        link = self.url.get().strip()
        if not link.startswith("http"):
            messagebox.showwarning("Link", "Pehle sahi link paste karein.")
            return
        self.cancel = False
        self.btn.config(state="disabled")
        self.stop.config(state="normal")
        self.bar["value"] = 0
        q = self.quality.get()
        lang = self.lang_map.get(self.lang.get())
        height = int(q[:-1]) if q.endswith("p") and q[:-1].isdigit() else None
        args = (link, q == MP3, height, lang, self.playlist.get(), self.folder.get())
        threading.Thread(target=self.run, args=args, daemon=True).start()

    def stop_dl(self):
        self.cancel = True
        self.set_status("Ruk raha hai...")

    def run(self, link, audio_only, height, lang, is_playlist, base):
        if is_playlist:
            tmpl = os.path.join(base, "%(playlist_title)s", "%(playlist_index)03d - %(title)s.%(ext)s")
        else:
            tmpl = os.path.join(base, "%(title)s.%(ext)s")
        opts = {
            "format": build_format(height, lang, audio_only),
            "outtmpl": tmpl,
            "noplaylist": not is_playlist,
            "ignoreerrors": is_playlist,
            "progress_hooks": [self.hook],
            "quiet": True,
            "no_warnings": True,
            "windowsfilenames": True,
        }
        if audio_only:
            opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]
        else:
            opts["merge_output_format"] = "mp4"
        if os.path.exists(os.path.join(app_dir(), "ffmpeg.exe")):
            opts["ffmpeg_location"] = app_dir()
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([link])
            self.set_status("Mukammal! Folder: " + base, 100)
        except Cancelled:
            self.set_status("Download rok diya gaya.")
        except Exception as e:
            self.set_status("Error: " + str(e)[:300])
        finally:
            self.ui(self.done)

    def done(self):
        self.btn.config(state="normal")
        self.stop.config(state="disabled")


def main():
    url = None
    if "--url" in sys.argv:
        i = sys.argv.index("--url")
        url = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    # Agar app pehle se chal rahi hai to link usi ko bhej do
    if send_to_running(url or ""):
        return
    srv = None
    try:
        srv = socket.socket()
        srv.bind(("127.0.0.1", PORT))
        srv.listen(5)
    except OSError:
        srv = None
    root = tk.Tk()
    App(root, url, srv)
    root.mainloop()


if __name__ == "__main__":
    main()
