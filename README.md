# hyuabot-subway-realtime-updater

A recurring job that fetches real-time subway arrival information and keeps the HYUabot database up to date. Runs every minute as a Kubernetes CronJob.

## Overview

On each run the job queries the Seoul Metro open API for real-time arrival data for the lines serving Hanyang University ERICA:

- **Line 4** (route ID: 1004) — Hanyang University station
- **Suin-Bundang Line** (route ID: 1071) — Sangnoksu station
- **Seohae Line** (route ID: 1093) — Choji station

The job clears stale `subway_realtime` records and inserts fresh arrival predictions. Supports master-DB failover.

## Architecture

```
src/
├── main.py              # Entry point; fetches Line 4 and Suin-Bundang Line data
├── models.py            # SQLAlchemy ORM models (SubwayRealtime)
└── utils/
    └── database.py      # PostgreSQL engine factory with master failover
```

## Requirements

- Python ≥ 3.12
- PostgreSQL
- Seoul Metro API key (`METRO_AUTH_KEY`)

## Environment Variables

| Variable            | Description                    |
|---------------------|--------------------------------|
| `METRO_AUTH_KEY`    | Seoul Metro open API key       |
| `POSTGRES_ID`       | PostgreSQL username            |
| `POSTGRES_PASSWORD` | PostgreSQL password            |
| `POSTGRES_HOST`     | PostgreSQL host                |
| `POSTGRES_PORT`     | PostgreSQL port                |
| `POSTGRES_DB`       | PostgreSQL database name       |

## Running Locally

```bash
pip install -e .

export METRO_AUTH_KEY=your_api_key
export POSTGRES_ID=postgres
export POSTGRES_PASSWORD=password
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=hyuabot

cd src && python main.py
```

## Docker

The container exits after a single run — schedule it externally (Kubernetes CronJob every minute).

```bash
docker build -t hyuabot-subway-realtime-updater .

docker run --rm \
  -e METRO_AUTH_KEY=your_api_key \
  -e POSTGRES_ID=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=hyuabot \
  hyuabot-subway-realtime-updater
```

## Development

```bash
pip install -e .[lint]       # flake8
pip install -e .[typecheck]  # mypy
pip install -e .[test]       # pytest
```

```bash
python -m flake8 src/ tests/
python -m mypy src/ tests/
python -m pytest -v
```

Tests run against a PostgreSQL instance at `localhost:25432`.

## CI/CD

| Workflow | Trigger | Jobs |
|---|---|---|
| `code-check.yml` | Push to any branch except `main` | lint, typecheck, test |
| `deploy.yml` | PR merged to `main` (or manual dispatch) | Docker build → push to `localhost:5000` |

CI runners: self-hosted X64 Linux (code checks) · ARM64 Linux (Docker build).

## License

GPLv3
