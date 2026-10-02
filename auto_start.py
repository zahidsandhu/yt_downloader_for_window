import base64
import hashlib
import importlib
import importlib.util
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
STAMP = os.path.join(HERE, ".ytdlp_updated")
NATIVE_NAME = "com.ytdl.helper"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

FFMPEG_URLS = [
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
]

BROWSER_KEYS = [
    r"Software\Google\Chrome\NativeMessagingHosts",
    r"Software\Microsoft\Edge\NativeMessagingHosts",
    r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
]


# ---------------- Native Messaging registration ----------------
def ext_id_from_key(key):
    h = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
    return "".join(chr(ord("a") + int(c, 16)) for c in h)


def register_native_host():
    """Chrome/Edge/Brave ko batata hai ke native_host.py kahan hai (IDM jaisa)."""
    try:
        mf = os.path.join(HERE, "extension", "manifest.json")
        with open(mf, encoding="utf-8") as f:
            key = json.load(f).get("key")
        if not key:
            return
        ext_id = ext_id_from_key(key)
        ndir = os.path.join(HERE, "native")
        os.makedirs(ndir, exist_ok=True)

        py = sys.executable
        if py.lower().endswith("pythonw.exe"):
            py = py[:-len("pythonw.exe")] + "python.exe"
        bat = os.path.join(ndir, "native_host.bat")
        with open(bat, "w") as f:
            f.write(f'@echo off\r\n"{py}" "{os.path.join(HERE, "native_host.py")}"\r\n')

        manifest = os.path.join(ndir, NATIVE_NAME + ".json")
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump({
                "name": NATIVE_NAME,
                "description": "Video Downloader helper",
                "path": bat,
                "type": "stdio",
                "allowed_origins": [f"chrome-extension://{ext_id}/"],
            }, f, indent=2)

        if sys.platform == "win32":
            import winreg
            for base in BROWSER_KEYS:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + NATIVE_NAME) as k:
                    winreg.SetValueEx(k, "", 0, winreg.REG_SZ, manifest)
    except Exception as e:
        print("Native host register nahi hua:", e)


# ---------------- Setup steps ----------------
def pip_install(name, log):
    p = subprocess.Popen(
        [sys.executable, "-m", "pip", "install", "-U", name, "--progress-bar", "off"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=NOWIN,
    )
    for line in p.stdout:
        line = line.strip()
        if line:
            log(line)
    if p.wait() != 0:
        raise RuntimeError("pip install fail hua: " + name)


def step_ytdlp(log, prog):
    prog(-1)
    pip_install("yt-dlp", log)
    with open(STAMP, "w") as f:
        f.write(str(time.time()))
    importlib.invalidate_caches()


def step_ffmpeg(log, prog):
    last_err = None
    for url in FFMPEG_URLS:
        try:
            log("Download shuru: " + url)
            tmp = os.path.join(tempfile.gettempdir(), "ffmpeg_dl.zip")

            def hook(blocks, bs, total):
                if total > 0:
                    done = min(blocks * bs, total)
                    prog(done / total * 100)
                    if blocks % 40 == 0:
                        log(f"ffmpeg: {done / 1048576:.1f} / {total / 1048576:.1f} MB")

            urllib.request.urlretrieve(url, tmp, hook)
            log("Extract ho raha hai...")
            prog(-1)
            found = False
            with zipfile.ZipFile(tmp) as z:
                for n in z.namelist():
                    low = n.lower()
                    for exe in ("ffmpeg.exe", "ffprobe.exe"):
                        if low.endswith("/bin/" + exe):
                            with z.open(n) as src, open(os.path.join(HERE, exe), "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            found = True
            if found:
                log("ffmpeg tayyar.")
                return
        except Exception as e:
            last_err = e
            log("Is link se nahi hua: " + str(e))
    raise RuntimeError(f"ffmpeg install nahi hua ({last_err}). ffmpeg.exe is folder me rakh dein.")


def collect_steps():
    steps = []
    if importlib.util.find_spec("yt_dlp") is None:
        steps.append(("yt-dlp install karna", step_ytdlp))
    else:
        try:
            with open(STAMP) as f:
                last = float(f.read())
        except Exception:
            last = 0
        if time.time() - last > 7 * 86400:  # YouTube badalta rehta hai
            steps.append(("yt-dlp update karna", step_ytdlp))
    if not (shutil.which("ffmpeg") or os.path.exists(os.path.join(HERE, "ffmpeg.exe"))):
        steps.append(("ffmpeg download karna (~100 MB)", step_ffmpeg))
    return steps


# ---------------- Setup window ----------------
def run_setup_window(steps):
    import tkinter as tk
    from tkinter import ttk

    BG, CARD, FG, ACC = "#0f172a", "#1e293b", "#e2e8f0", "#ef4444"
    root = tk.Tk()
    root.title("Pehli dafa setup")
    root.geometry("620x440")
    root.resizable(False, False)
    root.configure(bg=BG)
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure("P.Horizontal.TProgressbar", troughcolor="#0b1220", background=ACC,
                bordercolor=BG, lightcolor=ACC, darkcolor=ACC)
    s.configure("TButton", background=ACC, foreground="white", borderwidth=0, padding=(14, 7))

    tk.Label(root, text="Zaroori cheezein install ho rahi hain", bg=BG, fg=FG,
             font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=(16, 6))
    labels = []
    for name, _ in steps:
        lb = tk.Label(root, text="⏳  " + name, bg=BG, fg="#94a3b8", font=("Segoe UI", 10))
        lb.pack(anchor="w", padx=22)
        labels.append(lb)
    bar = ttk.Progressbar(root, style="P.Horizontal.TProgressbar", maximum=100)
    bar.pack(fill="x", padx=18, pady=10)
    box = tk.Text(root, height=12, bg="#0b1220", fg="#cbd5e1", bd=0, font=("Consolas", 9),
                  state="disabled")
    box.pack(fill="both", expand=True, padx=18, pady=(0, 10))
    done_btn = ttk.Button(root, text="Aage barhein", command=root.destroy)

    q = queue.Queue()
    failed = []

    def log(t):
        q.put(("log", t))

    def prog(v):
        q.put(("prog", v))

    def worker():
        for i, (name, fn) in enumerate(steps):
            q.put(("step", i, "run", name))
            try:
                fn(log, prog)
                q.put(("step", i, "ok", name))
            except Exception as e:
                failed.append(name)
                log("ERROR: " + str(e))
                q.put(("step", i, "bad", name))
        q.put(("end",))

    def poll():
        try:
            while True:
                m = q.get_nowait()
                if m[0] == "log":
                    box.config(state="normal")
                    box.insert("end", m[1] + "\n")
                    box.see("end")
                    box.config(state="disabled")
                elif m[0] == "prog":
                    if m[1] < 0:
                        bar.config(mode="indeterminate")
                        bar.start(12)
                    else:
                        bar.stop()
                        bar.config(mode="determinate")
                        bar["value"] = m[1]
                elif m[0] == "step":
                    icon = {"run": "🔄", "ok": "✔", "bad": "✖"}[m[2]]
                    colr = {"run": FG, "ok": "#4ade80", "bad": "#f87171"}[m[2]]
                    labels[m[1]].config(text=f"{icon}  {m[3]}", fg=colr)
                elif m[0] == "end":
                    bar.stop()
                    bar.config(mode="determinate")
                    bar["value"] = 100
                    if failed:
                        done_btn.pack(pady=8)
                    else:
                        root.after(800, root.destroy)
                    return
        except queue.Empty:
            pass
        root.after(100, poll)

    threading.Thread(target=worker, daemon=True).start()
    poll()
    root.mainloop()


def main():
    os.chdir(HERE)
    if importlib.util.find_spec("tkinter") is None:
        print("Tkinter nahi mila. Python dobara install karein aur 'tcl/tk' ka option ON rakhein.")
        input("Enter dabayen...")
        sys.exit(1)

    register_native_host()
    steps = collect_steps()
    if steps:
        run_setup_window(steps)
    importlib.invalidate_caches()

    sys.path.insert(0, HERE)
    import runpy
    runpy.run_path(os.path.join(HERE, "video_downloader.py"), run_name="__main__")


if __name__ == "__main__":
    main()
