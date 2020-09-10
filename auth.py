import json
import logging
import os
import socket
import threading
import time
import webbrowser

import requests
from flask import Flask, request, Response, render_template

import conf
import util


def _get_free_port() -> int:
    for p in range(conf.AUTH_PORT_RANGE_FIRST, conf.AUTH_PORT_RANGE_LAST + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', p))
            sock.close()
            return p
        except OSError:
            # Port already in use?
            pass

    raise OSError(f"Unable to bind to ports {conf.AUTH_PORT_RANGE_FIRST} - {conf.AUTH_PORT_RANGE_LAST}")


def _write_tokens(access_token, valid_sec, refresh_token):
    access_token_file = json.dumps({
        'access_token': access_token,
        'expires_at': round(time.time()) + valid_sec
    })

    util.write_restricted_file('access_token', access_token_file)
    util.write_restricted_file('refresh_token', refresh_token)


def _shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def _refresh_using_refresh_token() -> bool:
    if not os.path.isfile('refresh_token'):
        logging.debug("No refresh token found")
        return False

    with open('refresh_token') as f:
        refresh_token = f.read()

    token_req_body = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': conf.IDP_CLIENT_NAME
    }

    r = requests.post(f"{conf.IDP_URL}/auth/realms/master/protocol/openid-connect/token", data=token_req_body)

    if r.status_code == 200:
        resp_body = r.json()
        _write_tokens(resp_body['access_token'], resp_body['expires_in'], resp_body['refresh_token'])
        logging.debug("Refreshed tokens using refresh token")
        return True
    else:
        logging.warning(f"Refreshing tokens failed with status {r.status_code}")
        return False


def auth():
    app = Flask(__name__)
    port = _get_free_port()
    url = f'http://127.0.0.1:{port}/login'
    thread = threading.Thread(target=app.run, args=("127.0.0.1", port, False, False,))

    @app.route('/keycloak.json')
    def controller_keycloak_conf():
        return render_template("keycloak.json", idp_url=conf.IDP_URL, client_name=conf.IDP_CLIENT_NAME)

    @app.route('/login')
    def controller_login():
        return render_template("login.html", idp_url=conf.IDP_URL, port=port)

    @app.route('/deliver-tokens', methods=['POST'])
    def controller_deliver_tokens():
        try:
            if request.is_json:
                body = request.get_json()
                _write_tokens(body['access_token'], int(body['access_token_valid_sec']), body['refresh_token'])

                return Response(status=200)
            else:
                return Response(status=400)
        finally:
            _shutdown_server()

    if _refresh_using_refresh_token():
        return

    # Assume the server starts in 1 second
    threading.Timer(1, lambda: webbrowser.open(url)).start()

    thread.start()
    thread.join()
