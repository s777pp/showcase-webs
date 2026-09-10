import io
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from smweb.routers import process


def client_for(monkeypatch, tmp_path, job=None):
    archive = tmp_path / 'output.zip'
    png = io.BytesIO()
    Image.new('RGB', (10, 20), 'cyan').save(png, format='PNG')
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('demo_workshop/part_1.png', png.getvalue())
        z.writestr('demo_workshop/full_original.png', png.getvalue())
        z.writestr('debug.txt', 'private diagnostic')
    monkeypatch.setattr(process, '_job_get', lambda _: job or {'status': 'done', 'zip_path': str(archive), 'user_key': 'owner'})
    monkeypatch.setattr(process, '_auth_user', lambda req: {'id': req.headers.get('x-test-user', '')})
    app = FastAPI()
    app.include_router(process.router)
    return TestClient(app), archive, png.getvalue()


def test_preview_reuses_owner_check_and_only_exposes_final_images(monkeypatch, tmp_path):
    client, archive, png = client_for(monkeypatch, tmp_path)
    url = '/api/process/preview/' + 'a' * 24
    assert client.get(url).status_code == 404
    assert client.get(url + '/0', headers={'x-test-user': 'other'}).status_code == 404
    headers = {'x-test-user': 'owner'}
    manifest = client.get(url, headers=headers)
    assert manifest.status_code == 200
    assert [x['name'] for x in manifest.json()['files']] == ['demo_workshop/part_1.png']
    image = client.get(manifest.json()['files'][0]['url'], headers=headers)
    assert image.content == png
    assert image.headers['cache-control'] == 'private, no-store'
    assert image.headers['content-type'] == 'image/png'
    assert client.get(url + '/1', headers=headers).status_code == 404
    assert client.get(url + '/2', headers=headers).status_code == 404
    assert client.get(url + '/-1', headers=headers).status_code == 404
    archive.unlink()
    assert client.get(url, headers=headers).status_code == 410


def test_preview_rejects_excessive_archives(monkeypatch, tmp_path):
    client, archive, _ = client_for(monkeypatch, tmp_path)
    with zipfile.ZipFile(archive, 'w') as z:
        for i in range(501):
            z.writestr(str(i) + '/part_1.png', b'x')
    response = client.get('/api/process/preview/' + 'a' * 24, headers={'x-test-user': 'owner'})
    assert response.status_code == 410
