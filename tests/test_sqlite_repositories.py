from app.schemas import ClientPolicy
from app.services.client_policy_repository import ClientPolicyRepository
from app.services.usage_repository import UsageRepository


def test_client_policy_repository_upsert_and_get(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = ClientPolicyRepository(db_path)
    policy = ClientPolicy(client_id='client-x', enabled=True, plan='pro', default_strategy='quality', allowed_strategies=['quality'], allowed_response_formats=['json_object'], max_requests_per_minute=30, max_parallel_providers=2, allow_workflows=False, preferred_providers=['groq'], max_input_chars=5000)
    repo.upsert_policy(policy)
    fetched = repo.get_policy('client-x')
    assert fetched is not None
    assert fetched.client_id == 'client-x'
    assert fetched.default_strategy == 'quality'
    assert fetched.preferred_providers == ['groq']


def test_usage_repository_persists_counts(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = UsageRepository(db_path)
    repo.increment('client-a')
    repo.increment('client-a')
    repo.increment('client-b')
    usage = {item.client_id: item.requests_total for item in repo.list_usage()}
    assert usage['client-a'] == 2
    assert usage['client-b'] == 1
