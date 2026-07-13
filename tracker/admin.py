from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Client,
    ClientTerm,
    CompanyProfile,
    Employee,
    HoursPurchase,
    OverageBilling,
    Retainer,
    TimeEntry,
)


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = ("email", "name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("name",)}),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2"),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and not obj.has_usable_password():
            return self.readonly_fields + ("password",)
        return self.readonly_fields


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Retainer)
class RetainerAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "client__name")


@admin.register(ClientTerm)
class ClientTermAdmin(admin.ModelAdmin):
    list_display = (
        "retainer",
        "term_number",
        "start_date",
        "end_date",
        "monthly_hours",
        "monthly_minutes",
        "carry_over_type",
    )
    list_filter = ("carry_over_type",)


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "retainer",
        "date",
        "hours",
        "minutes",
        "type",
        "employee",
        "description",
    )
    list_filter = ("type",)
    search_fields = ("client__name", "retainer__name", "description")


@admin.register(OverageBilling)
class OverageBillingAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "term",
        "type",
        "hours_charged",
        "minutes_charged",
        "invoice_ref",
        "billed_at",
    )


@admin.register(HoursPurchase)
class HoursPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "term",
        "hours",
        "minutes",
        "invoice_ref",
        "resolution",
        "from_historical_billing",
        "purchased_at",
    )
    list_filter = ("resolution", "from_historical_billing")


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("name", "logo_url")}),
        (
            "Address",
            {
                "fields": (
                    "address_line1",
                    "address_line2",
                    "postal_code",
                    "city",
                    "country",
                )
            },
        ),
        ("Contact", {"fields": ("email", "phone")}),
        (
            "Registration & Banking",
            {"fields": ("vat_number", "registration_number", "iban", "bic")},
        ),
    )

    def has_add_permission(self, request):
        return not CompanyProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
