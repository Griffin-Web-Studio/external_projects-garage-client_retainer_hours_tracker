"""Pluggable PDF rendering backends for generated overage reports.

WeasyPrint ships as the default backend. Call sites go through
`get_pdf_renderer()` rather than instantiating a backend directly, so a
different renderer (e.g. an HTTP call to a Gotenberg service) can be
swapped in later without touching anything that renders a report.
"""

from typing import Protocol

from django.http import HttpResponse
from weasyprint import HTML


class PDFRenderer(Protocol):
    """Interface every PDF rendering backend must implement."""

    def render(self, html: str) -> bytes:
        """Renders an HTML string to PDF bytes.

        Args:
            html (str): Report HTML to render.

        Returns:
            bytes: The generated PDF's raw bytes.
        """

        ...


class WeasyPrintRenderer:
    """Default PDF renderer, backed by WeasyPrint."""

    def render(self, html: str) -> bytes:
        """Renders an HTML string to PDF bytes via WeasyPrint.

        Args:
            html (str): Report HTML to render.

        Returns:
            bytes: The generated PDF's raw bytes.
        """

        return HTML(string=html).write_pdf()


def get_pdf_renderer() -> PDFRenderer:
    """Resolves the PDF renderer backend to use.

    Returns:
        PDFRenderer: The configured renderer - `WeasyPrintRenderer` by
            default.
    """

    return WeasyPrintRenderer()


def pdf_http_response(
    pdf_bytes: bytes, filename: str, disposition: str = "attachment"
) -> HttpResponse:
    """Builds an HTTP response streaming raw PDF bytes to the browser.

    Args:
        pdf_bytes (bytes): The PDF's raw bytes.
        filename (str): Filename suggested to the browser.
        disposition (str, optional): "attachment" (forces a download)
            or "inline" (opens in-browser). Defaults to "attachment".

    Returns:
        HttpResponse: `pdf_bytes` with the right Content-Type/
            Content-Disposition headers set.
    """

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response
