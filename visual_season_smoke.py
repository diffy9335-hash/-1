"""Run manually: PYTHONPATH=. python tests/visual_season_smoke.py"""
from pathlib import Path
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
import server

BASE=Path(__file__).resolve().parents[1]
server.DEMO_MODE=True
server.DB_PATH=BASE/'data'/'visual_season.sqlite3'
if server.DB_PATH.exists():server.DB_PATH.unlink()
with TestClient(server.app) as backend:
    r=backend.post('/api/careers/1/create',json={'role':'coach','name':'Алексей Морозов','place':'Арсенал'})
    assert r.status_code==200,r.text
    for _ in range(12):
        c=backend.get('/api/state').json()['careers'][0]
        r=backend.post('/api/careers/1/decide',json={'event_id':c['event']['id'],'choice_id':1,'expected_turn':c['turns']})
        assert r.status_code==200,r.text
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':393,'height':850},device_scale_factor=1)
        page.set_content('<!DOCTYPE html><html lang="ru"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div></body></html>')
        page.add_style_tag(content=(BASE/'static/style.css').read_text())
        def bridge(_src,args):
            res=backend.request(args.get('method','GET'),args['url'],json=args.get('body'))
            return {'status':res.status_code,'body':res.json()}
        page.expose_binding('__apiBridge',bridge)
        page.evaluate('''() => {window.fetch = async (url,opt={}) => {const r=await window.__apiBridge({url,method:opt.method||'GET',body:opt.body?JSON.parse(opt.body):undefined});return {ok:r.status>=200&&r.status<300,json:async()=>r.body};}}''')
        page.add_script_tag(content=(BASE/'static/app.js').read_text())
        page.wait_for_selector('[data-action="open"][data-slot="1"]')
        page.locator('[data-action="open"][data-slot="1"]').click()
        page.wait_for_selector('[data-action="finish-season"]')
        page.screenshot(path=str(BASE/'season_ready.png'))
        page.locator('[data-action="finish-season"]').click()
        page.wait_for_selector('.season-report')
        assert 'СЕЗОН 1 ЗАВЕРШЁН' in page.locator('.season-report').inner_text()
        page.screenshot(path=str(BASE/'season_report.png'))
        page.locator('[data-action="advance-season"]').click()
        page.wait_for_function("document.querySelector('.career-meta')?.textContent.includes('Сезон 2')")
        assert 'Неделя 1 / 12' in page.locator('.career-meta').inner_text()
        page.screenshot(path=str(BASE/'season_new.png'))
        page.locator('[data-page="home"]').click()
        page.locator('[data-action="world-browser"]').click()
        page.wait_for_selector('.world-league-row')
        page.locator('[data-action="browse-league"][data-league="ENG_1"]').click()
        page.wait_for_function("document.querySelectorAll('.world-club-row').length === 20")
        page.locator('[data-action="browse-club"]').first.click()
        page.wait_for_selector('.world-club-row')
        assert 'Бюджет:' in page.locator('#app').inner_text()
        page.screenshot(path=str(BASE/'world_club.png'))
        print('PASS — season report, advance, club browser, no page errors')
        print('Document overflow:',page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
        browser.close()
