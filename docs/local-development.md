# Local Development

## Web App

```bash
cd apps/web
npm install
npm run dev
```

The web app expects Supabase public environment variables. Copy the root `.env.example` values into `apps/web/.env.local` or provide them through your shell.

## Ingest Worker

```bash
cd services/ingest
python -m pip install -r requirements.txt
python src/main.py
```

Copy `services/ingest/.env.example` to `services/ingest/.env` and fill in the required Supabase and AI provider values.

## Tests

Run Python tests from the ingest worker directory:

```bash
cd services/ingest
python -m unittest discover tests
```

Run web linting from the web app directory:

```bash
cd apps/web
npm run lint
```

## Admin migration checks

The replacement lives in the separate admin checkout. Its integration suite requires `TEST_DATABASE_URL` pointing to a disposable loopback database named `aiblogpost_migration_test`, plus `BLOG_CONTRACT_ROOT` pointing to this checkout. Tests reset that named local schema and refuse remote targets. Auth tests simulate upstream identity responses; local SQL tests do not establish live Supabase Data API behavior or Google login. Never run ingestion as a migration test.
