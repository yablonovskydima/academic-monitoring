import re

_NAME_PATTERN = re.compile(r"^[A-Za-zА-ЯЁІЇЄҐа-яёіїєґ'’\- ]+$")
_SPECIAL_CHAR_PATTERN = re.compile(r"""[!"#$%&'()*+,\-./:;<=>?@\[\]^_`{|}~]""")
_LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

MIN_PASSWORD_LENGTH = 8
MAX_NAME_LENGTH = 100
MIN_LOGIN_LENGTH = 3
MAX_LOGIN_LENGTH = 50


def validate_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    if len(value) > MAX_NAME_LENGTH:
        raise ValueError(f"must be at most {MAX_NAME_LENGTH} characters")
    if not _NAME_PATTERN.match(value):
        raise ValueError("may only contain letters, spaces, hyphens, and apostrophes")
    return value


def validate_login(value: str) -> str:
    value = value.strip()
    if len(value) < MIN_LOGIN_LENGTH:
        raise ValueError(f"must be at least {MIN_LOGIN_LENGTH} characters long")
    if len(value) > MAX_LOGIN_LENGTH:
        raise ValueError(f"must be at most {MAX_LOGIN_LENGTH} characters")
    if not _LOGIN_PATTERN.match(value):
        raise ValueError("may only contain letters, digits, dots, underscores, and hyphens")
    return value


def validate_password_strength(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"must be at least {MIN_PASSWORD_LENGTH} characters long")
    if not re.search(r"[a-z]", value):
        raise ValueError("must contain at least one lowercase letter")
    if not re.search(r"[A-Z]", value):
        raise ValueError("must contain at least one uppercase letter")
    if not re.search(r"\d", value):
        raise ValueError("must contain at least one digit")
    if not _SPECIAL_CHAR_PATTERN.search(value):
        raise ValueError("must contain at least one special character")
    return value
