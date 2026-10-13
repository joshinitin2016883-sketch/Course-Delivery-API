# Course Delivery & Enrolment

An internal training tool that replaces the course spreadsheet: instructors build and publish courses,
learners enrol and work through lessons, and progress is tracked automatically.

- Assignment brief: [docs/brief.md](docs/brief.md)
- Design decisions: [docs/decisions.md](docs/decisions.md)
- Submission notes and demo logins: [SUBMISSION.md](SUBMISSION.md)

## Stack

FastAPI (Python 3.12), SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, bcrypt · PostgreSQL (Neon in production,
Docker locally) · React + Vite + Tailwind · Render (API) and Vercel (frontend).

## Running the backend locally (Windows, PowerShell)

Needs Python 3.12 and Docker Desktop. Run every command from `backend/`, and always start Python tools
with `python -m`.

```powershell
cd backend
copy .env.example .env                     # then fill in the values (see the comments in the file)
docker compose up -d                       # dev database on port 5433, test database on 5434

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1                 # after this, "python" means the project's Python 3.12
python -m pip install -r requirements.txt

python -m alembic upgrade head             # create the tables
python -m app.seed                         # demo accounts; their password is SEED_PASSWORD from .env
python -m uvicorn app.main:app --reload    # API on http://localhost:8000, interactive docs at /docs

python -m pytest                           # tests; they only ever use the test database
```

If PowerShell refuses to run `Activate.ps1`, allow local scripts once with
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or skip activation and run `.venv\Scripts\python.exe -m ...`.
