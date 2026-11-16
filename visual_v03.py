"""Optional mobile smoke test: cd project; PYTHONPATH=. python tests/visual_v03.py"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from fastapi.testclient import TestClient
import server
BASE=Path(__file__).resolve().parents[1]
server.DEMO_MODE=True
server.DB_PATH=BASE/'data'/'visual_v03.sqlite3'
if server.DB_PATH.exists():server.DB_PATH.unlink()
with TestClient(server.app) as backend:
    clubs=backend.get('/api/world/clubs?league=ENG_1').json()['clubs']
    arsenal=next(c for c in clubs if c['name']=='Arsenal')
    r=backend.post('/api/careers/1/create',json={'role':'coach','name':'Александр Ветров','place':'Лондон','club_id':arsenal['id']})
    assert r.status_code==200,r.text
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':393,'height':852},device_scale_factor=1)
        page.set_content('<!DOCTYPE html><html lang="ru"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div></body></html>')
        page.add_style_tag(content=(BASE/'static/style.css').read_text())
        def bridge(_src,args):
            resp=backend.request(args.get('method','GET'),args['url'],json=args.get('body'))
            return {'status':resp.status_code,'body':resp.json()}
        page.expose_binding('__apiBridge',bridge)
        page.evaluate('''() => {window.fetch = async(url,opt={})=>{const r=await window.__apiBridge({url,method:opt.method||'GET',body:opt.body?JSON.parse(opt.body):undefined});return {ok:r.status>=200&&r.status<300,json:async()=>r.body}};}''')
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.add_script_tag(content=(BASE/'static/app.js').read_text())
        page.locator('[data-action="open"][data-slot="1"]').click()
        page.wait_for_selector('[data-action="open-market"]')
        page.screenshot(path=str(BASE/'preview_career_v03.png'),full_page=True)
        assert 'Матчи клуба' in page.locator('#app').inner_text()
        page.locator('[data-action="open-calendar"]').click()
        page.wait_for_selector('.calendar-game')
        assert page.locator('.calendar-game').count()==38
        page.locator('[data-action="close-calendar"]').click()
        page.locator('[data-action="open-archive"]').click()
        page.wait_for_selector('.modal-head')
        assert 'Завершённых сезонов ещё нет' in page.locator('.modal').inner_text()
        page.locator('[data-action="close-archive"]').click()
        page.locator('[data-action="open-squad"]').click()
        page.wait_for_selector('.squad-list')
        assert 'Bukayo Saka' in page.locator('.squad-list').inner_text()
        page.screenshot(path=str(BASE/'preview_squad_v03.png'))
        page.locator('[data-action="close-squad"]').click()
        page.locator('[data-action="open-market"]').click()
        page.wait_for_selector('.market-results')
        page.locator('#market-search').fill('Neuer')
        page.locator('#market-search-form [type="submit"]').click()
        page.wait_for_function("document.querySelector('.market-results')?.textContent?.includes('Manuel Neuer')")
        page.locator('[data-action="pick-player"]').first.click()
        page.wait_for_selector('#offer-eur')
        page.screenshot(path=str(BASE/'preview_market_v03.png'))
        page.locator('[data-action="offer-transfer"]').click()
        page.wait_for_function("document.querySelector('.toast')?.textContent?.includes('Трансфер оформлен')")
        page.locator('[data-action="close-market"]').click()
        page.locator('[data-action="open-squad"]').click()
        assert 'Manuel Neuer' in page.locator('.squad-list').inner_text()
        page.locator('[data-action="close-squad"]').click()
        page.locator('[data-action="tactic"][data-tactic="attack"]').click()
        page.wait_for_function("document.querySelector('[data-tactic=\"attack\"]')?.classList.contains('active')")
        page.locator('[data-action="decide"]').first.click()
        page.wait_for_selector('.result-title')
        page.locator('[data-action="dismiss-result"]').click()
        page.screenshot(path=str(BASE/'preview_match_v03.png'),full_page=True)
        assert 'Турнирная таблица' in page.locator('#app').inner_text()
        assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        assert not errors,errors
        browser.close()
        print('PASS: mobile roster, market purchase, tactic, matchday, no JS errors or horizontal overflow')
