# GitHub Workflows - Agent Guidelines

## Role
This directory manages the CI/CD pipelines and the scheduled orchestration of the `services/ingest` background worker. Since the backend is a batch process rather than a long-running web server, GitHub Actions acts as the orchestrator.

## Key Workflows
- `workflows/ingest.yml`: The primary production pipeline. It runs the Python ingestion script on a CRON schedule (twice a day) or via manual dispatch.
- `workflows/rss-health.yml`: A separate pipeline to monitor the health of the RSS feeds.

## Important Constraints & Rules
- **Environment Variables:** If you add a new environment variable requirement to the Python worker (`services/ingest`), you **MUST** also update `workflows/ingest.yml` to ensure the secret or variable is passed into the job's `env:` block.
- **Workflow Isolation:** Keep the ingest pipeline and the RSS health checks as separate files to ensure failures in one do not block the other.
- **Python Setup:** Changes to Python dependencies or version requirements in the `ingest` service must be reflected in the GitHub Action setup steps.