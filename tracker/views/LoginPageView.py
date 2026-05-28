from django.views import View
from django.shortcuts import redirect, render


class LoginPageView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")

        # OIDC_ENABLED is injected by the context processor;
        # no need to pass it here
        return render(request, "login.html")
