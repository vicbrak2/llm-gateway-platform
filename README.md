# llm-gateway-platform

Starter de gateway multi-provider para LLMs en Railway.

## Incluye
- FastAPI
- Orquestación `fast`, `balanced`, `quality`
- Cache Redis
- Integración n8n
- Retries + backoff
- Circuit breaker simple
- Provider registry + routing policy
- Health extendido
- GitHub Actions para compile y tests

## Endpoints
- `GET /health`
- `POST /v1/chat/completions`
- `POST /v1/workflows/trigger`
