import logging
from dataclasses import dataclass
from typing import Callable

import conf
import data
import util

logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s - %(message)s-%(levelname)s', level=logging.DEBUG)


class Student:
    def __init__(self, root: str, header_func: Callable):
        self.root: str = root
        self.header_func = header_func

    def get_courses(self) -> data.StudentCourseResp:
        """
        GET summaries of courses the authenticated student has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated student has access to")
        path = f"{self.root}/student/courses"
        return util.simple_get_request(path, data.StudentCourseResp, self.header_func)

    def get_exercise_details(self, course_id: str, course_exercise_id: str) -> data.ExerciseDetailsResp:
        """
        GET the specified course exercise details.
        """
        logging.debug(f"GET exercise details for course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}"
        return util.simple_get_request(path, data.ExerciseDetailsResp, self.header_func)

    def get_latest_exercise_submission_details(self, course_id: str, course_exercise_id: str) -> data.SubmissionResp:
        """
        GET and wait for the latest submission's details to the specified course exercise.
        """
        logging.debug(f"GET latest submission's details to the '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/latest/await"
        return util.simple_get_request(path, data.SubmissionResp, self.header_func)

    def get_all_submissions(self, course_id: str, course_exercise_id: str) -> data.StudentAllSubmissionsResp:
        """
        GET submissions to this course exercise.
        """
        logging.debug(f" GET submissions to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/all"
        return util.simple_get_request(path, data.StudentAllSubmissionsResp, self.header_func)

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
        return util.post_request(path, Submission(solution), self.header_func)


class Teacher:
    def __init__(self, root: str, header_func: Callable):
        self.root: str = root
        self.header_func = header_func

    def get_courses(self) -> data.TeacherCourseResp:
        """
        GET summaries of courses the authenticated teacher has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated teacher has access to")
        path = f"{self.root}/teacher/courses"
        return util.simple_get_request(path, data.TeacherCourseResp, self.header_func)


class Ez:
    def __init__(self, header_func: Callable):
        self.student: Student = Student(conf.BASE_URL, header_func)
        self.teacher: Teacher = Teacher(conf.BASE_URL, header_func)


# TODO: rm after implementation
if __name__ == '__main__':
    # print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("1", "1"))
    # print(ez.student.get_latest_exercise_submission_details("1", "1"))
    # print(ez.student.get_all_submissions("1", "1"))
    # print(ez.student.post_submission("1", "1", "solution1"))
    # print(ez.teacher.get_courses())

    ez = Ez(util.get_token_header)
    print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("2", "1"))
