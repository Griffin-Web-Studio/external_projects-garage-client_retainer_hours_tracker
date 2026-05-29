from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "dashboard/dashboard.html")
