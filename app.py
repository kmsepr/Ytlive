import time
import threading
import logging
import subprocess
import os

from flask import Flask, Response, render_template_string, abort

# -----------------------
# Basic setup
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)

COOKIES_FILE = "/mnt/data/cookies.txt"

# -----------------------
# TV Streams (direct HLS)
# -----------------------
TV_STREAMS = {
    "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/chunks.m3u8",
    "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "bloomberg_tv": "https://bloomberg-bloomberg-3-br.samsung.wurl.tv/manifest/playlist.m3u8",
    "france_24": "https://live.france24.com/hls/live/2037218/F24_EN_HI_HLS/master_500.m3u8",
    "kairali_we": "https://cdn-3.pishow.tv/live/1530/master.m3u8",
    "amrita_tv": "https://ddash74r36xqp.cloudfront.net/master.m3u8",
}

# -----------------------
# YouTube Live Channels
# -----------------------
YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@MediaoneTVLive/live",
    "asianet_news": "https://www.youtube.com/@asianetnews/live",
    "aljazeera_english": "https://www.youtube.com/@AlJazeeraEnglish/live",
    "xylem_psc": "https://www.youtube.com/@XylemPSC/live",
}

# -----------------------
# Logos (UI unchanged)
# -----------------------
CHANNEL_LOGOS = {
    **{k: "https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg"
       for k in YOUTUBE_STREAMS}
}

# -----------------------
# Runtime cache
# -----------------------
CACHE = {}        # channel -> hls url
LIVE_STATUS = {}  # channel -> bool

# -----------------------
# yt-dlp extractor (CLOUD SAFE)
# -----------------------
def get_youtube_hls(url: str):
    if not os.path.exists(COOKIES_FILE):
        logging.error("❌ cookies.txt missing at /mnt/data/cookies.txt")
        return None

    cmd = [
        "yt-dlp",
        "--cookies", COOKIES_FILE,
        "--no-playlist",
        "--geo-bypass",
        "--geo-bypass-country", "IN",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "--add-header", "Accept-Language:en-US,en;q=0.9",
        "--add-header", "Referer:https://www.youtube.com/",
        "--extractor-retries", "3",
        "-f", "best[protocol^=m3u8]/best",
        "-g",
        url
    ]

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip()

        logging.warning(f"YouTube blocked/offline: {url}\n{p.stderr}")

    except Exception as e:
        logging.exception(f"yt-dlp exception: {e}")

    return None

# -----------------------
# Background refresh (SINGLE)
# -----------------------
def refresh_youtube():
    logging.info("🍪 cookies.txt exists: %s", os.path.exists(COOKIES_FILE))

    while True:
        logging.info("🔄 Refreshing YouTube live streams")
        for name, url in YOUTUBE_STREAMS.items():
            hls = get_youtube_hls(url)
            if hls:
                CACHE[name] = hls
                LIVE_STATUS[name] = True
                logging.info(f"✅ {name} LIVE")
            else:
                LIVE_STATUS[name] = False
        time.sleep(45)  # MUST be < YouTube expiry

# ensure only one refresh thread (gunicorn-safe)
if os.environ.get("YT_REFRESH_STARTED") != "1":
    os.environ["YT_REFRESH_STARTED"] = "1"
    threading.Thread(target=refresh_youtube, daemon=True).start()

# -----------------------
# Home (UI unchanged)
# -----------------------
@app.route("/")
def home():
    tv_channels = list(TV_STREAMS.keys())
    yt_live = [k for k, v in LIVE_STATUS.items() if v]

    html = """
<!DOCTYPE html>
<html>
<head>
<title>📺 TV & YouTube Live</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { font-family:sans-serif; background:#111; color:#fff; margin:0; }
.tabs { display:flex; justify-content:center; padding:10px; background:#000; }
.tab { padding:10px 20px; background:#222; margin:5px; border-radius:10px; cursor:pointer; }
.tab.active { background:#0ff; color:#000; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(120px,1fr)); gap:12px; padding:10px; }
.card { background:#222; padding:10px; border-radius:10px; text-align:center; }
.card img { width:100%; height:80px; object-fit:contain; }
.hidden { display:none; }
</style>
<script>
function showTab(t){
 document.querySelectorAll('.grid').forEach(g=>g.classList.add('hidden'));
 document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
 document.getElementById(t).classList.remove('hidden');
 document.getElementById('tab_'+t).classList.add('active');
}
window.onload=()=>showTab('tv');
</script>
</head>
<body>
<div class="tabs">
 <div class="tab active" id="tab_tv" onclick="showTab('tv')">📺 TV</div>
 <div class="tab" id="tab_youtube" onclick="showTab('youtube')">▶ YouTube</div>
</div>

<div id="tv" class="grid">
{% for c in tv %}
<div class="card">
 <span>{{ c.replace('_',' ').title() }}</span><br>
 <a href="/watch/{{c}}">Video</a> | <a href="/audio/{{c}}">Audio</a>
</div>
{% endfor %}
</div>

<div id="youtube" class="grid hidden">
{% for c in yt %}
<div class="card">
 <img src="{{ logos[c] }}">
 <span>{{ c.replace('_',' ').title() }}</span><br>
 <a href="/watch/{{c}}">Video</a> | <a href="/audio/{{c}}">Audio</a>
</div>
{% endfor %}
</div>
</body>
</html>
"""
    return render_template_string(
        html,
        tv=tv_channels,
        yt=yt_live,
        logos=CHANNEL_LOGOS
    )

# -----------------------
# Watch (TV direct, YouTube direct HLS)
# -----------------------
@app.route("/watch/<channel>")
def watch(channel):
    if channel in TV_STREAMS:
        src = TV_STREAMS[channel]
    elif channel in CACHE:
        src = CACHE[channel]
    else:
        abort(404)

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>{channel}</title>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<body style="background:#000;text-align:center">
<video id="v" controls autoplay style="width:95%"></video>
<script>
const v=document.getElementById("v");
const src="{src}";
if(v.canPlayType("application/vnd.apple.mpegurl")) v.src=src;
else if(Hls.isSupported()){{let h=new Hls();h.loadSource(src);h.attachMedia(v);}}
</script>
</body>
</html>
"""

# -----------------------
# Audio (TV + YouTube via ffmpeg)
# -----------------------
@app.route("/audio/<channel>")
def audio(channel):
    url = TV_STREAMS.get(channel) or CACHE.get(channel)
    if not url:
        return "Not live", 503

    def gen():
        while True:
            cmd = [
                "ffmpeg",
                "-loglevel", "error",
                "-user_agent", "Mozilla/5.0",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-i", url,
                "-vn",
                "-ac", "1",
                "-ar", "44100",
                "-c:a", "aac",
                "-b:a", "48k",
                "-f", "adts",
                "pipe:1"
            ]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            while True:
                data = p.stdout.read(4096)
                if not data:
                    break
                yield data
            time.sleep(1)

    return Response(gen(), mimetype="audio/aac")

# -----------------------
# Run (local only)
# -----------------------
if __name__ == "__main__":
    app.run("0.0.0.0", 8000)
