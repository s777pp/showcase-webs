"""Presentation regression; external APIs mocked, no paid jobs or real uploads."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect



def open_tab(page, name):
    """Tools tabs may sit in a navigation group (static/js/nav-groups.js); open it first."""
    button = page.locator('#nav [data-tab="' + name + '"]')
    if not button.is_visible():
        trigger = page.locator('#nav .nav-group:has([data-tab="' + name + '"]) .nav-group__trigger')
        if trigger.count():
            trigger.click()
    button.click()

def run():
    base = os.environ.get('QA_BASE_URL', 'http://127.0.0.1:8091')
    output = Path('output/playwright')
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        context.add_init_script("localStorage.setItem('sm_analytics_consent_v1','no')")
        context.route('**/api/**', lambda r: r.fulfill(json={'ok':True,'items':[],'topics':[],'left':5,'used':0,'limit':5,'pro':False,'available':False}))
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        for language in ['ru','en','de','tr','fr','uk','es','pt']:
            page.goto(base + '/' + language + '/app')
            expect(page.locator('#composeFineSettings')).to_be_attached()
            # The generic task chooser is hidden on every tab since 2026-10-01 (tools-unified.css);
            # About > All tools and the tool strip replace it.
            chooser = page.locator('#toolTaskChooser')
            expect(chooser).to_be_hidden()
            open_tab(page, 'download')
            page.locator('#dlUrl').fill('https://example.com/my-media')
            for width in [390, 1440]:
                page.set_viewport_size({'width': width, 'height': 1000})
                open_tab(page, 'download')
                expect(page.locator('#tab-download .tu-guide')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language,width,'download')
                assert page.locator('#dlUrl').input_value() == 'https://example.com/my-media'
                expect(page.locator('#dlLink + .tool-next-step')).to_be_hidden()
                # Simulate the existing success/reset link contract, not a
                # provider job. Navigation must never fetch the output itself.
                page.evaluate("const a=document.getElementById('dlLink');a.href='/test-result.mp4';a.style.display='inline-block'")
                expect(page.locator('#dlLink + .tool-next-step')).to_be_visible()
                page.locator('#dlLink + .tool-next-step button').click()
                expect(page.locator('#tab-process')).to_have_class(__import__('re').compile(r'\bactive\b'))
                page.evaluate("document.getElementById('dlLink').style.display='none'")
                expect(page.locator('#dlLink + .tool-next-step')).to_be_hidden()
                for name in ['compose','download','convert','upscale','loop','hex','doctor','design-ai','steam','da','about']:
                    open_tab(page, name)
                    expect(page.locator('#tab-' + name)).to_have_class(__import__('re').compile(r'\bactive\b'))
                    page.wait_for_timeout(80)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language,width,name)
                    if language == 'ru':
                        page.screenshot(path=str(output / f'tool-{name}-{width}.png'),full_page=True)
            open_tab(page, 'compose')
            expect(page.locator('#composeFineSettings')).not_to_have_attribute('open','')
            assert page.locator('#composeGifEncoder').input_value() == 'gifski'
            page.locator('#composeFineSettings summary').click()
            expect(page.locator('#composeScale')).to_be_visible()
            page.locator('#composeScale').fill('125')
            assert page.locator('#composeScale').input_value() == '125'
            help_button = page.locator('#tab-compose .sm-help-heading .sm-help__button').first
            help_button.scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            help_button.click()
            expect(page.locator('#' + help_button.get_attribute('aria-controls'))).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#' + help_button.get_attribute('aria-controls'))).to_be_hidden()
            open_tab(page, 'steam')
            expect(page.locator('#steamCode')).to_be_hidden()
            page.locator('#steamManualInstructions summary').click()
            expect(page.locator('#btnCopyCode')).to_be_visible()
            page.locator('#steamMode').select_option('split')
            assert page.locator('#steamMode').input_value() == 'split'
            open_tab(page, 'convert')
            assert page.locator('#cvDrop').bounding_box()['y'] < page.locator('#cvTarget').bounding_box()['y']
            for target in ['builder','compose','upscale','steam','da','process']:
                # About > All tools routes to every tool (it replaced the task chooser).
                open_tab(page, 'about')
                page.locator('#tab-about .tu-tool[data-tool="' + target + '"]').click()
                expect(page.locator('#tab-' + target)).to_have_class(__import__('re').compile(r'\bactive\b'))
            assert page.locator('#dlUrl').input_value() == 'https://example.com/my-media'
        assert not errors, errors
        browser.close()
    print('Tool clarity QA passed: 11 tabs, 8 languages, desktop/mobile, help, advanced controls, manual Steam route.')


if __name__ == '__main__':
    run()
