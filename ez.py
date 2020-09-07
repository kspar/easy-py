import logging
from dataclasses import dataclass

import conf
import data
import util

# TODO 1: add multithreading support for logging in threads
# TODO 2: move logging conf to proper location
logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s - %(message)s-%(levelname)s', level=logging.DEBUG)


class Ez:
    def __init__(self):
        self.is_auth = False
        self.root = conf.BASE_URL

    def get_my_courses(self) -> data.StudentCourseResp:
        """
        GET summaries of courses the authenticated student has access to.
        """
        logging.debug(f"Get summaries of courses the authenticated student has access to")
        path = f"{self.root}/student/courses"
        return util.simple_get_request(path, data.StudentCourseResp)

    def get_exercise_details(self, course_id: str, course_exercise_id: str) -> data.ExerciseDetailsResp:
        """
        GET the specified course exercise details.
        """
        logging.debug(f"GET exercise details for course '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}"
        return util.simple_get_request(path, data.ExerciseDetailsResp)

    def get_latest_exercise_submission_details(self, course_id: str, course_exercise_id: str) -> data.SubmissionResp:
        """
        GET and wait for the latest submission's details to the specified course exercise.
        """
        logging.debug(f"GET latest submission's details to the '{course_id}' exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/latest/await"
        return util.simple_get_request(path, data.SubmissionResp)

    def get_all_student_submissions(self, course_id: str, course_exercise_id: str) -> data.StudentAllSubmissionsResp:
        """
        GET submissions to this course exercise.
        """
        logging.debug(f" Get submissions to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id)
        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions/all"
        return util.simple_get_request(path, data.StudentAllSubmissionsResp)

    def post_student_submissions(self, course_id: str, course_exercise_id: str, solution: str) -> int:
        """
        POST submission to this course exercise.
        """
        logging.debug(f" POST submission '{solution}' to course '{course_id}' course exercise '{course_exercise_id}'")
        util.assert_not_none(course_id, course_exercise_id, solution)

        @dataclass
        class Submission:
            solution: str

        path = f"{self.root}/student/courses/{course_id}/exercises/{course_exercise_id}/submissions"
        return util.post_request(path, Submission(solution))


# TODO: rm after implementation
if __name__ == '__main__':
    ez = Ez()
    print(ez.get_my_courses())
    print(ez.get_exercise_details("1", "1"))
    print(ez.get_latest_exercise_submission_details("1", "1").autograde_status)
    print(ez.get_all_student_submissions("1", "1"))
    print(ez.post_student_submissions("1", "1", "solution1"))
