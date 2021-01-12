import base64
import dataclasses
import json
import logging
import pathlib
import sys
import threading
import time
import typing as T
import webbrowser
from dataclasses import dataclass
from enum import Enum

import requests
from flask import Flask, request, Response, render_template
from requests import RequestException

from . import data, util
from .exceptions import AuthRequiredException

API_VERSION_PREFIX = '/v2'
AUTH_SERVER_HOST = '127.0.0.1'
AUTH_SERVER_START_POLL_DELAY_SEC = 0.2
AUTH_SERVER_START_POLL_MAX_RETRIES = 20
TIMEOUT = 60


class TokenType(str, Enum):
    ACCESS = "access_token"
    REFRESH = "refresh_token"


@dataclass
class StorableToken:
    token_type: TokenType
    token: str
    expires_at: int


class RequestUtil:
    def __init__(self,
                 api_url: str,
                 idp_url: str,
                 idp_client_name: str,
                 auth_token_min_valid_sec: int,
                 auth_browser_success_msg: str,
                 auth_browser_fail_msg: str,
                 retrieve_token: T.Callable[[TokenType], T.Optional[dict]],
                 persist_token: T.Callable[[TokenType, dict], None]):

        self.api_url = api_url
        self.idp_url = idp_url
        self.idp_client_name = idp_client_name
        self.auth_token_min_valid_sec = auth_token_min_valid_sec
        self.auth_browser_success_msg = auth_browser_success_msg
        self.auth_browser_fail_msg = auth_browser_fail_msg
        self.retrieve_token = retrieve_token
        self.persist_token = persist_token

        self.auth_server_port: T.Optional[int] = None
        self.auth_server_thread: T.Optional[threading.Thread] = None

    def simple_get_request(self, path: str, response_dto_class: T.Type[T.Any]) -> T.Any:
        dto = self.get_request(path, {200: response_dto_class})
        assert isinstance(dto, response_dto_class)
        return dto

    # TODO: refactor to a single underlying request method?
    def get_request(self, path: str, resp_code_to_dto_class: T.Dict[int, T.Type[T.Any]]) -> T.Any:
        resp: requests.Response = requests.get(self.api_url + path, headers=self.get_token_header(), timeout=TIMEOUT)
        if resp.status_code == 401:
            raise AuthRequiredException()
        dto = util.handle_response(resp, resp_code_to_dto_class)
        return dto

    def post_request(self, path: str, request_dto_dataclass: T.Any,
                     resp_code_to_dto_class: T.Dict[int, T.Type[T.Any]]) -> T.Any:
        req_body_dict = dataclasses.asdict(request_dto_dataclass)
        resp: requests.Response = requests.post(self.api_url + path, json=req_body_dict,
                                                headers=self.get_token_header(), timeout=TIMEOUT)
        if resp.status_code == 401:
            raise AuthRequiredException()
        dto = util.handle_response(resp, resp_code_to_dto_class)
        return dto

    def get_token_header(self) -> T.Dict[str, str]:
        return {"Authorization": f"Bearer {self.get_valid_access_token().token}"}

    def get_valid_access_token(self) -> StorableToken:
        access_token = self.get_stored_token(TokenType.ACCESS)
        if not self.access_token_is_valid(access_token):
            if self._refresh_using_refresh_token():
                access_token = self.get_stored_token(TokenType.ACCESS)
                assert self.access_token_is_valid(access_token), 'Access token is not valid after refreshing'
            else:
                raise AuthRequiredException()

        return access_token

    def access_token_is_valid(self, access_token: T.Optional[StorableToken]):
        return access_token is not None and time.time() <= access_token.expires_at + self.auth_token_min_valid_sec

    def _refresh_using_refresh_token(self) -> bool:
        refresh_token = self.get_stored_token(TokenType.REFRESH)

        if refresh_token is None:
            logging.debug("No refresh token found")
            return False

        token_req_body = {
            'grant_type': "refresh_token",
            'refresh_token': refresh_token.token,
            'client_id': self.idp_client_name
        }

        r = requests.post(f"{self.idp_url}/auth/realms/master/protocol/openid-connect/token", data=token_req_body,
                          timeout=TIMEOUT)

        if r.status_code == 200:
            body = r.json()
            access_token = StorableToken(TokenType.ACCESS, body["access_token"],
                                         round(time.time()) + int(body['expires_in']))
            refresh_token = StorableToken(TokenType.REFRESH, body["refresh_token"],
                                          round(time.time()) + int(body['refresh_expires_in']))

            self.set_stored_token(TokenType.ACCESS, access_token)
            self.set_stored_token(TokenType.REFRESH, refresh_token)
            logging.info("Refreshed tokens using refresh token")
            return True
        else:
            logging.info(f"Refreshing tokens failed with status {r.status_code}")
            return False

    def start_auth_in_browser(self):
        templates_path = str((pathlib.Path(__file__).parent / 'auth-templates').resolve())
        app = Flask(__name__, template_folder=templates_path)
        # Disable Flask banner
        cli = sys.modules['flask.cli']
        cli.show_server_banner = lambda *x: None

        def shutdown_server():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()

        @app.route('/shutdown', methods=['POST'])
        def controller_shutdown():
            self.clear_server()
            shutdown_server()
            return Response(status=200)

        @app.route('/keycloak.json')
        def controller_keycloak_conf():
            return render_template("keycloak.json", idp_url=self.idp_url, client_name=self.idp_client_name)

        @app.route('/login')
        def controller_login():
            return render_template("login.html", idp_url=self.idp_url, port=self.auth_server_port,
                                   success_msg=self.auth_browser_success_msg, fail_msg=self.auth_browser_fail_msg)

        @app.route('/deliver-tokens', methods=['POST'])
        def controller_deliver_tokens():
            try:
                # Clear server first to decrease the race condition window
                self.clear_server()

                if request.is_json:
                    body = request.get_json()
                    access_token = StorableToken(TokenType.ACCESS, body["access_token"],
                                                 round(time.time()) + int(body['access_token_valid_sec']))
                    refresh_token = StorableToken(TokenType.REFRESH, body["refresh_token"],
                                                  round(time.time()) + int(body['refresh_token_valid_sec']))
                    self.set_stored_token(TokenType.ACCESS, access_token)
                    self.set_stored_token(TokenType.REFRESH, refresh_token)
                    return Response(status=200)
                else:
                    return Response(status=400)
            finally:
                shutdown_server()

        # Set and start server thread if it's not already running
        if not self.is_server_active():
            logging.debug('Auth server not active, starting it')
            self.auth_server_port = util.get_free_port()
            self.auth_server_thread = threading.Thread(target=app.run,
                                                       args=(AUTH_SERVER_HOST, self.auth_server_port, False, False))
            logging.debug('Starting server thread')
            self.auth_server_thread.start()
            logging.debug('Server thread started')
        else:
            logging.debug('Auth server already active')

        login_url = f'http://{AUTH_SERVER_HOST}:{self.auth_server_port}/login'

        # Wait until server has started
        for _ in range(AUTH_SERVER_START_POLL_MAX_RETRIES):
            time.sleep(AUTH_SERVER_START_POLL_DELAY_SEC)
            logging.debug('Checking if auth server is ready to serve...')
            try:
                status = requests.head(login_url).status_code
                if status == 200:
                    logging.debug('Auth server is ready')
                    break
                else:
                    logging.debug(f'Got unexpected status code {status} from auth server')
            except RequestException:
                logging.debug('Auth server is not ready yet')

        else:
            logging.error('Waiting for the local auth server to start timed out')
            raise RuntimeError('Waiting for the local auth server to start timed out')

        # And then open browser
        logging.debug('Opening browser')
        webbrowser.open(login_url)

    def is_server_active(self) -> bool:
        return self.auth_server_thread is not None

    def clear_server(self):
        self.auth_server_thread = None
        self.auth_server_port = None

    def get_stored_token(self, token_type: TokenType) -> T.Optional[StorableToken]:
        token_dict = self.retrieve_token(token_type)
        if token_dict is None:
            return None
        if token_dict is not None:
            return StorableToken(**token_dict)

    def set_stored_token(self, token_type: TokenType, token: StorableToken):
        self.persist_token(token_type, dataclasses.asdict(token))


class Common:
    def __init__(self, request_util: RequestUtil):
        self.request_util = request_util

    def get_course_basic_info(self, course_id: str) -> data.BasicCourseInfoResp:
        """
        Get basic info about this course.
        """
        logging.debug(f"GET basic info about this course.")
        path = f"/courses/{course_id}/basic"
        return self.request_util.simple_get_request(path, data.BasicCourseInfoResp)


class Student:
    def __init__(self, request_util: RequestUtil):
        self.request_util = request_util

    def get_courses(self) -> data.StudentCourseResp:
        """
        GET summaries of courses the authenticated student has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated student has access to")
        path = "/student/courses"
        return self.request_util.simple_get_request(path, data.StudentCourseResp)

    def get_course_exercises(self, course_id: str) -> data.StudentExerciseResp:
        """
        GER summaries of exercises on this course.
        """
        util.assert_not_none(course_id)
        logging.debug(f"GER summaries of exercises on this course.")
        path = f"/student/courses/{course_id}/exercises"
        return self.request_util.simple_get_request(path, data.StudentExerciseResp)

    def get_exercise_details(self, course_id: str, course_exercise_id: str) -> data.ExerciseDetailsResp:
        """
        GET the specified course exercise details.
        """
        logging.debug(f"GET exercise details for course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"/student/courses/{course_id}/exercises/{course_exercise_id}"
        return self.request_util.simple_get_request(path, data.ExerciseDetailsResp)

    def get_latest_exercise_submission_details(self, course_id: str, course_exercise_id: str) -> data.SubmissionResp:
        """
        GET and wait for the latest submission's details to the specified course exercise.
        """
        logging.debug(f"GET latest submission's details to the '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/latest/await"
        return self.request_util.simple_get_request(path, data.SubmissionResp)

    def get_all_submissions(self, course_id: str, course_exercise_id: str) -> data.StudentAllSubmissionsResp:
        """
        GET submissions to this course exercise.
        """
        logging.debug(f" GET submissions to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/all"
        return self.request_util.simple_get_request(path, data.StudentAllSubmissionsResp)

    def post_submission(self, course_id: str, course_exercise_id: str, solution: str) -> int:
        """
        POST submission to this course exercise.
        """
        logging.debug(f" POST submission '{solution}' to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id, solution)

        @dataclass
        class Submission:
            solution: str

        path = f"/student/courses/{course_id}/exercises/{course_exercise_id}/submissions"
        return self.request_util.post_request(path, Submission(solution), {200: data.EmptyResp})


class Teacher:
    def __init__(self,
                 request_util: RequestUtil):
        self.request_util = request_util

    def get_courses(self) -> data.TeacherCourseResp:
        """
        GET summaries of courses the authenticated teacher has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated teacher has access to")
        path = "/teacher/courses"
        return self.request_util.simple_get_request(path, data.TeacherCourseResp)


# TODO: hide private fields/methods
# TODO: should use TokenStorer type/class instead of functions?
# TODO: add logging and check whether the current levels make sense
# TODO: check that argument validation is reasonable for service functions
class Ez:
    def __init__(self,
                 api_base_url: str,
                 idp_url: str,
                 idp_client_name: str,
                 retrieve_token: T.Optional[T.Callable[[TokenType], T.Optional[dict]]] = None,
                 persist_token: T.Optional[T.Callable[[TokenType, dict], None]] = None,
                 auth_token_min_valid_sec: int = 20,
                 auth_browser_success_msg: str = "Authentication was successful! You can now close this page.",
                 auth_browser_fail_msg: str = "Something failed... did you try turning it off and on again?",
                 logging_level: int = logging.INFO):
        """
        TODO: doc
        :param logging_level: default logging level, e.g. logging.DEBUG. Default: logging.INFO
        """
        # Both must be either None or defined
        if (retrieve_token is None) != (persist_token is None):
            raise ValueError('Both retrieve_token and persist_token must be either defined or None')

        # ====== used only when token storage methods are undefined ======
        local_token_store = {}

        def in_memory_retrieve_token(token_type):
            return local_token_store[token_type] if token_type in local_token_store else None

        def in_memory_persist_token(token_type, token):
            local_token_store[token_type] = token

        # ======

        versioned_api_url = util.normalise_url(api_base_url) + API_VERSION_PREFIX
        normalised_idp_url = util.normalise_url(idp_url)

        self.util = RequestUtil(versioned_api_url, normalised_idp_url, idp_client_name,
                                auth_token_min_valid_sec,
                                auth_browser_success_msg.strip().replace('\n', ''),
                                auth_browser_fail_msg.strip().replace('\n', ''),
                                retrieve_token if retrieve_token is not None else in_memory_retrieve_token,
                                persist_token if persist_token is not None else in_memory_persist_token)
        self.student: Student = Student(self.util)
        self.teacher: Teacher = Teacher(self.util)
        self.common: Common = Common(self.util)

        logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s : %(message)s', level=logging_level)

    def check_in(self) -> int:

        """
        POST check-in.
        """
        logging.debug("POST check-in")
        # https://stackoverflow.com/questions/38683439/how-to-decode-base64-in-python3
        b64_string = self.util.get_valid_access_token().token.split(".")[1]
        b64_string += "=" * ((4 - len(b64_string) % 4) % 4)
        d = json.loads(base64.b64decode(b64_string))

        @dataclass
        class Account:
            first_name: str
            last_name: str

        self.util.get_valid_access_token()

        path = f"/account/checkin"
        return self.util.post_request(path, Account(d["given_name"], d["family_name"]), {200: data.EmptyResp})

    def start_auth_in_browser(self):
        self.util.start_auth_in_browser()

    def is_auth_in_progress(self, timeout_sec: int = 0) -> bool:
        thread = self.util.auth_server_thread
        if thread is None:
            return False
        else:
            thread.join(timeout_sec)
            return thread.is_alive()

    def is_auth_required(self) -> bool:
        try:
            self.util.get_valid_access_token()
            return False
        except AuthRequiredException:
            return True

    def shutdown(self):
        # Best effort stop server if running
        host, port, thread = AUTH_SERVER_HOST, self.util.auth_server_port, self.util.auth_server_thread
        if port is not None and thread is not None:
            logging.debug('Auth server seems to be running, attempting to shut down')
            shutdown_url = f'http://{host}:{port}/shutdown'
            try:
                status = requests.post(shutdown_url, timeout=2).status_code
                if status == 200:
                    logging.debug('Auth server shutdown seems to have worked')
                else:
                    logging.debug(f'Got unexpected status {status} when trying to shut down auth server')
            except Exception as e:
                logging.warning(f'Got exception {repr(e)}')

    def logout_in_browser(self):
        url = f"/auth/realms/master/protocol/openid-connect/logout?redirect_uri=https%3A%2F%2F"
        webbrowser.open(self.util.idp_url + url + self.util.idp_client_name)
