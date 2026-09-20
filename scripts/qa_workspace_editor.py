"""Exercise the redesigned workspace in a real browser with local, mocked APIs.

Serve the repository on QA_BASE_URL (default localhost:8091), mapping /<lang>/app
to static/app.html. No account, processing job, or upload reaches production.
"""
import io
import os
import re
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright, expect


def run():
    stream = io.BytesIO()
    Image.new('RGB', (900, 1200), '#256a85').save(stream, 'PNG')
    image = stream.getvalue()
    base = os.environ.get('QA_BASE_URL', 'http://127.0.0.1:8091')
    output = Path(tempfile.gettempdir())
    languages = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt']
    submitted = []

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
            route.fulfill(json={'ok': True, 'items': [
                {'appid': 1, 'defid': number, 'name': 'Steam background ' + str(number),
                 'image': '/static/img/hero-creator-cyberpunk.png'}
                for number in range(1, 9)]})
        else:
            route.fulfill(json={'ok': True, 'items': [], 'topics': [], 'available': False,
                                'pro': False, 'is_pro': False, 'email': '', 'left': 5,
                                'used': 0, 'limit': 5})

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('sm_analytics_consent_v1','no')")
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
        page.locator('#btnRun').click()
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
        assert page.locator('#workspaceResult').evaluate("node => !node.closest('#tab-process')")
        page.screenshot(path=str(output / 'showcase-editor-result-modal.png'))
        page.locator('.workspace-result-modal__close').click()
        expect(page.locator('.workspace-result-modal')).to_have_count(0)
        page.locator('#btnClear').click()
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
                page.wait_for_function('document.documentElement.scrollWidth <= innerWidth', timeout=2000)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width, 'process')
            mismatch = page.evaluate('''() => [...document.querySelectorAll('[data-editor-copy]')]
                .filter(n => n.textContent !== WorkspaceEditorCopy(n.dataset.editorCopy)).map(n=>n.dataset.editorCopy)''')
            assert not mismatch, (language, mismatch)
            page.locator('[data-open-tool=builder]').first.click()
            expect(page.locator('#builderStart')).to_be_visible()
            for width in [360, 768, 1440, 2328]:
                page.set_viewport_size({'width': width, 'height': 1000})
                page.wait_for_function('document.documentElement.scrollWidth <= innerWidth', timeout=2000)
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
        expect(page.locator('#builderCatalogGrid button')).to_have_count(8)
        expect(page.locator('#builderCatalogSearch')).to_be_focused()
        for width in [360, 768, 1440, 1920, 2328]:
            page.set_viewport_size({'width': width, 'height': 1000})
            page.wait_for_function('document.documentElement.scrollWidth <= innerWidth', timeout=2000)
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
