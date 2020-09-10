from dataclasses import dataclass
from enum import Enum
from typing import List

import requests


class AutogradeStatus(Enum):
    NONE = "NONE"
    IN_PROGRESS = "IN_PRGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GraderType(Enum):
    AUTO = "AUTO"
    TEACHER = "TEACHER"


class Token(Enum):
    ACCESS = "access_token"
    REFRESH = "refresh_token"


@dataclass
class Resp:
    resp_code: int = None,
    response: requests.Response = None


@dataclass
class ExerciseDetailsResp(Resp):
    effective_title: str = None,
    text_html: str = None,
    deadline: str = None,
    grader_type: GraderType = None,
    threshold: int = None,
    instructions_html: str = None


@dataclass
class StudentCourse:
    id: str = None,
    title: str = None


@dataclass
class StudentCourseResp(Resp):
    courses: List[StudentCourse] = None


@dataclass
class SubmissionResp(Resp):
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
    submissions: List[SubmissionResp] = None,
    count: int = None


@dataclass
class TeacherCourse:
    id: str = None,
    title: str = None,
    student_count: int = None


@dataclass
class TeacherCourseResp(Resp):
    courses: List[TeacherCourse] = None
