"""Chrome Native Messaging host (IDM jaisa tareeqa).
Chrome extension se message leta hai aur app ko link bhejta hai.
App band ho to usay khud khol deta hai."""
import json
import os
import socket
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 47653

if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)


def read_msg():
    raw = sys.stdin.buffer.read(4)
    if len(raw) < 4:
        return None
    size = struct.unpack("<I", raw)[0]
    return json.loads(sys.stdin.buffer.read(size).decode("utf-8"))


def send_msg(obj):
    data = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)) + data)
    sys.stdout.buffer.flush()


def send_to_app(url):
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=1) as s:
            s.sendall(json.dumps({"url": url}).encode("utf-8") + b"\n")
        return True
    except OSError:
        return False


def app_running():
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5) as s:
            s.sendall(b"{}\n")
        return True
    except OSError:
        return False


def launch_app(url):
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    args = [exe, os.path.join(HERE, "auto_start.py")]
    if url:
        args += ["--url", url]
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(args, cwd=HERE, creationflags=flags, close_fds=True)


def main():
    msg = read_msg()
    if not msg:
        return
    action = msg.get("action")
    if action == "ping":
        send_msg({"ok": True, "app_running": app_running()})
    elif action == "download":
        url = (msg.get("url") or "").strip()
        if url and not url.startswith("http"):
            send_msg({"ok": False, "error": "Link sahi nahi"})
            return
        if send_to_app(url):
            send_msg({"ok": True, "mode": "existing"})
        else:
            try:
                launch_app(url)
                send_msg({"ok": True, "mode": "launched"})
            except Exception as e:
                send_msg({"ok": False, "error": str(e)})
    else:
        send_msg({"ok": False, "error": "Unknown action"})


if __name__ == "__main__":
    main()
