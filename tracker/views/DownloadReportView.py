from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views import View

from tracker.models import OverageReport
from tracker.pdf import pdf_http_response


class DownloadReportView(LoginRequiredMixin, View):
    """View for downloading a previously generated, persisted overage
    report PDF.
    """

    def get(self, request, pk, retainer_pk, report_pk):
        """Streams a persisted `OverageReport`'s PDF as a download.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer.
            report_pk (int): Primary key of the report to download.

        Returns:
            HttpResponse: The report's stored PDF bytes as a download.
        """

        report = get_object_or_404(
            OverageReport,
            pk=report_pk,
            term__retainer_id=retainer_pk,
            term__retainer__client_id=pk,
        )
        client = report.term.retainer.client
        filename = (
            f"overage-report-{slugify(client.name)}-"
            f"term-{report.term.term_number}.pdf"
        )

        return pdf_http_response(bytes(report.pdf), filename)
