"""
Application custom settings for the entire project.


For more information on this file, see
TODO: add link

For the full list of settings and their values, see
TODO: add link
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class AppConfig:
    """
    Immutable application configuration singleton.
    Initialised once at startup from settings.ini (.env for secrets).
    Access anywhere via AppConfig.get() - no need to go through
    django.conf.settings for app-level values.
    """

    # ────────────────────────────────────────────────────────────| Branding |──
    app_name: str

    # ──────────────────────────────────────────────| Hours / business rules |──
    term_months: int
    dev_conversion_ratio: float
    max_migrate_hours: float
    low_hours_threshold: float

    # ────────────────────────────────────────────────────────────────| OIDC |──
    oidc_enabled: bool
    oidc_issuer: str
    oidc_client_id: str
    oidc_client_secret: str
    oidc_allowed_domains: tuple[str, ...]  # tuple keeps the instance hashable

    # ───────────────────────────────────────────────────────────| Singleton |──
    # ClassVar fields are excluded from __init__ / __hash__ by the dataclass
    # machinery, so frozen=True doesn't prevent us setting this class attribute.
    _instance: ClassVar[AppConfig | None] = None

    # ─────────────────────────────────────────────────────────────| Factory |──

    @classmethod
    def initialise(cls, ini_path: Path, env) -> AppConfig:
        """
        Build and store the singleton.
        Call once in settings.py after environ.Env.read_env() has run.
        Subsequent calls are no-ops and return the existing instance.

        `env` is the django-environ Env() accessor already configured in
        settings.py - keeps this class free of a hard environ dependency.
        """
        if cls._instance is not None:
            return cls._instance

        # Auto-create settings.ini from the example file on first run
        if not ini_path.exists():
            example = ini_path.parent / (ini_path.name + ".example")
            if example.exists():
                import shutil

                shutil.copy(example, ini_path)
                print(
                    f"Created {ini_path.name} from {example.name} -"
                    " review it before continuing."
                )
            else:
                print(
                    f"Warning: {ini_path.name} not found and no .example to"
                    " copy from. All business settings will use built-in "
                    "defaults."
                )

        config = configparser.ConfigParser()
        config.read(ini_path)

        oidc_issuer = env("OIDC_ISSUER", default="")

        cls._instance = cls(
            # Branding
            app_name=config.get(
                "branding", "app_name", fallback="RetainerTracker"
            ),
            # Hours
            term_months=config.getint("hours", "term_months", fallback=12),
            dev_conversion_ratio=config.getfloat(
                "hours", "dev_conversion_ratio", fallback=2.0
            ),
            max_migrate_hours=config.getfloat(
                "hours", "max_migrate_hours", fallback=6.0
            ),
            low_hours_threshold=config.getfloat(
                "hours", "low_hours_threshold", fallback=75.0
            ),
            # OIDC - only read credentials from env if issuer is actually set
            oidc_enabled=bool(oidc_issuer),
            oidc_issuer=oidc_issuer,
            oidc_client_id=(
                env("OIDC_CLIENT_ID", default="") if oidc_issuer else ""
            ),
            oidc_client_secret=(
                env("OIDC_CLIENT_SECRET", default="") if oidc_issuer else ""
            ),
            oidc_allowed_domains=tuple(
                d.strip()
                for d in config.get(
                    "auth", "oidc_allowed_domains", fallback=""
                ).split(",")
                if d.strip()
            ),
        )
        return cls._instance

    @classmethod
    def get(cls) -> AppConfig:
        """
        Retrieve the singleton from anywhere in the codebase.
        Raises RuntimeError if called before initialise() - which means
        something is importing app config before settings.py has run.
        """
        if cls._instance is None:
            raise RuntimeError(
                "AppConfig has not been initialised. "
                "AppConfig.initialise() must be called in settings.py "
                "before anything else imports it."
            )
        return cls._instance
