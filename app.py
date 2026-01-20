import time
import threading
import logging
from flask import Flask, Response, render_template_string, abort
import subprocess, os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = Flask(__name__)

# -----------------------
# TV Streams
# -----------------------
TV_STREAMS = {
    "kairali_we": "https://cdn-3.pishow.tv/live/1530/master.m3u8",
    "amrita_tv": "https://ddash74r36xqp.cloudfront.net/master.m3u8",
    "mazhavil_manorama": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama_nim_https/050522/mazhavilmanorama/playlist.m3u8",
    "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/chunks.m3u8",
    "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "dd_sports": "https://cdn-6.pishow.tv/live/13/master.m3u8",
    "dd_malayalam": "https://d3eyhgoylams0m.cloudfront.net/v1/manifest/93ce20f0f52760bf38be911ff4c91ed02aa2fd92/ed7bd2c7-8d10-4051-b397-2f6b90f99acb/562ee8f9-9950-48a0-ba1d-effa00cf0478/2.m3u8",
}

# -----------------------
# YouTube Channels
# -----------------------
YOUTUBE_STREAMS = {
    "asianet_news": "https://www.youtube.com/@asianetnews/live",
    "media_one": "https://www.youtube.com/@MediaoneTVLive/live",
    "xylem_psc": "https://www.youtube.com/@XylemPSC/live",
}

# -----------------------
# Logos
# -----------------------
CHANNEL_LOGOS = {
    **{k: "https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg" for k in YOUTUBE_STREAMS},
    "kairali_we": "https://i.imgur.com/zXpROBj.png",
    "amrita_tv": "https://i.imgur.com/WdSjlPl.png",
    "mazhavil_manorama": "https://i.imgur.com/fjgzW20.png",
    "victers_tv": "https://i.imgur.com/kj4OEsb.png",
    "safari_tv": "https://i.imgur.com/dSOfYyh.png",
    "dd_sports": "https://i.imgur.com/J2Ky5OO.png",
    "dd_malayalam": "https://i.imgur.com/ywm2dTl.png",
}

CACHE = {}
LIVE_STATUS = {}

# -----------------------
# YouTube extractor
# -----------------------
def get_youtube_live_url(url):
    try:
        cmd = [
            "yt-dlp",
            "--no-warnings",
            "--live-from-start",
            "-f", "best[protocol=m3u8]",
            "-g",
            url
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except:
        pass
    return None

# -----------------------
# Background refresh
# -----------------------
def refresh_youtube():
    while True:
        for name, url in YOUTUBE_STREAMS.items():
            hls = get_youtube_live_url(url)
            if hls:
                CACHE[name] = hls
                LIVE_STATUS[name] = True
            else:
                LIVE_STATUS[name] = False
        time.sleep(60)

threading.Thread(target=refresh_youtube, daemon=True).start()

# -----------------------
# Home
# -----------------------
@app.route("/")
def home():
    tv = list(TV_STREAMS.keys())
    yt = [k for k, v in LIVE_STATUS.items() if v]

    html = """
<html>
<body style="background:#111;color:white;font-family:sans-serif">
<h2>TV</h2>
{% for c in tv %}
<a href="/watch/{{c}}">{{c}}</a><br>
{% endfor %}
<h2>YouTube Live</h2>
{% for c in yt %}
<a href="/watch/{{c}}">{{c}}</a><br>
{% endfor %}
</body>
</html>
"""
    return render_template_string(html, tv=tv, yt=yt)

# -----------------------
# Watch
# -----------------------
@app.route("/watch/<channel>")
def watch(channel):
    if channel in TV_STREAMS:
        video_url = TV_STREAMS[channel]
    elif channel in CACHE:
        video_url = CACHE[channel]
    else:
        abort(404)

    return f"""
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<body style="background:black">
<video id="v" controls autoplay muted style="width:100%"></video>
<script>
var v=document.getElementById("v");
if(v.canPlayType("application/vnd.apple.mpegurl")) {{
  v.src="{video_url}";
}} else if(Hls.isSupported()) {{
  var h=new Hls();
  h.loadSource("{video_url}");
  h.attachMedia(v);
}}
</script>
</body>
</html>
"""

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)