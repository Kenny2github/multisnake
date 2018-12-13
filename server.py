import sys
import time
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

@contextmanager
def newgame(s, path):
    if path not in games:
        games[path] = {'socks': set(), 'pids': set(), 'apples': [
            (random.randint(0, WIDTH - 1) // BLOCW * BLOCW,
            random.randint(0, HEIGHT - 1) // BLOCH * BLOCH),
            (random.randint(0, WIDTH - 1) // (BLOCW * 2) * (BLOCW * 2),
            random.randint(0, HEIGHT - 1) // (BLOCH * 2) * (BLOCH * 2))
        ]}
    games[path]['socks'].add(s)
    try:
        yield s
    finally:
        if path in games:
            games[path]['socks'].remove(s)
            if not games[path]['socks']:
                del games[path]

async def game(request):
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    path = request.match_info['path']
    with newgame(ws, path):
        for pid in games[path]['pids']:
            print('<+', pid)#, file=fil)
            await ws.send_str('+ ' + str(pid))
            await ws.send_str('a 0 0 {} {}'.format(*games[path]['apples'][0]))
            await ws.send_str('b 0 0 {} {}'.format(*games[path]['apples'][1]))
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            print('>{}'.format(msg.data))#, file=fil)
            deeta = msg.data
            if deeta.startswith('+'):
                games[path]['pids'].add(int(deeta[2:]))
            if deeta.startswith('-'):
                try:
                    games[path]['pids'].remove(int(deeta[2:]))
                except KeyError:
                    pass
            if deeta.startswith('a'):
                games[path]['apples'][0] = (
                    random.randint(0, WIDTH - 1)
                    // BLOCW * BLOCW,
                    random.randint(0, HEIGHT - 1)
                    // BLOCH * BLOCH
                )
                deeta += ' {} {}'.format(*games[path]['apples'][0])
            elif deeta.startswith('b'):
                games[path]['apples'][1] = (
                    random.randint(0, WIDTH - 1)
                    // (BLOCW * 2)
                    * (BLOCW * 2),
                    random.randint(0, HEIGHT - 1)
                    // (BLOCW * 2)
                    * (BLOCW * 2)
                )
                deeta += ' {} {}'.format(*games[path]['apples'][1])
            for s in games[path]['socks']:
                print('<{}'.format(deeta))#, file=fil)
                await s.send_str(deeta)
    return ws

@contextmanager
def partysock(s, path):
    if path not in parties:
        parties[path] = {'socks': set(), 'size': 0, 'ready': 0}
    parties[path]['socks'].add(s)
    parties[path]['size'] += 1
    try:
        yield s
    finally:
        if path in parties:
            parties[path]['socks'].remove(s)
            if not parties[path]['size']:
                del parties[path]

async def party(request):
    #server: member joined
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    path = request.match_info['path']
    #PID = (await ws.receive_str())[5:]
    with partysock(ws, path):
        for s in parties[path]['socks']:
            #tell clients
            if s != ws:
                await s.send_str('joined')
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            #server: member ready
            if msg.data == 'ready':
                parties[path]['ready'] += 1
            elif msg.data == 'unready':
                parties[path]['ready'] -= 1
            #all ready?
            if parties[path]['ready'] == parties[path]['size']:
                for s in parties[path]['socks']:
                    #tell clients
                    await s.send_str('start: ' + sha256(
                        (str(time.time()) + path).encode('ascii')
                    ).hexdigest())
    return ws

async def party_size(request):
    return aiohttp.web.Response(text=str(
        parties[request.match_info['path']]['size']
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
