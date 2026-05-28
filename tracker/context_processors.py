from django.http import HttpRequest

from core.app_settings import AppConfig


def app_settings(request: HttpRequest) -> dict[str, str | bool]:
    """Injects global application settings into every template context so views
    don't have to pass them manually.

    Available in all templates:
        {{ APP_NAME }}     - configurable via settings.ini [branding] app_name
        {{ OIDC_ENABLED }} - True when OIDC is configured in .env

    Args:
        request (HttpRequest): HTTP request object

    Returns:
        dict[str, str | bool]: context
    """

    settings = AppConfig.get()

    return {
        "APP_NAME": getattr(settings, "app_name", "UnnamedApp"),
        "OIDC_LABEL": getattr(settings, "oidc_label", "OIDC"),
        "OIDC_ENABLED": getattr(settings, "oidc_enabled", False),
    }
