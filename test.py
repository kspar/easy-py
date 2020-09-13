import logging

from defaults import read_token, write_tokens
from ez import Ez

# TODO: rm after implementation
if __name__ == '__main__':
    # print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("1", "1"))
    # print(ez.student.get_latest_exercise_submission_details("1", "1"))
    # print(ez.student.get_all_submissions("1", "1"))
    # print(ez.student.post_submission("1", "1", "solution1"))
    # print(ez.teacher.get_courses())

    ez = Ez('dev.ems.lahendus.ut.ee', 'dev.idp.lahendus.ut.ee', 'dev.lahendus.ut.ee', read_token,
            write_tokens, logging_level=logging.DEBUG)
    print(ez.student.get_courses())
    # print(ez.student.post_submission('7', '181', 'print("ez!")'))
    # print(ez.student.get_exercise_details("2", "1"))
