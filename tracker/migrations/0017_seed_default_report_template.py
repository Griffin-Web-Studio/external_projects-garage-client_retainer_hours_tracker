from django.db import migrations

DEFAULT_TEMPLATE_CONTENT = """<html>
<head>
<style>
  @page { size: A4; margin: 2cm; }
  body { font-family: sans-serif; color: #1a1a1a; font-size: 11pt; }
  .header { display: flex; justify-content: space-between; margin-bottom: 24px; }
  .company, .client { width: 48%; }
  h1 { font-size: 18pt; margin: 0 0 4px 0; }
  h2 { font-size: 13pt; margin-top: 24px; margin-bottom: 8px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #eee; font-size: 10pt; }
  th { color: #555; text-transform: uppercase; font-size: 9pt; }
  .stats { display: flex; gap: 24px; margin-top: 12px; }
  .stat .label { font-size: 9pt; color: #666; }
  .stat .value { font-size: 14pt; font-weight: bold; }
  .muted { color: #666; font-size: 9.5pt; }
  .bill-to-label { font-size: 9pt; color: #666; }
  .footer { margin-top: 32px; font-size: 9pt; color: #888; }
</style>
</head>
<body>
  <div class="header">
    <div class="company">
      {% if company.logo_url %}<img src="{{ company.logo_url }}" style="max-height: 48px;"><br>{% endif %}
      <h1>{{ company.name }}</h1>
      {% if company.address_line1 %}<div class="muted">{{ company.address_line1 }}</div>{% endif %}
      {% if company.address_line2 %}<div class="muted">{{ company.address_line2 }}</div>{% endif %}
      {% if company.postal_code or company.city or company.country %}
        <div class="muted">{{ company.postal_code }} {{ company.city }} {{ company.country }}</div>
      {% endif %}
      {% if company.email %}<div class="muted">{{ company.email }}</div>{% endif %}
      {% if company.vat_number %}<div class="muted">VAT: {{ company.vat_number }}</div>{% endif %}
    </div>
    <div class="client">
      <div class="bill-to-label">BILL TO</div>
      <h1>{{ client.name }}</h1>
      {% if client.address_line1 %}<div class="muted">{{ client.address_line1 }}</div>{% endif %}
      {% if client.address_line2 %}<div class="muted">{{ client.address_line2 }}</div>{% endif %}
      {% if client.postal_code or client.city or client.country %}
        <div class="muted">{{ client.postal_code }} {{ client.city }} {{ client.country }}</div>
      {% endif %}
    </div>
  </div>

  <h2>Overage Report &mdash; {{ retainer.name }}, Term {{ term.term_number }}</h2>
  <div class="muted">
    {{ term.start_date }} to {{ term.end_date }} &mdash;
    Generated {{ generated_at.strftime("%Y-%m-%d %H:%M") }}
  </div>

  <div class="stats">
    <div class="stat">
      <div class="label">Support used</div>
      <div class="value">
        {{ summary.total_support_used|fmt_hm }} /
        {{ summary.total_support_allocated|fmt_hm }}
      </div>
    </div>
    <div class="stat">
      <div class="label">Support overage</div>
      <div class="value">{{ summary.support_overage|fmt_hm }}</div>
    </div>
    {% if summary.purchased_support %}
      <div class="stat">
        <div class="label">Purchased buffer</div>
        <div class="value">
          {{ summary.purchased_support_remaining|fmt_hm }} /
          {{ summary.purchased_support|fmt_hm }}
        </div>
      </div>
    {% endif %}
    {% if summary.total_dev_available %}
      <div class="stat">
        <div class="label">Dev used</div>
        <div class="value">
          {{ summary.total_dev_used|fmt_hm }} /
          {{ summary.total_dev_available|fmt_hm }}
        </div>
      </div>
    {% endif %}
  </div>

  <h2>Time Entries</h2>
  <table>
    <tr><th>Date</th><th>Type</th><th>Hours</th><th>Employee</th><th>Description</th></tr>
    {% for e in entries %}
      <tr>
        <td>{{ e.date }}</td>
        <td>{{ e.type }}</td>
        <td>{{ e.hours|hm(e.minutes) }}</td>
        <td>{{ e.employee.name }}</td>
        <td>{{ e.description }}</td>
      </tr>
    {% else %}
      <tr><td colspan="5" class="muted">No time entries this term.</td></tr>
    {% endfor %}
  </table>

  {% if purchases %}
    <h2>Purchased Buffer Hours</h2>
    <table>
      <tr><th>Date</th><th>Hours</th><th>Invoice Ref</th><th>Status</th></tr>
      {% for p in purchases %}
        <tr>
          <td>{{ p.purchased_at.date() }}</td>
          <td>{{ p.hours|hm(p.minutes) }}</td>
          <td>{{ p.invoice_ref or "-" }}</td>
          <td>{{ p.resolution or "Active" }}</td>
        </tr>
      {% endfor %}
    </table>
  {% endif %}

  {% if billings %}
    <h2>Overage Billings</h2>
    <table>
      <tr><th>Date</th><th>Type</th><th>Hours</th><th>Invoice Ref</th></tr>
      {% for b in billings %}
        <tr>
          <td>{{ b.billed_at.date() }}</td>
          <td>{{ b.type }}</td>
          <td>{{ b.hours_charged|hm(b.minutes_charged) }}</td>
          <td>{{ b.invoice_ref or "-" }}</td>
        </tr>
      {% endfor %}
    </table>
  {% endif %}

  <div class="footer">
    {{ company.name }} &mdash; generated {{ generated_at.strftime("%Y-%m-%d %H:%M") }}
  </div>
</body>
</html>
"""


def seed_default_report_template(apps, schema_editor):
    """Creates a default ReportTemplate if none exists yet.

    Without this, generating a report requires hand-writing a Jinja2
    template from scratch in the admin before the feature works at
    all. This gives every install a usable, reasonably complete
    default (company/client details, hours summary, entries,
    purchases, billings) out of the box - a no-op if a template
    already exists, so it won't clobber anything a user has already
    set up.

    Args:
        apps: Historical app registry.
        schema_editor: Unused, required by the RunPython signature.
    """

    ReportTemplate = apps.get_model("tracker", "ReportTemplate")

    if ReportTemplate.objects.exists():
        return

    ReportTemplate.objects.create(
        name="Default Overage Report",
        content=DEFAULT_TEMPLATE_CONTENT,
        is_default=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0016_overagereport"),
    ]

    operations = [
        migrations.RunPython(
            seed_default_report_template, migrations.RunPython.noop
        ),
    ]
