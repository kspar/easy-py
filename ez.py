import logging
from dataclasses import dataclass

import conf
import data
import util

# TODO 1: add multithreading support for logging in threads
# TODO 2: move logging conf to proper location
logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s - %(message)s-%(levelname)s', level=logging.DEBUG)


class Student:
    def __init__(self, root: str, headers: dict):
        self.root: str = root
        self.headers: dict = headers

    def get_courses(self) -> data.StudentCourseResp:
        """
        GET summaries of courses the authenticated student has access to.
        """
        logging.debug(f"Get summaries of courses the authenticated student has access to")
        path = f"{self.root}/student/courses"
        return util.simple_get_request(path, data.StudentCourseResp, self.headers)

    def get_exercise_details(self, course_id: str, course_exercise_id: str) -> data.ExerciseDetailsResp:
        """
        GET the specified course exercise details.
        """
        logging.debug(f"GET exercise details for course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}"
        return util.simple_get_request(path, data.ExerciseDetailsResp, self.headers)

    def get_latest_exercise_submission_details(self, course_id: str, course_exercise_id: str) -> data.SubmissionResp:
        """
        GET and wait for the latest submission's details to the specified course exercise.
        """
        logging.debug(f"GET latest submission's details to the '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/latest/await"
        return util.simple_get_request(path, data.SubmissionResp, self.headers)

    def get_all_submissions(self, course_id: str, course_exercise_id: str) -> data.StudentAllSubmissionsResp:
        """
        GET submissions to this course exercise.
        """
        logging.debug(f" Get submissions to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/all"
        return util.simple_get_request(path, data.StudentAllSubmissionsResp, self.headers)

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
        return util.post_request(path, Submission(solution), self.headers)


class Teacher:
    def __init__(self, root: str, headers: dict):
        self.root: str = root
        self.headers: dict = headers

    def get_courses(self) -> data.TeacherCourseResp:
        """
        GET summaries of courses the authenticated teacher has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated teacher has access to")
        path = f"{self.root}/teacher/courses"
        return util.simple_get_request(path, data.TeacherCourseResp, self.headers)


class Ez:
    def __init__(self):
        self.is_auth = False
        self.root = conf.BASE_URL
        self.student: Student = Student(self.root, util.get_student_testing_header())
        self.teacher: Teacher = Teacher(self.root, util.get_teacher_testing_header())


# TODO: rm after implementation
if __name__ == '__main__':
    ez = Ez()
    print(ez.student.get_courses())
    print(ez.student.get_exercise_details("1", "1"))
    print(ez.student.get_latest_exercise_submission_details("1", "1"))
    print(ez.student.get_all_submissions("1", "1"))
    print(ez.student.post_submission("1", "1", "solution1"))
    print(ez.teacher.get_courses())
