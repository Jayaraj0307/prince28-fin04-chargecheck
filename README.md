# ChargeCheck

ChargeCheck helps students and parents compare savings accounts and avoid hidden banking charges.

**Status:** FastAPI application, PostgreSQL database, Alembic migrations, Docker Compose, Redis and automated tests.

## Who it's for

First-year college student in Chennai and her parents choosing a savings account without hidden charges.

## The problem

Every bank publishes a long schedule of charges that varies by account type, location (metro/urban/semi-urban/rural), number of transactions and effective dates.

## Data sources

Schedules of service charges of 12 banks (SBI, Indian Bank, IOB, Canara, HDFC, ICICI, Axis, Kotak, South Indian Bank, Karur Vysya, City Union, TMB) and RBI customer-service circulars (including BSBD accounts).

- https://sbi.bank.in/
- https://www.southindianbank.bank.in/userfiles/file/compendium%20of%20service%20charges%20new.pdf
- https://www.rbi.org.in/

## Signature feature

My-usage cost calculator: enter monthly ATM, NEFT, cash and SMS use and compare estimated bank charges.

## Run locally

Install dependencies:

```bash
uv sync
```

Create environment file (Windows PowerShell):

```powershell
Copy-Item .env.example .env
```

Start the development server:

```bash
uv run uvicorn chargecheck.api.main:create_app --factory --reload
```

Open http://localhost:8000/docs

## Docker setup

Start PostgreSQL, Redis and API:

```bash
docker compose -f compose.yaml up --build -d
```

Check running services:

```bash
docker compose -f compose.yaml ps
```

Stop services:

```bash
docker compose -f compose.yaml down
```

## Database

- PostgreSQL for persistent storage.
- SQLAlchemy for database models and access.
- Alembic for database migrations.
- Redis as a supporting service.

## Tests and coverage

Run tests:

```bash
uv run pytest -v
```

Run coverage:

```bash
uv run pytest --cov=chargecheck --cov-report=term-missing
```

Generate HTML coverage:

```bash
uv run pytest --cov=chargecheck --cov-report=html
```

HTML report is generated in the `htmlcov` directory.

## Code quality

```bash
uv run ruff check .
uv run ruff format .
```

## Makefile commands

```bash
make help
make install
make dev
make test
make coverage
make lint
make format
make check
make docker-up
make docker-down
make docker-logs
```

## Database verification

See [NOTES.md](NOTES.md) for PostgreSQL index verification and EXPLAIN query-plan evidence.
