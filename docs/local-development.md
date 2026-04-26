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
