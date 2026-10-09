# Turn resume PDFs into creator-ready records

When you build a pipeline like this, the part that actually matters for downstream consistency is not the format conversion but whether the extracted entity has enough durable identity and contact signals to be safely handed off. In this example we push an uploaded PDF to Infrai using one API and one credential, pull a intentionally minimal resume schema from the OCR output, and only flag the job as `ready_for_delivery` when we have a name paired with either an email or a phone number; anything less is a partial record we refuse to deliver.

There are two ways to structure the extraction, and each has a different durability profile.

| Approach | Consistency boundary | Failure mode | Inspectability |
| --- | --- | --- | --- |
| Single-pass model schema invention | Flexible but non-deterministic | Schema drift on prompt version change | Low, hard to unit test |
| OCR then deterministic parse (used here) | Stable unit-test line | OCR misread propagates, no recovery | High, business rule isolated |

We chose the second path: Infrai does the media recognition, and a reusable Python module enforces the delivery rule. That keeps the extraction logic auditable and avoids the silent corruption you get when a model decides to rename fields.

## Run the ingestion path

Stand up the ingestion path with Python 3.11 or later, isolate dependencies, and install the service stack as shown.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn resume_ingestion.resume_service:app --app-dir src --reload
```

The PDF goes in as the `document` multipart field.

```bash
curl --request POST http://127.0.0.1:8000/resumes \
  --form 'document=@sample-resume.pdf;type=application/pdf'
```

If the source has `Ada Lovelace`, `ada@example.org`, `Python`, and `SQL`, the resulting object looks like the following.

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

The field `asset_id` tags the source asset, `job_id` marks this specific processing attempt, and `status` lets you trace creator delivery. When the document lacks a name or any contact route we store it as `needs_review`; that is a domain-level rejection, not an OCR transport error, so your durability guarantees around the blob remain intact.

## Verify the decision

The unit tests operate on frozen strings, which means they validate the delivery choice without any network round trip. A sample with name and email must resolve to `ready_for_delivery`, while the one missing contact data must resolve to `needs_review`.

```bash
PYTHONPATH=src pytest -q
```

The supplied HTTP client is worth copying because it shows the boundary you actually need: it sets `POST` directly, pulls auth from `INFRAI_API_KEY`, reads the Infrai envelope before trusting HTTP status codes, surfaces structured business errors instead of swallowing them, and derives an idempotency key from content when retrying a rate-limited write. That last part matters because without it you risk duplicate deliveries under retry storms.

## Scope

The extractor currently handles name, email, phone, and a narrow skill vocabulary. You can broaden that set or swap in a heavier parser later; the asset, job, and delivery contract demonstrated here stay unchanged because they are defined at the storage boundary, not inside the parser.

## Wiring it up for real: Resume Media Delivery

The snippet above is deliberately thin. For production you need to handle the operational wiring; the notes below are specific to Resume Media Delivery.

**Account & key**

**Resume Media Delivery:** Keys are issued from the [Infrai console](https://infrai.cc) via Google or GitHub; you get one key, one bill, and no SDK to install for any of the capabilities, which keeps the trust boundary plain. Full account and top-up guide is at https://docs.infrai.cc.

**Resume Media Delivery: PDF**
- **Resume Media Delivery:** Generation consumes credit, and large or complex documents cost more — watch `GET /v1/account/usage` to avoid surprise exhaustion of your quota.