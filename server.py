import time
from hashlib import sha256
from contextlib import contextmanager
#from socket import gethostbyname, gethostname
import asyncio
import aiohttp
import aiohttp.web

connections = {}
parties = {}

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
    aiohttp.web.get('/party/{path}', party),
    aiohttp.web.get('/party_size/{path}', party_size)
])
aiohttp.web.run_app(app)
