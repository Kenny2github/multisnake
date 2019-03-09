#low-level
import random
from os import getpid
import asyncio
import sys
import time
#mid-level
from hashlib import sha256
from contextlib import suppress
#3rd-party
from pypresence import Client as shush, AioClient as Client, InvalidPipe
import websockets
import aiohttp
import pygame
from pygame.locals import *

import traceback
import warnings

def warn_with_traceback(message, category, filename, lineno, file=None, line=None):

    log = file if hasattr(file,'write') else sys.stderr
    traceback.print_stack(file=log)
    log.write(warnings.formatwarning(message, category, filename, lineno, line))

warnings.showwarning = warn_with_traceback

BLOCS = BLOCW, BLOCH = 20, 20
SIZE = WIDTH, HEIGHT = 60 * BLOCW, 35 * BLOCH
FPS = 25
SN_L = 'l'
SN_R = 'r'
SN_U = 'u'
SN_D = 'd'
BIGAPPLE_TIME = 8 * FPS
DEDAPPLE_FREQ = 6
PID = getpid()
GID = sha256((str(PID) + str(time.time())).encode('ascii')).hexdigest()

class Snake(pygame.sprite.Sprite):
    def __init__(self, sid=0):
        super(type(self), self).__init__()
        self.image = pygame.Surface(BLOCS)
        self.image.fill((
            random.randint(128, 255),
            random.randint(128, 255),
            random.randint(128, 255)
        ))
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = 0, 0
        self.direction = SN_R
        self.len = 1
        self.id = sid

    def update(self):
        global trail
        trail.add(Trail(self.rect.x, self.rect.y, self.len))
        if self.direction == SN_D:
            self.rect.y += BLOCH
        elif self.direction == SN_U:
            self.rect.y -= BLOCH
        elif self.direction == SN_L:
            self.rect.x -= BLOCW
        elif self.direction == SN_R:
            self.rect.x += BLOCW
        self.rect.x %= WIDTH
        self.rect.y %= HEIGHT

class Trail(pygame.sprite.Sprite):
    def __init__(self, x, y, len):
        super(type(self), self).__init__()
        self.len = len
        self.image = pygame.Surface(BLOCS)
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = x, y
    def update(self):
        self.len -= 1
        if self.len <= 0:
            self.kill()

class Apple(pygame.sprite.Sprite):
    def __init__(self):
        super(type(self), self).__init__()
        self.image = pygame.Surface(BLOCS)
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, WIDTH - 1) // BLOCW * BLOCW
        self.rect.y = random.randint(0, HEIGHT - 1) // BLOCH * BLOCH

    async def update(self, ws):
        global snake
        for snak in pygame.sprite.spritecollide(self, snake, False):
            snak.len += 1
            self.image.fill((255, 0, 0))
            #self.rect.x = random.randint(0, WIDTH - 1) // BLOCW * BLOCW
            #self.rect.y = random.randint(0, HEIGHT - 1) // BLOCH * BLOCH
            await ws.send('{} {} {}'.format('a', PID, snak.id))
            break

class BigApple(pygame.sprite.Sprite):
    def __init__(self):
        super(type(self), self).__init__()
        self.image = pygame.Surface((BLOCW * 2, BLOCH * 2))
        self.image.fill((255, 255, 0))
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, WIDTH - 1) // (BLOCW * 2) * (BLOCW * 2)
        self.rect.y = random.randint(0, HEIGHT - 1) // (BLOCH * 2) * (BLOCH * 2)

    async def update(self, ws):
        global snake
        collides = pygame.sprite.spritecollide(self, snake, False)
        for snak in collides:
            snak.len += 4
            #self.rect.x = random.randint(0, WIDTH - 1) \
            #        // (BLOCW * 2) \
            #        * (BLOCW * 2)
            #self.rect.y = random.randint(0, HEIGHT - 1) \
            #        // (BLOCH * 2) \
            #        * (BLOCH * 2)
            self.kill()
            await ws.send('{} {} {}'.format('b', PID, snak.id))
            break

class Mine(pygame.sprite.Sprite):
    def __init__(self, pos, direction, leng):
        super(type(self), self).__init__()
        self.direction = direction
        self.len = leng
        self.pos = list(pos)
        self.image = pygame.Surface(BLOCS)
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = pos
        self.done = False
        self.life = BIGAPPLE_TIME

    def update(self):
        if self.len <= 0 and not self.done:
            if self.direction in (SN_R, SN_L):
                self.image = pygame.Surface((BLOCW, BLOCH * 3))
                self.pos[1] -= BLOCH
            else:
                self.image = pygame.Surface((BLOCW * 3, BLOCH))
                self.pos[0] -= BLOCW
            self.image.fill((255, 255, 255))
            self.rect = self.image.get_rect()
            self.rect.x, self.rect.y = self.pos
            self.done = True
        elif self.len <= 0:
            self.life -= 1
            if self.life <= 0:
                self.kill()
        else:
            self.len -= 1

pygame.init()
SCREEN = pygame.display.set_mode(SIZE)
snake = pygame.sprite.RenderPlain()
trail = pygame.sprite.RenderPlain()
apple = pygame.sprite.RenderPlain(Apple())
thebigapple = BigApple()
frames = 0
if sys.platform.startswith('win32'):
    loop = asyncio.ProactorEventLoop()
else:
    loop = asyncio.get_event_loop()

async def register_event(self, event: str, func: callable, args: dict = {}):
    if not callable(func):
        raise TypeError
    await self.subscribe(event, args)
    self._events[event.lower()] = func

Client.on_event = shush.on_event
Client.register_event = register_event
RPC = Client('511398745057787905', loop=loop, pipe=sys.argv[1] if len(sys.argv) > 1 else 0)
status = {
    'pid': PID,
    'large_image': 'python-logo'
}

def mktext(surf, text, pos, size=15, color=(255, 255, 255)):
    font = pygame.font.SysFont('monospace', size)
    label = font.render(text, 1, color)
    surf.blit(label, pos)

async def intro():
    status.clear()
    status.update({
        'pid': PID,
        'large_image': 'python-logo',
        'state': 'In Intro'
    })
    global RPC
    try:
        await RPC.start()
    except (AttributeError, InvalidPipe) as exc:
        RPC = None
        print(type(exc).__name__, exc, sep=': ')
    if RPC:
        await RPC.set_activity(**status)
    SCREEN.fill((0, 0, 0))
    mktext(SCREEN, 'If you hit anything white except a snake head you die.', (0, 0))
    mktext(SCREEN, 'At any point, Escape or close the window to quit.', (0, BLOCH))
    mktext(SCREEN, 'Press 1 for solo snake. Press 2 for local/Press 3 for online multiplayer.', (0, BLOCH * 2))
    pygame.display.flip()
    while 1:
        for e in pygame.event.get():
            if e.type == QUIT or e.type == KEYDOWN and e.key == K_ESCAPE:
                raise SystemExit(0)
            if e.type == KEYDOWN:
                if e.key == K_1:
                    MODE = 1
                elif e.key == K_2:
                    MODE = 2
                elif e.key == K_3:
                    MODE = 3
                else:
                    continue
                return MODE
        await asyncio.sleep(1/FPS)

async def party():
    #client start
    session = aiohttp.ClientSession(loop=loop)
    #connect - secret = server room
    SCREEN.fill((0, 0, 0))
    mktext(SCREEN, 'Connecting...', (0, 0))
    pygame.display.flip()
    path = GID
    ws = await websockets.connect('ws://localhost:8080/party/{}'.format(path))
    status['state'] = 'In Lobby'
    status['party_id'] = GID
    status['party_size'] = [1, 2]
    status['join'] = ''.join(chr(ord(i) + 1) for i in GID)
    await RPC.set_activity(**status)
    #wait for events
    fut = loop.create_future()
    def handler(deeta):
        #discord says: joined party
        print('handler:', deeta)
        secret = deeta['secret']
        status['party_id'] = ''.join(chr(ord(i) - 1) for i in secret)
        status['party_size'][0] += 1
        status['party_size'][1] += 1
        status['join'] = secret
        nonlocal path
        fut.set_result('joined other')
        path = status['party_id']
    async def wait_ws():
        try:
            await ws.recv()
        except websockets.ConnectionClosed:
            return
        fut.set_result('other joined')
    loop.create_task(wait_ws())
    await RPC.register_event('ACTIVITY_JOIN', handler)
    SCREEN.fill((0, 0, 0))
    mktext(SCREEN, 'Waiting for party member...', (0, 0))
    pygame.display.flip()
    while not fut.done():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await ws.close()
                RPC.close()
                return
        await asyncio.sleep(1/FPS)
    print(status)
    if fut.result() == 'other joined': #server says: member joined
        print('other joined')
        status['party_size'][0] += 1
        status['party_size'][1] += 1
    else: #discord says: joined party
        await ws.close() #disconnect
        #join party server with secret
        ws = await websockets.connect(
            'ws://localhost:8080/party/{}'.format(path)
        )
        async with session.get('http://localhost:8080/party_size/{}'.format(path)) as resp:
            assert resp.status == 200
            status['party_size'][0] = int(await resp.text())
            status['party_size'][1] = status['party_size'][0] + 1
    await RPC.set_activity(**status)
    #wait for events
    ready = False
    startable = False
    readied = 0
    async def wait_start(fut):
        nonlocal readied, startable
        async for msg in ws:
            if msg.startswith('start: '):
                fut.set_result(msg[len('start: '):])
                return
            elif msg in {'startable', 'unstartable'}:
                startable = msg == 'startable'
            elif msg.startswith('ready: '):
                readied = int(msg[len('ready: '):])
            else:
                status['party_size'][0] = int(msg)
                status['party_size'][1] = status['party_size'][0] + 1
                await RPC.set_activity(**status)
    startable = False
    fut = loop.create_future()
    loop.create_task(wait_start(fut))
    while not fut.done():
        for event in pygame.event.get():
            if event.type == QUIT:
                await ws.close()
                RPC.close()
                raise SystemExit
            if event.type == KEYDOWN:
                if event.key == K_SPACE:
                    if not ready:
                        ready = True
                        await ws.send('ready')
                    elif startable:
                        await ws.send('start')
                elif event.key == K_ESCAPE:
                    if ready:
                        ready = False
                        await ws.send('unready')
        SCREEN.fill((0, 0, 0))
        if ready:
            if startable:
                text = 'Press Space to start the game!'
            else:
                text = 'Waiting for {} players to ready up... \
Press Escape to unready if needed'
        else:
            text = 'Press Space to ready up!'
        mktext(SCREEN, text, (0, 0))
        pygame.display.flip()
        await asyncio.sleep(1/FPS)
    await ws.close()
    await session.close()
    status['party_size'] = [1, 1]
    del status['join']
    #join game room
    return fut.result()

def getpbyid(gp, pid):
    for p in gp:
        if p.id == pid:
            return p

async def game(ws):
    global frames, SCREEN, snake, trail, apple, thebigapple, meh
    await ws.send('{} {}'.format('+', PID))
    status['start'] = int(time.time())
    while 1:
        scorestr = ''
        scores = {}
        for snak in snake:
            scores[snak.id] = snak.len
        scores = list(scores.items())
        scores.sort(key=lambda s: s[0])
        for sn, sc in scores:
            scorestr += 'Snake {}: {}; '.format(sn, sc)
        scorestr = scorestr.strip()
        pygame.display.set_caption(scorestr)
        for e in pygame.event.get():
            if e.type == QUIT or e.type == KEYDOWN and e.key == K_ESCAPE:
                RPC.close()
                with suppress(websockets.ConnectionClosed):
                    await ws.send('{} {}'.format('x', PID))
                return
            if e.type == KEYDOWN:
                with suppress(websockets.ConnectionClosed):
                    if e.key == K_UP and meh.direction != SN_D:
                        await ws.send('{} {} {} {} {}'.format(
                            'd', PID, SN_U, meh.rect.x, meh.rect.y
                        ))
                    elif e.key == K_DOWN and meh.direction != SN_U:
                        await ws.send('{} {} {} {} {}'.format(
                            'd', PID, SN_D, meh.rect.x, meh.rect.y
                        ))
                    elif e.key == K_LEFT and meh.direction != SN_R:
                        await ws.send('{} {} {} {} {}'.format(
                            'd', PID, SN_L, meh.rect.x, meh.rect.y
                        ))
                    elif e.key == K_RIGHT and meh.direction != SN_L:
                        await ws.send('{} {} {} {} {}'.format(
                            'd', PID, SN_R, meh.rect.x, meh.rect.y
                        ))
        if frames % BIGAPPLE_TIME == 0 and str(PID) == status['party_id']:
            with suppress(websockets.ConnectionClosed):
                if apple.has(thebigapple):
                    await ws.send('{} {} {}'.format('b', PID, 0))
                else:
                    await ws.send('{} {}'.format('B', PID))
        if frames % FPS == 0:
            status['details'] = 'Competitive' if len(snake.sprites()) > 1 else 'Solo'
            status['state'] = scorestr or 'No players'
            if RPC:
                await RPC.set_activity(**status)
        SCREEN.fill((0, 0, 0))
        snake.update()
        trail.update()
        for spr in apple:
            with suppress(websockets.ConnectionClosed):
                await spr.update(ws)
        for snak in snake:
            if pygame.sprite.spritecollide(snak, trail, False):
                snak.kill()
                with suppress(websockets.ConnectionClosed):
                    await ws.send('{} {}'.format('x', snak.id))
        snake.draw(SCREEN)
        trail.draw(SCREEN)
        apple.draw(SCREEN)
        pygame.display.flip()
        await asyncio.sleep(1/FPS)
        frames += 1

async def sock(ws):
    global meh
    try:
        async for msg in ws:
            cmd, pid, *args = msg.split()
            pid = int(pid)
            if 1:#cmd in {'+', 'x'}:
                print(cmd, pid, *args)
            if cmd == '+':
                snak = Snake(pid)
                if pid == PID:
                    meh = snak
                else:
                    status['party_size'][0] += 1
                    status['party_size'][1] += 1
                snake.add(snak)
            elif cmd == 'x':
                snak = getpbyid(snake, pid)
                if snak:
                    snak.kill()
                status['party_size'][0] -= 1
                status['party_size'][1] -= 1
                if pid == PID:
                    return
            elif cmd == 'd':
                snak = getpbyid(snake, pid)
                if snak:
                    snak.direction = args[0]
                    snak.rect.x, snak.rect.y = map(int, args[1:])
            elif cmd == 'a':
                for spr in apple:
                    if isinstance(spr, Apple):
                        leapp = spr
                        break
                leapp.rect.x, leapp.rect.y = map(int, args[1:])
                snak = getpbyid(snake, int(args[0]))
                if snak:
                    snak.len += 1
            elif cmd == 'b' and (pid == 0 or str(pid) == status['party_id']):
                thebigapple.kill()
                thebigapple.rect.x, thebigapple.rect.y = map(int, args[1:])
                snak = getpbyid(snake, int(args[0]))
                if snak:
                    snak.len += 4
            elif cmd == 'B' and str(pid) == status['party_id']:
                apple.add(thebigapple)
    except websockets.ConnectionClosed:
        return

async def main():
    try:
        while 1:
            MODE = await intro()
            if MODE - 2 <= 0:
                return True
            elif MODE == 3:
                path = await party()
                print('path:', path)
                try:
                    async with websockets.connect('ws://localhost:8080/game/{}'.format(path)) as s:
                        done, pending = await asyncio.wait(
                            (game(s), sock(s)), return_when=asyncio.FIRST_COMPLETED
                        )
                        for task in pending:
                            task.cancel()
                except ConnectionRefusedError:
                    continue
            cont = False
            SCREEN.fill((0, 0, 0))
            mktext(SCREEN, 'Game End!', (0, 0))
            mktext(SCREEN,
                'Press Escape or close the window to quit, or'
                ' press Space to play again.',
            (0, BLOCH))
            pygame.display.flip()
            while not cont:
                for event in pygame.event.get():
                    if event.type == QUIT or event.type == KEYDOWN and event.key == K_ESCAPE:
                        return
                    if event.type == KEYDOWN and event.key == K_SPACE:
                        cont = True
                        break
                await asyncio.sleep(1/FPS)
    finally:
        if RPC:
            RPC.close()
try:
    if loop.run_until_complete(main()):
        import snake
finally:
    loop.stop()
    pygame.quit()
