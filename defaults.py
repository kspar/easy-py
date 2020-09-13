import json
import os
import typing as T

import ez


# TODO: both to gen-style 2nd-order funs to customise file path

def read_token_from_file(token_type: ez.TokenType) -> T.Optional[dict]:
    if os.path.isfile(token_type.value):
        try:
            return json.loads(get_file_content(token_type.value).strip())
        except json.JSONDecodeError:
            pass
    return None


def write_token_to_file(token_type: ez.TokenType, token: dict):
    write_restricted_file(token_type.value, json.dumps(token, sort_keys=True, indent=2))


def get_file_content(file_name) -> str:
    with open(file_name, encoding="utf-8") as f:
        return f.read()


def write_restricted_file(file_name, file_content):
    with open(os.open(file_name, os.O_CREAT | os.O_WRONLY, 0o600), "w") as f:
        f.write(file_content)
