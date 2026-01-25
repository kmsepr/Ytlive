import time
import threading
import logging
from flask import Flask, Response, render_template_string, abort
import subprocess, os, requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = Flask(__name__)

# -----------------------
# TV Streams (direct m3u8)
# -----------------------
TV_STREAMS = {
    "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/chunks.m3u8",
    "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "bloomberg_tv": "https://bloomberg-bloomberg-3-br.samsung.wurl.tv/manifest/playlist.m3u8",
    "france_24": "https://live.france24.com/hls/live/2037218/F24_EN_HI_HLS/master_500.m3u8",
    "kairali_we": "https://cdn-3.pishow.tv/live/1530/master.m3u8",
    "amrita_tv": "https://ddash74r36xqp.cloudfront.net/master.m3u8",
    "mazhavil_manorama": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama_nim_https/050522/mazhavilmanorama/playlist.m3u8",
    "dd_sports": "https://cdn-6.pishow.tv/live/13/master.m3u8",
    "dd_malayalam": "https://d3eyhgoylams0m.cloudfront.net/v1/manifest/93ce20f0f52760bf38be911ff4c91ed02aa2fd92/ed7bd2c7-8d10-4051-b397-2f6b90f99acb/562ee8f9-9950-48a0-ba1d-effa00cf0478/2.m3u8",
    "aqsa_tv": "http://167.172.161.13/hls/feedspare/6udfi7v8a3eof6nlps6e9ovfrs65c7l7.m3u8",
    "mult": "http://stv.mediacdn.ru/live/cdn/mult/playlist.m3u8",
    "yemen_today": "https://video.yementdy.tv/hls/yementoday.m3u8",
}

# -----------------------
# YouTube Live Channels
# -----------------------
YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@MediaoneTVLive/live",
    "shajahan_rahmani": "https://www.youtube.com/@ShajahanRahmaniOfficial/live",
    "qsc_mukkam": "https://www.youtube.com/c/quranstudycentremukkam/live",
    "valiyudheen_faizy": "https://www.youtube.com/@voiceofvaliyudheenfaizy600/live",
    "skicr_tv": "https://www.youtube.com/@SKICRTV/live",
    "asianet_news": "https://www.youtube.com/@asianetnews/live",
    "eft_guru": "https://www.youtube.com/@EFTGuru-ql8dk/live",
    "unacademy_ias": "https://www.youtube.com/@UnacademyIASEnglish/live",
    "aljazeera_english": "https://www.youtube.com/@AlJazeeraEnglish/live",
    "entri_degree": "https://www.youtube.com/@EntriDegreeLevelExams/live",
    "xylem_psc": "https://www.youtube.com/@XylemPSC/live",
    "xylem_sslc": "https://www.youtube.com/@XylemSSLC2023/live",
    "entri_app": "https://www.youtube.com/@entriapp/live",
    "entri_ias": "https://www.youtube.com/@EntriIAS/live",
    "studyiq_english": "https://www.youtube.com/@studyiqiasenglish/live",
}

# -----------------------
# Channel Logos
# -----------------------
CHANNEL_LOGOS = {
    **{k: "https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg" for k in YOUTUBE_STREAMS}
}

CACHE = {}
LIVE_STATUS = {}
COOKIES_FILE = "/mnt/data/cookies.txt"

# -----------------------
# ORIGINAL extractor (kept)
# -----------------------
def get_youtube_live_url(youtube_url: str):
    try:
        cmd = ["yt-dlp", "-f", "best[height<=360]", "-g", youtube_url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None

# -----------------------
# NEW: HLS-only extractor
# -----------------------
def get_youtube_hls_url(youtube_url: str):
    try:
        cmd = [
            "yt-dlp",
            "-f", "best[protocol^=m3u8]/best",
            "--live-from-start",
            "-g",
            youtube_url
        ]
        if os.path.exists(COOKIES_FILE):
            cmd.insert(1, "--cookies")
            cmd.insert(2, COOKIES_FILE)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and ".m3u8" in r.stdout:
            return r.stdout.strip()
    except Exception as e:
        logging.error(e)
    return None

# -----------------------
# ORIGINAL refresh (kept)
# -----------------------
def refresh_stream_urls():
    while True:
        for name, url in YOUTUBE_STREAMS.items():
            direct_url = get_youtube_live_url(url)
            if direct_url:
                CACHE[name] = direct_url
                LIVE_STATUS[name] = True
        time.sleep(60)

threading.Thread(target=refresh_stream_urls, daemon=True).start()

# -----------------------
# NEW refresh (HLS safe)
# -----------------------
def refresh_youtube_hls():
    while True:
        for name, url in YOUTUBE_STREAMS.items():
            hls = get_youtube_hls_url(url)
            if hls:
                CACHE[name] = hls
                LIVE_STATUS[name] = True
        time.sleep(30)

threading.Thread(target=refresh_youtube_hls, daemon=True).start()

# -----------------------
# Home
# -----------------------
@app.route("/")
def home():
    tv_channels = list(TV_STREAMS.keys())
    live_youtube = [n for n, live in LIVE_STATUS.items() if live]

    html = """
<html>
<head>
<title>📺 TV & YouTube Live</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { font-family:sans-serif; background:#111; color:#fff; margin:0; padding:0; }
h2 { text-align:center; margin:10px 0; }
.tabs { display:flex; justify-content:center; background:#000; padding:10px; }
.tab { padding:10px 20px; cursor:pointer; background:#222; color:#0ff; border-radius:10px; margin:0 5px; transition:0.2s; }
.tab.active { background:#0ff; color:#000; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(120px,1fr)); gap:12px; padding:10px; }
.card { background:#222; border-radius:10px; padding:10px; text-align:center; transition:0.2s; }
.card:hover { background:#333; }
.card img { width:100%; height:80px; object-fit:contain; margin-bottom:8px; }
.card span { font-size:14px; color:#0f0; }
.hidden { display:none; }
</style>
<script>
function showTab(tab){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.grid').forEach(g=>g.classList.add('hidden'));
  document.getElementById(tab).classList.remove('hidden');
  document.getElementById('tab_'+tab).classList.add('active');
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
{% for key in tv_channels %}
<div class="card">
    <img src="{{ logos.get(key) }}">
    <span>{{ key.replace('_',' ').title() }}</span><br>
    <a href="/watch/{{ key }}" style="color:#0ff;">Video</a> |
<a href="/audio/{{ key }}" style="color:#ff0;">Audio</a>
</div>
{% endfor %}
</div>

<div id="youtube" class="grid hidden">
{% for key in youtube_channels %}
<div class="card">
    <img src="{{ logos.get(key) }}">
    <span>{{ key.replace('_',' ').title() }}</span><br>
    <a href="/watch/{{ key }}" style="color:#0ff;">Video</a> |
    <a href="/audio/{{ key }}" style="color:#ff0;">Audio</a>
</div>
{% endfor %}
</div>
</body>
</html>
"""
    return render_template_string(html, tv_channels=tv_channels, youtube_channels=live_youtube, logos=CHANNEL_LOGOS)

# -----------------------
# ORIGINAL watch route (kept)
# -----------------------
@app.route("/watch/<channel>")
def watch(channel):
    if channel in TV_STREAMS:
        video_url = TV_STREAMS[channel]
    else:
        video_url = f"/stream/{channel}"

    return f"""
<html>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<video id=v controls autoplay></video>
<script>
var v=document.getElementById("v");
var src="{video_url}";
if(v.canPlayType("application/vnd.apple.mpegurl")){{v.src=src;}}
else if(Hls.isSupported()){{var h=new Hls();h.loadSource(src);h.attachMedia(v);}}
</script>
</html>
"""

# -----------------------
# NEW YouTube watch (NO ffmpeg)
# -----------------------
@app.route("/watch_yt/<channel>")
def watch_yt(channel):
    if channel not in CACHE:
        return "YouTube not ready", 503
    return f"""
<html>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<video id=v controls autoplay></video>
<script>
var v=document.getElementById("v");
var src="{CACHE[channel]}";
if(v.canPlayType("application/vnd.apple.mpegurl")){{v.src=src;}}
else if(Hls.isSupported()){{var h=new Hls();h.loadSource(src);h.attachMedia(v);}}
</script>
</html>
"""

# -----------------------
# NEW auto redirect
# -----------------------
@app.before_request
def redirect_yt():
    from flask import request, redirect
    if request.path.startswith("/watch/"):
        ch = request.path.split("/")[-1]
        if ch in YOUTUBE_STREAMS:
            return redirect(f"/watch_yt/{ch}")

# -----------------------
# Stream (TV only)
# -----------------------
@app.route("/stream/<channel>")
def stream(channel):
    if channel not in TV_STREAMS:
        abort(404)

    cmd = [
        "ffmpeg","-i",TV_STREAMS[channel],
        "-c:v","libx264","-b:v","40k",
        "-c:a","aac","-b:a","24k",
        "-f","mpegts","pipe:1"
    ]

    def gen():
        p=subprocess.Popen(cmd,stdout=subprocess.PIPE)
        while True:
            d=p.stdout.read(1024)
            if not d: break
            yield d

    return Response(gen(), mimetype="video/mp2t")

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
