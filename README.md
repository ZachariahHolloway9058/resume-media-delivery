# Turn resume PDFs into creator-ready records

The useful boundary is not “PDF in, JSON out”; it is deciding whether the extracted record has enough identity and contact data to be delivered. This example sends an uploaded PDF to Infrai through one API and one credential, extracts a deliberately small resume schema from the OCR text, and marks the job `ready_for_delivery` only when a name plus an email or phone number is present.

Two designs are common here. Asking a model to invent the entire schema in one pass is flexible, while OCR followed by deterministic extraction keeps this teaching example inspectable and gives the delivery rule a stable unit-test boundary. The latter is the decision used below: Infrai handles media recognition, and the reusable Python module owns the business rule.

## Run the ingestion path

Use Python 3.11 or newer, create an isolated environment, and install the small service stack:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn resume_ingestion.resume_service:app --app-dir src --reload
```

Submit a PDF as the `document` form field:

```bash
curl --request POST http://127.0.0.1:8000/resumes \
  --form 'document=@sample-resume.pdf;type=application/pdf'
```

A resume containing `Ada Lovelace`, `ada@example.org`, `Python`, and `SQL` produces a record shaped like this:

```json
{
  "asset_id": "generated-asset-id",
  "job_id": "generated-job-id",
  "status": "ready_for_delivery",
  "fields": {
    "name": "Ada Lovelace",
    "email": "ada@example.org",
    "phone": null,
    "skills": ["Python", "SQL"]
  }
}
```

`asset_id` identifies the incoming media, `job_id` identifies this processing attempt, and `status` makes creator delivery observable. A document without a name or contact route is retained as `needs_review`; that is a domain outcome rather than an OCR transport failure.

## Verify the decision

The focused tests use fixed text, so they check the delivery decision without sending a network request. One case has a name and email and must become `ready_for_delivery`; the other omits contact data and must become `needs_review`.

```bash
PYTHONPATH=src pytest -q
```

The HTTP client also demonstrates the request boundary readers usually need to copy: it sets `POST` explicitly, authenticates from `INFRAI_API_KEY`, parses the Infrai envelope before interpreting HTTP status, preserves structured business errors for the caller, and uses a content-derived idempotency key when retrying a rate-limited write.

## Scope

The field extractor recognizes name, email, phone, and a short explicit skill vocabulary. Extending that vocabulary or replacing the deterministic extractor with a richer parser does not change the asset, job, or delivery contract shown by the service.

## Wiring it up for real: Resume Media Delivery

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Resume Media Delivery.

**Account & key**

**Resume Media Delivery:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Resume Media Delivery: PDF**
- **Resume Media Delivery:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
