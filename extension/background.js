const HOST = "com.ytdl.helper";

function sendNative(msg) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendNativeMessage(HOST, msg, (reply) => {
        if (chrome.runtime.lastError) {
          resolve({ ok: false, error: chrome.runtime.lastError.message });
        } else {
          resolve(reply || { ok: false, error: "Koi jawab nahi aya" });
        }
      });
    } catch (e) {
      resolve({ ok: false, error: String(e) });
    }
  });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  sendNative(msg).then(sendResponse);
  return true; // async response
});
