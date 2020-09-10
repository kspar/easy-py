import logging
from dataclasses import dataclass
from typing import Callable, Tuple

import conf
import data
import util
from defaults import read_token, write_tokens

logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s - %(message)s-%(levelname)s', level=logging.DEBUG)


class Student:
    def __init__(self, root: str,
                 read_token: Callable[[data.Token], Tuple[str, int]],
                 save_tokens: Callable[[str, int, str], None]):
        self.root: str = root
        self.read_token: Callable[[data.Token], Tuple[str, int]] = read_token
        self.write_token: Callable[[str, int, str], None] = save_tokens

    def get_courses(self) -> data.StudentCourseResp:
        """
        GET summaries of courses the authenticated student has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated student has access to")
        path = f"{self.root}/student/courses"
        return util.simple_get_request(path, data.StudentCourseResp, self.read_token, self.write_token)

    def get_exercise_details(self, course_id: str, course_exercise_id: str) -> data.ExerciseDetailsResp:
        """
        GET the specified course exercise details.
        """
        logging.debug(f"GET exercise details for course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}"
        return util.simple_get_request(path, data.ExerciseDetailsResp, self.read_token, self.write_token)

    def get_latest_exercise_submission_details(self, course_id: str, course_exercise_id: str) -> data.SubmissionResp:
        """
        GET and wait for the latest submission's details to the specified course exercise.
        """
        logging.debug(f"GET latest submission's details to the '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/latest/await"
        return util.simple_get_request(path, data.SubmissionResp, self.read_token, self.write_token)

    def get_all_submissions(self, course_id: str, course_exercise_id: str) -> data.StudentAllSubmissionsResp:
        """
        GET submissions to this course exercise.
        """
        logging.debug(f" GET submissions to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/all"
        return util.simple_get_request(path, data.StudentAllSubmissionsResp, self.read_token, self.write_token)

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
        return util.post_request(path, Submission(solution), self.read_token, self.write_token)


class Teacher:
    def __init__(self, root: str,
                 read_token: Callable[[data.Token], Tuple[str, int]],
                 save_tokens: Callable[[str, int, str], None]):
        self.root: str = root
        self.read_token: Callable[[data.Token], Tuple[str, int]] = read_token
        self.write_token: Callable[[str, int, str], None] = save_tokens

    def get_courses(self) -> data.TeacherCourseResp:
        """
        GET summaries of courses the authenticated teacher has access to.
        """
        logging.debug(f"GET summaries of courses the authenticated teacher has access to")
        path = f"{self.root}/teacher/courses"
        return util.simple_get_request(path, data.TeacherCourseResp, self.read_token, self.write_token)


class Ez:
    def __init__(self,
                 read_token: Callable[[data.Token], Tuple[str, int]],
                 save_tokens: Callable[[str, int, str], None]):
        self.student: Student = Student(conf.BASE_URL, read_token, save_tokens)
        self.teacher: Teacher = Teacher(conf.BASE_URL, read_token, save_tokens)


# TODO: rm after implementation
if __name__ == '__main__':
    # print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("1", "1"))
    # print(ez.student.get_latest_exercise_submission_details("1", "1"))
    # print(ez.student.get_all_submissions("1", "1"))
    # print(ez.student.post_submission("1", "1", "solution1"))
    # print(ez.teacher.get_courses())

    ez = Ez(read_token, write_tokens)
    print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("2", "1"))
