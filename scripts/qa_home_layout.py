"""Local presentation checks. API and VRM calls are isolated from production."""
import os
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def run():
    base = os.environ.get('QA_BASE_URL', 'http://127.0.0.1:8091')
    output = Path(tempfile.gettempdir())
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080}, reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('sm_analytics_consent_v1','no')")
        context.route('**/api/**', lambda r: r.fulfill(json={'ok': True, 'items': [], 'topics': [], 'used': 0, 'limit': 5}))
        context.route('**/*.vrm*', lambda r: r.abort())
        context.route('**/hero-vrm.js*', lambda r: r.fulfill(content_type='application/javascript', body="const image=document.querySelector('.creator-scene__character');if(image)image.src=image.dataset.src;document.querySelector('.creator-scene').classList.add('is-vrm-fallback');"))
        page = context.new_page()
        for language in ['ru', 'en', 'de', 'tr', 'fr', 'uk', 'es', 'pt']:
            page.goto(base + '/' + language)
            page.locator('html:not(.home-is-loading)').wait_for(state='attached')
            page.evaluate('document.fonts.ready')
            for width in [390, 1440, 1920, 2560]:
                page.set_viewport_size({'width': width, 'height': 1080})
                page.wait_for_timeout(250)  # Shell's resize handler updates rail spacing.
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width)
                if width > 1180:
                    geometry = page.evaluate('''() => {
                        const title = document.querySelector('.hero h1').getBoundingClientRect();
                        const art = document.querySelector('.hero-studio').getBoundingClientRect();
                        const rects = [...document.querySelectorAll('.hero .echo-text__echo--front')].flatMap(n=>{
                            const r=document.createRange();r.selectNodeContents(n);return [...r.getClientRects()];
                        });
                        return {titleRight:title.right,artLeft:art.left,wordsRight:Math.max(...rects.map(r=>r.right))};
                    }''')
                    assert geometry['titleRight'] < geometry['artLeft'], (language, width, geometry)
                    assert geometry['wordsRight'] <= geometry['artLeft'], (language, width, geometry)
            if language == 'de':
                page.screenshot(path=str(output / 'showcase-home-german-wide.png'))
        # Real scroll reveal: containers must be transparent before cards appear.
        page.emulate_media(reduced_motion='no-preference')
        page.goto(base + '/ru')
        page.locator('html:not(.home-is-loading)').wait_for(state='attached')
        for selector in ['.q-grid', '.grid2 .triage-card']:
            assert page.locator(selector).evaluate("n=>getComputedStyle(n).backgroundColor") == 'rgba(0, 0, 0, 0)'
        for selector in ['.subc', '.q-card']:
            page.goto(base + '/ru')
            page.evaluate('window.scrollTo(0,0)')
            page.locator('html:not(.home-is-loading)').wait_for(state='attached')
            card = page.locator(selector).first
            expect(card).to_have_attribute('data-home-reveal', 'block')
            expect(card).to_have_css('opacity', '0')
            assert card.evaluate("n=>getComputedStyle(n).opacity") == '0', (selector, card.get_attribute('data-home-visible'), card.bounding_box())
            card.scroll_into_view_if_needed()
            expect(card).to_have_attribute('data-home-visible', 'true')
            page.wait_for_timeout(800)
            assert card.evaluate("n=>getComputedStyle(n).opacity") == '1'
            assert card.evaluate("n=>getComputedStyle(n).translate") == 'none'
        page.screenshot(path=str(output / 'showcase-home-card-reveal.png'))
        page.goto(base + '/ru/app')
        page.locator('#processAdvanced summary').click()
        for width in [390, 1440, 2560]:
            page.set_viewport_size({'width': width, 'height': 1080})
            page.wait_for_timeout(250)
            first = page.locator('#allModes').bounding_box()
            second = page.locator('#autoContrast').bounding_box()
            assert abs(first['y'] - second['y']) <= 2, (width, first, second)
            assert second['x'] > first['x'], (width, first, second)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#processSettingsCard').screenshot(path=str(output / 'showcase-horizontal-switches.png'))
        browser.close()
    print('Home layout QA passed: eight languages, four widths, text/art separation, transparent reveal and horizontal switches.')


if __name__ == '__main__':
    run()
