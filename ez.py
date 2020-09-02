import logging
from dataclasses import dataclass

import requests

import conf
import util

# TODO 1: add multithreading support for logging in threads
# TODO 2: move logging conf to proper location
logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s - %(message)s-%(levelname)s', level=logging.DEBUG)


@dataclass
class Resp:
    resp_code: int = None,
    response: requests.Response = None


@dataclass
class ExerciseDetailsResp(Resp):
    effective_title: str = None,
    text_html: str = None,
    deadline: str = None,
    grader_type: str = None,
    threshold: int = None,
    instructions_html: str = None


class Ez:
    def __init__(self):
        self.is_auth = False
        self.root = conf.BASE_URL

    def get_exercise_details(self, course_id: str, course_exercise_id: str) -> ExerciseDetailsResp:
        logging.debug(f"GET exercise details for course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)

        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}"

        resp: requests.Response = requests.get(path, headers=util.get_student_testing_header())

        dto = util.handle_response({200: (resp, ExerciseDetailsResp)})[200]
        assert isinstance(dto, ExerciseDetailsResp)
        return dto


# TODO: rm after implementation
if __name__ == '__main__':
    ez = Ez()
    print(ez.get_exercise_details("14", "2"))
