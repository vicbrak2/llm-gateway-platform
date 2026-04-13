from app.schemas import CapabilityRequest, ChatRequest, ChatMessage, PromptPolicyUpsert
from app.services.client_policy_service import ClientPolicyService
from app.services.prompt_policy_repository import PromptPolicyRepository
from app.services.prompt_policy_service import PromptPolicyService


def test_prompt_policy_applies_global_system_prompt(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = PromptPolicyRepository(db_path)
    service = PromptPolicyService(repo)
    service.upsert_policy(PromptPolicyUpsert(client_id='default', system_prompt='Always answer in Spanish.', style_rules='Be concise.'))
    request = ChatRequest(messages=[ChatMessage(role='user', content='hello')])
    updated = service.apply_policy('default', request)
    assert updated.messages[0].role == 'system'
    assert 'Always answer in Spanish.' in updated.messages[0].content
    assert 'Be concise.' in updated.messages[0].content


def test_prompt_policy_applies_capability_override(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    prompt_repo = PromptPolicyRepository(db_path)
    prompt_service = PromptPolicyService(prompt_repo)
    prompt_service.upsert_policy(PromptPolicyUpsert(client_id='default', capability='summarize', system_prompt='Summaries must be bullet-free.', content_rules='No markdown tables.'))
    client_policy_service = ClientPolicyService(prompt_policy_service=prompt_service)
    req, _ = client_policy_service.build_capability_request('default', 'summarize', CapabilityRequest(input='hello'))
    joined = '\n'.join(m.content for m in req.messages if m.role == 'system')
    assert 'Summaries must be bullet-free.' in joined
    assert 'No markdown tables.' in joined
