# ChargeCheck

Compares bank service charges (minimum balance, ATM, NEFT, SMS, cards) across 12 banks and estimates the monthly cost for a person's actual usage.

**Status:** Day 1 foundation (FastAPI skeleton, quality gates). Live URL from Day 5.

## Who it's for

First-year college student in Chennai and her parents choosing a savings account without hidden charges.

## The problem

Every bank publishes a long schedule of charges that varies by account type, location (metro/urban/semi-urban/rural) and number of transactions, and changes with 'w.e.f.' dates.

## Data sources

Schedules of service charges of 12 banks (SBI, Indian Bank, IOB, Canara, HDFC, ICICI, Axis, Kotak, South Indian Bank, Karur Vysya, City Union, TMB) and RBI customer-service circulars (incl. BSBD accounts).

- https://sbi.bank.in/
- https://www.southindianbank.bank.in/userfiles/file/compendium%20of%20service%20charges%20new.pdf
- https://www.rbi.org.in/
- Terms: Public bank disclosures. Indian banks moved to .bank.in domains in 2025: find each bank's 'Schedule of charges' page and record the URL and date.

## Hardest problem (my interview story)

Charges depend on account variant x location x channel x monthly count, with effective dates. The answer must pick the right row and compute monthly cost in code from a usage profile.

## Signature feature

My-usage cost calculator: enter monthly ATM, NEFT, cash and SMS use and see each bank's estimated monthly cost.

## Target metric

Monthly cost exact for 100% of 30 usage profiles; charge lookups correct for 90%+ of 50 questions.

## Run it locally

```bash
uv sync
cp .env.example .env   # Windows: copy .env.example .env
uv run uvicorn chargecheck.api.main:create_app --factory --reload
```

Then open http://localhost:8000/docs

## Checks

```bash
uv run pytest
uv run ruff check .
```
