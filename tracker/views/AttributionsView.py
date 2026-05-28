from django.views import View
from django.shortcuts import render


class AttributionsView(View):
    def get(self, request):
        return render(request, "attributions.html")
