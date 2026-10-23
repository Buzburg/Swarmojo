"""ROMS 1.4 and offline utility integrations preserve project and origin boundaries."""
import hashlib
import json
from pathlib import Path

from tests.test_desktop import desktop, project
from app.db import init_database, get_connection


def test_task_brief_uses_only_selected_current_project_sources(desktop, tmp_path, monkeypatch):
    client, service, calls = desktop
    scope = project(client)
    other = project(client, 'Other project')
    db = tmp_path / 'knowledge.db'
    init_database(db)
    monkeypatch.setattr('app.config.DB_PATH', db)
    with get_connection(db) as conn:
        conn.execute("INSERT INTO okf_registry(doc_id,title,checksum) VALUES ('policy.md','Deployment policy',?)", ('a'*64,))
        conn.execute("INSERT INTO fts_chunks(chunk_id,doc_id,content) VALUES (1,'policy.md','Deployment requires operator approval.')")
    url = f'/api/projects/{scope}/knowledge'
    result = client.post(url, json={'query':'deployment'}).json()['sources'][0]
    assert result['chunk_id'] == 1
    selected = client.post(url+'-selection', json={'query':'deployment','source_id':result['source_id'],
                         'indexed_chunk_sha256':result['indexed_chunk_sha256']})
    assert selected.status_code == 200
    source_id = selected.json()['sources'][0]['id']
    body = {'task':'Plan deployment','constraints':'No execution','source_ids':[source_id]}
    response = client.post(url+'-brief', json=body)
    assert response.status_code == 200, response.text
    assert 'operator approval' in response.json()['markdown'] and not response.json()['persisted']
    assert client.post(f'/api/projects/{other}/knowledge-brief', json=body).status_code == 409
    assert client.post(url+'-brief', json={**body,'source_ids':[source_id,source_id]}).status_code == 409
    with get_connection(db) as conn:
        conn.execute("UPDATE fts_chunks SET content='Changed deployment procedure' WHERE chunk_id=1")
    assert client.post(url+'-brief', json=body).status_code == 409
    assert not calls
    assert not service.conversation(scope)['approvals']


def test_utility_downloads_are_pinned_attachments_not_desktop_scripts(desktop):
    client, _, _ = desktop
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root/'app/desktop_assets/utilities/PROVENANCE.json').read_text())
    for repo in manifest:
        for path, digest in repo['files'].items():
            assert hashlib.sha256((root/path).read_bytes()).hexdigest() == digest
        name = repo['repository'].rsplit('/',1)[-1] + '.html'
        response = client.get('/utilities/' + name)
        assert response.status_code == 200
        assert response.headers['Content-Disposition'].startswith('attachment;')
        assert response.headers['Content-Security-Policy'] == "sandbox; default-src 'none'"
        assert "connect-src 'none'" in response.text
        assert response.content == (root/'app/desktop_assets/utilities'/name).read_bytes()
    assert client.get('/utilities/desktop.js').status_code == 404
    assert client.get('/utilities/PROVENANCE.json').status_code == 404
