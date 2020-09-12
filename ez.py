import dataclasses
import logging
import socket
import threading
import time
import typing as T
import webbrowser
from dataclasses import dataclass

import requests
from flask import Flask, request, Response, render_template

import data
import util
from defaults import read_token, write_tokens

# TODO:
# hide private fields/methods

API_VERSION_PREFIX = '/v2'


class RequestUtil:
    def __init__(self,
                 api_url: str,
                 idp_url: str,
                 idp_client_name: str,
                 auth_token_min_valid_sec: int,
                 auth_port_range_first: int,
                 auth_port_range_last: int,
                 retrieve_tokens: T.Callable[[data.Token], T.Tuple[str, int]],
                 persist_tokens: T.Callable[[str, int, str], None]):

        self.api_url = api_url
        self.idp_url = idp_url
        self.idp_client_name = idp_client_name
        self.auth_token_min_valid_sec = auth_token_min_valid_sec
        self.auth_port_range_first = auth_port_range_first
        self.auth_port_range_last = auth_port_range_last
        self.retrieve_tokens = retrieve_tokens
        self.persist_tokens = persist_tokens

    def simple_get_request(self, path: str, response_dto_class: T.Type[T.Any]) -> T.Any:
        resp: requests.Response = requests.get(self.api_url + path, headers=self.get_token_header())
        dto = util.handle_response(resp, {200: response_dto_class})
        assert isinstance(dto, response_dto_class)
        return dto

    def post_request(self, path: str, request_dto_dataclass: T.Any,
                     resp_code_to_dto_class: T.Dict[int, T.Type[T.Any]]) -> T.Any:
        req_body_dict = dataclasses.asdict(request_dto_dataclass)
        resp: requests.Response = requests.post(self.api_url + path, json=req_body_dict,
                                                headers=self.get_token_header())
        dto = util.handle_response(resp, resp_code_to_dto_class)
        return dto

    def get_token_header(self) -> T.Dict[str, str]:
        access_token_file, expires_at = self.retrieve_tokens(data.Token.ACCESS)

        # TODO: make sure and test that we account for clock skew
        if access_token_file is None or time.time() > expires_at + self.auth_token_min_valid_sec:
            self.auth()
            access_token_file, expires_at = self.retrieve_tokens(data.Token.ACCESS)

            if access_token_file is None or time.time() > expires_at + self.auth_token_min_valid_sec:
                raise RuntimeError("Could not get/refresh tokens")

        return {"Authorization": f"Bearer {access_token_file[data.Token.ACCESS.value]}"}

    def auth(self):
        app = Flask(__name__)

        def shutdown_server():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()

        @app.route('/keycloak.json')
        def controller_keycloak_conf():
            return render_template("keycloak.json", idp_url=self.idp_url, client_name=self.idp_client_name)

        @app.route('/login')
        def controller_login():
            return render_template("login.html", idp_url=self.idp_url, port=port)

        @app.route('/deliver-tokens', methods=['POST'])
        def controller_deliver_tokens():
            try:
                if request.is_json:
                    body = request.get_json()
                    self.persist_tokens(body[data.Token.ACCESS.value],
                                        int(body['access_token_valid_sec']),
                                        body[data.Token.REFRESH.value])

                    return Response(status=200)
                else:
                    return Response(status=400)
            finally:
                shutdown_server()

        if self._refresh_using_refresh_token():
            return

        local, port = "127.0.0.1", self._get_free_port()
        url = f'http://{local}:{port}/login'
        thread = threading.Thread(target=app.run, args=(local, port, False, False,))

        # Assume the server starts in 1 second
        threading.Timer(1, lambda: webbrowser.open(url)).start()

        thread.start()
        thread.join()

    def _get_free_port(self) -> int:
        for p in range(self.auth_port_range_first, self.auth_port_range_last + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('127.0.0.1', p))
                sock.close()
                return p
            except OSError:
                # Port already in use?
                pass

        raise OSError(f"Unable to bind to ports {self.auth_port_range_first} - {self.auth_port_range_last}")

    def _refresh_using_refresh_token(self) -> bool:
        refresh_token, _ = self.retrieve_tokens(data.Token.REFRESH)

        if refresh_token is None:
            logging.debug("No refresh token found")
            return False

        token_req_body = {
            'grant_type': "refresh_token",
            'refresh_token': refresh_token,
            'client_id': self.idp_client_name
        }

        r = requests.post(f"{self.idp_url}/auth/realms/master/protocol/openid-connect/token", data=token_req_body)

        if r.status_code == 200:
            resp_body = r.json()
            self.persist_tokens(resp_body[data.Token.ACCESS.value],
                                resp_body['expires_in'],
                                resp_body[data.Token.REFRESH.value])

            logging.debug("Refreshed tokens using refresh token")
            return True
        else:
            logging.warning(f"Refreshing tokens failed with status {r.status_code}")
            return False


class Student:
    def __init__(self,
                 request_util: RequestUtil):
        self.request_util = request_util

    def get_courses(self) -> data.StudentCourseResp:
        """
        GET summaries of courses the authenticated student has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated student has access to")
        path = "/student/courses"
        return self.request_util.simple_get_request(path, data.StudentCourseResp)

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


# TODO: token methods to optional
class Ez:
    def __init__(self,
                 api_base_url: str,
                 idp_url: str,
                 idp_client_name: str,
                 retrieve_tokens: T.Callable[[data.Token], T.Tuple[str, int]],
                 persist_tokens: T.Callable[[str, int, str], None],
                 auth_token_min_valid_sec: int = 20,
                 auth_port_range_first: int = 5100,
                 auth_port_range_last: int = 5109,
                 logging_level: int = logging.INFO):
        """
        TODO
        :param logging_level: default logging level, e.g. logging.DEBUG. Default: logging.INFO
        """
        if not api_base_url.startswith('http'):
            api_base_url = 'https://' + api_base_url
        api_base_url = api_base_url.rstrip('/')
        versioned_api_url = api_base_url + API_VERSION_PREFIX

        if not idp_url.startswith('http'):
            idp_url = 'https://' + idp_url
        idp_url = idp_url.rstrip('/')

        self.util = RequestUtil(versioned_api_url, idp_url, idp_client_name, auth_token_min_valid_sec,
                                auth_port_range_first, auth_port_range_last, retrieve_tokens, persist_tokens)
        self.student: Student = Student(self.util)
        self.teacher: Teacher = Teacher(self.util)

        logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s : %(message)s', level=logging_level)


# TODO: rm after implementation
if __name__ == '__main__':
    # print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("1", "1"))
    # print(ez.student.get_latest_exercise_submission_details("1", "1"))
    # print(ez.student.get_all_submissions("1", "1"))
    # print(ez.student.post_submission("1", "1", "solution1"))
    # print(ez.teacher.get_courses())

    ez = Ez('dev.ems.lahendus.ut.ee', 'dev.idp.lahendus.ut.ee', 'dev.lahendus.ut.ee', read_token,
            write_tokens, logging_level=logging.DEBUG)
    print(ez.student.get_courses())
    # print(ez.student.post_submission('7', '181', 'print("ez!")'))
    # print(ez.student.get_exercise_details("2", "1"))
