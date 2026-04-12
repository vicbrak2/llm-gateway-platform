from app.services.usage_repository import UsageRepository


def test_billing_summary_aggregates_usage(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = UsageRepository(db_path)
    repo.increment('client-a', capability='summarize', usage_date='2026-04-12')
    repo.increment('client-a', capability='summarize', usage_date='2026-04-12')
    repo.increment('client-a', capability='generate_json', usage_date='2026-04-13')
    repo.increment('client-b', capability='chat', usage_date='2026-04-13')

    summary = repo.billing_summary()
    total = {item.client_id: item.requests_total for item in summary.total_usage}
    by_cap = {(item.client_id, item.capability): item.requests_total for item in summary.usage_by_capability}
    by_day = {(item.client_id, item.usage_date): item.requests_total for item in summary.usage_by_day}

    assert total['client-a'] == 3
    assert total['client-b'] == 1
    assert by_cap[('client-a', 'summarize')] == 2
    assert by_cap[('client-a', 'generate_json')] == 1
    assert by_day[('client-a', '2026-04-12')] == 2
    assert by_day[('client-b', '2026-04-13')] == 1
