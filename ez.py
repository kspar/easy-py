import dataclasses
import json
import logging
import time
import typing as T
from dataclasses import dataclass

import requests

import auth
import conf
import data
import util
from defaults import read_token, write_tokens


# TODO:
# conf

class RequestUtil:
    def __init__(self,
                 retrieve_tokens: T.Callable[[data.Token], T.Tuple[str, int]],
                 persist_tokens: T.Callable[[str, int, str], None]):
        self.retrieve_tokens = retrieve_tokens
        self.persist_tokens = persist_tokens

    def simple_get_request(self, path: str, response_dto_class: T.Type[T.Any]) -> T.Any:
        resp: requests.Response = requests.get(path, headers=self.get_token_header())
        dto = util.handle_response(resp, {200: response_dto_class})
        assert isinstance(dto, response_dto_class)
        return dto

    # TODO. can also return DTO from this
    def post_request(self, path: str, request_dto_dataclass: T.Any) -> int:
        json_data = json.dumps(dataclasses.asdict(request_dto_dataclass)).encode("utf-8")
        resp: requests.Response = requests.post(path, data=json_data, headers=self.get_token_header())
        return resp.status_code

    def get_token_header(self) -> T.Dict[str, str]:
        access_token_file, expires_at = self.retrieve_tokens(data.Token.ACCESS)

        # TODO: make sure and test that we account for clock skew
        if access_token_file is None or time.time() > expires_at + conf.AUTH_TOKEN_MIN_VALID_SEC:
            auth.auth(self.retrieve_tokens, self.persist_tokens)
            access_token_file, expires_at = self.retrieve_tokens(data.Token.ACCESS)

            if access_token_file is None or time.time() > expires_at + conf.AUTH_TOKEN_MIN_VALID_SEC:
                raise RuntimeError("Could not get/refresh tokens")

        return {"Authorization": f"Bearer {access_token_file[data.Token.ACCESS.value]}"}


class Student:
    def __init__(self, root: str,
                 request_util: RequestUtil):
        self.root: str = root
        self.request_util = request_util

    def get_courses(self) -> data.StudentCourseResp:
        """
        GET summaries of courses the authenticated student has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated student has access to")
        path = f"{self.root}/student/courses"
        return self.request_util.simple_get_request(path, data.StudentCourseResp)

    def get_exercise_details(self, course_id: str, course_exercise_id: str) -> data.ExerciseDetailsResp:
        """
        GET the specified course exercise details.
        """
        logging.debug(f"GET exercise details for course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}"
        return self.request_util.simple_get_request(path, data.ExerciseDetailsResp)

    def get_latest_exercise_submission_details(self, course_id: str, course_exercise_id: str) -> data.SubmissionResp:
        """
        GET and wait for the latest submission's details to the specified course exercise.
        """
        logging.debug(f"GET latest submission's details to the '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/latest/await"
        return self.request_util.simple_get_request(path, data.SubmissionResp)

    def get_all_submissions(self, course_id: str, course_exercise_id: str) -> data.StudentAllSubmissionsResp:
        """
        GET submissions to this course exercise.
        """
        logging.debug(f" GET submissions to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/all"
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

        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions"
        return self.request_util.post_request(path, Submission(solution))


class Teacher:
    def __init__(self, root: str,
                 request_util: RequestUtil):
        self.root: str = root
        self.request_util = request_util

    def get_courses(self) -> data.TeacherCourseResp:
        """
        GET summaries of courses the authenticated teacher has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated teacher has access to")
        path = f"{self.root}/teacher/courses"
        return self.request_util.simple_get_request(path, data.TeacherCourseResp)


class Ez:
    def __init__(self,
                 retrieve_tokens: T.Callable[[data.Token], T.Tuple[str, int]],
                 persist_tokens: T.Callable[[str, int, str], None],
                 logging_level: int = logging.INFO):
        """

        :param retrieve_tokens:
        :param persist_tokens:
        :param logging_level: default logging level, e.g. logging.DEBUG. Default: logging.INFO
        """
        self.util = RequestUtil(retrieve_tokens, persist_tokens)
        self.student: Student = Student(conf.BASE_URL, self.util)
        self.teacher: Teacher = Teacher(conf.BASE_URL, self.util)
        logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s : %(message)s', level=logging_level)


# TODO: rm after implementation
if __name__ == '__main__':
    # print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("1", "1"))
    # print(ez.student.get_latest_exercise_submission_details("1", "1"))
    # print(ez.student.get_all_submissions("1", "1"))
    # print(ez.student.post_submission("1", "1", "solution1"))
    # print(ez.teacher.get_courses())

    ez = Ez(read_token, write_tokens)
    print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("2", "1"))
