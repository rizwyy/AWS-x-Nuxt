# Deploy Atlas to Netlify

## First deployment

1. Put this folder in a GitHub repository.
2. In Netlify, choose **Add new project → Import an existing project** and select the repository.
3. Netlify should detect Nuxt. The committed `netlify.toml` supplies `npm run build` and Node 24.
4. Add these environment variables before deploying:

```text
NUXT_PUBLIC_API_BASE=https://6vnoteuva5.execute-api.us-east-1.amazonaws.com/dev
NUXT_PUBLIC_COGNITO_DOMAIN=https://us-east-1fnlw9cio1.auth.us-east-1.amazoncognito.com
NUXT_PUBLIC_COGNITO_CLIENT_ID=6blpnr1pl4062bmvh91pbggos1
NUXT_PUBLIC_COGNITO_REDIRECT_URI=http://localhost:3000
NUXT_PUBLIC_COGNITO_LOGOUT_URI=http://localhost:3000
```

5. Deploy once and copy the assigned URL, such as `https://atlas-knowledge.netlify.app`.

The first deployment is only used to obtain the final hostname. Cognito login will still return to localhost until the next steps are completed.

## Connect the production hostname

Assume Netlify assigned `https://atlas-knowledge.netlify.app`. Use your actual URL everywhere below, without a trailing slash.

### Netlify environment variables

Change both values and redeploy:

```text
NUXT_PUBLIC_COGNITO_REDIRECT_URI=https://atlas-knowledge.netlify.app
NUXT_PUBLIC_COGNITO_LOGOUT_URI=https://atlas-knowledge.netlify.app
```

### Cognito app client

Keep localhost for development and add the production URL to both lists:

- Allowed callback URLs: `http://localhost:3000`, `https://atlas-knowledge.netlify.app`
- Allowed sign-out URLs: `http://localhost:3000`, `https://atlas-knowledge.netlify.app`

### API Gateway CORS

Allowed origins:

- `http://localhost:3000`
- `https://atlas-knowledge.netlify.app`

Keep methods `GET`, `POST`, `OPTIONS` and headers `authorization`, `content-type`.

### S3 bucket CORS

Add the Netlify hostname to `AllowedOrigins`:

```json
[
  {
    "AllowedHeaders": ["content-type", "x-amz-meta-owner", "x-amz-meta-document-id"],
    "AllowedMethods": ["PUT"],
    "AllowedOrigins": ["http://localhost:3000", "https://atlas-knowledge.netlify.app"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 300
  }
]
```

## Production verification

1. Open the Netlify URL in a private browser window.
2. Sign in through Cognito and confirm it returns to Netlify.
3. Ask an annual-leave question and open its citation.
4. Upload a small test PDF and wait for indexing.
5. Reload the page and confirm conversation history returns.

Do not copy `.env` into Git. Netlify injects the public configuration during its build.
