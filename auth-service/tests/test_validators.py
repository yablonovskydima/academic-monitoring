import pytest

from auth_service.validators import validate_login, validate_name, validate_password_strength


@pytest.mark.parametrize("value", ["Ivan", "O'Brien", "Anna-Maria", "Оксана"])
def test_validate_name_accepts_valid_names(value):
    assert validate_name(value) == value


@pytest.mark.parametrize("value", ["", "   ", "J0hn", "Name123", "a" * 101])
def test_validate_name_rejects_invalid_names(value):
    with pytest.raises(ValueError):
        validate_name(value)


@pytest.mark.parametrize("value", ["abc", "valid.login-1", "a_b_c", "A" * 50])
def test_validate_login_accepts_valid_logins(value):
    assert validate_login(value) == value


@pytest.mark.parametrize("value", ["ab", "a" * 51, "bad login", "bad@login"])
def test_validate_login_rejects_invalid_logins(value):
    with pytest.raises(ValueError):
        validate_login(value)


@pytest.mark.parametrize("value", ["Str0ng!Pass", "Another$1Ok"])
def test_validate_password_strength_accepts_strong_passwords(value):
    assert validate_password_strength(value) == value


@pytest.mark.parametrize("value", [
    "short1!",
    "nouppercase1!",
    "NOLOWERCASE1!",
    "NoDigitsHere!",
    "NoSpecial123",
])
def test_validate_password_strength_rejects_weak_passwords(value):
    with pytest.raises(ValueError):
        validate_password_strength(value)
