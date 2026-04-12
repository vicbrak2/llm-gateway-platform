# llm-gateway-platform

Production-ready starter for a multi-provider LLM gateway on Railway.

## Included

- FastAPI public API
- Orchestrator with `fast`, `balanced`, and `quality` strategies
- Parallel calls to OpenAI-compatible providers
- Redis cache
- n8n webhook trigger integration
- Structured logging with trace IDs
- Secret resolution from environment, with optional Infisical fallback
- Railway-ready deployment files

## Quick start

1. Copy `.env.example` to `.env`
2. Fill provider credentials and Redis URL
3. Run locally:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Test:

```bash
curl http://localhost:8000/health
```
