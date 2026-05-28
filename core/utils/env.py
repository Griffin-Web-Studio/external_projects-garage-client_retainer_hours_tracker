from pathlib import Path


def populate_secure_secret(env_path: Path):
    import secrets
    import string

    _alphabet = string.ascii_letters + string.digits + "!@/|\\^&*(-_=+)"
    SECRET_KEY = "".join(secrets.choice(_alphabet) for _ in range(50))
    _ini_path = env_path

    with open(_ini_path, "r") as f:
        _contents = f.read()

    with open(_ini_path, "w") as f:
        f.write(
            _contents.replace(
                "SECRET_KEY=your-secret-key-here", f"SECRET_KEY={SECRET_KEY}"
            )
        )

    print("Generated new SECRET_KEY and saved to .env.")
