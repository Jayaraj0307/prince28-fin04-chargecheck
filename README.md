
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

## Production Deployment

ChargeCheck is deployed on Render using Docker images published to GitHub Container Registry (GHCR).

- **Live API:** https://prince28-fin04-chargecheck-main.onrender.com
- **Swagger documentation:** https://prince28-fin04-chargecheck-main.onrender.com/docs
- **Health check:** https://prince28-fin04-chargecheck-main.onrender.com/health
- **Container image:** `ghcr.io/jayaraj0307/prince28-fin04-chargecheck`

### CI/CD Pipeline

GitHub Actions automates the following steps:

1. Run Ruff lint checks and formatting checks.
2. Run database migrations and load sample data.
3. Execute automated tests using PostgreSQL.
4. Build and publish the Docker image to GHCR.
5. Deploy the image to Render.
6. Verify production health after deployment.

### Rollback

Previous deployments can be restored from the Render Dashboard using the deployment rollback option.

A rollback drill was successfully completed, and the latest production version was restored and verified using the `/health` endpoint.

## Production Monitoring

Production health is monitored using UptimeRobot.

- **Monitor:** ChargeCheck Production API
- **Endpoint:** `/health`
- **Check interval:** 5 minutes
