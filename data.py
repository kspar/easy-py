from dataclasses import dataclass
from enum import Enum
from typing import List

import requests


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
class Submission(Resp):
    id: str = None,
    solution: str = None
    submission_time: str = None
    autograde_status: AutogradeStatus = None
    grade_auto: int = None
    feedback_auto: str = None
    grade_teacher: int = None
    feedback_teacher: str = None


@dataclass
class StudentAllSubmissionsResp(Resp):
    submissions: List[Submission] = None,
    count: int = None
