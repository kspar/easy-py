import dataclasses
import logging
import pathlib
import secrets
import threading
import time
import typing as T
import webbrowser
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlencode

import requests
from flask import Flask, request, Response, render_template, redirect
from requests import RequestException
from werkzeug.serving import make_server

from . import data, util
from .exceptions import AuthRequiredException
from .util import decode_token

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
                 idp_realm_path: str,
                 logout_redirect_url: str,
                 auth_token_min_valid_sec: int,
                 auth_browser_success_msg: str,
                 auth_browser_fail_msg: str,
                 retrieve_token: T.Callable[[TokenType], T.Optional[dict]],
                 persist_token: T.Callable[[TokenType, T.Optional[dict]], None]):

        self.api_url = api_url
        self.idp_url = idp_url
        self.idp_client_name = idp_client_name
        self.idp_realm_path = idp_realm_path
        self.logout_redirect_url = logout_redirect_url
        self.auth_token_min_valid_sec = auth_token_min_valid_sec
        self.auth_browser_success_msg = auth_browser_success_msg
        self.auth_browser_fail_msg = auth_browser_fail_msg
        self.retrieve_token = retrieve_token
        self.persist_token = persist_token

        oidc_base = f'{idp_url}{idp_realm_path}/protocol/openid-connect'
        self.idp_auth_url = oidc_base + '/auth'
        self.idp_token_url = oidc_base + '/token'
        self.idp_logout_url = oidc_base + '/logout'

        self.auth_server_port: T.Optional[int] = None
        self.auth_server_thread: T.Optional[threading.Thread] = None

    def simple_get_request(self, path: str, response_dto_class: T.Type[T.Any]) -> T.Any:
        dto_class = {200: response_dto_class, 204: data.EmptyResp}

        resp: requests.Response = requests.get(self.api_url + path, headers=self.get_token_header(), timeout=TIMEOUT)

        if resp.status_code == 401:
            raise AuthRequiredException()

        return util.handle_response(resp, dto_class)

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
        return access_token is not None and time.time() <= access_token.expires_at - self.auth_token_min_valid_sec

    def _refresh_using_refresh_token(self) -> bool:
        refresh_token = self.get_stored_token(TokenType.REFRESH)

        if refresh_token is None:
            logging.debug("No refresh token found")
            return False

        if time.time() > refresh_token.expires_at - self.auth_token_min_valid_sec:
            logging.debug("Refresh token expired")
            return False

        token_req_body = {
            'grant_type': "refresh_token",
            'refresh_token': refresh_token.token,
            'client_id': self.idp_client_name
        }

        r = requests.post(self.idp_token_url, data=token_req_body, timeout=TIMEOUT)

        if r.status_code == 200:
            self._persist_tokens_from_idp_body(r.json())
            logging.info("Refreshed tokens using refresh token")
            return True
        else:
            logging.info(f"Refreshing tokens failed with status {r.status_code}")
            return False

    def _persist_tokens_from_idp_body(self, body: dict):
        access_token = StorableToken(TokenType.ACCESS, body["access_token"],
                                     round(time.time()) + int(body['expires_in']))
        refresh_token = StorableToken(TokenType.REFRESH, body["refresh_token"],
                                      round(time.time()) + int(body['refresh_expires_in']))

        self.set_stored_token(TokenType.ACCESS, access_token)
        self.set_stored_token(TokenType.REFRESH, refresh_token)

    def _create_auth_app(self, port: int, shutdown_server: T.Callable[[], None]) -> Flask:
        templates_path = str((pathlib.Path(__file__).parent / 'auth-templates').resolve())
        app = Flask(__name__, template_folder=templates_path)

        # The redirect URI sent to the token endpoint must be byte-identical to the one used in the
        # authorization request, and the callback clears self.auth_server_port before exchanging,
        # so both are captured here instead of being rebuilt from self inside the handlers.
        redirect_uri = f'http://{AUTH_SERVER_HOST}:{port}/login'
        # state -> code_verifier; one entry per opened login page, popped on use.
        # The server is single-threaded (make_server without threaded=True), so no locking is needed.
        pending_states: T.Dict[str, str] = {}

        @app.route('/shutdown', methods=['POST'])
        def controller_shutdown():
            self.clear_server()
            shutdown_server()
            return Response(status=200)

        @app.route('/health')
        def controller_health():
            return Response(status=200)

        @app.route('/login')
        def controller_login():
            if 'code' not in request.args and 'error' not in request.args:
                # Fresh login: send the browser to the IdP with a new state + PKCE pair
                verifier, challenge = util.generate_pkce_pair()
                state = secrets.token_urlsafe(32)
                pending_states[state] = verifier
                return redirect(self.idp_auth_url + '?' + urlencode({
                    'client_id': self.idp_client_name,
                    'redirect_uri': redirect_uri,
                    'response_type': 'code',
                    'scope': 'openid',
                    'state': state,
                    'code_challenge': challenge,
                    'code_challenge_method': 'S256',
                }))

            # OAuth callback: this request ends the auth server, whatever the outcome.
            # Clear server first to decrease the race condition window
            self.clear_server()

            def fail_page():
                return render_template('auth-result.html', message=self.auth_browser_fail_msg, close_window=False)

            try:
                if 'error' in request.args:
                    logging.info(f"Authentication failed: {request.args.get('error')} "
                                 f"({request.args.get('error_description')})")
                    return fail_page()

                verifier = pending_states.pop(request.args.get('state'), None)
                code = request.args.get('code')
                if verifier is None or not code:
                    logging.info('Authentication failed: unknown state or missing code')
                    return fail_page()

                r = requests.post(self.idp_token_url, data={
                    'grant_type': 'authorization_code',
                    'client_id': self.idp_client_name,
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'code_verifier': verifier,
                }, timeout=TIMEOUT)

                if r.status_code != 200:
                    # The failure body is an error JSON; a success body would contain tokens - never log that
                    logging.info(f'Token exchange failed with status {r.status_code}: {r.text}')
                    return fail_page()

                self._persist_tokens_from_idp_body(r.json())
                return render_template('auth-result.html', message=self.auth_browser_success_msg, close_window=True)
            except Exception as e:
                logging.warning(f'Token exchange failed: {repr(e)}')
                return fail_page()
            finally:
                shutdown_server()

        return app

    def start_auth_in_browser(self):
        # Set and start server thread if it's not already running
        if not self.is_server_active():
            logging.debug('Auth server not active, starting it')
            port = util.get_free_port()

            # The routes need to be able to stop the server, and the server needs the app that holds
            # those routes, so the reference is handed over through a holder.
            server_holder: T.Dict[str, T.Any] = {}

            def shutdown_server():
                server = server_holder.get('server')
                if server is None:
                    return
                # shutdown() returns once the serving loop has stopped, and the loop cannot stop
                # while this request is still being handled - so ask for it from another thread
                threading.Thread(target=server.shutdown, daemon=True).start()

            app = self._create_auth_app(port, shutdown_server)
            # threaded=False keeps handlers serialized, which pending_states relies on
            server = make_server(AUTH_SERVER_HOST, port, app, threaded=False)
            server_holder['server'] = server

            def serve():
                try:
                    server.serve_forever()
                finally:
                    server.server_close()

            self.auth_server_port = port
            self.auth_server_thread = threading.Thread(target=serve)
            logging.debug('Starting server thread')
            self.auth_server_thread.start()
            logging.debug('Server thread started')
        else:
            logging.debug('Auth server already active')

        login_url = f'http://{AUTH_SERVER_HOST}:{self.auth_server_port}/login'
        health_url = f'http://{AUTH_SERVER_HOST}:{self.auth_server_port}/health'

        # Wait until server has started. Polling /login would generate a pending state per poll
        # and would return a 302, so a dedicated health endpoint is polled instead.
        for _ in range(AUTH_SERVER_START_POLL_MAX_RETRIES):
            time.sleep(AUTH_SERVER_START_POLL_DELAY_SEC)
            logging.debug('Checking if auth server is ready to serve...')
            try:
                status = requests.head(health_url, timeout=2).status_code
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

    def set_stored_token(self, token_type: TokenType, token: T.Optional[StorableToken]):
        self.persist_token(token_type, None if token is None else dataclasses.asdict(token))


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

    def await_latest_exercise_submission_details(self, course_id: str, course_exercise_id: str) -> None:
        """
        GET and wait for the latest submission's details to the specified course exercise.
        """
        logging.debug(f"GET latest submission's details to the '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/latest/await"
        self.request_util.simple_get_request(path, data.SubmissionResp)

    def get_all_exercise_teacher_activities(self, course_id: str, course_exercise_id: str) -> data.TeacherActivities:
        """
        GET all teacher activities for this exercise
        """
        logging.debug(f"GET teacher activities on course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"/student/courses/{course_id}/exercises/{course_exercise_id}/activities"
        return self.request_util.simple_get_request(path, data.TeacherActivities)

    def get_inline_comments(self, course_id: str, course_exercise_id: str) -> data.InlineCommentsResp:
        """
        GET teachers' inline comments on the authenticated student's submissions to this course exercise.
        Comments span all submissions; use submission_number to tell them apart.
        """
        logging.debug(f"GET inline comments on course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"/student/courses/{course_id}/exercises/{course_exercise_id}/inline-comments"
        return self.request_util.simple_get_request(path, data.InlineCommentsResp)

    def get_all_submissions(self, course_id: str, course_exercise_id: str) -> data.StudentAllSubmissionsResp:
        """
        GET submissions to this course exercise.
        """
        logging.debug(f" GET submissions to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/all"
        return self.request_util.simple_get_request(path, data.StudentAllSubmissionsResp)

    def set_student_last_access(self, course_id: str):
        logging.debug(f"POST set student last access  to course '{course_id}'")
        util.assert_not_none(course_id)

        @dataclass
        class EmptyReq:
            pass

        path = f"/student/courses/{course_id}/access"
        return self.request_util.post_request(path, EmptyReq(),{200: data.EmptyResp})

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

    def get_course_participants(self, course_id: str, role: data.ParticipantRole = data.ParticipantRole.ALL,
                                limit: int = 1_000_000, offset: int = 0) -> data.TeacherCourseParticipantsResp:
        """
        TODO
        """
        logging.debug(f"Get participants on course {course_id} with role {role} (offset: {offset}, limit: {limit})")
        path = f"/courses/{course_id}/participants?role={role.value}&offset={offset}&limit={limit}"
        return self.request_util.simple_get_request(path, data.TeacherCourseParticipantsResp)

    def get_course_exercises(self, course_id: str) -> data.TeacherCourseExercisesResp:
        """
        TODO
        """
        logging.debug(f"Get teacher exercises on course {course_id}")
        path = f"/teacher/courses/{course_id}/exercises"
        return self.request_util.simple_get_request(path, data.TeacherCourseExercisesResp)

    def get_course_exercise_submissions_student(self, course_id: str, course_exercise_id: str, student_id: str,
                                                limit: int = 1_000_000,
                                                offset: int = 0) -> data.TeacherCourseExerciseSubmissionsStudentResp:
        """
        TODO
        """
        logging.debug(f"Get submissions to course exercise {course_exercise_id} on course {course_id} by "
                      f"student {student_id} (offset: {offset}, limit: {limit})")
        path = f"/teacher/courses/{course_id}/exercises/{course_exercise_id}/submissions/all/students/{student_id}" \
               f"?offset={offset}&limit={limit}"
        return self.request_util.simple_get_request(path, data.TeacherCourseExerciseSubmissionsStudentResp)


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
                 logging_level: int = logging.INFO,
                 idp_realm_path: str = '/auth/realms/master',
                 logout_redirect_url: T.Optional[str] = None):
        """
        TODO: doc
        :param logging_level: default logging level, e.g. logging.DEBUG. Default: logging.INFO
        :param idp_realm_path: path of the Keycloak realm on the IdP host; OIDC endpoints are derived as
        {idp_url}{idp_realm_path}/protocol/openid-connect/{auth,token,logout}. Default: /auth/realms/master
        :param logout_redirect_url: where the browser is sent after logout (must be registered as a valid
        post-logout redirect URI on the IdP client). Default: https://{idp_client_name}
        """
        # Both must be either None or defined
        if (retrieve_token is None) != (persist_token is None):
            raise ValueError('Both retrieve_token and persist_token must be either defined or None')

        # ====== used only when token storage methods are undefined ======
        local_token_store = {}

        def in_memory_retrieve_token(token_type):
            return local_token_store[token_type] if token_type in local_token_store else None

        def in_memory_persist_token(token_type, token):
            if token is None:
                local_token_store.pop(token_type, None)
            else:
                local_token_store[token_type] = token

        # ======

        versioned_api_url = util.normalise_url(api_base_url) + API_VERSION_PREFIX
        normalised_idp_url = util.normalise_url(idp_url)
        stripped_realm_path = idp_realm_path.strip().strip('/')
        normalised_realm_path = f'/{stripped_realm_path}' if stripped_realm_path else ''
        if logout_redirect_url is None:
            logout_redirect_url = f'https://{idp_client_name}'

        self.util = RequestUtil(versioned_api_url, normalised_idp_url, idp_client_name,
                                normalised_realm_path, logout_redirect_url,
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
        d = decode_token(self.util.get_valid_access_token().token)

        @dataclass
        class Account:
            first_name: str
            last_name: str

        self.util.get_valid_access_token()

        path = f"/account/checkin"
        return self.util.post_request(path, Account(d["given_name"], d["family_name"]), {200: data.EmptyResp})

    def start_auth_in_browser(self):
        self.util.start_auth_in_browser()

    def is_auth_in_progress(self, timeout_sec: T.Optional[int] = 0) -> bool:
        thread = self.util.auth_server_thread
        if thread is None:
            return False
        else:
            thread.join(timeout_sec)
            return thread.is_alive()

    def await_is_auth_completed(self, timeout_sec: T.Optional[int] = None) -> bool:
        self.is_auth_in_progress(timeout_sec)
        return not self.is_auth_required()

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
        self.util.set_stored_token(TokenType.ACCESS, None)
        self.util.set_stored_token(TokenType.REFRESH, None)
        # Without an id_token_hint, Keycloak honours post_logout_redirect_uri only together with
        # client_id, and shows a one-click logout confirmation page first.
        webbrowser.open(self.util.idp_logout_url + '?' + urlencode({
            'client_id': self.util.idp_client_name,
            'post_logout_redirect_uri': self.util.logout_redirect_url,
        }))
