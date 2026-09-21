"""Exercise the redesigned workspace in a real browser with local, mocked APIs.

Serve the repository on QA_BASE_URL (default localhost:8091), mapping /<lang>/app
to static/app.html. No account, processing job, or upload reaches production.
"""
import io
import os
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image
from playwright.sync_api import sync_playwright, expect


def run():
    stream = io.BytesIO()
    Image.new('RGB', (900, 1200), '#256a85').save(stream, 'PNG')
    image = stream.getvalue()
    archive_stream = io.BytesIO()
    with zipfile.ZipFile(archive_stream, 'w') as archive:
        archive.writestr('showcase_split/part_1.png', image)
        archive.writestr('showcase_split/part_2.png', image)
    archive_bytes = archive_stream.getvalue()
    base = os.environ.get('QA_BASE_URL', 'http://127.0.0.1:8091')
    output = Path(tempfile.gettempdir())
    languages = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt']
    submitted = []
    catalog_pages = []

    def api(route):
        path = route.request.url.split('/api/', 1)[1]
        if path == 'assets/uploads':
            route.fulfill(status=401, json={'ok': False, 'msg': 'Login required'})
        elif path == 'builder/assets':
            route.fulfill(status=401, json={'ok': False, 'msg': 'Login required'})
        elif path == 'process/start':
            submitted.append(route.request.post_data_buffer)
            route.fulfill(json={'ok': True, 'job_id': 'a' * 32})
        elif path.startswith('process/status/'):
            route.fulfill(json={'ok': True, 'status': 'done', 'processed': 1, 'readiness': {
                'status': 'ready', 'group_count': 1, 'file_count': 2, 'failures': 0, 'warnings': 0,
                'groups': [{
                    'name': 'showcase_split', 'mode': 'split', 'status': 'ready',
                    'checks': [{'id': check, 'state': 'pass'} for check in
                               ['format', 'geometry', 'weight', 'animation', 'sync', 'hex21', 'set', 'naming']],
                    'files': [
                        {'name': 'part_1.png', 'format': 'PNG', 'width': 506, 'height': 422,
                         'size': len(image), 'animated': False, 'issues': []},
                        {'name': 'part_2.png', 'format': 'PNG', 'width': 100, 'height': 422,
                         'size': len(image), 'animated': False, 'issues': []}
                    ]
                }]
            }})
        elif path.startswith('process/download/'):
            route.fulfill(content_type='application/zip', body=archive_bytes,
                          headers={'Content-Disposition': 'attachment; filename="showcase.zip"'})
        elif path.startswith('process/preview/'):
            if path.count('/') > 2:
                route.fulfill(content_type='image/png', body=image)
            else:
                route.fulfill(json={'ok': True, 'files': [
                    {'name': 'showcase_split/part_1.png', 'size': len(image), 'url': '/api/process/preview/' + 'a' * 32 + '/0'},
                    {'name': 'showcase_split/part_2.png', 'size': len(image), 'url': '/api/process/preview/' + 'a' * 32 + '/1'}]})
        elif path == 'stats':
            route.fulfill(json={'today': 0, 'total': 0})
        elif path.startswith('steam/backgrounds?'):
            query = parse_qs(urlsplit(route.request.url).query)
            page_index = int(query.get('page', ['0'])[0])
            catalog_pages.append(page_index)
            numbers = range(1, 25) if page_index == 0 else (range(25, 33) if page_index == 1 else [])
            animated = query.get('asset', [''])[0] == 'animated_background'
            route.fulfill(json={'ok': True, 'items': [
                {'appid': 1, 'defid': number + (1000 if animated else 0), 'name': 'Steam background ' + str(number),
                 'image': '/static/img/hero-creator-cyberpunk.png',
                 'buy_url': ('https://store.steampowered.com/points/shop/app/1/reward/' + str(number + 1000)
                             if animated else
                             'https://steamcommunity.com/market/listings/753/1-Steam%20background%20' + str(number))}
                for number in numbers]})
        else:
            route.fulfill(json={'ok': True, 'items': [], 'topics': [], 'available': False,
                                'pro': False, 'is_pro': False, 'email': '', 'left': 5,
                                'used': 0, 'limit': 5})

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('sm_analytics_consent_v1','no')")
        context.add_init_script('''
            window.__qaBridgeMessages = [];
            window.addEventListener('message', event => {
              const message = event.data || {};
              if (event.source !== window || event.origin !== location.origin || message.source !== 'SSH_SITE' || message.type !== 'REQUEST') return;
              window.__qaBridgeMessages.push(message.payload);
              const reply = message.payload?.type === 'PING' ? {ok:true, version:'1.0.3'} : {ok:true};
              window.postMessage({source:'SSH_EXTENSION', type:'RESPONSE', requestId:message.requestId, reply}, location.origin);
            });
        ''')
        context.route('**/api/**', api)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/ru/app')
        expect(page.locator('#drop strong')).to_have_text('Выбрать файл')
        expect(page.locator('#btnRun')).to_be_disabled()
        expect(page.locator('#btnCancelProcess')).to_be_hidden()
        page.wait_for_timeout(900)  # Legacy delayed translation must not replace the upload UI.
        expect(page.locator('#drop .editor-icon')).to_have_count(1)
        page.locator('#drop').focus()
        with page.expect_file_chooser() as chooser:
            page.keyboard.press('Enter')
        chooser.value.set_files({'name': 'portrait.png', 'mimeType': 'image/png', 'buffer': image})
        expect(page.locator('#processPreflight')).to_have_class('process-preflight is-ready')
        expect(page.locator('#btnRun')).to_be_enabled()
        for mode in ['featured', 'split', 'workshop']:
            page.locator('.mode[data-mode=' + mode + ']').click()
            expect(page.locator('.mode[data-mode=' + mode + ']')).to_have_attribute('aria-pressed', 'true')
            assert page.locator('.editor-preview-sample i:visible').count() == 0  # Real file preview replaces the sample.
            assert page.evaluate('state.mode') == mode
        page.locator('#processRotateRight').click()
        expect(page.locator('#processRotationAngle')).to_have_text('90°')
        page.locator('#processAdvanced summary').click()
        page.locator('#fps').select_option('18')
        page.locator('#gifEncoder').select_option('gifski')
        page.locator('[data-mode=split]').click()
        with page.expect_download(timeout=15000) as automatic_zip:
            page.locator('#btnRun').click()
        assert automatic_zip.value.suggested_filename.endswith('.zip')
        expect(page.locator('#workspaceResult')).to_be_visible(timeout=15000)
        expect(page.locator('.workspace-result-modal')).to_be_visible()
        expect(page.locator('.workspace-result-modal__dialog')).to_have_attribute('role', 'dialog')
        assert len(submitted) == 1
        payload = submitted[0].decode('latin1')
        for field, value in [('mode', 'split'), ('fps', '18'), ('gif_encoder', 'gifski'), ('rotations', '[90]')]:
            assert 'name="' + field + '"\r\n\r\n' + value in payload, field
        expect(page.locator('#workspaceResult .workspace-result__parts img')).to_have_count(2)
        expect(page.locator('#workspaceResult .workspace-result__download')).to_have_attribute('href', '/api/process/download/' + 'a' * 32)
        expect(page.locator('.workspace-result__readiness .steam-check__file-report')).to_have_count(2)
        expect(page.locator('.workspace-result__readiness')).to_contain_text('506×422')
        expect(page.locator('#steamCheckAutoUpload')).to_be_visible()
        expect(page.locator('#steamCheckUploadSteam')).to_be_visible()
        assert page.locator('.steam-check__result-actions a').count() == 0
        page.locator('#steamCheckAutoUpload').click()
        expect(page.locator('#steamCheckExtensionNote')).to_contain_text('Очередь автоматической загрузки')
        automatic_payload = page.evaluate("window.__qaBridgeMessages.find(message => message.type === 'START_AUTO_UPLOAD')")
        assert automatic_payload['mode'] == 'split'
        assert [item['fileName'] for item in automatic_payload['items']] == ['part_1.png', 'part_2.png']
        assert all(item['fileBase64'].startswith('data:image/png;base64,') for item in automatic_payload['items'])
        assert page.locator('#workspaceResult').evaluate("node => !node.closest('#tab-process')")
        page.screenshot(path=str(output / 'showcase-editor-result-modal.png'))
        page.set_viewport_size({'width': 390, 'height': 844})
        expect(page.locator('.workspace-result-modal__dialog')).to_be_visible()
        page.screenshot(path=str(output / 'showcase-editor-result-modal-mobile.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1')
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('.workspace-result-modal__close').click()
        expect(page.locator('.workspace-result-modal')).to_have_count(0)
        page.locator('#btnClear').click()

        page.locator('#nav button[data-tab=steam]').click()
        expect(page.locator('#steamExtensionPicker')).to_be_enabled()
        expect(page.locator('#steamExtensionUpload')).to_be_enabled()
        page.locator('#steamExtensionPicker').click()
        expect(page.locator('#steamExtensionLaunchStatus')).to_contain_text('Выбор файлов открыт')
        assert page.evaluate("window.__qaBridgeMessages.find(message => message.type === 'OPEN_AUTO_UPLOADER').mode") in ('workshop', 'featured', 'split')
        page.screenshot(path=str(output / 'showcase-editor-steam-extension.png'))
        page.locator('#nav button[data-tab=process]').click()
        page.locator('#fileInput').set_input_files({'name': 'empty.png', 'mimeType': 'image/png', 'buffer': b''})
        expect(page.locator('#processPreflight')).to_have_class('process-preflight is-blocked')
        expect(page.locator('#btnRun')).to_be_disabled()
        page.locator('#btnClear').click()

        page.locator('[data-open-tool=builder]').first.click()
        expect(page.locator('#builderStart')).to_be_visible()
        motion = page.locator('.builder-stage > .builder-motion-panel')
        expect(motion).to_have_count(1)
        motion.locator('summary').click()
        assert motion.bounding_box()['width'] > 500
        assert motion.locator('[data-motion-i="seams"]').evaluate('node => node.getBoundingClientRect().height < 80')
        motion.screenshot(path=str(output / 'showcase-editor-motion-panel.png'))
        expect(page.locator('#builderExport')).to_be_disabled()
        page.locator('[data-add-layer=text]').click()
        expect(page.locator('#builderStart')).to_be_hidden()
        expect(page.locator('#builderInspector')).to_be_visible()
        expect(page.locator('.builder-layers #builderText')).to_be_visible()
        page.locator('#builderText').fill('TEST SHOWCASE')
        page.locator('[data-builder-mode=split]').click()
        page.locator('#builderExport').click()
        expect(page.locator('#tab-process')).to_have_class(re.compile(r'\bactive\b'), timeout=15000)
        expect(page.locator('#fileList .process-file')).to_have_count(1)
        assert page.evaluate('state.mode') == 'split'
        assert page.evaluate('state.files[0].type') == 'image/png'
        expect(page.locator('#wmCanvas')).to_be_visible()

        for language in languages:
            page.goto(base + '/' + language + '/app')
            page.wait_for_timeout(250)
            for width in [360, 768, 1440, 2328]:
                page.set_viewport_size({'width': width, 'height': 1000})
                page.wait_for_timeout(100)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width, 'process')
            mismatch = page.evaluate('''() => [...document.querySelectorAll('[data-editor-copy]')]
                .filter(n => n.textContent !== WorkspaceEditorCopy(n.dataset.editorCopy)).map(n=>n.dataset.editorCopy)''')
            assert not mismatch, (language, mismatch)
            page.locator('[data-open-tool=builder]').first.click()
            expect(page.locator('#builderStart')).to_be_visible()
            for width in [360, 768, 1440, 2328]:
                page.set_viewport_size({'width': width, 'height': 1000})
                page.wait_for_timeout(100)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width, 'builder')
            page.locator('[data-add-layer=effect]').click()
            expect(page.locator('#builderEffectControls')).to_be_visible()
            expect(page.locator('.editor-effect-options')).not_to_have_attribute('open', '')
            page.locator('#builderEffectColor').fill('#25ddbb')
            page.locator('.editor-effect-options summary').click()
            expect(page.locator('#bmDepth')).to_be_visible()
            page.set_viewport_size({'width': 360, 'height': 1000})
            page.locator('[data-editor-jump=edit]').click()
            assert page.locator('#builderInspector').bounding_box()['y'] >= 0
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, 'inspector')
        # The catalogue fills the canvas column, with readable thumbnails at every width.
        page.goto(base + '/ru/app')
        page.locator('[data-open-tool=builder]').first.click()
        page.locator('#builderSteamBackgrounds').click()
        expect(page.locator('#builderCatalogGrid button')).to_have_count(48)
        expect(page.locator('#builderCatalogSearch')).to_be_focused()
        page.locator('#builderCatalogGrid').evaluate('node => { node.scrollTop = node.scrollHeight; node.dispatchEvent(new Event("scroll")); }')
        expect(page.locator('#builderCatalogGrid button')).to_have_count(64)
        assert 1 in catalog_pages
        for width in [360, 768, 1440, 1920, 2328]:
            page.set_viewport_size({'width': width, 'height': 1000})
            page.wait_for_timeout(100)
            assert page.locator('#builderCatalogGrid button').first.bounding_box()['width'] >= 200, width
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, 'catalogue')
            if width == 2328:
                assert page.locator('.main').bounding_box()['width'] > 1900
        page.evaluate('window.scrollTo(0, 0)')
        page.screenshot(path=str(output / 'showcase-editor-wide-catalog.png'))
        page.keyboard.press('Escape')
        expect(page.locator('#builderCatalog')).to_be_hidden()
        expect(page.locator('#builderSteamBackgrounds')).to_be_focused()
        page.locator('#builderSteamBackgrounds').click()
        page.locator('#builderCatalogGrid button').first.click()
        expect(page.locator('#builderCatalog')).to_be_hidden()
        expect(page.locator('#builderLayerName')).to_have_value('Steam background 1')
        buy_background = page.locator('#builderBuyBackground')
        expect(buy_background).to_be_visible()
        expect(buy_background).to_have_text('Купить на торговой площадке')
        expect(buy_background).to_have_attribute('href', 'https://steamcommunity.com/market/listings/753/1-Steam%20background%201')
        expect(buy_background).to_have_attribute('target', '_blank')
        page.screenshot(path=str(output / 'showcase-editor-purchase.png'), full_page=True)
        page.locator('#builderSteamBackgrounds').click()
        expect(page.locator('#builderCatalogGrid button')).to_have_count(48)
        page.locator('#builderCatalogGrid button').nth(24).click()
        expect(buy_background).to_have_text('Купить за очки Steam')
        expect(buy_background).to_have_attribute('href', 'https://store.steampowered.com/points/shop/app/1/reward/1001')
        assert not errors, errors
        page.goto(base + '/ru/app')
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.screenshot(path=str(output / 'showcase-editor-process.png'), full_page=True)
        page.locator('[data-open-tool=builder]').first.click()
        page.screenshot(path=str(output / 'showcase-editor-builder.png'), full_page=True)
        # Inspect a populated editor too, with an existing local site asset.
        sample = Path(__file__).resolve().parents[1] / 'static/img/hero-creator-cyberpunk.png'
        page.locator('[data-add-layer=background]').click()
        page.locator('#builderMediaInput').set_input_files(str(sample))
        expect(page.locator('#builderElementCount')).to_have_text('1')
        page.locator('[data-add-layer=text]').click()
        page.locator('#builderText').fill('МОЯ ВИТРИНА')
        expect(page.locator('#builderElementCount')).to_have_text('2')
        page.wait_for_timeout(400)
        page.screenshot(path=str(output / 'showcase-editor-builder-filled.png'), full_page=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('[data-editor-jump=canvas]').click()
        page.screenshot(path=str(output / 'showcase-editor-builder-mobile.png'), full_page=True)
        page.locator('[data-open-tool=process]').first.click()
        page.locator('#fileInput').set_input_files(str(sample))
        expect(page.locator('#wmCanvas')).to_be_visible()
        page.screenshot(path=str(output / 'showcase-editor-process-mobile.png'), full_page=True)
        assert not errors, errors
        browser.close()
    print('Editor QA passed: upload, preview, rotation, submitted options, ZIP result, Builder export, 8 languages, 4 widths; large Steam catalogue, keyboard close and selection.')


if __name__ == '__main__':
    run()
