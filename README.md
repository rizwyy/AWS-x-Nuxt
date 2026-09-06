# Atlas · Nuxt knowledge assistant

A Nuxt 4 / Vue / TypeScript internal RAG assistant backed by Amazon Cognito, API Gateway, Lambda, Bedrock Knowledge Bases, S3, DynamoDB, and CloudWatch.

## Run

Use Node.js 24 (or Node 22.19+) as required by the patched Nuxt version.

```sh
npm install --legacy-peer-deps
npm run dev
```

Open the local address printed by Nuxt. `npm run build` creates a Node deployment; `npm run generate` creates static frontend output in `.output/public`. Use `npm run typecheck` for TypeScript validation.

## Implemented

- Responsive workspace with chat, document library, insights, and settings.
- Sample-document retrieval, source selection, inspectable citations, unsupported-question fallback, loading/error states, copy, and feedback.
- Local demo conversation history and staged upload metadata, persisted in this browser; reset in Settings.
- Filename/type/size checks for demo uploads. File contents are never uploaded in demo mode.
- Session counts and latency, with no fabricated cost or evaluation scores.

## AWS deployment

The app is connected to the development Cognito and API Gateway environment. The deployable Lambda package supports chat, citations, presigned S3 uploads, Knowledge Base ingestion, per-user metadata filters, DynamoDB conversation history, feedback, and metrics. Follow [docs/finish-today.md](docs/finish-today.md) to add the remaining AWS routes and resources.

The Nuxt 4 app structure follows https://nuxt.com/docs/4.x/directory-structure/app/app.

## AWS handoff

See [docs/aws-integration.md](docs/aws-integration.md). `app/composables/useKnowledge.ts` is the chat adapter and `shared/types.ts` defines the response types. Set `NUXT_PUBLIC_API_BASE` to enable the chat and feedback API adapters after configuring authenticated API access. Never put AWS credentials or API secrets into a `NUXT_PUBLIC_*` value.

The document list remains demo data until the document adapter is implemented. Uploads in API mode intentionally do not pretend to succeed. Browser history is demo-only; implement server conversation loading before real use. Do not use sensitive company data in this prototype.
