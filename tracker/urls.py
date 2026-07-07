from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = [
    path("login/", views.LoginPageView.as_view(), name="login"),
    path(
        "attributions/", views.AttributionsView.as_view(), name="attributions"
    ),
    path(
        "dashboard/",
        login_required(views.DashboardView.as_view()),
        name="dashboard",
    ),
    path(
        "clients/new/",
        login_required(views.NewClientView.as_view()),
        name="client-new",
    ),
    path(
        "clients/<int:pk>/edit/",
        login_required(views.EditClientView.as_view()),
        name="client-edit",
    ),
    path(
        "clients/<int:pk>/delete/",
        login_required(views.DeleteClientView.as_view()),
        name="client-delete",
    ),
    path(
        "clients/<int:pk>/log/",
        login_required(views.LogTimeView.as_view()),
        name="log-time",
    ),
    path(
        "clients/<int:pk>/",
        login_required(views.ClientDetailView.as_view()),
        name="client-detail",
    ),
    path(
        "time-entries/<int:pk>/delete/",
        login_required(views.DeleteTimeEntryView.as_view()),
        name="delete-time-entry",
    ),
    path(
        "clients/<int:pk>/new-term/",
        login_required(views.NewTermView.as_view()),
        name="new-term",
    ),
    path(
        "clients/<int:pk>/bill-overage/",
        login_required(views.BillOverageView.as_view()),
        name="bill-overage",
    ),
]
