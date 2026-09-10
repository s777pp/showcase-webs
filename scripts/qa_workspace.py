"""Local browser regression checks; APIs are mocked, no production data is touched."""
import base64
import io
import json
import os
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


def run():
    png = io.BytesIO()
    Image.new('RGB', (100, 200), '#52d5ff').save(png, 'PNG')
    image = png.getvalue()
    base = os.environ.get('QA_BASE_URL', 'http://127.0.0.1:8091')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        signed_in = False
        def api(route):
            url = route.request.url
            if '/api/process/preview/' in url:
                tail = url.split('/preview/', 1)[1].split('/')
                if len(tail) > 1:
                    route.fulfill(content_type='image/png', body=image)
                else:
                    files = [{'name':f'demo_workshop/part_{i+1}.png','size':len(image),'url':f'/api/process/preview/{tail[0]}/{i}'} for i in range(5)]
                    route.fulfill(json={'ok':True,'files':files})
            elif '/api/builder/assets' in url:
                if route.request.method == 'POST':
                    route.fulfill(status=401,json={'ok':False,'msg':'Login required'})
                else:
                    route.fulfill(content_type='image/png',body=image)
            else:
                route.fulfill(json={'ok':True,'items':[],'topics':[],'available':False,'pro':False,'email':'qa@example.test' if signed_in else '', 'left':5})
        context.route('**/api/**', api)
        page = context.new_page()
        errors=[]
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base+'/ru/app')
        page.wait_for_timeout(900)
        assert page.locator('#processRoute [data-process-step]').count() == 4
        page.locator('#fileInput').set_input_files({'name':'source.png','mimeType':'image/png','buffer':image})
        page.wait_for_timeout(500)
        assert page.locator('#processPreflight.is-ready').count() == 1
        assert '100×200' in page.locator('#processPreflight').inner_text()
        page.locator('#processAdvanced summary').click()
        assert page.locator('#processAdvanced').evaluate('node => node.open')
        assert page.locator('#processSettingsCard').evaluate('node => node.scrollWidth <= node.clientWidth + 1')
        page.screenshot(path=str(Path(tempfile.gettempdir()) / 'showcase-usability-process.png'), full_page=True)
        page.locator('#btnClear').click()
        help_button = page.locator('#wmPreviewCard .sm-help__button')
        help_button.scroll_into_view_if_needed()
        page.wait_for_timeout(80)
        help_button.click()
        page.wait_for_timeout(120)
        assert page.locator('.sm-help__popup:not([hidden])').count() == 1
        page.keyboard.press('Escape')
        assert page.locator('.sm-help__popup:not([hidden])').count() == 0
        page.locator('[data-open-tool=builder]').first.click()
        page.locator('[data-add-layer=text]').click()
        page.locator('#builderText').fill('History sample')
        page.wait_for_timeout(500)
        page.locator('.builder-history button').nth(0).click()
        assert page.locator('#builderText').input_value() != 'History sample'
        page.locator('.builder-history button').nth(1).click()
        assert page.locator('#builderText').input_value() == 'History sample'
        page.locator('#builderMediaInput').set_input_files({'name':'demo.png','mimeType':'image/png','buffer':image})
        page.wait_for_timeout(1600)
        assert page.locator('#builderLayerList .builder-layer').count()==2
        page.locator('#builderCanvas').scroll_into_view_if_needed()
        page.screenshot(path=str(Path(tempfile.gettempdir()) / 'showcase-usability-builder.png'))
        assert 'сохранён' in page.locator('.builder-draft-status').inner_text()
        page.reload()
        page.locator('[data-open-tool=builder]').first.click()
        page.locator('.workspace-draft button').first.click()
        page.wait_for_timeout(1000)
        assert page.locator('#builderLayerList .builder-layer').count()==2
        page.locator('#builderLayerList [data-action=delete]').first.click()
        page.locator('.builder-history button').first.click()
        assert page.locator('#builderLayerList .builder-layer').count()==2
        page.locator('#builderLayerList [data-action=lock]').first.click()
        assert page.locator('#builderInspector input').first.is_disabled()
        page.locator('#builderLayerList [data-action=lock]').first.click()
        page.locator('#builderLayerList [data-action=duplicate]').first.click()
        assert page.locator('#builderLayerList .builder-layer').count()==3
        page.locator('#builderTemplates summary').click()
        page.locator('[data-builder-template=minimal]').click()
        assert page.locator('#builderLayerList .builder-layer').count()==5
        page.locator('[data-builder-backdrop=light]').click()
        assert 'active' in page.locator('[data-builder-backdrop=light]').get_attribute('class')
        page.locator('[data-open-tool=process]').first.click()
        page.evaluate('''async (base64) => {
          const blob=new Blob([Uint8Array.from(atob(base64),c=>c.charCodeAt(0))],{type:'image/png'});
          await ProcessResult.open({},'aaaaaaaaaaaaaaaaaaaaaaaa',[new File([blob],'demo.png',{type:'image/png'})]);
        }''',base64.b64encode(image).decode())
        page.locator('.workspace-result__toolbar button').nth(2).click()
        assert page.locator('.workspace-result__parts img').count()==5
        assert page.locator('.workspace-result__original img').count()==1
        assert page.locator('.workspace-result__files a').count()==5
        page.screenshot(path=str(Path(tempfile.gettempdir()) / 'showcase-usability-result.png'))
        for width in [390,1440]:
            page.set_viewport_size({'width':width,'height':1000})
            page.wait_for_timeout(300)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
        signed_in = True
        page.evaluate('''async () => {
          const files=Array.from({length:5},(_,i)=>({name:'demo_workshop/part_'+(i+1)+'.png',width:100,height:200,size:1000,format:'PNG',animated:false,issues:[]}));
          const report={status:'ready',file_count:5,group_count:1,failures:0,warnings:0,groups:[{name:'demo_workshop',mode:'workshop',status:'ready',checks:[],files}]};
          await ProcessResult.open({readiness:report},'aaaaaaaaaaaaaaaaaaaaaaaa',[]);
        }''')
        assert page.locator('#steamCheckResults #workspaceResult').count()==1
        page.wait_for_timeout(500)
        assert page.locator('#steamCheckUploadSteam').is_visible()
        page.locator('#steamCheckAgain').click()
        assert page.locator('#tab-process').evaluate('n=>n.classList.contains("active")')
        expected_templates={'ru':'Быстрые шаблоны','en':'Quick templates','de':'Schnellvorlagen','tr':'Hızlı şablonlar','fr':'Modèles rapides','uk':'Швидкі шаблони','es':'Plantillas rápidas','pt':'Modelos rápidos'}
        for language in ['ru','en','de','tr','fr','uk','es','pt']:
            page.goto(base+'/'+language+'/app')
            page.set_viewport_size({'width':390,'height':1000})
            assert page.locator('[data-process-step=files] b').inner_text().strip()
            page.locator('#processAdvanced summary').click()
            assert page.locator('#processSettingsCard').evaluate('node => node.scrollWidth <= node.clientWidth + 1'), language
            overflow = page.evaluate('''() => Array.from(document.querySelectorAll('body *')).filter(node => {
              const box = node.getBoundingClientRect();
              return box.right > innerWidth + 1 || box.left < -1;
            }).slice(0, 16).map(node => ({tag:node.tagName,id:node.id,cls:node.className,parent:node.parentElement?.className || node.parentElement?.id || '',text:(node.textContent || '').trim().slice(0,40),left:node.getBoundingClientRect().left,right:node.getBoundingClientRect().right}))''')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (language, overflow)
            page.locator('[data-open-tool=builder]').first.click()
            page.wait_for_timeout(200)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), language
            assert page.locator('.builder-history button').first.inner_text()
            actual_template=page.locator('#builderTemplates summary').inner_text().strip()
            assert actual_template.casefold()==expected_templates[language].upper().casefold(), (language,actual_template,expected_templates[language])
        assert not errors, errors
        print('Workspace QA passed: guided process, preflight, help, history, media draft restore, layer tools, templates, actual result comparison, mobile layout.')
        context.close()
        browser.close()


if __name__ == '__main__':
    run()
