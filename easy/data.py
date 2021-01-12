import typing as T
from dataclasses import dataclass
from enum import Enum

import requests


class AutogradeStatus(Enum):
    NONE = "NONE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GraderType(Enum):
    AUTO = "AUTO"
    TEACHER = "TEACHER"


class ExerciseStatus(Enum):
    UNSTARTED = "UNSTARTED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"


# TODO: why do all fields have default values?

@dataclass
class Resp:
    resp_code: int = None
    response: requests.Response = None


@dataclass
class EmptyResp(Resp):
    pass


@dataclass
class ExerciseDetailsResp(Resp):
    effective_title: str = None
    text_html: str = None
    deadline: str = None
    grader_type: GraderType = None
    threshold: int = None
    instructions_html: str = None


@dataclass
class StudentExercise(Resp):
    id: str = None
    effective_title: str = None
    deadline: str = None
    status: ExerciseStatus = None
    grade: int = None
    graded_by: GraderType = None
    ordering_idx: int = None


@dataclass
class StudentExerciseResp(Resp):
    exercises: T.List[StudentExercise] = None


@dataclass
class StudentCourse(Resp):
    id: str = None
    title: str = None


@dataclass
class StudentCourseResp(Resp):
    courses: T.List[StudentCourse] = None


@dataclass
class SubmissionResp(Resp):
    id: str = None
    solution: str = None
    submission_time: str = None
    autograde_status: AutogradeStatus = None
    grade_auto: int = None
    feedback_auto: str = None
    grade_teacher: int = None
    feedback_teacher: str = None


@dataclass
class StudentAllSubmissionsResp(Resp):
    submissions: T.List[SubmissionResp] = None
    count: int = None


@dataclass
class TeacherCourse(Resp):
    id: str = None
    title: str = None
    student_count: int = None


@dataclass
class TeacherCourseResp(Resp):
    courses: T.List[TeacherCourse] = None


@dataclass
class BasicCourseInfoResp(Resp):
    title: str = None
