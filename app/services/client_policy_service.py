from __future__ import annotations

from fastapi import HTTPException

from app.schemas import CapabilityRequest, ChatMessage, ChatRequest, ClientPolicy
from app.services.client_policy_repository import ClientPolicyRepository
from app.services.prompt_policy_service import PromptPolicyService


class ClientPolicyService:
    def __init__(self, repository: ClientPolicyRepository | None = None, prompt_policy_service: PromptPolicyService | None = None) -> None:
        self.repository = repository or ClientPolicyRepository()
        self.prompt_policy_service = prompt_policy_service or PromptPolicyService()

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
        adjusted_request = self.prompt_policy_service.apply_policy(client_id, adjusted_request, capability=None)
        runtime_policy = {
            'preferred_providers': policy.preferred_providers,
            'max_parallel_providers': policy.max_parallel_providers,
        }
        return adjusted_request, runtime_policy

    def build_capability_request(self, client_id: str, capability: str, request: CapabilityRequest) -> tuple[ChatRequest, dict]:
        policy = self.get_policy(client_id)
        if capability not in policy.allowed_capabilities:
            raise HTTPException(status_code=403, detail='capability not allowed for client')
        capability_map = {
            'summarize': {'strategy': policy.default_strategy, 'response_format': 'text', 'require_workflow': False, 'system': 'Summarize the user input clearly and concisely.'},
            'extract': {'strategy': 'balanced', 'response_format': 'text', 'require_workflow': False, 'system': 'Extract the most relevant entities and facts from the user input.'},
            'generate_json': {'strategy': 'quality', 'response_format': 'json_object', 'require_workflow': False, 'system': 'Return a structured JSON object for the user input.'},
            'route_workflow': {'strategy': 'balanced', 'response_format': 'text', 'require_workflow': True, 'system': 'Prepare the request to be routed to a workflow and summarize the intended action.'},
        }
        if capability not in capability_map:
            raise HTTPException(status_code=404, detail='capability not found')
        config = capability_map[capability]
        chat_request = ChatRequest(
            messages=[
                ChatMessage(role='system', content=config['system']),
                ChatMessage(role='user', content=request.input),
            ],
            strategy=config['strategy'],
            trace_id=request.trace_id,
            context=request.context,
            require_workflow=config['require_workflow'],
            response_format=config['response_format'],
        )
        chat_request, runtime_policy = self.enforce_chat_policy(client_id, chat_request)
        chat_request = self.prompt_policy_service.apply_policy(client_id, chat_request, capability=capability)
        return chat_request, runtime_policy

    def list_policies(self) -> list[ClientPolicy]:
        return self.repository.list_policies()

    def upsert_policy(self, policy: ClientPolicy) -> ClientPolicy:
        return self.repository.upsert_policy(policy)
