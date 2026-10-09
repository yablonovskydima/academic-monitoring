def send_account_credentials(email: str, login: str, password: str) -> None:
    print(f"[account created] to {email}: login={login} password={password}")


def send_password_reset(email: str, login: str, token: str) -> None:
    print(f"[password reset] to {email}: login={login} token={token}")


def send_login_changed(email: str, login: str) -> None:
    print(f"[login changed] to {email}: new login={login}")
