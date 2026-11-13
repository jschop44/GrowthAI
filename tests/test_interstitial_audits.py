import pytest
from backend.main import analyze_html


@pytest.mark.parametrize('heading', ['You are now leaving Disney.com', "You're leaving Disney", 'Access denied', 'Verify you are human', 'Redirecting...'])
def test_interstitials_are_not_scored_as_business_content(heading):
    with pytest.raises(ValueError, match='No audit score was assigned'):
        analyze_html('<html><title>Disney</title><h2>'+heading+'</h2></html>', 'https://disney.com/exit', 1)


def test_ordinary_content_discussing_external_links_is_not_rejected():
    report = analyze_html('<html><title>Disney experiences and entertainment</title><h1>Explore Disney</h1><p>You are now leaving is our external-link notice.</p></html>', 'https://disney.com', 1)
    assert isinstance(report['score'], int)


def test_rejected_document_is_not_saved_as_completed_or_learned(monkeypatch, tmp_path):
    from backend import main, learning_engine
    from fastapi.testclient import TestClient
    import httpx
    monkeypatch.setenv('GROWTHLENS_PRIVATE_KEY', 'acceptance-test-only')
    monkeypatch.setattr(main, 'DB', str(tmp_path / 'audits.sqlite'))
    main.init_db()
    monkeypatch.setattr(main, 'validate_url', lambda value: value)
    monkeypatch.setattr(main, 'robots_decision', lambda *args: ('allowed', 'Allowed'))
    monkeypatch.setattr(main, 'fetch_public', lambda *args: (httpx.Response(200, text='<h1>You are now leaving Disney.com</h1>'), 'https://disney.com/exit'))
    def no_learning(*args, **kwargs):
        raise AssertionError('Rejected page must not enter shared evidence memory')
    monkeypatch.setattr(learning_engine, 'store', no_learning)
    response = TestClient(main.app).post('/api/audits', json={'url':'https://disney.com/exit'}, headers={'X-GrowthLens-Key':'acceptance-test-only'})
    assert response.status_code == 422
    assert 'No audit score was assigned' in response.json()['detail']
    with main.database() as connection:
        row = connection.execute('SELECT status, score FROM audits ORDER BY id DESC LIMIT 1').fetchone()
    assert row['status'] == 'failed'
    assert row['score'] is None
