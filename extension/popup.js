const st = document.getElementById("st");
const urlBox = document.getElementById("url");

function setStatus(text, cls) {
  st.textContent = text;
  st.className = cls || "";
}

chrome.runtime.sendMessage({ action: "ping" }, (r) => {
  if (chrome.runtime.lastError || !r || !r.ok) {
    setStatus("✖ Helper nahi mila. Pehle start.bat ek dafa chalayen.", "bad");
  } else {
    setStatus(r.app_running ? "✔ Helper tayyar, app chal rahi hai" : "✔ Helper tayyar", "ok");
  }
});

// Agar current tab YouTube hai to link khud bhar do
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const u = tabs && tabs[0] && tabs[0].url;
  if (u && /^https?:\/\//.test(u) && /youtube\.com|youtu\.be/.test(u)) urlBox.value = u;
});

document.getElementById("go").addEventListener("click", () => {
  const url = urlBox.value.trim();
  chrome.runtime.sendMessage({ action: "download", url }, (r) => {
    if (r && r.ok) {
      setStatus("✔ App me bhej diya", "ok");
    } else {
      setStatus("✖ " + ((r && r.error) || "Helper se rabta nahi hua"), "bad");
    }
  });
});
