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
    UNGRADED = "UNGRADED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"


class SolutionFileType(Enum):
    TEXT_EDITOR = "TEXT_EDITOR"
    TEXT_UPLOAD = "TEXT_UPLOAd"


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
    solution_file_name: str
    solution_file_type: SolutionFileType


@dataclass
class GradeResp(Resp):
    grade: int
    is_autograde: bool
    is_graded_directly: bool


@dataclass
class AutomaticAssessmentResp(Resp):
    grade: int
    feedback: str


@dataclass
class StudentExercise(Resp):
    id: str
    effective_title: str
    grader_type: GraderType
    deadline: str
    is_open: bool
    status: ExerciseStatus
    grade: GradeResp
    ordering_idx: int


@dataclass
class StudentExerciseResp(Resp):
    exercises: T.List[StudentExercise]


@dataclass
class StudentCourse(Resp):
    id: str
    title: str
    alias: str
    archived: bool


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
    grade: GradeResp
    submission_status: ExerciseStatus
    auto_assessment: AutomaticAssessmentResp


@dataclass
class StudentAllSubmissionsResp(Resp):
    submissions: T.List[SubmissionResp]


@dataclass
class TeacherCourse(Resp):
    id: str
    title: str
    alias: str
    archived: bool
    student_count: int


@dataclass
class TeacherCourseResp(Resp):
    courses: T.List[TeacherCourse]


@dataclass
class BasicCourseInfoResp(Resp):
    title: str
    alias: str
    archived: bool


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


@dataclass
class CourseParticipantsStudentPending:
    email: str
    valid_from: str
    groups: T.List[CourseGroup]


@dataclass
class CourseParticipantsStudentPendingMoodle:
    moodle_username: str
    email: str
    groups: T.List[CourseGroup]


@dataclass
class TeacherCourseParticipantsResp(Resp):
    students: T.List[CourseParticipantsStudent]
    teachers: T.List[CourseParticipantsTeacher]
    students_pending: T.List[CourseParticipantsStudentPending]
    students_moodle_pending: T.List[CourseParticipantsStudentPendingMoodle]


@dataclass
class TeacherCourseExercises:
    course_exercise_id: str
    exercise_id: str
    library_title: str
    title_alias: str
    effective_title: str
    grade_threshold: int
    student_visible: bool
    student_visible_from: str
    soft_deadline: str
    hard_deadline: str
    grader_type: GraderType
    ordering_idx: int
    unstarted_count: int
    ungraded_count: int
    started_count: int
    completed_count: int
    # latest_submissions: T.List[SubmissionRow] TODO:  #out of date as of 02.08.2024. Implement data class SubmissionRow.


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


@dataclass
class FeedbackResp(Resp):
    feedback_html: str
    feedback_adoc: str


@dataclass
class TeacherResp(Resp):
    id: str
    given_name: str
    family_name: str


@dataclass
class TeacherActivityResp(Resp):
    id: str
    submission_id: str
    submission_number: int
    created_at: str
    grade: int
    edited_at: str
    feedback: FeedbackResp

@dataclass
class TeacherActivities(Resp):
    teacher_activities: T.List[TeacherActivityResp]

