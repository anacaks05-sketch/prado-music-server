from flask import Flask, request, jsonify, send_file, Response
import yt_dlp
import os
import zipfile
import tempfile
import uuid
import threading
import time

app = Flask(__name__)

def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.after_request
def after_request(response):
    return add_cors(response)

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        resp = Response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp, 200

jobs = {}

def download_musics(job_id, music_list):
    try:
        jobs[job_id]['status'] = 'downloading'
        tmpdir = tempfile.mkdtemp()
        errors = []

        for i, music in enumerate(music_list):
            try:
                jobs[job_id]['current'] = music
                jobs[job_id]['progress'] = i
                jobs[job_id]['total'] = len(music_list)

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True,
                    'no_warnings': True,
                    'default_search': 'ytsearch1',
                    'noplaylist': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([music])

            except Exception as e:
                errors.append({'music': music, 'error': str(e)})

        zip_path = os.path.join(tmpdir, f'prado-music-{job_id[:8]}.zip')
        mp3_files = [f for f in os.listdir(tmpdir) if f.endswith('.mp3')]

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for mp3 in mp3_files:
                zf.write(os.path.join(tmpdir, mp3), mp3)

        jobs[job_id]['status'] = 'done'
        jobs[job_id]['zip_path'] = zip_path
        jobs[job_id]['errors'] = errors
        jobs[job_id]['count'] = len(mp3_files)
        jobs[job_id]['progress'] = len(music_list)

        def cleanup():
            time.sleep(1800)
            if job_id in jobs:
                del jobs[job_id]
        threading.Thread(target=cleanup, daemon=True).start()

    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)


@app.route('/')
def index():
    return send_file('index.html')


@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    data = request.get_json()
    music_list = data.get('musics', [])

    if not music_list:
        return jsonify({'error': 'Lista vazia'}), 400
    if len(music_list) > 20:
        return jsonify({'error': 'Máximo 20 músicas'}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'queued',
        'current': '',
        'progress': 0,
        'total': len(music_list),
        'zip_path': None,
        'errors': [],
        'count': 0
    }

    thread = threading.Thread(target=download_musics, args=(job_id, music_list))
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404
    return jsonify({
        'status': job['status'],
        'current': job.get('current', ''),
        'progress': job.get('progress', 0),
        'total': job.get('total', 0),
        'count': job.get('count', 0),
        'errors': job.get('errors', []),
        'error': job.get('error', '')
    })


@app.route('/get-zip/<job_id>', methods=['GET'])
def get_zip(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        return jsonify({'error': 'ZIP não disponível'}), 404

    zip_path = job.get('zip_path')
    if not zip_path or not os.path.exists(zip_path):
        return jsonify({'error': 'Arquivo não encontrado'}), 404

    return send_file(
        zip_path,
        as_attachment=True,
        download_name='prado-musics.zip',
        mimetype='application/zip'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
