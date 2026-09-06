# AWS backend handoff

## Current boundary

The frontend runs without AWS. `NUXT_PUBLIC_API_BASE` enables only `POST /chat` and `POST /feedback`. It is not a production-mode switch: authentication UI, document API integration, real uploads, and server history are still work to implement when the AWS API is available.

## Chat (adapter implemented)

`POST /chat`, JSON, authenticated cookie (`credentials: include`).

Request:
```json
{"question":"What is our leave policy?","documentIds":["handbook"],"conversationId":"uuid"}
```

Response:
```json
{"id":"message-uuid","text":"Answer text","citations":[{"documentId":"doc-id","title":"Handbook.pdf","excerpt":"Exact supporting passage"}],"latencyMs":1234,"costUsd":0.002}
```

Empty `documentIds` means all documents the authenticated user may access. Never trust IDs, role, tenant, or conversation IDs supplied by the client as authorization. Resolve identity and tenant from the verified session. Return an unsupported-answer response with no citations when evidence is absent. Apply Bedrock Guardrails on the server and return an appropriate policy message for blocked requests. Set timeouts, bounded question length, request quotas, and retrieval limits server-side.

## Feedback (adapter implemented)

`POST /feedback`: `{"messageId":"uuid","rating":"up"}` (or `down`). Return 204. Authenticate, authorize message ownership, and upsert the user's rating.

## Documents (proposed contract, adapter not implemented)

- `GET /documents`: return authorized `KnowledgeDocument[]` (see shared/types.ts; expand status for processing/error).
- `POST /documents/upload-url`: accept filename, content type, size; authorize and return `{ documentId, uploadUrl, headers }` for a short-lived upload.
- Browser uploads directly to S3 using the presigned URL and specified headers.
- `POST /documents/:id/ingest`: initiate indexing, idempotently.
- `GET /documents/:id`: retrieve ingestion status and authorized source preview.
- The frontend should poll with backoff while processing and expose retries for failed ingestion.

Validate type and size server-side, scan uploaded content, and enforce S3 object ownership and tenant-specific retrieval filters. Client extension checks are UX only. Never render document content as raw HTML.

## Authentication and history (to implement)

Use Cognito sign-in with a server-managed secure, HttpOnly session cookie, or implement a token adapter with an appropriate OAuth flow. Current `$fetch` uses cookies, not bearer tokens. Configure precise CORS origins, credentials, CSRF protection, and session expiry. Remove the demo identity when sign-in is connected.

Proposed routes: `GET /session`, `GET /conversations`, `GET /conversations/:id`, `DELETE /conversations/:id`. The server owns history and access control. Do not store real company conversation content in localStorage. Prevent unauthorized users from listing, retrieving, or citing protected documents.

## Monitoring and evaluation (to implement)

Emit server request IDs, retrieval/generation duration, token usage, estimated model cost, status, and guardrail outcome. Avoid logging raw confidential prompts by default. Return aggregate metrics through an authorized endpoint; the present Insights view shows local demo activity only.

Maintain a versioned evaluation set containing answerable, unanswerable, prompt-injection, and cross-permission questions. Compare retrieval recall, supported answers, abstention, latency, and cost against explicit release thresholds. The checklist in Insights is not an evaluation runner.

## Suggested implementation order

1. Authenticated session and document access policy.
2. S3 upload, ingestion status, and document listing.
3. Bedrock retrieval and generation with authorized citations.
4. Durable conversations and feedback.
5. Guardrails, rate limits, request telemetry, and evaluation.
6. Integration tests with two users in different permission groups, then deployment.
