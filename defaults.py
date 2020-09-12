import json
import os
import time
import typing as T

import data


def read_token(token_type: data.Token) -> T.Tuple[str, int]:
    token_file, expires_at = None, 0

    if os.path.isfile(token_type.value):
        if token_type == data.Token.ACCESS:
            token_file = json.loads(get_file_content(token_type.value).strip())
            expires_at = token_file["expires_at"]
        elif token_type == data.Token.REFRESH:
            token_file = get_file_content(token_type.value).strip()
            expires_at = 0

    return token_file, expires_at


def write_tokens(access_token: str, valid_sec: int, refresh_token: str):
    access_token_file = json.dumps({
        data.Token.ACCESS.value: access_token,
        'expires_at': round(time.time()) + valid_sec
    })

    write_restricted_file(data.Token.ACCESS.value, access_token_file)
    write_restricted_file(data.Token.REFRESH.value, refresh_token)


def get_file_content(file_name) -> str:
    with open(file_name, encoding="utf-8") as f:
        return f.read()


def write_restricted_file(file_name, file_content):
    with open(os.open(file_name, os.O_CREAT | os.O_WRONLY, 0o600), "w") as f:
        f.write(file_content)


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
