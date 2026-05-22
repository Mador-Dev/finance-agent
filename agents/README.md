# Agents Bootstrap Service

This module owns the bootstrap flow directly from the client:

1. Accept portfolio positions and optional ticker guidance
2. Create a bootstrap `full_report`-style job
3. Fan out one deep research agent per ticker
4. Persist ticker strategies and report artifacts into the shared workspace directory
5. Expose polling endpoints for progress and final results

The service is intentionally self-contained. It does not require the TypeScript server for bootstrap orchestration.

## Why shared workspace files

The existing app already knows how to read:

- `users/<user>/data/portfolio.json`
- `users/<user>/data/state.json`
- `users/<user>/data/tickers/<ticker>/strategy.json`
- `users/<user>/data/reports/<ticker>/*.json`
- `users/<user>/data/reports/full_report_state.json`
- `users/<user>/data/reports/index/*.json`

So the Python service writes those same files. That keeps the rest of the system readable even though bootstrap is no longer executed by the TypeScript server.

## API

### `POST /api/bootstrap/start`

Starts an end-to-end bootstrap run.

Example payload:

```json
{
  "userId": "demo-user",
  "displayName": "Demo User",
  "accounts": {
    "Main": [
      {
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "shares": 10,
        "unitAvgBuyPrice": 190,
        "unitCurrency": "USD"
      },
      {
        "ticker": "NVDA",
        "exchange": "NASDAQ",
        "shares": 5,
        "unitAvgBuyPrice": 980,
        "unitCurrency": "USD"
      }
    ]
  },
  "guidance": {
    "AAPL": {
      "thesis": "Services growth and ecosystem stickiness should keep compounding value.",
      "horizon": "years",
      "addOn": "",
      "reduceOn": "",
      "notes": ""
    }
  }
}
```

### `GET /api/bootstrap/jobs/{user_id}/{job_id}`

Returns progress for the bootstrap job.

### `GET /api/bootstrap/jobs/{user_id}/{job_id}/result`

Returns the final generated strategies when the job is complete.

### `GET /api/bootstrap/strategies/{user_id}`

Returns all persisted ticker strategies for a user.

## Run locally

1. Fill in `agents/.env`
2. Install dependencies:

```bash
pip install -r agents/requirements.txt
```

3. Run:

```bash
uvicorn agents.main:app --reload --port 8090
```

## Suggested structure

The layout is intentionally flat inside each agent package so future agents are easy to add:

```text
agents/
├── bootstrap_agent/
│   ├── deep_agent.py
│   ├── prompts.py
│   ├── state.py
│   └── tools.py
├── app/
│   ├── server.py
│   ├── service.py
│   ├── storage.py
│   └── schemas.py
├── .env
├── requirements.txt
└── langgraph.json
```

That gives you one place per future agent package:

- `your_new_agent/deep_agent.py`
- `your_new_agent/prompts.py`
- `your_new_agent/tools.py`

The API and storage layers stay small and shared.

## Notes

- `OPENAI_API_KEY` and `DEEP_AGENT_MODEL` are required for the deep agent path.
- `DATABASE_URL` is included for future expansion, but the current implementation persists bootstrap state to the shared workspace files for maximum compatibility.
