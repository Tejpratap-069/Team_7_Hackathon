"""Run with python app.py. One local server, no debug reloader."""
import atexit
import multiprocessing
import os
import secrets
from flask import Flask, jsonify, render_template, request, Response
from engine import Engine


def create_app(engine=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 4096
    controller = engine or Engine(max_duration=int(os.environ.get('STRESSLAB_MAX_DURATION', '120')))
    app.extensions['engine'] = controller
    token = secrets.token_urlsafe(32)

    @app.before_request
    def local_only():
        if request.remote_addr not in ('127.0.0.1', '::1'):
            return jsonify(error='Local access only.'), 403
        if request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
            return jsonify(error='Invalid local host.'), 403
        if request.method == 'POST' and not secrets.compare_digest(request.headers.get('X-StressLab-Token', ''), token):
            return jsonify(error='Reload the dashboard before using controls.'), 403

    @app.get('/')
    def dashboard():
        return render_template('index.html', token=token)

    @app.get('/api/status')
    def status():
        return jsonify(controller.snapshot())

    @app.post('/api/<action>')
    def control(action):
        try:
            if action == 'start':
                controller.start(request.get_json(silent=True))
            elif action == 'stop':
                controller.stop()
            elif action == 'reset':
                controller.reset()
            else:
                return jsonify(error='Unknown action.'), 404
            return jsonify(ok=True)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 409

    @app.get('/api/export')
    def export():
        try:
            return Response(controller.csv_text(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=stresslab-results.csv'})
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 409

    return app


if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = create_app()
    atexit.register(app.extensions['engine'].close)
    try:
        app.run(host='127.0.0.1', port=int(os.environ.get('STRESSLAB_PORT', '5050')), threaded=True, debug=False, use_reloader=False)
    finally:
        app.extensions['engine'].close()
