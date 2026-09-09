# Deployment Guide (Vercel + Render + Neon)

This documents exactly what to enter in each platform's dashboard to
deploy Kinvera. **Nothing has been deployed yet** - this is the
reference for when you're ready to click through it yourself, entirely
in the browser. No local installation is required to do any of this;
Render and Vercel both build from the GitHub repository directly.

Do the three platforms in this order, since Render needs to exist
before Vercel can point at it, and Render's CORS setting needs to
exist before Vercel's URL to put into it:

**Neon (database) → Render (backend) → Vercel (frontend) → back to Render to add the Vercel URL to CORS**

## 1. Neon (PostgreSQL)

1. Create a Neon project (any region).
2. Create a database inside it named `kinvera` (Neon calls this a "branch" database, or you can rename the default one).
3. From the Neon dashboard, copy the **connection string** it gives you. It looks like:
   ```
   postgresql://<user>:<password>@<endpoint>.neon.tech/kinvera?sslmode=require
   ```
4. Neon offers both a **pooled** and a **direct** connection string. Use the **direct** (non-pooled) one for `DATABASE_URL` - a few tools (including some Alembic operations) don't behave well through a connection pooler for DDL statements. The direct string is what Render's web service will use for normal traffic too, which is fine at this project's scale.
5. That connection string is the exact value for `DATABASE_URL` in the Render step below. Nothing else needs to be created in Neon - the app's own Alembic migration creates all 9 tables the first time it runs against this database.

## 2. Render (backend)

Create a new **Web Service** in Render, connected to this GitHub repository.

| Field | Value |
|---|---|
| Root Directory | `kinvera/backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt && alembic upgrade head` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

Environment variables (Render's dashboard, not committed to git):

| Key | Value |
|---|---|
| `DATABASE_URL` | The Neon connection string from step 1 |
| `API_CORS_ORIGINS` | `http://localhost:3000` for now - update this once you have the Vercel URL (step 4) |
| `DEFAULT_RELIEF_WINDOW_DAYS` | `30` (optional - this is already the default) |
| `MINIMUM_REST_DAYS` | `2` (optional - this is already the default) |

Notes:
- `$PORT` is set automatically by Render - don't hard-code a port number in the start command.
- The Build Command runs `alembic upgrade head` on every deploy, so the schema stays in sync automatically. It does **not** run the seed script - seeding is a one-time (or on-demand) action, not something that should happen on every deploy, since it wipes and rebuilds the workforce dataset.
- **To load the synthetic dataset**, after the first successful deploy, use Render's **Shell** tab (or a one-off **Job**, depending on your plan) on the same service and run:
  ```
  python -m app.seed.generate_synthetic_data
  ```
  This is a browser-based terminal inside Render's dashboard - nothing to install locally.
- Once deployed, Render gives you a URL like `https://kinvera-api.onrender.com`. You'll need it for the Vercel step.

## 3. Vercel (frontend)

Create a new Vercel project, importing the same GitHub repository.

| Field | Value |
|---|---|
| Root Directory | `kinvera/frontend` |
| Framework Preset | Next.js (auto-detected) |
| Build Command | default (`npm run build`) |
| Install Command | default (`npm install`) |

Environment variable (Vercel's dashboard, not committed to git):

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Your Render URL from step 2, e.g. `https://kinvera-api.onrender.com` |

Once deployed, Vercel gives you a URL like `https://kinvera.vercel.app`.

## 4. Close the loop: update Render's CORS setting

Go back to the Render service's environment variables and update:

| Key | Value |
|---|---|
| `API_CORS_ORIGINS` | `https://kinvera.vercel.app` (your real Vercel URL - add `,http://localhost:3000` too if you still want local frontend dev to reach the deployed backend) |

Saving an environment variable change triggers a redeploy automatically. `API_CORS_ORIGINS` accepts either a single origin, a comma-separated list, or a JSON array - whichever is easiest to paste into Render's UI.

## 5. Verify

Once both are deployed:
- `https://<your-render-url>/api/health` should return `{"status": "ok"}`.
- `https://<your-render-url>/api/dashboard/summary` should return real numbers (not zeros) once you've run the seed command.
- Opening the Vercel URL should show the dashboard with those same numbers - if it shows a CORS error in the browser console instead, double check `API_CORS_ORIGINS` on Render matches the exact Vercel URL (including `https://`, no trailing slash).

## What this deployment does *not* include

Per Phase 1 scope: no authentication, no CI/CD pipeline, no containerization, and no AI integration. These are documented as intentional gaps in the [README](../README.md#current-limitations), not omissions from this guide.
