import sys
import socket
import random
import pickle
from os import system
from time import time
from math import atan2, degrees, sin, cos, radians

import pygame
from pygame.locals import K_w, K_a, K_s, K_d, K_i


def get_angle(point_a, point_b):
    changeInX = point_b[0] - point_a[0]
    changeInY = point_b[1] - point_a[1]
    return degrees(atan2(changeInY, changeInX))


def send_to_server(client, data, server):
    client.sendto(pickle.dumps(data), server)


def receive_from_server(server):
    try:
        data, addr = server.recvfrom(2048)
        return pickle.loads(data)
    except BlockingIOError:
        return None


def size_in_percent(percent, horizontal=True):
    return int(SCREEN_SIZE[int(horizontal)] * (percent / 100))


def win_screen(screen, winner):
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        screen.fill((0, 0, 0))
        text_surface = font.render(f"Winner: {winner}", True, (255, 255, 255))

        size = pygame.display.get_surface().get_size()

        screen.blit(text_surface,
                    (int((size[0] - text_surface.get_width()) // 2), int((size[1] - text_surface.get_height()) // 2)))

        pygame.display.flip()

        elapsed = clock.tick(FPS) / 1000
        pygame.display.set_caption(str(elapsed))


pygame.init()
SCREEN_SIZE = [600, 600]
elapsed = 0
FPS = 200
RUNNING = True

screen = pygame.display.set_mode(SCREEN_SIZE)
font = pygame.font.Font(pygame.font.get_default_font(), 36)
clock = pygame.time.Clock()


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        global S_PLAYER, S_PLAYER_DEAD
        super(Player, self).__init__()

        self.image = S_PLAYER
        self.image_original = self.image.copy()
        self.image_dead_original = S_PLAYER_DEAD

        self.speed = 220
        self.angle = 0

        self.rect = self.image.get_rect()
        self.x = x
        self.y = y
        self.rect.x = int(x)
        self.rect.y = int(y)

        self.hp = 100

    def update(self, time, pressed_keys, walls):
        if pressed_keys[K_i]:
            print(time)
        if self.hp <= 0:
            return

        position_before = (self.x, self.y)

        if pressed_keys[K_w]:
            self.y -= self.speed * time

        if pressed_keys[K_s]:
            self.y += self.speed * time

        if pressed_keys[K_a]:
            self.x -= self.speed * time

        if pressed_keys[K_d]:
            self.x += self.speed * time

        if self.x + self.rect.width > SCREEN_SIZE[0] or self.x < 0 or self.y + self.rect.height > SCREEN_SIZE[
            1] or self.y < 0:
            self.x, self.y = position_before

        self.rect.x, self.rect.y = int(self.x), int(self.y)
        if pygame.sprite.spritecollideany(self, walls):
            self.x, self.y = position_before
            self.rect.x, self.rect.y = int(self.x), int(self.y)

        self.angle = get_angle(pygame.mouse.get_pos(), self.rect.center)
        self.image = pygame.transform.rotate(self.image_original, -self.angle + 90)

    def take_damage(self, dmg):
        if self.hp <= 0:
            return

        self.hp -= dmg

        if self.hp <= 0:
            self.image = pygame.transform.rotate(self.image_dead_original, -self.angle + 90)
            send_to_server(client, {"code": "PLAYER_DEAD"}, (HOST, PORT))

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, addr):
        global S_ENEMY, S_ENEMY_DEAD
        super(Enemy, self).__init__()

        self.image = S_ENEMY
        self.image_original = self.image.copy()
        self.image_dead_original = S_ENEMY_DEAD

        self.addr = addr
        self.speed = 350
        self.angle = 0

        self.rect = self.image.get_rect()
        self.x = x
        self.y = y
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.died = False

    def update(self, data):
        if self.died:
            return

        coordinates = data[self.addr]["coords"]

        self.x = coordinates[0]
        self.y = coordinates[1]

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.angle = data[self.addr]["angle"]

        self.image = pygame.transform.rotate(self.image_original, -self.angle + 90)

    def dead(self):
        self.died = True
        self.image = pygame.transform.rotate(self.image_dead_original, -self.angle + 90)

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        global S_WALL
        super(Wall, self).__init__()

        self.image = S_WALL

        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, angle, shooter):
        super(Bullet, self).__init__()

        self.image = S_BULLET
        self.image_original = self.image.copy()
        self.image = pygame.transform.rotate(self.image, -angle + 90)

        self.x = x
        self.y = y

        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

        self.angle = angle
        self.speed = 400
        self.shooter = shooter
        self.dmg = 25

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def update(self, time, walls, player, addr):
        self.x += sin(radians(-self.angle - 90)) * time * self.speed
        self.y += cos(radians(-self.angle - 90)) * time * self.speed

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

        if pygame.sprite.spritecollideany(self, walls):
            bullets.remove(self)

        enemy_collide = pygame.sprite.spritecollideany(self, enemies)
        if enemy_collide and enemy_collide.addr != self.shooter:
            bullets.remove(self)

        if self.shooter != addr and pygame.sprite.collide_rect(self, player):
            player.take_damage(self.dmg)
            bullets.remove(self)


class Health(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super(Health, self).__init__()

        self.image = S_HEALTH

        self.x = x
        self.y = y

        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

        self.regen = 50

        self.born = time()
        self.lifetime = random.randint(5, 10)

    def update(self, player, enemies):
        if pygame.sprite.collide_rect(self, player):
            if player.hp <= 150:
                player.hp += self.regen
            bonuses.remove(self)

        elif pygame.sprite.spritecollideany(self, enemies) or (time() - self.born) > self.lifetime:
            bonuses.remove(self)


system("CLS")

# Connecting to server
nickname = ""
while len(nickname) > 15 or len(nickname) <= 0:
    nickname = input("Enter your name (max. 15 chars): ")

HOST, PORT = 'localhost', 7777

print(f"Connecting to server at {HOST}:{PORT}")
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.setblocking(False)
send_to_server(client, {"code": "CONNECT_REQUEST", "nickname": nickname}, (HOST, PORT))

GAME_NOT_STARTED = True
while GAME_NOT_STARTED:
    data = receive_from_server(client)

    if not data:
        continue

    if data["code"] == "CONNECT_OK":
        print("Successfully connected\n\nWaiting for players")

        while True:
            data = receive_from_server(client)

            if not data or data["code"] != "START_GAME":
                continue

            game_map = data["map"]
            player_address = data["player_address"]
            main_player = data["player_coords"]
            enemies_data = data["enemies"]
            GAME_NOT_STARTED = False
            break

    else:
        print("Can't connect")
        sys.exit()

# Groups of objects
walls = pygame.sprite.Group()
bullets = pygame.sprite.Group()
enemies = pygame.sprite.Group()
bonuses = pygame.sprite.Group()

# Map Settings-
map_size = [len(game_map[0]), len(game_map)]  # Size of map
tile_size = [int(SCREEN_SIZE[0] / map_size[0]), int(SCREEN_SIZE[1] / map_size[1])]  # Size of one tile

# Sprites
S_BACKGROUND = pygame.transform.scale(pygame.image.load("assets/background.png"), SCREEN_SIZE)
S_WALL_ORIGINAL = pygame.image.load("assets/wall.png")
S_WALL = pygame.transform.scale(S_WALL_ORIGINAL, tile_size)

S_HEALTH = pygame.image.load("assets/bonus_hp.png")
S_HEALTH = pygame.transform.scale(S_HEALTH, (
    int(S_HEALTH.get_width() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width())),
    int(S_HEALTH.get_height() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width()))))

S_BULLET = pygame.image.load("assets/bullet.png")
S_BULLET = pygame.transform.scale(S_BULLET, (
    int(S_BULLET.get_width() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width())),
    int(S_BULLET.get_height() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width()))))

S_PLAYER = pygame.image.load("assets/player.png")
S_PLAYER = pygame.transform.scale(S_PLAYER, (
    int(S_PLAYER.get_width() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width())),
    int(S_PLAYER.get_height() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width()))))
S_PLAYER_DEAD = pygame.image.load("assets/player_dead.png")
S_PLAYER_DEAD = pygame.transform.scale(S_PLAYER_DEAD, (
    int(S_PLAYER_DEAD.get_width() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width())),
    int(S_PLAYER_DEAD.get_height() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width()))))

S_ENEMY = pygame.image.load("assets/enemy.png")
S_ENEMY = pygame.transform.scale(S_ENEMY, (
    int(S_ENEMY.get_width() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width())),
    int(S_ENEMY.get_height() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width()))))
S_ENEMY_DEAD = pygame.image.load("assets/enemy_dead.png")
S_ENEMY_DEAD = pygame.transform.scale(S_ENEMY_DEAD, (
    int(S_ENEMY_DEAD.get_width() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width())),
    int(S_ENEMY_DEAD.get_height() * (S_WALL.get_width() / S_WALL_ORIGINAL.get_width()))))

print(f"Game started. Player address: {player_address}")
main_player = Player(main_player[0] * tile_size[0], main_player[1] * tile_size[1])

# Parsing and building map
for yi, y in enumerate(game_map):
    for xi, x in enumerate(y):
        if x == 1:
            walls.add(Wall(tile_size[0] * xi, tile_size[1] * yi))

for e in enemies_data:
    print(e)
    if e[0] == player_address:
        continue
    enemies.add(Enemy(e[1][0] * tile_size[0], e[1][1] * tile_size[1], e[0]))

# Game loop
while RUNNING:
    new_bullets = []
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            RUNNING = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if not main_player.hp <= 0:
                new_bullets.append(
                    (main_player.rect.center[0], main_player.rect.center[1], 8, 14, main_player.angle, player_address))

    # Sending current info to server
    main_player.update(elapsed, pygame.key.get_pressed(), walls)
    send_to_server(client, {"code": None, "coords": (main_player.x, main_player.y), "angle": main_player.angle,
                            "bullets": new_bullets, "hp": main_player.hp}, (HOST, PORT))

    # Getting new info from server
    newest_data = None
    server_new_bullets = []
    keep = True
    while keep:
        data = receive_from_server(client)

        if data:
            newest_data = data
            if data.get("bullets") and len(data["bullets"]) != 0:
                server_new_bullets.extend(data["bullets"])

            if data["code"] == "PLAYER_DEAD":
                for e in enemies:
                    if e.addr == data["addr"]:
                        e.dead()

            elif data["code"] == "GAME_FINISHED":
                win_screen(screen, data["winner"])
                RUNNING = False

            if data.get("regen"):
                bonuses.add(Health(*data['regen']))

        else:
            keep = False

    if newest_data:
        enemies.update(newest_data)

        for b in server_new_bullets:
            bullets.add(Bullet(*b))

    bullets.update(elapsed, walls, main_player, player_address)
    bonuses.update(main_player, enemies)

    # Drawing
    screen.blit(S_BACKGROUND, (0, 0))
    bonuses.draw(screen)

    walls.draw(screen)
    enemies.draw(screen)
    bullets.draw(screen)
    main_player.draw(screen)

    # HP interface
    text_surface = font.render(f'{main_player.hp}', True, (255, 255, 255))
    back = pygame.Surface((text_surface.get_width(), text_surface.get_height()))
    back.blit(text_surface, (0, 0))
    screen.blit(back, (15, 15))

    pygame.display.flip()

    elapsed = clock.tick(FPS) / 1000
    pygame.display.set_caption(str(elapsed))

pygame.quit()
