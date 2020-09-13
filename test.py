import logging
import typing as T

import ez as e
from defaults import gen_read_token_from_file, gen_write_token_to_file


def get_student_testing_header() -> T.Dict[str, str]:
    return {"Content-Type": "application/json",
            "oidc_claim_easy_role": "student",
            "oidc_claim_email": "foo@bar.com",
            "oidc_claim_given_name": "Foo",
            "oidc_claim_family_name": "Bar",
            "oidc_claim_preferred_username": "fp"}


def get_teacher_testing_header() -> T.Dict[str, str]:
    return {"Content-Type": "application/json",
            "oidc_claim_easy_role": "teacher",
            "oidc_claim_email": "foo@bar.com",
            "oidc_claim_given_name": "Foo",
            "oidc_claim_family_name": "Bar",
            "oidc_claim_preferred_username": "fp"}


# TODO: rm after implementation
if __name__ == '__main__':
    # print(ez.student.get_courses())
    # print(ez.student.get_exercise_details("1", "1"))
    # print(ez.student.get_latest_exercise_submission_details("1", "1"))
    # print(ez.student.get_all_submissions("1", "1"))
    # print(ez.student.post_submission("1", "1", "solution1"))
    # print(ez.teacher.get_courses())

    path_provider = lambda _: 'ez-dev-tokens'
    namer = lambda tt: tt.value + '.json'
    success_msg = '''
    Autentimine õnnestus!
    Nüüd võid selle brauseriakna sulgeda.
    '''

    ez = e.Ez('dev.ems.lahendus.ut.ee', 'dev.idp.lahendus.ut.ee', 'dev.lahendus.ut.ee',
              gen_read_token_from_file(path_provider, namer),
              gen_write_token_to_file(path_provider, namer),
              auth_browser_success_msg=success_msg,
              logging_level=logging.INFO)
    print(ez.student.get_courses())
    # print(ez.student.post_submission('7', '181', 'print("ez!")'))
    # print(ez.student.get_exercise_details("2", "1"))
