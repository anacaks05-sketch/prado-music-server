from flask import Flask, request, jsonify, send_file, Response
import yt_dlp
import os
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

def try_download(music, tmpdir):
    """Tenta baixar de várias fontes, retorna path do mp3 ou None"""
    
    sources = [
        # SoundCloud
        {
            'default_search': 'scsearch1',
            'format': 'bestaudio/best',
        },
        # YouTube com user-agent mobile
        {
            'default_search': 'ytsearch1',
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
            },
        },
    ]

    uid = str(uuid.uuid4())[:8]
    out_template = os.path.join(tmpdir, f'{uid}_%(title)s.%(ext)s')

    for src in sources:
        try:
            ydl_opts = {
                **src,
                'outtmpl': out_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([music])

            # Acha o mp3 gerado
            for f in os.listdir(tmpdir):
                if f.startswith(uid) and f.endswith('.mp3'):
                    return os.path.join(tmpdir, f), f
        except:
            continue

    return None, None


def process_job(job_id, music_list):
    try:
        jobs[job_id]['status'] = 'downloading'
        tmpdir = tempfile.mkdtemp()
        results = []

        for i, music in enumerate(music_list):
            jobs[job_id]['current'] = music
            jobs[job_id]['progress'] = i
            jobs[job_id]['total'] = len(music_list)

            mp3_path, mp3_name = try_download(music, tmpdir)

            if mp3_path:
                results.append({
                    'music': music,
                    'path': mp3_path,
                    'name': mp3_name,
                    'status': 'ok'
                })
            else:
                results.append({
                    'music': music,
                    'path': None,
                    'name': None,
                    'status': 'error'
                })

        jobs[job_id]['status'] = 'done'
        jobs[job_id]['results'] = results
        jobs[job_id]['progress'] = len(music_list)
        jobs[job_id]['tmpdir'] = tmpdir

        def cleanup():
            time.sleep(3600)
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
        'status': 'queued', 'current': '',
        'progress': 0, 'total': len(music_list),
        'results': [], 'error': ''
    }

    t = threading.Thread(target=process_job, args=(job_id, music_list))
    t.daemon = True
    t.start()
    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404

    results = job.get('results', [])
    return jsonify({
        'status': job['status'],
        'current': job.get('current', ''),
        'progress': job.get('progress', 0),
        'total': job.get('total', 0),
        'error': job.get('error', ''),
        'tracks': [
            {
                'music': r['music'],
                'status': r['status'],
                'name': r['name'],
                'index': i
            } for i, r in enumerate(results)
        ]
    })


@app.route('/get-mp3/<job_id>/<int:index>')
def get_mp3(job_id, index):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404

    results = job.get('results', [])
    if index >= len(results):
        return jsonify({'error': 'Índice inválido'}), 404

    track = results[index]
    if track['status'] != 'ok' or not track['path']:
        return jsonify({'error': 'MP3 não disponível'}), 404

    return send_file(
        track['path'],
        as_attachment=True,
        download_name=track['name'],
        mimetype='audio/mpeg'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
