import time
import threading
import os
import logging
import subprocess
from flask import Flask, Response

# -------------------------------------------------
# Configure logging
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)

# -------------------------------------------------
# 📡 List of YouTube Live Streams
# -------------------------------------------------
YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@MediaoneTVLive/live",
    "shajahan_rahmani": "https://www.youtube.com/@ShajahanRahmaniOfficial/live",
    "qsc_mukkam": "https://www.youtube.com/c/quranstudycentremukkam/live",
    "valiyudheen_faizy": "https://www.youtube.com/@voiceofvaliyudheenfaizy600/live",
    "skicr_tv": "https://www.youtube.com/@SKICRTV/live",
    "yaqeen_institute": "https://www.youtube.com/@yaqeeninstituteofficial/live",
    "bayyinah_tv": "https://www.youtube.com/@bayyinah/live",
    "eft_guru": "https://www.youtube.com/@EFTGuru-ql8dk/live",
    "unacademy_ias": "https://www.youtube.com/@UnacademyIASEnglish/live",
    "studyiq_hindi": "https://www.youtube.com/@StudyIQEducationLtd/live",
    "aljazeera_arabic": "https://www.youtube.com/@aljazeera/live",
    "aljazeera_english": "https://www.youtube.com/@AlJazeeraEnglish/live",
    "entri_degree": "https://www.youtube.com/@EntriDegreeLevelExams/live",
    "xylem_psc": "https://www.youtube.com/@XylemPSC/live",
    "xylem_sslc": "https://www.youtube.com/@XylemSSLC2023/live",
    "entri_app": "https://www.youtube.com/@entriapp/live",
    "entri_ias": "https://www.youtube.com/@EntriIAS/live",
    "studyiq_english": "https://www.youtube.com/@studyiqiasenglish/live",
}
    
# -------------------------------------------------
# 🌐 Cache for direct stream URLs
# -------------------------------------------------
CACHE = {}

# -------------------------------------------------
# Extract YouTube audio URL
# -------------------------------------------------
def get_youtube_audio_url(youtube_url):
    try:
        command = [
            "/usr/local/bin/yt-dlp",
            "--cookies", "/mnt/data/cookies.txt",
            "-f", "bestaudio",
            "-g",
            youtube_url
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            logging.error(f"yt-dlp error: {result.stderr}")
            return None

    except Exception:
        logging.exception("Exception while extracting YouTube audio")
        return None
# -------------------------------------------------
# Refresh stream URLs every 30 minutes
# -------------------------------------------------
def refresh_stream_urls():
    last_update = {}

    while True:
        logging.info("🔄 Refreshing stream URLs...")

        for name, yt_url in YOUTUBE_STREAMS.items():
            now = time.time()

            if name not in last_update or now - last_update[name] > 1800:
                url = get_youtube_audio_url(yt_url)

                if url:
                    CACHE[name] = url
                    last_update[name] = now
                    logging.info(f"✅ Updated {name}")
                else:
                    logging.warning(f"❌ Failed to update {name}")

        time.sleep(60)  # Check every minute

# Start background thread
threading.Thread(target=refresh_stream_urls, daemon=True).start()

# -------------------------------------------------
# FFmpeg audio stream generator
# -------------------------------------------------
def generate_stream(url):
    """Streams audio using FFmpeg with auto-reconnect."""
    while True:
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "10",
                "-timeout", "5000000",
                "-user_agent", "Mozilla/5.0",
                "-i", url,
                "-vn",
                "-ac", "1",
                "-b:a", "40k",
                "-bufsize", "1M",
                "-f", "mp3",
                "-"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=4096
        )

        logging.info(f"🎵 Streaming from: {url}")

        try:
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                yield chunk
                time.sleep(0.02)

        except GeneratorExit:
            logging.info("❌ Client disconnected. Stopping FFmpeg...")
            process.terminate()
            process.wait()
            break

        except Exception as e:
            logging.error(f"Stream error: {e}")

        logging.warning("⚠️ FFmpeg stopped, restarting...")
        process.terminate()
        process.wait()
        time.sleep(5)

# -------------------------------------------------
# Flask Route
# -------------------------------------------------
@app.route("/<station_name>")
def stream(station_name):
    """Serve the requested station as a live stream."""
    url = CACHE.get(station_name)

    if not url:
        return "Station not found or not available", 404

    return Response(generate_stream(url), mimetype="audio/mpeg")


@app.route("/")
def home():
    html = """
    <html>
    <head>
        <title>Live Audio Streams</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial; background: #111; color: #fff; text-align: center; }
            a { display: block; padding: 12px; margin: 8px; background: #222; color: #0f0; 
                text-decoration: none; border-radius: 8px; }
            a:hover { background: #333; }
        </style>
    </head>
    <body>
        <h2>📻 Live Audio Streams</h2>
    """
    
    for name in YOUTUBE_STREAMS:
        html += f'<a href="/{name}">{name.replace("_"," ").title()}</a>'

    html += "</body></html>"
    return html

# -------------------------------------------------
# Run Server
# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)