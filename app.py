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
    uid = str(uuid.uuid4())[:8]

    sources = [
        # SoundCloud — sem precisar de ffmpeg
        {
            'default_search': 'scsearch1',
            'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio',
            'outtmpl': os.path.join(tmpdir, f'{uid}_%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        },
        # YouTube android client — menos bloqueios
        {
            'default_search': 'ytsearch1',
            'format': 'bestaudio[ext=webm]/bestaudio',
            'outtmpl': os.path.join(tmpdir, f'{uid}_%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extractor_args': {'youtube': {'player_client': ['android']}},
        },
    ]

    for opts in sources:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(music, download=True)
                title = info.get('title', music)

            for f in os.listdir(tmpdir):
                if f.startswith(uid):
                    fpath = os.path.join(tmpdir, f)
                    # Renomeia para .mp3 se precisar
                    if not f.endswith('.mp3'):
                        newpath = fpath.rsplit('.', 1)[0] + '.mp3'
                        os.rename(fpath, newpath)
                        fpath = newpath
                        f = os.path.basename(newpath)
                    return fpath, f, title
        except Exception as e:
            continue

    return None, None, None


def process_job(job_id, music_list):
    try:
        jobs[job_id]['status'] = 'downloading'
        tmpdir = tempfile.mkdtemp()
        results = []

        for i, music in enumerate(music_list):
            jobs[job_id]['current'] = music
            jobs[job_id]['progress'] = i
            jobs[job_id]['total'] = len(music_list)

            path, fname, title = try_download(music, tmpdir)

            results.append({
                'music': music,
                'title': title or music,
                'path': path,
                'name': fname,
                'status': 'ok' if path else 'error'
            })

        jobs[job_id]['status'] = 'done'
        jobs[job_id]['results'] = results
        jobs[job_id]['progress'] = len(music_list)

        def cleanup():
            time.sleep(3600)
            jobs.pop(job_id, None)
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
        'tracks': [{'index': i, 'music': r['music'], 'title': r.get('title',''), 'name': r.get('name',''), 'status': r['status']} for i, r in enumerate(results)]
    })


@app.route('/get-mp3/<job_id>/<int:index>')
def get_mp3(job_id, index):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Não encontrado'}), 404
    results = job.get('results', [])
    if index >= len(results):
        return jsonify({'error': 'Índice inválido'}), 404
    track = results[index]
    if track['status'] != 'ok' or not track['path']:
        return jsonify({'error': 'MP3 indisponível'}), 404
    return send_file(track['path'], as_attachment=True,
                     download_name=track['name'], mimetype='audio/mpeg')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
