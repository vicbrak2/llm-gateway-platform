from pathlib import Path

from app.services import vault_search


def test_search_finds_relevant_doc_by_keyword_overlap(tmp_path, monkeypatch):
    (tmp_path / 'general').mkdir()
    (tmp_path / 'general' / 'Arquitectura.md').write_text(
        '# Arquitectura\n\nEl sistema usa un gateway de canales y un agente IA central.', encoding='utf-8'
    )
    (tmp_path / 'general' / 'Roadmap.md').write_text(
        '# Roadmap\n\nFase 1: MVP. Fase 2: expansion de canales.', encoding='utf-8'
    )
    monkeypatch.setattr(vault_search, 'VAULT_DIR', tmp_path)
    vault_search.clear_cache()

    results = vault_search.search('¿cuál es la arquitectura del sistema?')
    assert results
    assert results[0].path == 'general/Arquitectura.md'
    vault_search.clear_cache()


def test_search_returns_empty_for_unrelated_query(tmp_path, monkeypatch):
    (tmp_path / 'x.md').write_text('# Arquitectura\n\nGateway de canales.', encoding='utf-8')
    monkeypatch.setattr(vault_search, 'VAULT_DIR', tmp_path)
    vault_search.clear_cache()

    results = vault_search.search('¿cuántos usuarios tengo registrados en el sistema?')
    assert results == []
    vault_search.clear_cache()


def test_search_returns_empty_when_vault_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_search, 'VAULT_DIR', tmp_path / 'does-not-exist')
    vault_search.clear_cache()

    assert vault_search.search('cualquier cosa') == []
    vault_search.clear_cache()


def test_real_bundled_vault_has_docs():
    # Sanity check against the actual bundled vault shipped in app/data/vault.
    vault_search.clear_cache()
    results = vault_search.search('arquitectura del agente omnicanal')
    vault_search.clear_cache()
    assert results, 'expected the bundled vault to contain architecture docs'
