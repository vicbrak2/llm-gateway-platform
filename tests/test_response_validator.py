import json

from app.services.response_validator import ResponseValidator


def test_validator_accepts_valid_json_object() -> None:
    validator = ResponseValidator()
    content, is_valid = validator.validate('{"a":1}', 'json_object')
    assert json.loads(content) == {'a': 1}
    assert is_valid is True


def test_validator_wraps_plain_text_when_json_is_required() -> None:
    validator = ResponseValidator()
    content, is_valid = validator.validate('hello world', 'json_object')
    assert json.loads(content) == {'result': 'hello world'}
    assert is_valid is False
