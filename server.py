import sys
import time
import json
from hashlib import sha256
from contextlib import contextmanager
import random
import asyncio
import aiohttp
import aiohttp.web

connections = {}
games = {}
parties = {}

#fil = open('log.log', 'w')
BLOCW, BLOCH = 20, 20
WIDTH, HEIGHT = 60 * BLOCW, 35 * BLOCH
BIGAPPLE_TIME = 8

def rx():
    return random.randint(0, WIDTH // BLOCW - 1) * BLOCW
def ry():
    return random.randint(0, HEIGHT // BLOCH - 1) * BLOCH

def m(*a):
    return json.dumps(a)

def n(s):
    return json.loads(s)

def newpid(gam):
    gam['nextpid'] = gam.setdefault('nextpid', 0) + 1
    return gam['nextpid']

@contextmanager
def newsock(s, path, d=connections):
    if path not in d:
        d[path] = set()
    d[path].add(s)
    try:
        yield s
    finally:
        if path in d:
            d[path].remove(s)
            if not d[path]:
                del d[path]

async def echo(request):
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    path = request.match_info['path']
    with newsock(ws, path):
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            for s in connections[path]:
                await s.send_str(msg.data)
    return ws

async def bigapple(gam):
    while 1:
        gam['bigapple?'] = not gam['bigapple?']
        if gam['bigapple?']:
            gam['bigapple'] = (rx() // 2 * 2, ry() // 2 * 2)
            await asyncio.gather(*(
                s.send_str(m('B', 0, *gam['bigapple']))
                for s in gam['socks'].values()
            ))
        else:
            await asyncio.gather(*(
                s.send_str(m('b', 0, 0))
                for s in gam['socks'].values()
            ))
        await asyncio.sleep(BIGAPPLE_TIME)

@contextmanager
def newgame(s, pid, path):
    if path not in games:
        raise aiohttp.web.HTTPNotFound
    if not games[path]['socks']:
        games[path]['task'] = asyncio.create_task(bigapple(games[path]))
    games[path]['socks'][pid] = s
    games[path]['lens'][pid] = 1
    try:
        yield s
    finally:
        if path in games:
            del games[path]['socks'][pid]
            if not games[path]['socks']:
                games[path]['task'].cancel()
                del games[path]

async def game(request):
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    print(request.match_info)
    path = request.match_info['path']
    game = games[path]
    PID = newpid(game)
    with newgame(ws, PID, path):
        await ws.send_str(m('+', PID))
        await asyncio.gather(*(
            ws.send_str(m('+', pid))
            for pid in game['socks']
            if pid != PID
        ), *(
            s.send_str(m('+', PID))
            for s in game['socks'].values()
            if s != ws
        ),
        ws.send_str(m('a', 0, 0, *game['apple']))
        )
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            print('>{}'.format(msg.data))#, file=fil)
            try:
                deeta = n(msg.data)
            except json.JSONDecodeError:
                await ws.close(code=4000, message=b'Invalid message')
                break
            if deeta[0] == 'a':
                game['apple'] = (rx(), ry())
                game['lens'][PID] += 1
                await asyncio.gather(*(
                    s.send_str(m('a', PID, game['lens'][PID], *game['apple']))
                    for s in game['socks'].values()
                ))
            if deeta[0] == 'b':
                if not game['bigapple?']:
                    await ws.close(code=4000, message=b'Big apple not availabe')
                    break
                game['bigapple'] = (rx() // 2 * 2, ry() // 2 * 2)
                game['bigapple?'] = False
                game['lens'][PID] += 4
                await asyncio.gather(*(
                    s.send_str(m('b', PID, game['lens'][PID]))
                    for s in game['socks'].values()
                ))
            if deeta[0] == 'd':
                await asyncio.gather(*(
                    s.send_str(m('d', PID, *deeta[1:]))
                    for s in game['socks'].values()
                ))
            if deeta[0] not in {'a', 'b', 'd'}:
                await ws.close(code=4000, message=b'Invalid oplet')
                break
    await asyncio.gather(*(
        s.send_str(m('-', PID))
        for s in game['socks'].values()
    ))
    return ws

@contextmanager
def partysock(s, path):
    if path not in parties:
        parties[path] = {'owner': s, 'socks': set(), 'ready': 0}
    parties[path]['socks'].add(s)
    try:
        yield s
    finally:
        if path in parties:
            parties[path]['socks'].remove(s)
            if not parties[path]['socks']:
                del parties[path]

async def party(request):
    #server: member joined
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    path = request.match_info['path']
    #PID = (await ws.receive_str())[5:]
    startable = False
    with partysock(ws, path):
        for s in parties[path]['socks']:
            #tell clients
            if s != ws:
                await s.send_str(str(len(parties[path]['socks'])))
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            #server: member ready
            if msg.data == 'ready':
                parties[path]['ready'] += 1
            elif msg.data == 'unready':
                parties[path]['ready'] -= 1
                startable = False
                await parties[path]['owner'].send_str('unstartable')
            for s in parties[path]['socks']:
                await s.send_str('ready: {}'.format(parties[path]['ready']))
            if msg.data == 'start' and ws == parties[path]['owner'] and startable:
                gameroom = sha256((str(time.time()) + path).encode('ascii')).hexdigest()
                games[gameroom] = {
                    'socks': {},
                    'apple': (rx(), ry()),
                    'bigapple': (rx() // 2 * 2, ry () // 2 * 2),
                    'bigapple?': True,
                    'lens': {},
                }
                for s in parties[path]['socks']:
                    await s.send_str('start: ' + gameroom)
            #all ready?
            if parties[path]['ready'] == len(parties[path]['socks']):
                await parties[path]['owner'].send_str('startable')
                startable = True
            elif startable:
                await parties[path]['owner'].send_str('unstartable')
                startable = False
    return ws

async def party_size(request):
    return aiohttp.web.Response(text=str(
        len(parties[request.match_info['path']]['socks'])
    ))

async def wakeup():
    while 1:
        await asyncio.sleep(1)

asyncio.get_event_loop().create_task(wakeup())
app = aiohttp.web.Application()
app.add_routes([
    aiohttp.web.get('/echo/{path}', echo),
    aiohttp.web.get('/game/{path}', game),
    aiohttp.web.get('/party/{path}', party),
    aiohttp.web.get('/party_size/{path}', party_size)
])
aiohttp.web.run_app(app)
