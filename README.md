# ▶ Video Downloader

Windows ke liye ek aasan video downloader. Ye **yt-dlp** par bani hai, apna dark UI rakhti hai, aur Chrome extension ke zariye **IDM jaisa** kaam karti hai: YouTube video kholein, **Download** button dabayen, aur video app me khul jata hai.

## Khasusiyat

- **Auto setup:** `start.bat` chalane par Python, yt-dlp aur ffmpeg khud check hote hain aur zaroorat ho to install ho jate hain. Har install ka progress window me nazar aata hai.
- **Chrome extension (Native Messaging):** YouTube ke video page par **⬇ Download** button aata hai. Chrome, Edge aur Brave teeno me kaam karta hai.
- **Language ki maloomat:** download se pehle video ki **default audio language** aur jitni languages me wo download ho sakti hai, sab dikhti hain. Aap apni pasand ki language chun sakte hain.
- **Quality ka intikhab:** video ki asal available qualities ki list, ya **Sirf Audio (MP3)**.
- **Playlist support:** poori playlist ek click me.
- **Bina extension ke bhi:** app khol kar link paste karein aur download kar lein.
- **yt-dlp auto update:** har 7 din baad khud update check hota hai.

## Zaroorat

- Windows 10 / 11
- Internet (pehli dafa setup ke liye)
- Python 3.12 (na ho to `start.bat` winget se khud install kar deta hai)

## Install aur chalana

1. Repository download ya clone karein.
2. `start.bat` par double click karein.
   - Agar Python install hota hai to wo khatam hone par window band karke `start.bat` dobara chalayen.
   - Pehli dafa yt-dlp aur ffmpeg (~100 MB) download hote hain.
3. App khul jayegi.

## Chrome extension lagana

1. Pehle `start.bat` kam az kam ek dafa chala len (isi se browser ko helper ka pata chalta hai).
2. Chrome me `chrome://extensions` kholein.
3. Upar **Developer mode** ON karein.
4. **Load unpacked** dabayen aur is repo ka `extension` folder chunein.
5. YouTube par koi video kholein. Neeche right me laal **⬇ Download** button nazar aayega.

> Edge ke liye `edge://extensions`, Brave ke liye `brave://extensions` istemal karein.

## Istemal

**Extension se:** video par **⬇ Download** dabayen → app khulegi aur video ki maloomat khud load hogi → language aur quality chunein → **Download**.

**Bina extension:** app me link paste karein → **Check karein** → language aur quality chunein → **Download**.

Files `Downloads` folder me save hoti hain (folder app me badla ja sakta hai).

## Folder ka dhancha

```
start.bat              # yahan se shuru karein
auto_start.py          # setup (Python packages, ffmpeg) + native host register + app launch
video_downloader.py    # main app (UI, download)
native_host.py         # Chrome aur app ke beech ka pul (Native Messaging)
extension/             # Chrome extension
  manifest.json
  background.js
  content.js / content.css
  popup.html / popup.js
```

`auto_start.py` chalne par ye cheezein khud ban jati hain (inhe git me na dalein): `native/`, `ffmpeg.exe`, `ffprobe.exe`, `.ytdlp_updated`.

## Ye kaise kaam karta hai

1. Extension ka button `background.js` ko message bhejta hai.
2. `background.js` Chrome Native Messaging se `native_host.py` ko chalata hai (host `com.ytdl.helper` naam se registry me register hota hai).
3. `native_host.py` link ko local port `47653` (sirf `127.0.0.1`) par chal rahi app ko bhejta hai. App chal nahi rahi ho to usay `auto_start.py` ke zariye khud kholta hai.
4. App link ki maloomat yt-dlp se leti hai, languages dikhati hai, aur download karti hai.

Extension me ek fixed `key` hai, isliye uska ID har machine par ek jaisa rehta hai aur native host ki `allowed_origins` hamesha sahi rehti hain.

## Masail aur hal

| Masla | Hal |
|---|---|
| Extension ka button dabane par "App setup nahi" aaye | `start.bat` ek dafa chalayen, phir `chrome://extensions` me extension reload karein |
| Naya design / nayi file nazar nahi aa rahi | Purani app band karein (zaroorat ho to Task Manager me `python.exe` / `pythonw.exe` End Task), phir dobara chalayen |
| ffmpeg install nahi hua | `ffmpeg.exe` khud is folder me rakh dein |
| "Sign in to confirm you're not a bot" jaisa error | yt-dlp update karein (`pip install -U yt-dlp`) ya thori der baad dobara try karein |
| Download button chhota window me gum ho | Latest `video_downloader.py` istemal karein, bottom bar ab hamesha nazar aati hai |
| Button dabane par ek kala window chand lamhe ke liye aaye | Normal hai, native host `.bat` se chalta hai |

## Zaroori note

Sirf wohi content download karein jo aapka apna ho, Creative Commons ho, ya jis ki aapko ijazat ho. YouTube aur doosri websites ki terms of service aur apne mulk ke copyright qawanin ki zimmedari aap par hai.

## Shukriya

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)
