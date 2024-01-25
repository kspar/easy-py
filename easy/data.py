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


@dataclass
class Resp:
    resp_code: int
    response: requests.Response


@dataclass
class EmptyResp(Resp):
    pass


@dataclass
class ExerciseDetailsResp(Resp):
    effective_title: str
    text_html: str
    deadline: str
    grader_type: GraderType
    threshold: int
    instructions_html: str
    is_open: bool


@dataclass
class StudentExercise(Resp):
    id: str
    effective_title: str
    deadline: str
    status: ExerciseStatus
    grade: int
    graded_by: GraderType
    ordering_idx: int


@dataclass
class StudentExerciseResp(Resp):
    exercises: T.List[StudentExercise]


@dataclass
class StudentCourse(Resp):
    id: str
    title: str
    alias: str


@dataclass
class StudentCourseResp(Resp):
    courses: T.List[StudentCourse]


@dataclass
class SubmissionResp(Resp):
    id: str
    number: int
    solution: str
    submission_time: str
    autograde_status: AutogradeStatus
    grade_auto: int
    feedback_auto: str
    grade_teacher: int
    feedback_teacher: str


@dataclass
class StudentAllSubmissionsResp(Resp):
    submissions: T.List[SubmissionResp]
    count: int


@dataclass
class TeacherCourse(Resp):
    id: str
    title: str
    alias: str
    student_count: int


@dataclass
class TeacherCourseResp(Resp):
    courses: T.List[TeacherCourse]


@dataclass
class BasicCourseInfoResp(Resp):
    title: str
    alias: str


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
    moodle_short_name: str
    moodle_students_synced: bool
    moodle_grades_synced: bool
    student_count: int
    teacher_count: int
    students_pending_count: int
    students_moodle_pending_count: int
    students: T.List[CourseParticipantsStudent]
    teachers: T.List[CourseParticipantsTeacher]
    students_pending: T.List[CourseParticipantsStudentPending]
    students_moodle_pending: T.List[CourseParticipantsStudentPendingMoodle]


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
    exercises: T.List[TeacherCourseExercises]


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
    submissions: T.List[TeacherCourseExerciseSubmissionsStudent]
    count: int
