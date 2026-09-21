import pytest
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient
from smweb.middleware import CachedStaticFiles


@pytest.mark.parametrize('name', ['app.html.before-fix', 'js/app.js.bak', 'js/app.js.bak.1', '.env.save', 'js/.hidden', 'app.html~', 'APP.HTML.BEFORE-FIX'])
def test_existing_backup_files_are_not_public(tmp_path, name):
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('private fixture', encoding='utf-8')
    app = Starlette(routes=[Mount('/static', CachedStaticFiles(directory=tmp_path))])
    with TestClient(app) as client:
        assert client.get('/static/' + name).status_code == 404
    assert target.is_file()  # Blocking access must not delete the backup.


def test_normal_asset_keeps_cache_and_content(tmp_path):
    (tmp_path / 'app.js').write_text('/* public */', encoding='utf-8')
    app = Starlette(routes=[Mount('/static', CachedStaticFiles(directory=tmp_path))])
    with TestClient(app) as client:
        response = client.get('/static/app.js?v=1')
        assert response.status_code == 200
        assert response.text == '/* public */'
        assert 'max-age=' in response.headers['cache-control']
