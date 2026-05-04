# Deployment

This project deploys as a small monorepo:

- `frontend_original/`: Next.js website, deploy to Vercel.
- `app/` and `trust_ml/`: FastAPI backend, deploy to Render/Railway/Fly.
- `artifacts/trust_model.joblib`: ML artifact required by the backend.

## 1. Push to GitHub

Create the GitHub repo from the root folder, not from `frontend_original` alone. The root `.gitignore` keeps local databases, logs, screenshots, build output, `node_modules`, and secrets out of git.

If `frontend_original/.git` exists, remove or move that nested git folder before creating the root repo so GitHub receives the frontend files as normal folders.

```bash
git init
git add .
git commit -m "Prepare app for deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

## 2. Deploy Backend

Render can use `render.yaml` from the repo root.

Required settings:

- Build command: `pip install -e .`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

Set these environment variables in the backend host:

```env
APP_ENV=production
DOCS_ENABLED=false
DATABASE_URL=sqlite:////var/data/placement_trust.db
MODEL_ARTIFACT_PATH=artifacts/trust_model.joblib
AUTH_SECRET_KEY=<strong random value>
ADMIN_REGISTRATION_KEY=<strong random value>
CORS_ORIGINS=https://your-frontend.vercel.app
```

Optional integrations:

```env
GITHUB_TOKEN=
JUDGE0_BASE_URL=
JUDGE0_API_KEY=
JUDGE0_AUTH_TOKEN=
HUGGINGFACE_API_TOKEN=
RAPIDAPI_KEY=
```

## 3. Deploy Frontend

In Vercel:

- Framework: Next.js
- Root directory: `frontend_original`
- Build command: `npm run build`

Set:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-host.example.com
NEXT_PUBLIC_HARNESS_APP_URL=https://ide.judge0.com
```

Add the Firebase `NEXT_PUBLIC_FIREBASE_*` values if Firebase login is enabled.

## 4. Verify

After both services are live:

1. Open `https://your-backend/health`.
2. Open the Vercel frontend URL.
3. Run the demo flow that registers/logs in a student.
4. Check roadmap, coding problems, resume analysis, trust score, and job matching.

