from __future__ import annotations

from app.schemas import ChatMessage, ChatRequest, PromptPolicy, PromptPolicyUpsert
from app.services.prompt_policy_repository import PromptPolicyRepository


class PromptPolicyService:
    def __init__(self, repository: PromptPolicyRepository | None = None) -> None:
        self.repository = repository or PromptPolicyRepository()

    def list_policies(self, client_id: str) -> list[PromptPolicy]:
        return self.repository.list_policies(client_id)

    def upsert_policy(self, policy: PromptPolicyUpsert) -> PromptPolicy:
        return self.repository.upsert_policy(policy)

    def apply_policy(self, client_id: str, request: ChatRequest, capability: str | None = None) -> ChatRequest:
        policy = self.repository.resolve_policy(client_id, capability)
        if not policy:
            return request
        system_parts = [policy.system_prompt]
        if policy.style_rules:
            system_parts.append(f'Style rules: {policy.style_rules}')
        if policy.content_rules:
            system_parts.append(f'Content rules: {policy.content_rules}')
        policy_message = ChatMessage(role='system', content='\n'.join(system_parts))
        return request.model_copy(update={'messages': [policy_message] + request.messages})
