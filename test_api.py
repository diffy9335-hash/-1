import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

import server
from game import ROLES

TOKEN = '123456789:TEST_TOKEN_DO_NOT_USE'

def signed_init_data(user_id, *, token=TOKEN, auth_date=None):
    fields = {
        'auth_date': str(auth_date if auth_date is not None else int(time.time())),
        'user': json.dumps({'id': user_id, 'first_name': f'Player{user_id}'}, separators=(',', ':')),
    }
    secret = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
    value = '\n'.join(f'{k}={v}' for k, v in sorted(fields.items()))
    fields['hash'] = hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'DB_PATH', tmp_path / 'velton.sqlite3')
    monkeypatch.setattr(server, 'DEMO_MODE', False)
    monkeypatch.setattr(server, 'BOT_TOKEN', TOKEN)
    with TestClient(server.app) as c:
        yield c

def auth(uid=41):
    return {'X-Telegram-Init-Data': signed_init_data(uid)}

def create(client, slot, role='player', uid=41):
    return client.post(f'/api/careers/{slot}/create', headers=auth(uid), json={
        'role': role, 'name': 'Игровой герой', 'place': 'ФК Север'
    })

def test_signature_valid_and_tampered_rejected():
    raw=signed_init_data(99)
    assert server.validate_telegram_init_data(raw,TOKEN)['id']==99
    altered=raw.replace('Player99','Imposter')
    with pytest.raises(ValueError):
        server.validate_telegram_init_data(altered,TOKEN)
    with pytest.raises(ValueError):
        server.validate_telegram_init_data(signed_init_data(99,auth_date=int(time.time())-90000),TOKEN)

def test_unauthorized_and_five_slots(client):
    assert client.get('/api/state').status_code==401
    assert len(client.get('/api/state',headers=auth()).json()['careers'])==0
    for i,role in enumerate(ROLES,start=1):
        res=create(client,i,role)
        assert res.status_code==200, res.text
    state=client.get('/api/state',headers=auth()).json()
    assert len(state['careers'])==5
    assert state['profile']['level']==1
    assert any(a['id']=='all_paths' and a['unlocked'] for a in state['achievements'])
    assert create(client,5).status_code==409
    assert create(client,6).status_code==400
    assert client.get('/api/state',headers=auth(12)).json()['careers']==[]

def test_decision_progression_replay_protection_and_awards(client):
    assert create(client,1).status_code==200
    initial=client.get('/api/state',headers=auth()).json()
    career=initial['careers'][0]
    body={'event_id':career['event']['id'],'choice_id':0,'expected_turn':0}
    res=client.post('/api/careers/1/decide',headers=auth(),json=body)
    assert res.status_code==200, res.text
    data=res.json()
    assert data['state']['careers'][0]['turns']==1
    assert data['state']['profile']['xp']>0
    assert any(a['id']=='first_move' and a['unlocked'] for a in data['state']['achievements'])
    # A double click or a stale request must not grant points twice.
    assert client.post('/api/careers/1/decide',headers=auth(),json=body).status_code==409
    assert client.get('/api/state',headers=auth()).json()['profile']['decisions']==1

def test_slot_deletion_keeps_profile_history(client):
    create(client,1)
    c=client.get('/api/state',headers=auth()).json()['careers'][0]
    payload={'event_id':c['event']['id'],'choice_id':2,'expected_turn':0}
    assert client.post('/api/careers/1/decide',headers=auth(),json=payload).status_code==200
    assert client.delete('/api/careers/1',headers=auth()).status_code==200
    state=client.get('/api/state',headers=auth()).json()
    assert state['careers']==[]
    assert state['profile']['decisions']==1
    assert any(a['id']=='pioneer' and a['unlocked'] for a in state['achievements'])
    assert create(client,1,role='coach').status_code==200

def test_user_data_isolation(client):
    assert create(client,2,uid=100).status_code==200
    assert client.get('/api/state',headers=auth(101)).json()['careers']==[]
    assert client.delete('/api/careers/2',headers=auth(101)).status_code==404

def test_strict_names_and_role(client):
    res=client.post('/api/careers/1/create',headers=auth(),json={
        'role':'spy','name':'A','place':'\u0000'
    })
    assert res.status_code==422
    res=client.post('/api/careers/1/create',headers=auth(),json={
        'role':'player','name':'   ', 'place':'Test'
    })
    assert res.status_code==422
