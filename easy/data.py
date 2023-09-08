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


class ParticipantRole(Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ALL = "all"


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
    is_open: bool = None


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
    alias: str = None


@dataclass
class StudentCourseResp(Resp):
    courses: T.List[StudentCourse] = None


@dataclass
class SubmissionResp(Resp):
    id: str = None
    number: int = None
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
    alias: str = None
    student_count: int = None


@dataclass
class TeacherCourseResp(Resp):
    courses: T.List[TeacherCourse] = None


@dataclass
class BasicCourseInfoResp(Resp):
    title: str = None
    alias: str = None


@dataclass
class CourseGroup:
    id: str
    name: str


@dataclass
class CourseParticipantsStudent:
    id: str
    email: str
    given_name: str
    family_name: str
    created_at: str
    groups: T.List[CourseGroup]
    moodle_username: str


@dataclass
class CourseParticipantsTeacher:
    id: str
    email: str
    given_name: str
    family_name: str
    created_at: str
    groups: T.List[CourseGroup]


@dataclass
class CourseParticipantsStudentPending:
    email: str
    valid_from: str
    groups: T.List[CourseGroup]


@dataclass
class CourseParticipantsStudentPendingMoodle:
    ut_username: str
    groups: T.List[CourseGroup]


@dataclass
class TeacherCourseParticipantsResp(Resp):
    moodle_short_name: str = None
    moodle_students_synced: bool = None
    moodle_grades_synced: bool = None
    student_count: int = None
    teacher_count: int = None
    students_pending_count: int = None
    students_moodle_pending_count: int = None
    students: T.List[CourseParticipantsStudent] = None
    teachers: T.List[CourseParticipantsTeacher] = None
    students_pending: T.List[CourseParticipantsStudentPending] = None
    students_moodle_pending: T.List[CourseParticipantsStudentPendingMoodle] = None


@dataclass
class TeacherCourseExercises:
    id: str
    effective_title: str
    soft_deadline: str
    grader_type: GraderType
    ordering_idx: int
    unstarted_count: int
    ungraded_count: int
    started_count: int
    completed_count: int


@dataclass
class TeacherCourseExercisesResp(Resp):
    exercises: T.List[TeacherCourseExercises] = None


@dataclass
class TeacherCourseExerciseSubmissionsStudent:
    id: str
    solution: str
    created_at: str
    grade_auto: int
    feedback_auto: str
    grade_teacher: int
    feedback_teacher: str


@dataclass
class TeacherCourseExerciseSubmissionsStudentResp(Resp):
    submissions: T.List[TeacherCourseExerciseSubmissionsStudent] = None
    count: int = None

