(() => {
  const ID = "ytdl-helper-btn";

  const isVideoPage = () =>
    location.pathname === "/watch" || location.pathname.startsWith("/shorts/");

  function flash(btn, text, ms = 3500) {
    btn.textContent = text;
    setTimeout(() => (btn.textContent = "⬇ Download"), ms);
  }

  async function onClick(btn) {
    btn.disabled = true;
    btn.textContent = "Bhej raha hun...";
    try {
      const r = await chrome.runtime.sendMessage({ action: "download", url: location.href });
      if (r && r.ok) {
        flash(btn, "✔ App khul gayi");
      } else {
        flash(btn, "✖ App setup nahi: start.bat chalayen", 6000);
        console.warn("Video Downloader:", r && r.error);
      }
    } catch (e) {
      flash(btn, "✖ Extension reload karein", 5000);
    }
    btn.disabled = false;
  }

  function ensure() {
    const existing = document.getElementById(ID);
    if (!isVideoPage()) {
      if (existing) existing.remove();
      return;
    }
    if (existing) return;
    const btn = document.createElement("button");
    btn.id = ID;
    btn.textContent = "⬇ Download";
    btn.title = "Video Downloader app me kholein (language aur quality chunein)";
    btn.addEventListener("click", () => onClick(btn));
    document.body.appendChild(btn);
  }

  document.addEventListener("yt-navigate-finish", ensure);
  setInterval(ensure, 1000);
  ensure();
})();
