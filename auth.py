import logging
import socket
import threading
import typing as T
import webbrowser

import requests
from flask import Flask, request, Response, render_template

import conf
import data


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


def _refresh_using_refresh_token(retrieve_tokens: T.Callable[[data.Token], T.Tuple[str, int]],
                                 persist_tokens: T.Callable[[str, int, str], None]) -> bool:
    refresh_token, _ = retrieve_tokens(data.Token.REFRESH)

    if refresh_token is None:
        logging.debug("No refresh token found")
        return False

    token_req_body = {
        'grant_type': "refresh_token",
        'refresh_token': refresh_token,
        'client_id': conf.IDP_CLIENT_NAME
    }

    r = requests.post(f"{conf.IDP_URL}/auth/realms/master/protocol/openid-connect/token", data=token_req_body)

    if r.status_code == 200:
        resp_body = r.json()
        persist_tokens(resp_body[data.Token.ACCESS.value],
                       resp_body['expires_in'],
                       resp_body[data.Token.REFRESH.value])

        logging.debug("Refreshed tokens using refresh token")
        return True
    else:
        logging.warning(f"Refreshing tokens failed with status {r.status_code}")
        return False


def auth(retrieve_tokens: T.Callable[[data.Token], T.Tuple[str, int]],
         persist_tokens: T.Callable[[str, int, str], None]):
    app = Flask(__name__)

    def shutdown_server():
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

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
                persist_tokens(body[data.Token.ACCESS.value],
                               int(body['access_token_valid_sec']),
                               body[data.Token.REFRESH.value])

                return Response(status=200)
            else:
                return Response(status=400)
        finally:
            shutdown_server()

    if _refresh_using_refresh_token(retrieve_tokens, persist_tokens):
        return

    local, port = "127.0.0.1", _get_free_port()
    url = f'http://{local}:{port}/login'
    thread = threading.Thread(target=app.run, args=(local, port, False, False,))

    # Assume the server starts in 1 second
    threading.Timer(1, lambda: webbrowser.open(url)).start()

    thread.start()
    thread.join()
