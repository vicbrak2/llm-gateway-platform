# llm-gateway-platform

Production-ready starter for a multi-provider LLM gateway on Railway.

## Included

- FastAPI public API
- Orchestrator with `fast`, `balanced`, and `quality` strategies
- Parallel calls to OpenAI-compatible providers
- Redis cache
- n8n webhook trigger integration
- Structured logging with trace IDs
- Retries with exponential backoff
- Simple circuit breaker per provider
- Railway-ready deployment files
- GitHub Actions for compile and test checks

## Quick start

1. Copy `.env.example` to `.env`
2. Fill provider credentials and Redis URL
3. Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Test

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @example_chat_request.json
```

## Notes

- `fast` now waits for the first **successful** provider instead of the first completed task.
- Provider failures are retried according to the settings in `.env.example`.
- Circuit breaker state is kept in-process per provider.
