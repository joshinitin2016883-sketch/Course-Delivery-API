# Deploying the API and the frontend

The backend runs on Render's free tier against Postgres on Neon's free tier, both in Singapore so that
database queries don't cross regions. Why it's set up this way: [Decision 23](decisions.md). The frontend
is a set of static files on Vercel's free tier ([below](#the-frontend-on-vercel)).

Live API: https://course-delivery-api.onrender.com (interactive docs at `/docs`)

## Services

| Service | What runs there | Settings |
|---------|-----------------|----------|
| Neon (free) | Postgres 17, database `course_delivery` | Region AWS Asia Pacific (Singapore). The app uses the **direct** connection string, not the pooled one. |
| Render (free web service) | The FastAPI app | Root directory `backend`, region Singapore, health check path `/health`. |
| Vercel (Hobby) | The React app, built by `npm run build` | Root directory `frontend`, framework preset Vite. |

## Environment variables on Render

Names only; the values live in Render's dashboard and nowhere in this repository.

| Name | What it holds |
|------|---------------|
| `PYTHON_VERSION` | A full 3.12 version (`major.minor.patch`). Render's default is 3.14, and this variable needs the patch number. |
| `DATABASE_URL` | Neon's direct connection string, with `postgresql://` at the start changed to `postgresql+psycopg://`. Keep its `sslmode` and `channel_binding` settings. |
| `JWT_SECRET` | A long random string. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `JWT_EXPIRE_MINUTES` | Optional; the code defaults to 480 (8 hours). |
| `CORS_ORIGINS` | The browser origins allowed to call the API, separated by commas, each with no trailing slash: `https://<project>.vercel.app,http://localhost:5173`. The second one is for running the frontend on your machine. |

`SEED_PASSWORD` isn't set on Render: the seed runs from a developer's machine (below).

## Commands

- Build: `pip install -r requirements.txt`
- Start: `python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`

The free tier has no shell and no pre-deploy command, so the start command migrates the database before
the app starts. When the schema is already up to date, the migration does nothing.

## Migrating and seeding Neon from your machine

Run these from `backend/` with the venv active. Typing the connection string at a prompt, rather than on
the command line, keeps it out of your shell history.

```powershell
$env:DATABASE_URL = [System.Net.NetworkCredential]::new("", (Read-Host "Neon direct connection string" -AsSecureString)).Password
$env:SEED_PASSWORD = [System.Net.NetworkCredential]::new("", (Read-Host "Demo password" -AsSecureString)).Password
python -m alembic upgrade head
python -m app.seed
Remove-Item Env:DATABASE_URL, Env:SEED_PASSWORD
```

Variables set like this win over `backend/.env` for that PowerShell window only, so your local Docker
database isn't touched. The tests never use `DATABASE_URL`: they always run against `TEST_DATABASE_URL`.

## Cold starts

- **Render** puts a free service to sleep after 15 minutes without traffic. The next request takes about a
  minute while it starts again, and that start includes the migration check.
- **Neon** suspends its free compute after 5 idle minutes and wakes in a few hundred milliseconds on the
  next query. `pool_pre_ping` in `app/core/database.py` notices a connection Neon has closed and opens a new
  one, so the first request after a pause doesn't fail.
- `/health` doesn't touch the database, so Render's health checks don't keep waking Neon.
- The frontend shows "Waking the server, this can take up to a minute" whenever a request has taken
  longer than 3 seconds, so a cold start doesn't look like a broken page.

## Problems on the first deploy

1. **No root directory set:** the build couldn't find `requirements.txt`. Set Root Directory to `backend`.
2. **Python 3.14 used:** Render's default. Set `PYTHON_VERSION` to a full 3.12 version, and check the
   Python version printed near the top of the build log.
3. **Environment variables not saved:** the start command failed with
   `Environment variable DATABASE_URL is not set`. Add the variables, save them, then redeploy.

On Render, each deploy and its build log are under the service's **Events**, and the running app's output
(including the migration and any traceback) is under **Logs**.

## Resetting Neon before the final demo seed

The activity log is append-only ([Decision 6](decisions.md)), so courses created on the live database,
such as the smoke test's, can never be deleted, only archived. Before the final demo seed, start again
from an empty database:

1. In Render, suspend the service so nothing writes while you reset (**Settings**, then **Suspend Web Service**).
2. In Neon's **SQL Editor**, on the `course_delivery` database, run:
   ```sql
   DROP SCHEMA public CASCADE;
   CREATE SCHEMA public;
   ```
3. From your machine, run the migration and seed commands above.
4. Resume the Render service. Its start command finds the schema already up to date.

## The frontend on Vercel

Vercel builds the app from `frontend/` on every push to `main` and serves the files the build produces.
`frontend/vercel.json` sends every path that isn't a real file to `index.html`, so a reload, or a shared
link to a page such as `/courses/12`, opens the app instead of Vercel's 404 page.

### Environment variable on Vercel

| Name | What it holds |
|------|---------------|
| `VITE_API_URL` | The API's address, with no trailing slash: `https://course-delivery-api.onrender.com`. |

Vite writes this value into the JavaScript during the build. Changing it does nothing until the next
deployment, and a build without it shows a blank page with `VITE_API_URL is not set` in the browser console.

### First deployment

1. In Vercel, choose **Add New**, then **Project**, and import the GitHub repository. It's private, so
   let Vercel read it when GitHub asks.
2. Set **Root Directory** to `frontend`. Vercel then recognises a Vite project and fills in the build
   command and the output directory (`dist`). Leave both as they are.
3. Under **Environment Variables**, add `VITE_API_URL` as above.
4. Choose **Deploy**. When it finishes, note the domain: `https://<project>.vercel.app`.
5. In Render, set `CORS_ORIGINS` to `https://<project>.vercel.app,http://localhost:5173`, and save it with
   an option that also deploys: the running service only reads its environment when it starts. Until
   then the browser refuses every answer from the API, and the app says "Couldn't reach the server".
6. Open the Vercel domain and sign in.

### Redeploying

- Every push to `main` deploys again on its own.
- After changing `VITE_API_URL`, open **Deployments**, then the latest deployment's **⋯** menu, then
  **Redeploy**. The new value is only read during a build.

### Problems you might meet

1. **A blank page:** `VITE_API_URL` was missing when the app was built. Add it, then redeploy.
2. **"Couldn't reach the server" on every request:** the Vercel domain isn't in `CORS_ORIGINS` on Render,
   or Render hasn't deployed since it was added. A preview deployment has a domain of its own, so the API
   refuses it too unless that domain is added.
3. **Vercel's 404 page after a reload:** Root Directory isn't `frontend`, so `vercel.json` wasn't used.
