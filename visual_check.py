"""Visual browser smoke check without navigating restricted loopback URLs."""
import os, json
from pathlib import Path
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
import server

BASE=Path(__file__).resolve().parents[1]
server.DEMO_MODE=True
server.DB_PATH=BASE/'data'/'visual_check.sqlite3'
if server.DB_PATH.exists(): server.DB_PATH.unlink()
with TestClient(server.app) as backend:
  def bridge(_source, args):
    method=args.get('method','GET')
    res=backend.request(method, args['url'], json=args.get('body'))
    return {'status':res.status_code,'body':res.json()}
  with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':393,'height':850},device_scale_factor=1)
    page.set_content('<!DOCTYPE html><html lang="ru"><head><meta name="viewport" content="width=device-width,initial-scale=1" /></head><body><div id="app"></div></body></html>')
    page.add_style_tag(content=(BASE/'static'/'style.css').read_text())
    page.expose_binding('__apiBridge', bridge)
    page.evaluate('''() => {window.fetch = async (url,opt={}) => {const payload= {url,method:opt.method||'GET',body:opt.body?JSON.parse(opt.body):undefined}; const r=await window.__apiBridge(payload);return {ok:r.status>=200&&r.status<300,json:async()=>r.body};}}''')
    page.add_script_tag(content=(BASE/'static'/'app.js').read_text())
    page.wait_for_selector('.slot-list')
    page.screenshot(path=str(BASE/'demo_home.png'),full_page=True)
    print('Home:', page.locator('.headline').inner_text())
    page.locator('[data-action="create"][data-slot="1"]').click()
    page.wait_for_selector('.role-option')
    print('Available role options:',page.locator('.role-option').count())
    page.locator('[data-role="player"]').click()
    page.locator('#character-name').fill('Максим Волков')
    page.locator('#new-career button[type="submit"]').click()
    page.wait_for_selector('.career-head h1')
    print('Career:',page.locator('.career-head h1').inner_text())
    page.wait_for_timeout(4000)  # let the 'career created' toast disappear
    page.screenshot(path=str(BASE/'demo_career.png'),full_page=True)
    page.locator('.choice').first.click()
    page.wait_for_selector('.result-title')
    print('Decision:',page.locator('.result-title').inner_text())
    page.locator('[data-action="dismiss-result"]').click()
    page.locator('[data-page="profile"]').click()
    page.wait_for_selector('.profile-card')
    page.screenshot(path=str(BASE/'demo_profile.png'),full_page=True)
    print('Achievements unlocked:',page.locator('.award:not(.locked)').count())
    print('Horizontal scroll:',page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
    browser.close()
