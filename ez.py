import logging
from dataclasses import dataclass
from enum import Enum
from typing import List

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


@dataclass
class StudentCourse:
    id: str = None,
    title: str = None


@dataclass
class StudentCourseResp(Resp):
    courses: List[StudentCourse] = None


class AutogradeStatus(Enum):
    NONE = "NONE"
    IN_PROGRESS = "IN_PRGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class LatestSubmission(Resp):
    id: str = None,
    solution: str = None
    submission_time: str = None
    autograde_status: AutogradeStatus = None
    grade_auto: int = None
    feedback_auto: str = None
    grade_teacher: int = None
    feedback_teacher: str = None


class Ez:
    def __init__(self):
        self.is_auth = False
        self.root = conf.BASE_URL

    def get_my_courses(self) -> StudentCourseResp:
        """
        Get summaries of courses the authenticated student has access to.
        """
        logging.debug(f"Get summaries of courses the authenticated student has access to")
        path = f"{self.root}/student/courses"
        return util.create_simple_get_request(path, StudentCourseResp)

    def get_exercise_details(self, course_id: str, course_exercise_id: str) -> ExerciseDetailsResp:
        """
        Get the specified course exercise details.
        """
        logging.debug(f"GET exercise details for course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}"
        return util.create_simple_get_request(path, ExerciseDetailsResp)

    def get_latest_exercise_submission_details(self, course_id: str, course_exercise_id: str) -> LatestSubmission:
        """
        Get and wait for the latest submission's details to the specified course exercise.
        """
        logging.debug(f"GET latest submission's details to the '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/latest/await"
        return util.create_simple_get_request(path, LatestSubmission)


# TODO: rm after implementation
if __name__ == '__main__':
    ez = Ez()
    # print(ez.get_my_courses())
    # print(ez.get_exercise_details("1", "1"))
    print(ez.get_latest_exercise_submission_details("1", "1").autograde_status)
