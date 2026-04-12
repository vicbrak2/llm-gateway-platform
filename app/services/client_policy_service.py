from __future__ import annotations

from fastapi import HTTPException

from app.schemas import ChatRequest, ClientPolicy
from app.services.client_policy_repository import ClientPolicyRepository


class ClientPolicyService:
    def __init__(self, repository: ClientPolicyRepository | None = None) -> None:
        self.repository = repository or ClientPolicyRepository()

    def get_policy(self, client_id: str) -> ClientPolicy:
        policy = self.repository.get_policy(client_id)
        if policy is None:
            raise HTTPException(status_code=403, detail='client policy not found')
        if not policy.enabled:
            raise HTTPException(status_code=403, detail='client is disabled')
        return policy

    def enforce_chat_policy(self, client_id: str, request: ChatRequest) -> tuple[ChatRequest, dict]:
        policy = self.get_policy(client_id)
        total_chars = sum(len(m.content) for m in request.messages)
        effective_strategy = request.strategy
        if request.strategy == 'balanced' and policy.default_strategy != 'balanced':
            effective_strategy = policy.default_strategy
        if effective_strategy not in policy.allowed_strategies:
            raise HTTPException(status_code=403, detail='strategy not allowed for client')
        if request.response_format not in policy.allowed_response_formats:
            raise HTTPException(status_code=403, detail='response format not allowed for client')
        if request.require_workflow and not policy.allow_workflows:
            raise HTTPException(status_code=403, detail='workflows not allowed for client')
        if total_chars > policy.max_input_chars:
            raise HTTPException(status_code=413, detail='input too large for client policy')
        adjusted_request = request.model_copy(update={'strategy': effective_strategy})
        runtime_policy = {
            'preferred_providers': policy.preferred_providers,
            'max_parallel_providers': policy.max_parallel_providers,
        }
        return adjusted_request, runtime_policy

    def list_policies(self) -> list[ClientPolicy]:
        return self.repository.list_policies()

    def upsert_policy(self, policy: ClientPolicy) -> ClientPolicy:
        return self.repository.upsert_policy(policy)
