import json
import logging
from dataclasses import dataclass

import requests

import conf
import util
from exceptions import EmptyResponseException, ResponseCodeNot200Exception

# TODO 1: add multithreading support for logging in threads
# TODO 2: move logging conf to proper location
logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s - %(message)s-%(levelname)s', level=logging.DEBUG)


@dataclass
class ExerciseDetailsResp:
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

    def get_exercise_details(self, course_id: str, course_exercise_id: str):
        util.assert_not_none(course_id, course_exercise_id)

        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}"

        exercise_details_resp = requests.get(path, headers=util.get_student_testing_header())

        if exercise_details_resp.status_code == 200:
            logging.debug(f"GET exercise details: {exercise_details_resp.status_code}")
            try:
                j = exercise_details_resp.json()
            except json.decoder.JSONDecodeError as e:
                raise EmptyResponseException(exercise_details_resp, e)

            return ExerciseDetailsResp(j["effective_title"],
                                       j["text_html"],
                                       j["deadline"],
                                       j["grader_type"],
                                       int(j["threshold"]),
                                       j["instructions_html"])
        else:
            logging.error(f"Exercise details returned: {exercise_details_resp}")
            raise ResponseCodeNot200Exception(exercise_details_resp)


# TODO: rm after implementation
if __name__ == '__main__':
    ez = Ez()
    resp = ez.get_exercise_details("1", "1")
    print(resp.instructions_html)
