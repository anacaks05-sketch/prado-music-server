from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import zipfile
import tempfile
import uuid
import threading
import time

app = Flask(__name__)
CORS(app)

# Armazena jobs em memória
jobs = {}

def download_musics(job_id, music_list):
    try:
        jobs[job_id]['status'] = 'downloading'
        tmpdir = tempfile.mkdtemp()
        downloaded = []
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

                downloaded.append(music)

            except Exception as e:
                errors.append({'music': music, 'error': str(e)})

        # Criar ZIP com todos os MP3s
        zip_path = os.path.join(tmpdir, f'prado-music-{job_id[:8]}.zip')
        mp3_files = [f for f in os.listdir(tmpdir) if f.endswith('.mp3')]

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for mp3 in mp3_files:
                zf.write(os.path.join(tmpdir, mp3), mp3)

        jobs[job_id]['status'] = 'done'
        jobs[job_id]['zip_path'] = zip_path
        jobs[job_id]['downloaded'] = downloaded
        jobs[job_id]['errors'] = errors
        jobs[job_id]['count'] = len(mp3_files)
        jobs[job_id]['tmpdir'] = tmpdir

        # Limpar job depois de 30 minutos
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


@app.route('/download', methods=['POST'])
def start_download():
    data = request.get_json()
    music_list = data.get('musics', [])

    if not music_list:
        return jsonify({'error': 'Lista vazia'}), 400

    if len(music_list) > 20:
        return jsonify({'error': 'Máximo 20 músicas por vez'}), 400

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


@app.route('/status/<job_id>')
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


@app.route('/get-zip/<job_id>')
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
        download_name=f'prado-musics.zip',
        mimetype='application/zip'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
