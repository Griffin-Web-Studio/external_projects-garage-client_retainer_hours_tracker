from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest


class SuperuserOnlyModelBackend(ModelBackend):
    """Superuser Authentication backend, allows ONLY superuser to login using
    basic auth. Rest of the users, must use OIDC.

    Args:
        ModelBackend (ModelBackend): Extends the base model backend
    """

    def authenticate(
        self: SuperuserOnlyModelBackend, request: HttpRequest, **kwargs
    ):

        user = super().authenticate(request, **kwargs)

        if user and not user.is_superuser:
            return None

        return user
