from flask import Flask, request, jsonify, send_from_directory
import os
import requests
import subprocess

app = Flask(__name__)
OUTPUT_DIR = 'static'
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
    return "FFmpeg Video API is running."

@app.route('/create', methods=['POST'])
def create_video():
    data = request.json
    image_url = data.get('image_url')
    audio_url = data.get('audio_url')
    subtitle_url = data.get('subtitle_url')  # Optional

    if not image_url or not audio_url:
        return jsonify({"error": "Missing image_url or audio_url"}), 400

    image_path = os.path.join(OUTPUT_DIR, 'image.jpg')
    audio_path = os.path.join(OUTPUT_DIR, 'audio.mp3')
    video_path = os.path.join(OUTPUT_DIR, 'output.mp4')
    subtitle_path = os.path.join(OUTPUT_DIR, 'subtitles.srt') if subtitle_url else None

    try:
        # Download image and audio
        with open(image_path, 'wb') as f:
            f.write(requests.get(image_url).content)
        with open(audio_path, 'wb') as f:
            f.write(requests.get(audio_url).content)

        # Download subtitles if provided
        if subtitle_url:
            with open(subtitle_path, 'wb') as f:
                f.write(requests.get(subtitle_url).content)
            # Make subtitle path absolute and escape for ffmpeg
            subtitle_path = os.path.abspath(subtitle_path).replace('\\', '/')
            subtitle_filter = f"subtitles='{subtitle_path}'"
        else:
            subtitle_filter = None

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', image_path,
            '-i', audio_path,
        ]

        # Apply scale filter ensuring both width and height are even
        vf_filters = ["scale=trunc(iw/2)*2:trunc(ih/2)*2"]
        if subtitle_filter:
            vf_filters.append(subtitle_filter)

        cmd += ['-vf', ','.join(vf_filters)]
        cmd += [
            '-c:v', 'libx264',
            '-tune', 'stillimage',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            '-y',
            video_path
        ]

        # Run ffmpeg and capture output
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({
                "error": "FFmpeg failed",
                "ffmpeg_stderr": result.stderr
            }), 500

        return jsonify({"video_url": request.host_url + 'static/output.mp4'})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/static/<path:filename>')
def static_file(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/ping')
def ping():
    return "✅ I'm alive!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
