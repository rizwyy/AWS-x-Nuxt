# Finish Atlas on AWS today

The Nuxt app is complete for the portfolio MVP. Complete these AWS console steps to enable uploads, durable history, feedback, metrics, and per-user document filtering.

## 1. Add metadata for the three shared PDFs

Upload each file from `aws/metadata/` beside its matching PDF in the S3 prefix used by the Knowledge Base. The names must be exact, for example `leave-policy.pdf.metadata.json` beside `leave-policy.pdf`. Sync the Knowledge Base once afterward. This marks the starter policies as shared; newly uploaded documents are marked private to their Cognito user.

## 2. Create DynamoDB storage

Create a table named `atlas-app-dev` in `us-east-1`:

- Partition key: `pk` (String)
- Sort key: `sk` (String)
- Capacity: On-demand
- Encryption: AWS owned key
- Point-in-time recovery: On

The equivalent configuration is in `aws/dynamodb-table.json`.

## 3. Replace the Lambda code

Upload `output/lambda/atlas-api-full.zip` to `atlas-chat-api-dev`. Keep the existing current boto3 layer. Set the handler to `lambda_function.lambda_handler`, memory to 512 MB, and timeout to 90 seconds.

Add these environment variables:

| Name | Value |
|---|---|
| `DOCUMENT_BUCKET` | `atlas-knowledge-dev-rizwin-20260906` |
| `KNOWLEDGE_BASE_ID` | `J9NYEIYUOU` |
| `DATA_SOURCE_ID` | Copy the ID from Bedrock → Knowledge Bases → atlas-knowledge-dev → Data source |
| `TABLE_NAME` | `atlas-app-dev` |
| `MAX_FILE_BYTES` | `20971520` |
| `GUARDRAIL_ID` | Leave unset until the Bedrock guardrail is created |
| `GUARDRAIL_VERSION` | Leave unset until the guardrail has a numbered version |

Attach the permissions in `aws/iam-policy.json` to the Lambda execution role after replacing `REPLACE_BUCKET_NAME` and `REPLACE_ACCOUNT_ID` (`991322955723`).

## 4. Add API Gateway routes

Create these HTTP API routes. Attach the existing Cognito JWT authorizer and the existing Lambda integration to every route:

- `GET /documents`
- `POST /documents/upload-url`
- `POST /documents/{id}/ingest`
- `GET /conversations`
- `POST /feedback`
- `GET /metrics`

Keep the existing `POST /chat`. If the `dev` stage has auto-deploy enabled, the routes become live immediately. Otherwise deploy them to `dev`.

Update API Gateway CORS:

- Origin: `http://localhost:3000`
- Methods: `GET`, `POST`, `OPTIONS`
- Headers: `authorization`, `content-type`
- Credentials: No
- Max age: 300

## 5. Add S3 upload CORS

On the document bucket, Permissions → CORS, use:

```json
[
  {
    "AllowedHeaders": ["content-type", "x-amz-meta-owner", "x-amz-meta-document-id"],
    "AllowedMethods": ["PUT"],
    "AllowedOrigins": ["http://localhost:3000"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 300
  }
]
```

## 6. Verify the complete flow

1. Sign out and sign in again.
2. Ask the annual-leave question and open its citation.
3. Upload a small PDF in Documents.
4. Wait for its status to become Ready, then ask a question unique to that PDF.
5. Rate the answer and reload the app; the conversation should return from DynamoDB.
6. Open Insights and confirm latency and feedback activity.

## 7. Run the RAG evaluation

Copy a current Cognito access token from browser session storage and run:

```sh
ATLAS_API_URL=https://6vnoteuva5.execute-api.us-east-1.amazonaws.com/dev \
ATLAS_ACCESS_TOKEN='paste-token-here' \
python3 evaluation/run_eval.py
```

The versioned test set covers answerable questions, unsupported questions, prompt injection, citations, latency, and abstention.
