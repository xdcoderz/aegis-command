# Deploy Aegis Command on Railway

This procedure deploys the repository as three Railway services: `postgres`, `api`, and `web`. Both application services use the repository root as their build context because the Dockerfiles copy files from multiple top-level directories.

## 1. Create the project

1. Create an empty Railway project.
2. Add a PostgreSQL service and name it `postgres`.
3. Add the GitHub repository twice and name the services `api` and `web`.
4. Keep the root directory `/` for both application services.

Railway supports service variables that reference values from another service using `${{service.VARIABLE}}` syntax. The API settings also accept Railway's `postgres://` URL and normalize it to SQLAlchemy's asyncpg driver.

## 2. Configure the API service

Set the custom Dockerfile path:

```text
RAILWAY_DOCKERFILE_PATH=/infra/docker/api.Dockerfile
```

Add these service variables. Replace the example credentials with randomly generated values of at least 16 characters.

```text
AEGIS_ENVIRONMENT=production
AEGIS_LOG_LEVEL=INFO
AEGIS_DATABASE_URL=${{postgres.DATABASE_URL}}
AEGIS_AUTO_CREATE_SCHEMA=false
AEGIS_AUTH_ENABLED=true
AEGIS_API_KEYS={"replace-observer-key":"observer","replace-analyst-key":"analyst","replace-admin-key":"admin"}
AEGIS_PQC_REQUIRED=true
AEGIS_ENFORCEMENT_SANDBOX_ENABLED=true
AEGIS_CORS_ORIGINS=["https://${{web.RAILWAY_PUBLIC_DOMAIN}}"]
AEGIS_TRUSTED_HOSTS=["healthcheck.railway.app","${{RAILWAY_PUBLIC_DOMAIN}}"]
```

In **Settings → Deploy**, set the health-check path to:

```text
/api/v1/health/ready
```

Generate a public domain for `api`. The container listens on Railway's injected `PORT`; do not add a fixed port variable.

The API image compiles pinned Open Quantum Safe libraries, so its first build is materially longer than a normal Python image. Subsequent builds use layer caching when the cryptographic dependency stages have not changed.

## 3. Configure the web service

Set the custom Dockerfile path:

```text
RAILWAY_DOCKERFILE_PATH=/infra/docker/web.Dockerfile
```

Add the build variables:

```text
VITE_API_BASE_URL=https://${{api.RAILWAY_PUBLIC_DOMAIN}}/api/v1
VITE_API_KEY=replace-analyst-key
VITE_ADMIN_API_KEY=replace-admin-key
```

The values for `VITE_API_KEY` and `VITE_ADMIN_API_KEY` must match entries in `AEGIS_API_KEYS`. Generate a public domain for `web`; the Nginx image also listens on Railway's injected `PORT`.

Vite variables are embedded in the delivered JavaScript and can be read by anyone who can load the site. Use disposable keys and restrict the deployment to a controlled demonstration. A shared production service must use OIDC and server-side session handling.

## 4. Resolve the domain references

After both public domains exist, confirm the rendered values in each service:

- `AEGIS_CORS_ORIGINS` contains the exact web origin, including `https://` and no trailing slash.
- `AEGIS_TRUSTED_HOSTS` contains the API hostname plus `healthcheck.railway.app`.
- `VITE_API_BASE_URL` contains the API domain followed by `/api/v1`.

Redeploy `api`, then redeploy `web`. Railway health checks originate with the host `healthcheck.railway.app`; the trusted-host entry is required for readiness checks to receive HTTP 200.

## 5. Load the reference scenarios

The API image includes the guarded seed utility. Install and authenticate the Railway CLI, link the project, then open a shell in the deployed API container:

```powershell
railway ssh --service api
```

Inside the container, run:

```sh
python /app/scripts/seed_demo.py \
  --api-base "http://127.0.0.1:${PORT}/api/v1/" \
  --api-key "replace-admin-key"
```

Do not use `--reset-local-db` in Railway. That option is intentionally limited to the local SQLite development database. Re-running the hosted seed command is safe because its event IDs are deterministic and the API is idempotent.

## 6. Verify the deployment

Check these URLs and behaviors:

1. `https://<api-domain>/api/v1/health/live` returns `status: alive`.
2. `https://<api-domain>/api/v1/health/ready` returns HTTP 200 and reports database, model, authentication, enforcement, and PQC state.
3. `https://<web-domain>` loads the sign-in screen without browser console CORS errors.
4. The command center displays the seeded sessions.
5. An attack simulation reaches a decision, records enforcement, and appears in the audit view.
6. The PQC vault round trip reports ML-KEM rather than compatibility mode.

## 7. Operational follow-up

- Seal API keys and the webhook secret in Railway after confirming the deployment.
- Enable PostgreSQL backups and review resource metrics before retaining real data.
- Rotate the demonstration keys after any public event.
- Keep `AEGIS_ENFORCEMENT_SANDBOX_ENABLED=true` until a controlled PAM/IAM endpoint is available.
- For a real enforcement integration, configure the webhook URL and secret, add mTLS at the gateway, and validate rollback behavior in a non-production environment.

Platform references: [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles), [health checks](https://docs.railway.com/deployments/healthchecks), [variables](https://docs.railway.com/variables), [PostgreSQL](https://docs.railway.com/databases/postgresql), and [SSH](https://docs.railway.com/cli/ssh).
