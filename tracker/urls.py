from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.LoginPageView.as_view(), name="login"),
    path(
        "attributions/", views.AttributionsView.as_view(), name="attributions"
    ),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
