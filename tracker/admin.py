from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Client, Employee


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
