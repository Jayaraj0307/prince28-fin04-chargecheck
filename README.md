
## Run locally in one command

Make sure Docker Desktop is running.

Start the complete application (API, PostgreSQL, and Redis):

```bash
make docker-up
```

Check the API:

- API: http://localhost:8000
- Swagger documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Stop the application:

```bash
make docker-down
```

## Test Coverage

Run the test suite with coverage:

```bash
uv run pytest --cov=chargecheck --cov-report=term-missing --cov-report=html
```

Latest test results: **15 passed**

Total code coverage: **75%**

HTML coverage report: `htmlcov/index.html`
