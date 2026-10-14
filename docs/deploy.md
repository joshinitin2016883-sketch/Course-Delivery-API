# Deploying the API

The backend runs on Render's free tier against Postgres on Neon's free tier, both in Singapore so that
database queries don't cross regions. The frontend isn't deployed yet. Why it's set up this way:
[Decision 23](decisions.md).

Live API: https://course-delivery-api.onrender.com (interactive docs at `/docs`)

## Services

| Service | What runs there | Settings |
|---------|-----------------|----------|
| Neon (free) | Postgres 17, database `course_delivery` | Region AWS Asia Pacific (Singapore). The app uses the **direct** connection string, not the pooled one. |
| Render (free web service) | The FastAPI app | Root directory `backend`, region Singapore, health check path `/health`. |

## Environment variables on Render

Names only; the values live in Render's dashboard and nowhere in this repository.

| Name | What it holds |
|------|---------------|
| `PYTHON_VERSION` | A full 3.12 version (`major.minor.patch`). Render's default is 3.14, and this variable needs the patch number. |
| `DATABASE_URL` | Neon's direct connection string, with `postgresql://` at the start changed to `postgresql+psycopg://`. Keep its `sslmode` and `channel_binding` settings. |
| `JWT_SECRET` | A long random string. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `JWT_EXPIRE_MINUTES` | Optional; the code defaults to 480 (8 hours). |
| `CORS_ORIGINS` | Not set yet. Once the frontend is deployed, its Vercel URL. |

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
