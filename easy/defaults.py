import json
import os
import typing as T

from easy import ez


def gen_read_token_from_file(storage_path_provider: T.Callable[[ez.TokenType], str],
                             namer: T.Callable[[ez.TokenType], str]):
    def read_token_from_file(token_type: ez.TokenType) -> T.Optional[dict]:
        path = os.path.join(storage_path_provider(token_type), namer(token_type))
        if os.path.isfile(path):
            try:
                return json.loads(get_file_content(path).strip())
            except json.JSONDecodeError:
                pass
        return None

    return read_token_from_file


def gen_write_token_to_file(storage_path_provider: T.Callable[[ez.TokenType], str],
                            namer: T.Callable[[ez.TokenType], str]):
    def write_token_to_file(token_type: ez.TokenType, token: dict):
        containing_dir = storage_path_provider(token_type)
        os.makedirs(containing_dir, exist_ok=True)
        path = os.path.join(containing_dir, namer(token_type))
        write_restricted_file(path, json.dumps(token, sort_keys=True, indent=2))

    return write_token_to_file


def get_file_content(file_name) -> str:
    with open(file_name, encoding="utf-8") as f:
        return f.read()


def write_restricted_file(file_name, file_content):
    with open(os.open(file_name, os.O_CREAT | os.O_WRONLY, 0o600), "w") as f:
        f.write(file_content)
