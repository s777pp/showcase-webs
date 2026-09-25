"""Local presentation checks. API and VRM calls are isolated from production."""
import os
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright


def run():
    base = os.environ.get('QA_BASE_URL', 'http://127.0.0.1:8091')
    output = Path(tempfile.gettempdir())
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080}, reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('sm_analytics_consent_v1','no')")
        context.route('**/api/**', lambda r: r.fulfill(json={'ok': True, 'items': [], 'topics': [], 'used': 0, 'limit': 5}))
        context.route('**/*.vrm*', lambda r: r.abort())
        # Without the model the hero releases through the fallback path.
        page = context.new_page()
        for language in ['ru', 'en', 'de', 'tr', 'fr', 'uk', 'es', 'pt']:
            page.goto(base + '/' + language)
            page.locator('html:not(.home-is-loading)').wait_for(state='attached')
            page.evaluate('document.fonts.ready')
            for width in [390, 1440, 1920, 2560]:
                page.set_viewport_size({'width': width, 'height': 1080})
                page.wait_for_timeout(250)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, width)
                geometry = page.evaluate('''() => {
                    const box = s => document.querySelector(s).getBoundingClientRect();
                    const head = box('.ss-head'), title = box('.home-title'), actions = box('.home-actions');
                    const cards = box('.home-features');
                    const lefts = ['.home-title', '.home-lead', '.home-actions', '.home-telegram', '.home-features']
                        .map(s => box(s).left);
                    return {headBottom: head.bottom, titleTop: title.top, actionsBottom: actions.bottom,
                            cardsTop: cards.top, cardsBottom: cards.bottom, height: innerHeight,
                            leftSpread: Math.max(...lefts) - Math.min(...lefts), titleLeft: title.left,
                            rightSpread: (() => { const rs = [box('.home-actions').right, box('.home-telegram').right,
                                box('.home-features li:last-child').right]; return Math.max(...rs) - Math.min(...rs); })()};
                }''')
                assert geometry['titleTop'] >= geometry['headBottom'], (language, width, geometry)
                assert geometry['cardsTop'] >= geometry['actionsBottom'], (language, width, geometry)
                if width > 820:
                    assert geometry['cardsBottom'] <= geometry['height'], (language, width, geometry)
                    # One left edge for the whole copy column, on the owner's 7.75vw line.
                    assert geometry['leftSpread'] <= 1.5, (language, width, geometry)
                    assert abs(geometry['titleLeft'] - max(24, width * .0775)) <= 1.5, (language, width, geometry)
                    # Buttons, Telegram offer and cards end on one right edge too.
                    assert geometry['rightSpread'] <= 2, (language, width, geometry)
            if language == 'de':
                page.screenshot(path=str(output / 'showcase-home-german-wide.png'))
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
    print('Home layout QA passed: eight languages, four widths, header/title/actions/cards separation and horizontal switches.')


if __name__ == '__main__':
    run()
