import random
from os import getpid
from pypresence import Presence
import pygame
from pygame.locals import *

BLOCS = BLOCW, BLOCH = 20, 20
SIZE = WIDTH, HEIGHT = 60 * BLOCW, 35 * BLOCH
FPS = 25
SN_L = 'l'
SN_R = 'r'
SN_U = 'u'
SN_D = 'd'
KEYS = [[K_UP, K_DOWN, K_LEFT, K_RIGHT],
    [K_w, K_s, K_a, K_d]]
KEYS_OCC = set((0,))
BIGAPPLE_TIME = 8 * FPS
DEDAPPLE_FREQ = 6

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
        keys = pygame.key.get_pressed()
        if keys[KEYS[self.id][0]] and self.direction != SN_D:
            self.direction = SN_U
        elif keys[KEYS[self.id][3]] and self.direction != SN_L:
            self.direction = SN_R
        elif keys[KEYS[self.id][1]] and self.direction != SN_U:
            self.direction = SN_D
        elif keys[KEYS[self.id][2]] and self.direction != SN_R:
            self.direction = SN_L
        else:
            if (keys[KEYS[self.id][0]] and self.direction == SN_D \
                    or keys[KEYS[self.id][3]] and self.direction == SN_L \
                    or keys[KEYS[self.id][1]] and self.direction == SN_U \
                    or keys[KEYS[self.id][2]] and self.direction == SN_R) and self.len > 0:
                trail.add(Mine((self.rect.x, self.rect.y),
                        self.direction,
                        self.len))
                self.len -= 1
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
        self.poison = False
        self.poisonlen = 0

    def update(self):
        global snake
        if self.poison:
            self.poisonlen += 1
        if self.poisonlen > BIGAPPLE_TIME:
            self.poison = False
            self.poisonlen = 0
            self.image.fill((255, 0, 0))
        for snak in pygame.sprite.spritecollide(self, snake, False):
            snak.len += (-1 if self.poison else 1)
            self.poison = random.randint(0, DEDAPPLE_FREQ) == 1
            if self.poison:
                self.image.fill((192, 0, 0))
            else:
                self.image.fill((255, 0, 0))
            self.poisonlen = 0
            self.rect.x = random.randint(0, WIDTH - 1) // BLOCW * BLOCW
            self.rect.y = random.randint(0, HEIGHT - 1) // BLOCH * BLOCH

class BigApple(pygame.sprite.Sprite):
    def __init__(self):
        super(type(self), self).__init__()
        self.image = pygame.Surface((BLOCW * 2, BLOCH * 2))
        self.image.fill((255, 255, 0))
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, WIDTH - 1) // (BLOCW * 2) * (BLOCW * 2)
        self.rect.y = random.randint(0, HEIGHT - 1) // (BLOCH * 2) * (BLOCH * 2)

    def update(self):
        global snake
        collides = pygame.sprite.spritecollide(self, snake, False)
        for snak in collides:
            snak.len += 4
            self.rect.x = random.randint(0, WIDTH - 1) \
                    // (BLOCW * 2) \
                    * (BLOCW * 2)
            self.rect.y = random.randint(0, HEIGHT - 1) \
                    // (BLOCH * 2) \
                    * (BLOCH * 2)
        if collides:
            self.kill()

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
snake = pygame.sprite.RenderPlain(Snake(0))
trail = pygame.sprite.RenderPlain()
apple = pygame.sprite.RenderPlain(Apple())
thebigapple = BigApple()
clock = pygame.time.Clock()
frames = 0
RPC = Presence('511398745057787905')

def mktext(surf, text, pos, size=15, color=(255, 255, 255)):
    font = pygame.font.SysFont('monospace', size)
    label = font.render(text, 1, color)
    surf.blit(label, pos)

try:
    SCREEN.fill((0, 0, 0))
    mktext(SCREEN, 'Space to spawn a new snake.', (0, 0))
    mktext(SCREEN, 'Controls for first two snakes are arrow keys and WASD.', (0, BLOCH))
    mktext(SCREEN, 'Attempt to move backwards to make a landmine and subtract your length.', (0, BLOCH * 2))
    mktext(SCREEN, 'If you hit anything white except a snake head you die.', (0, BLOCH * 3))
    mktext(SCREEN, 'At any point, Escape or close the window to quit.', (0, BLOCH * 4))
    mktext(SCREEN, 'Space to continue. Watch out for poison apples.', (0, BLOCH * 5))
    pygame.display.flip()
    while 1:
        for e in pygame.event.get():
            if e.type == QUIT or e.type == KEYDOWN and e.key == K_ESCAPE:
                raise SystemExit(0)
            if e.type == KEYDOWN and e.key == K_SPACE:
                raise KeyboardInterrupt
except KeyboardInterrupt:
    pass
except SystemExit:
    pygame.quit()
    raise

try:
    RPC.connect()
    status = {'pid': getpid(), 'large_image': 'python-logo'}
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
                raise SystemExit(0)
            if e.type == KEYDOWN and e.key == K_SPACE:
                idx = -1
                for i in range(len(KEYS)):
                    if i not in KEYS_OCC:
                        KEYS_OCC.add(i)
                        idx = i
                        break
                if idx == -1:
                    newkeys = []
                    for dir in ('up','down','left','right'):
                        SCREEN.fill((0, 0, 0))
                        mktext(SCREEN, 'Map ' + dir + ' for new snake', (BLOCW * 10, BLOCH * 20))
                        pygame.display.flip()
                        ev = pygame.event.poll()
                        while ev.type != KEYDOWN:
                            ev = pygame.event.wait()
                        newkeys.append(ev.key)
                    KEYS.append(newkeys)
                    idx = len(KEYS) - 1
                    KEYS_OCC.add(idx)
                snake.add(Snake(idx))
        if frames % BIGAPPLE_TIME == 0:
            if apple.has(thebigapple):
                apple.remove(thebigapple)
            else:
                apple.add(thebigapple)
        if frames % FPS == 0:
            status['details'] = 'Competitive' if len(snake.sprites()) > 1 else 'Solo'
            status['state'] = scorestr
            RPC.update(**status)
        SCREEN.fill((0, 0, 0))
        snake.update()
        trail.update()
        apple.update()
        for snak in snake:
            if pygame.sprite.spritecollide(snak, trail, False):
                snak.kill()
                KEYS_OCC.remove(snak.id)
        snake.draw(SCREEN)
        trail.draw(SCREEN)
        apple.draw(SCREEN)
        pygame.display.flip()
        clock.tick(FPS)
        frames += 1
finally:
    pygame.quit()
    RPC.close()
