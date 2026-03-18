# Bulk Email Sending Component — Design Spec

**Date:** 2026-03-18
**Branch:** email-sending-component-b6b

---

## Problem

There is no way to send bulk emails to a filtered subset of schools from the admin. Currently each school communication is handled individually or outside the system entirely. Admins need a tool to compose, preview, and send templated emails to koordinatorer or økonomiansvarlige across a filtered set of schools, with safeguards against accidental sends and full visibility into who received what.

---

## Goals

1. Allow admins to compose and send HTML emails to a filtered subset of schools.
2. Support template variables from School and Person data with missing-field warnings.
3. Provide dry-run, preview, and test-email capabilities before sending.
4. Save sent campaigns with a full recipient log for historical reference.
5. Handle up to ~500 recipients without request timeouts.

---

## Architecture

A new Django app `apps/bulk_email/` with its own URL namespace mounted at `/masseudsendelse/`. A new top-level nav entry "Masseudsendelse" is added to the admin navigation. All views require staff login (same `@login_required` + `is_staff` guard used elsewhere).

The sending mechanism uses Django's `StreamingHttpResponse` with Server-Sent Events (SSE) to stream per-recipient progress back to the browser in real time. This avoids gunicorn timeouts for large recipient sets without requiring a task queue. Since the send endpoint accepts POST, the browser cannot use the native `EventSource` API (GET-only). The frontend uses `fetch()` with `ReadableStream` instead, which supports POST and streams chunks as they arrive. Gunicorn must use gthread workers for `StreamingHttpResponse` to flush chunks incrementally rather than buffering the full response — the Dockerfile CMD gains `--worker-class gthread --threads 4`.

The school filter reuses the `school_filter.html` component being developed in the `better-school-filter-7ac` branch. This branch must be merged before or alongside this feature. The filter component reads from `request.GET` and requires the parent view to supply these context variables: `kommuner`, `school_years`, `filter_summary`, `has_active_filters`, `selected_year`. `BulkEmailCreateView` must produce all of them — this logic is extracted into a `SchoolFilterMixin` shared with `SchoolListView`.

---

## Data Models

### `BulkEmail`

One record per send campaign.

| Field | Type | Notes |
|---|---|---|
| `subject` | CharField | Supports `{{ variable }}` syntax |
| `body_html` | TextField | HTML, Summernote-edited, supports `{{ variable }}` syntax |
| `recipient_type` | CharField (choices) | `koordinator` or `oekonomisk_ansvarlig` |
| `filter_params` | JSONField | Snapshot of GET params at send time: `search`, `year`, `status_filter`, `kommune`, `unused_seats` — these are the exact param names emitted by `school_filter.html` (confirmed against `better-school-filter-7ac` spec) |
| `sent_at` | DateTimeField (null) | Null until actually sent |
| `sent_by` | ForeignKey(User, null) | Set at send time |
| `created_at` | DateTimeField (auto) | |
| `updated_at` | DateTimeField (auto) | |

### `BulkEmailAttachment`

One record per attached file. FK to `BulkEmail`.

| Field | Type | Notes |
|---|---|---|
| `bulk_email` | ForeignKey(BulkEmail) | `related_name='attachments'` |
| `file` | FileField | Uploaded to `bulk_email_attachments/` — served only to authenticated staff; not publicly accessible via `MEDIA_URL` |
| `filename` | CharField | Display name for the attachment |

### `BulkEmailRecipient`

One record per resolved recipient. FK to `BulkEmail`. Written during the SSE send stream.

| Field | Type | Notes |
|---|---|---|
| `bulk_email` | ForeignKey(BulkEmail) | `related_name='recipients'` |
| `person` | ForeignKey(Person) | The contact person |
| `school` | ForeignKey(School) | The school |
| `email` | CharField | Snapshot of email address at send time |
| `success` | BooleanField | |
| `error_message` | CharField (blank) | Populated on failure |

The recipient snapshot decouples the historical record from future Person/School edits.

---

## URL Structure

| URL | View | Method | Purpose |
|---|---|---|---|
| `/masseudsendelse/` | `BulkEmailListView` | GET | Campaign history list |
| `/masseudsendelse/ny/` | `BulkEmailCreateView` | GET | Composer — render form |
| `/masseudsendelse/<pk>/` | `BulkEmailDetailView` | GET | Campaign detail + recipient table |
| `/masseudsendelse/preview/` | `BulkEmailPreviewView` | POST (AJAX) | Returns rendered email HTML for a given school + current body/subject |
| `/masseudsendelse/dry-run/` | `BulkEmailDryRunView` | POST (AJAX) | Returns recipient list + missing-field warnings for current filter state |
| `/masseudsendelse/send/` | `BulkEmailSendView` | POST (SSE) | Creates BulkEmail, streams send progress, sets sent_at on completion |
| `/masseudsendelse/attachments/<pk>/` | `BulkEmailAttachmentView` | GET | Protected attachment download — staff-only |

**Copy to new:** The list and detail views include a "Kopier til ny" button. Clicking it redirects to `/masseudsendelse/ny/` with all filter params and composer fields expanded as individual GET params — e.g. `/masseudsendelse/ny/?copy_from=12&search=aarhus&year=2024/25&status_filter=tilmeldt_ny&recipient_type=koordinator`. The `copy_from` param is used only for page title context ("Kopieret fra udsendelse #12"); the actual pre-population comes from the expanded individual params. This means the school filter component's standard GET-param-driven UI renders with the copied state without any special handling in the template.

**`BulkEmail` lifecycle:**
1. No `BulkEmail` row exists while the user fills in the composer.
2. When the user confirms "Send til alle", the browser POSTs to `/masseudsendelse/send/`.
3. The send view creates the `BulkEmail` row (with `sent_at=null`) and begins streaming.
4. `BulkEmailRecipient` rows are written one by one as sends complete.
5. When all recipients are processed, `sent_at` is set and the stream emits the `done` event.
6. If the stream is interrupted (server crash, browser close) the `BulkEmail` row remains with `sent_at=null` and partial recipients. These appear in the list view as "Afbrudt" and are shown at the top of the history list. The double-send guard prevents re-sending an interrupted campaign.

**Attachment upload:** Files are uploaded separately via a small `POST /masseudsendelse/preview/` does not preview attachments — it only renders the HTML body for a given school. Attachments are uploaded via a dedicated AJAX upload call to `POST /masseudsendelse/ny/upload/` which returns an attachment PK; the form collects these PKs and sends them to the main send endpoint. Uploaded-but-unsent attachment files (orphaned if user navigates away without sending) are cleaned up by a periodic management command.

**Attachment access:** `BulkEmailAttachment.file` URLs are never exposed directly. The detail view links to `/masseudsendelse/attachments/<pk>/`, which checks `request.user.is_staff` and streams the file.

**Double-send guard:** Once `sent_at` is set on a `BulkEmail`, the record is read-only. The send endpoint rejects POSTs to already-sent campaigns.

---

## Composer Page Layout

`/masseudsendelse/ny/` — a single page with five Bootstrap card sections.

### 1. Modtagere

- The reusable `{% include 'schools/components/school_filter.html' %}` component — same filter bar as the school list page, submitting GET params to this view
- Recipient type radio buttons: **Koordinator** / **Økonomiansvarlig**
- Live counter updated via dry-run AJAX on filter/type change: _"47 skoler matcher — 44 har en koordinator"_
- Warning badge when one or more matched schools lack a contact of the selected type

### 2. Emne & indhold

- Subject `<input>` — plain text, supports `{{ variable }}` syntax
- Summernote HTML editor for body — supports `{{ variable }}` syntax and inline images
- Collapsible "Tilgængelige variabler" reference card (see Template Variables section)
- Warning panel: lists any `{{ variable }}` that resolves to blank/None on one or more recipient schools, e.g. _"{{ ean_nummer }} mangler på 3 skoler: Skole A, Skole B, Skole C"_. Warning only — does not block sending.

### 3. Vedhæftninger

- Multi-file `<input type="file" multiple>` — each file is uploaded immediately via AJAX to `POST /masseudsendelse/ny/upload/` on selection; returns an attachment PK
- List of uploaded attachments with individual remove buttons (AJAX delete)
- The form tracks attachment PKs as hidden inputs; these are submitted with "Send til alle"

### 4. Forhåndsvisning

- School picker `<select>` — populated from the current matched school set
- `<iframe>` showing the rendered email for the selected school
- Refreshes automatically when the selected school changes or when subject/body changes (debounced 800ms), via POST AJAX to the preview endpoint with `school_pk`, `subject`, and `body_html` in the request body
- Attachments are not shown in the preview (HTML body only)

### 5. Afsendelse

- **"Tør-kørsel" button** — expands inline panel with a table: recipient name, school, email address, one row per resolved contact. Populated via dry-run AJAX.
- **"Send test-email"** — email address input + school context picker + "Send" button. Renders the email as if for the selected school and sends to the provided address via the existing `resend.Emails.send()`.
- **"Send til alle" button** — opens a Bootstrap confirmation modal showing:
  > _"Du er ved at sende til 47 modtagere — Ny tilmeldt i 2024/25 · Kommune: Aarhus. Er du sikker?"_
  Confirming triggers the SSE send stream. The button area is replaced by a progress bar and live log. On completion: _"Afsluttet — 45 sendt, 2 fejlede"_ with a link to the detail view.

---

## Template Variables

Body and subject are rendered using Django's template engine: `Template(body_html).render(Context({...}))`. This is the same pattern as the existing `send_email()` service in `apps/emails/services.py`.

Available variables:

| Variable | Source |
|---|---|
| `{{ skole_navn }}` | `school.name` |
| `{{ adresse }}` | `school.adresse` |
| `{{ postnummer }}` | `school.postnummer` |
| `{{ by }}` | `school.by` |
| `{{ kommune }}` | `school.kommune` |
| `{{ ean_nummer }}` | `school.ean_nummer` |
| `{{ fakturering_ean_nummer }}` | `school.fakturering_ean_nummer` |
| `{{ fakturering_kontakt_navn }}` | `school.fakturering_kontakt_navn` |
| `{{ fakturering_kontakt_email }}` | `school.fakturering_kontakt_email` |
| `{{ tilmeldt_dato }}` | `school.enrolled_at` |
| `{{ aktiv_fra }}` | `school.active_from` |
| `{{ kontakt_navn }}` | `person.name` |
| `{{ kontakt_email }}` | `person.email` |
| `{{ kontakt_telefon }}` | `person.phone` |
| `{{ tilmeldings_link }}` | Full URL built from `school.signup_token` |
| `{{ skoleside_link }}` | Full URL to the school's personal page |
| `{{ tilmeldings_adgangskode }}` | `school.signup_password` |

The remaining `fakturering_*` fields (`fakturering_adresse`, `fakturering_postnummer`, `fakturering_by`) are intentionally omitted — billing address fields are not expected to appear in outbound school communications.

Missing-field warnings are computed before send and on dry-run by iterating all resolved recipients and checking each referenced variable.

**Security note:** Template rendering uses `Template(body_html).render(Context({...}))` with a sandboxed `Context` (not `RequestContext`). This prevents arbitrary Python execution but still allows Django template tags (`{% ... %}`). This is accepted for an admin-only tool with staff access. The template engine is not further restricted.

---

## SSE Send Stream

The send endpoint (`POST /masseudsendelse/send/`) returns a `StreamingHttpResponse` with `Content-Type: text/event-stream`.

Protocol:
- `data: {"type": "start", "total": 47}`
- `data: {"type": "progress", "n": 1, "total": 47, "school": "Skole A", "email": "foo@bar.dk", "success": true}`
- `data: {"type": "progress", "n": 2, ..., "success": false, "error": "..."}`
- `data: {"type": "done", "sent": 45, "failed": 2, "detail_url": "/masseudsendelse/12/"}`

Each `BulkEmailRecipient` is written to the database immediately after its send attempt. Failures do not abort the stream — sending continues for remaining recipients.

The frontend uses `fetch()` with `ReadableStream` (not `EventSource`, which is GET-only) to POST to the send endpoint and consume the stream incrementally. Each `data: {...}\n\n` chunk is parsed as JSON and used to update the progress bar and live log.

---

## Campaign History & Detail

**List view (`/masseudsendelse/`):**
- Table: sent_at, subject (truncated), recipient_type, filter summary, sent_by, recipient count, failure count
- "Kopier til ny" button per row
- Interrupted sends (sent_at=null, has recipients) shown at top with "Afbrudt" status badge

**Detail view (`/masseudsendelse/<pk>/):**
- Header: subject, sent_at, sent_by, recipient_type, filter summary (from stored filter_params)
- Stats: total sent, failures
- Recipient table: school name, contact name, email, ✓/✗, error message if failed (failures highlighted)
- "Kopier til ny" button

---

## Error Handling

- **Individual send failures:** logged to `BulkEmailRecipient.error_message`, stream continues
- **Missing contact type:** schools without the selected contact type are silently skipped during send (counted separately in the final summary: _"3 skoler sprunget over — ingen koordinator"_)
- **Missing template variables:** warning shown pre-send, not a blocker
- **Dev mode guard:** existing `if not settings.RESEND_API_KEY:` pattern applies — logs to console instead of sending. `BulkEmailRecipient` is written with `success=True` and `error_message="[DEV MODE - not actually sent]"` (consistent with `EmailLog` pattern in `services.py`).
- **Domain allowlist:** existing `EMAIL_ALLOWED_DOMAINS` check in `services.py` applies to each recipient

---

## Audit

`BulkEmail` is registered in `apps/audit/apps.py` inside the `AuditConfig.ready()` method, following the existing pattern:

```python
class AuditConfig(AppConfig):
    def ready(self):
        # ... existing registrations ...
        from apps.bulk_email.models import BulkEmail
        register_for_audit(BulkEmail, AuditCfg(
            excluded_fields=['id', 'created_at', 'updated_at', 'body_html'],
        ))
```

`body_html` is excluded from audit tracking (too large, not useful as a diff). Note: since `BulkEmail` is not linked to a single school, no `get_school` lambda is needed.

`BulkEmailAttachment` and `BulkEmailRecipient` are intentionally not registered in audit — attachment adds/removes are visible in the campaign detail view, and recipient rows are append-only write-once records. Auditing them would produce noise without value.

---

## Files to Create / Modify

| File | Change |
|---|---|
| `apps/bulk_email/__init__.py` | New app |
| `apps/bulk_email/models.py` | `BulkEmail`, `BulkEmailAttachment`, `BulkEmailRecipient` |
| `apps/bulk_email/views.py` | All views: list, create, detail, preview, dry-run, SSE send, attachment upload + protected download |
| `apps/bulk_email/urls.py` | URL patterns |
| `apps/bulk_email/forms.py` | `BulkEmailForm` with Summernote widget |
| `apps/bulk_email/apps.py` | AppConfig |
| `apps/schools/views.py` | Extract `SchoolFilterMixin` from `SchoolListView` for reuse |
| `apps/bulk_email/templates/bulk_email/bulk_email_list.html` | Campaign history |
| `apps/bulk_email/templates/bulk_email/bulk_email_create.html` | Composer page |
| `apps/bulk_email/templates/bulk_email/bulk_email_detail.html` | Campaign detail |
| `apps/bulk_email/templates/bulk_email/bulk_email_preview.html` | Rendered email HTML (for iframe) |
| `apps/audit/apps.py` | Register `BulkEmail` |
| `config/settings/base.py` | Add `bulk_email` to `INSTALLED_APPS` |
| `config/urls.py` | Mount `/masseudsendelse/` |
| `templates/core/base.html` | Add "Masseudsendelse" nav link |
| `Dockerfile` | Add `--worker-class gthread --threads 4` to gunicorn CMD |

---

## Dependencies

- `better-school-filter-7ac` branch must be merged first (provides `school_filter.html` component, updated `SchoolListView` filter logic, and the `SchoolFilterMixin` to be extracted)
- No new Python packages required (SSE via `StreamingHttpResponse`, Summernote already installed)
- Dockerfile CMD updated to add `--worker-class gthread --threads 4` for gunicorn streaming support

---

## Out of Scope

- Attachment file library / reuse across campaigns
- Scheduled / delayed sending
- Celery or any task queue
- Multi-select recipient types (one type per send)
- Unsubscribe / opt-out management
- Email open/click tracking
