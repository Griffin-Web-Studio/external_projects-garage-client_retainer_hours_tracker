from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify
from django.views import View

from tracker.models import Client, OverageReport, ReportTemplate, Retainer
from tracker.pdf import get_pdf_renderer, pdf_http_response
from tracker.reports import build_term_report_context, render_report_template


class ReportView(LoginRequiredMixin, View):
    """View for rendering a term's overage report to PDF.

    GET streams an ad-hoc preview - nothing is persisted. POST renders
    the same PDF but also saves it as a formal `OverageReport`, so it
    stays in the term's report history.
    """

    def get(self, request, pk, retainer_pk, term_number=None):
        """Streams an ad-hoc PDF preview, without saving anything.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer.
            term_number (int | None, optional): Specific term to
                report on. Defaults to None, in which case the
                retainer's current term is used.

        Returns:
            HttpResponse: The rendered PDF, opened inline, or a
                redirect back to the retainer detail page if there's
                no term or no default report template configured.
        """

        client, term = self._resolve(pk, retainer_pk, term_number)

        if not term:
            return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

        template = ReportTemplate.objects.filter(is_default=True).first()

        if template is None:
            return self._no_template(request, pk, retainer_pk, term_number)

        pdf_bytes = self._render_pdf(template, term)

        return pdf_http_response(
            pdf_bytes, self._filename(client, term), disposition="inline"
        )

    def post(self, request, pk, retainer_pk, term_number=None):
        """Renders the report, persists it as an `OverageReport`, and
        streams it back as a download.

        Args:
            request (HttpRequest): Incoming POST request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer.
            term_number (int | None, optional): Specific term to
                report on. Defaults to None, in which case the
                retainer's current term is used.

        Returns:
            HttpResponse: The rendered PDF as a download, or a
                redirect back to the retainer detail page if there's
                no term or no default report template configured.
        """

        client, term = self._resolve(pk, retainer_pk, term_number)

        if not term:
            return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

        template = ReportTemplate.objects.filter(is_default=True).first()

        if template is None:
            return self._no_template(request, pk, retainer_pk, term_number)

        pdf_bytes = self._render_pdf(template, term)

        OverageReport.objects.create(
            term=term,
            template=template,
            pdf=pdf_bytes,
            generated_by=request.user,
        )

        return pdf_http_response(pdf_bytes, self._filename(client, term))

    def _resolve(self, pk, retainer_pk, term_number):
        """Resolves the client and term a report is being built for.

        Args:
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer.
            term_number (int | None): Specific term number, or None
                for the retainer's current term.

        Returns:
            tuple[Client, ClientTerm | None]: The client and the
                resolved term (None if the retainer has no term yet).
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)

        if term_number is not None:
            term = get_object_or_404(retainer.terms, term_number=term_number)
        else:
            term = retainer.current_term

        return client, term

    def _render_pdf(self, template, term):
        """Renders a term's report template to PDF bytes.

        Args:
            template (ReportTemplate): Template to render.
            term (ClientTerm): Term to build the report context from.

        Returns:
            bytes: The rendered PDF's raw bytes.
        """

        html = render_report_template(template, build_term_report_context(term))
        return get_pdf_renderer().render(html)

    def _filename(self, client, term):
        """Builds the suggested download filename for a term's report.

        Args:
            client (Client): The report's client.
            term (ClientTerm): The report's term.

        Returns:
            str: A filesystem-safe filename, e.g.
                "overage-report-acme-ltd-term-2.pdf".
        """

        return (
            f"overage-report-{slugify(client.name)}-term-{term.term_number}.pdf"
        )

    def _no_template(self, request, pk, retainer_pk, term_number):
        """Flashes an error and redirects back when no default report
        template is configured.

        Args:
            request (HttpRequest): The incoming request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer.
            term_number (int | None): Specific term number, or None
                for the retainer's current term.

        Returns:
            HttpResponse: Redirect back to the retainer detail page.
        """

        messages.error(
            request,
            "No default report template is configured. Set one as "
            "default in the admin before generating a report.",
        )

        if term_number is not None:
            return redirect(
                "retainer-detail-term",
                pk=pk,
                retainer_pk=retainer_pk,
                term_number=term_number,
            )

        return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)
