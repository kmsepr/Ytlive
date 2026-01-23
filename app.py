import logging
import subprocess
import time
from flask import Flask, Response, render_template_string, abort

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = Flask(__name__)

# -----------------------
# TV Streams
# -----------------------
TV_STREAMS = {
    "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/chunks.m3u8",
    "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "bloomberg_tv": "https://bloomberg-bloomberg-3-br.samsung.wurl.tv/manifest/playlist.m3u8",
    "france_24": "https://live.france24.com/hls/live/2037218/F24_EN_HI_HLS/master_500.m3u8",
    "kairali_we": "https://cdn-3.pishow.tv/live/1530/master.m3u8",
    "amrita_tv": "https://ddash74r36xqp.cloudfront.net/master.m3u8",
    "mazhavil_manorama": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama/playlist.m3u8",
    "dd_sports": "https://cdn-6.pishow.tv/live/13/master.m3u8",
    "dd_malayalam": "https://d3eyhgoylams0m.cloudfront.net/v1/manifest/93ce20f0f52760bf38be911ff4c91ed02aa2fd92/2.m3u8",
}

# -----------------------
# YouTube Live
# -----------------------
YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@MediaoneTVLive/live",
    "asianet_news": "https://www.youtube.com/@asianetnews/live",
    "aljazeera_english": "https://www.youtube.com/@AlJazeeraEnglish/live",
}

# -----------------------
# Home
# -----------------------
@app.route("/")
def home():
    html = """
    <html><body style="background:#111;color:#fff">
    <h2>📺 TV</h2>
    {% for k in tv %}
      <a href="/watch/{{k}}">{{k}}</a> |
      <a href="/audio/{{k}}">audio</a><br>
    {% endfor %}
    <h2>▶ YouTube</h2>
    {% for k in yt %}
      <a href="/watch/{{k}}">{{k}}</a> |
      <a href="/audio/{{k}}">audio</a><br>
    {% endfor %}
    </body></html>
    """
    return render_template_string(html, tv=TV_STREAMS, yt=YOUTUBE_STREAMS)

# -----------------------
# Watch
# -----------------------
@app.route("/watch/<channel>")
def watch(channel):
    if channel not in TV_STREAMS and channel not in YOUTUBE_STREAMS:
        abort(404)

    return f"""
    <html>
    <body style="margin:0;background:#000">
    <video autoplay controls playsinline style="width:100%;height:100%"
        src="/stream/{channel}"></video>
    </body>
    </html>
    """

# -----------------------
# Stream (TV + YouTube)
# -----------------------
@app.route("/stream/<channel>")
def stream(channel):

    # -------- YOUTUBE VIDEO --------
    if channel in YOUTUBE_STREAMS:
        cmd = (
            f'yt-dlp -f "bv*+ba/b" --no-part -o - {YOUTUBE_STREAMS[channel]} | '
            'ffmpeg -loglevel error -i pipe:0 '
            '-c:v libx264 -preset ultrafast -tune zerolatency '
            '-b:v 120k -maxrate 120k -bufsize 240k -g 30 '
            '-c:a aac -b:a 48k -ac 1 '
            '-f mpegts pipe:1'
        )

        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
        )

        return Response(proc.stdout, mimetype="video/MP2T")

    # -------- TV VIDEO --------
    if channel in TV_STREAMS:
        url = TV_STREAMS[channel]

        def generate():
            proc = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error", "-i", url,
                 "-c:v", "libx264", "-preset", "ultrafast",
                 "-c:a", "aac", "-f", "mpegts", "pipe:1"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
            )
            while True:
                data = proc.stdout.read(4096)
                if not data:
                    break
                yield data

        return Response(generate(), mimetype="video/MP2T")

    abort(404)

# -----------------------
# Audio Only
# -----------------------
@app.route("/audio/<channel>")
def audio(channel):

    # -------- YOUTUBE AUDIO --------
    if channel in YOUTUBE_STREAMS:
        cmd = (
            f'yt-dlp -f bestaudio --no-part -o - {YOUTUBE_STREAMS[channel]} | '
            'ffmpeg -loglevel error -i pipe:0 -vn '
            '-ac 1 -ar 44100 -c:a aac -b:a 48k '
            '-f adts pipe:1'
        )

        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
        )

        return Response(proc.stdout, mimetype="audio/aac")

    # -------- TV AUDIO --------
    if channel in TV_STREAMS:
        url = TV_STREAMS[channel]

        def generate():
            while True:
                proc = subprocess.Popen(
                    ["ffmpeg", "-loglevel", "error", "-i", url,
                     "-vn", "-ac", "1", "-ar", "44100",
                     "-c:a", "aac", "-b:a", "40k",
                     "-f", "adts", "pipe:1"],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
                )
                while True:
                    data = proc.stdout.read(4096)
                    if not data:
                        break
                    yield data
                time.sleep(1)

        return Response(generate(), mimetype="audio/aac")

    abort(404)

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
