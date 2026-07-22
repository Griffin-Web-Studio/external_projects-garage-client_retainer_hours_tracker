"""
Custom OIDC authentication backend for RetainerTracker.

Extends mozilla-django-oidc to:
  1. Use email as the lookup key (not username).
  2. Auto-provision Employee accounts on first OIDC login,
     subject to an optional domain allow-list.
  3. Keep the employee's display name in sync with the OIDC claims.
"""

import logging

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from core.app_settings import AppConfig

logger = logging.getLogger(__name__)


class RetainerOIDCBackend(OIDCAuthenticationBackend):
    """OIDC authentication backend for auto-provisioned Employee accounts.

    Attributes:
        UserModel: Django auth user model, resolved by the base class to
            `tracker.Employee` via `AUTH_USER_MODEL`.
    """

    # ── User lookup ───────────────────────────────────────────────────────────

    def filter_users_by_claims(self, claims):
        """Looks up an existing Employee by the OIDC `email` claim.

        Args:
            claims (dict): Claims returned by the OIDC userinfo endpoint.

        Returns:
            QuerySet: Employees matching the claimed email (case-insensitive),
                or an empty queryset if the claim has no usable email.
        """

        email = claims.get("email", "").strip().lower()

        if not email:
            return self.UserModel.objects.none()

        return self.UserModel.objects.filter(email__iexact=email)

    # ── Domain allow-list check ───────────────────────────────────────────────

    def _domain_allowed(self, email: str) -> bool:
        """Checks whether an email's domain is permitted to auto-register.

        Args:
            email (str): Email address to check.

        Returns:
            bool: True if the domain is allowed (or no allow-list is
                configured), False otherwise.
        """

        # oidc_allowed_domains is read from settings.ini [auth]
        # OIDC_ALLOWED_DOMAINS.
        allowed = AppConfig.get().oidc_allowed_domains

        if not allowed:
            return True  # blank = unrestricted

        domain = email.split("@")[-1].lower()

        return domain in [d.lower() for d in allowed]

    # ── Create ────────────────────────────────────────────────────────────────

    def create_user(self, claims):
        """Auto-provisions an Employee on first successful OIDC login.

        The very first Employee ever created in the system - regardless
        of how any earlier ones were made (seeded, `createsuperuser`,
        etc.) - is auto-promoted to admin, so a fresh deployment always
        ends up with at least one admin without a manual DB edit.

        Args:
            claims (dict): Claims returned by the OIDC userinfo endpoint.

        Returns:
            Employee | None: The newly created Employee, or None if the
                claims have no usable email or the domain is not allowed.
        """

        email = claims.get("email", "").strip().lower()

        if not email:
            logger.warning("OIDC: no email in claims, rejecting.")

            return None

        if not self._domain_allowed(email):
            logger.warning(
                "OIDC: domain not in OIDC_ALLOWED_DOMAINS for %s", email
            )

            return None

        is_first_employee = not self.UserModel.objects.exists()

        name = (
            claims.get("name")
            or claims.get("preferred_username")
            or email.split("@")[0]
        )
        user = self.UserModel.objects.create_user(email=email, name=name)
        logger.info("OIDC: auto-provisioned employee %s", email)

        if is_first_employee:
            user.role = self.UserModel.ROLE_ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["role", "is_staff", "is_superuser"])
            logger.info(
                "OIDC: %s is the first employee in the system - "
                "auto-promoted to admin",
                email,
            )

        return user

    # ── Update ────────────────────────────────────────────────────────────────

    def update_user(self, user, claims):
        """Syncs an existing Employee's display name with fresh OIDC claims.

        Args:
            user (Employee): Employee instance being logged in.
            claims (dict): Claims returned by the OIDC userinfo endpoint.

        Returns:
            Employee: `user`, with `name` updated and saved if it changed.
        """

        name = claims.get("name") or claims.get("preferred_username") or ""

        if name and user.name != name:
            user.name = name
            user.save(update_fields=["name"])

        return user
