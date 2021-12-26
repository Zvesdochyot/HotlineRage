import random
from time import time
from math import atan2, degrees, sin, cos, radians

import pygame
from pygame.locals import K_w, K_a, K_s, K_d, K_i

SCREEN_SIZE = [600, 600]


def get_angle(pointA, pointB):
    changeInX = pointB[0] - pointA[0]
    changeInY = pointB[1] - pointA[1]
    return degrees(atan2(changeInY,changeInX))


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        global S_PLAYER, S_PLAYER_DEAD
        super(Player, self).__init__()
        width = int(width)
        height = int(height)

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
            self.y -= self.speed*time

        if pressed_keys[K_s]:
            self.y += self.speed*time

        if pressed_keys[K_a]:
            self.x -= self.speed*time

        if pressed_keys[K_d]:
            self.x += self.speed*time

        if self.x + self.rect.width > SCREEN_SIZE[0] or self.x < 0 or self.y+self.rect.height > SCREEN_SIZE[1] or self.y < 0:
            self.x, self.y = position_before

        self.rect.x, self.rect.y = int(self.x), int(self.y)
        if pygame.sprite.spritecollideany(self, walls):
            self.x, self.y = position_before
            self.rect.x, self.rect.y = int(self.x), int(self.y)

        self.angle = get_angle(pygame.mouse.get_pos(), self.rect.center)
        self.image = pygame.transform.rotate(self.image_original, -self.angle+90)

    def take_damage(self, dmg):
        if self.hp <= 0:
            return

        self.hp -= dmg

        if self.hp <= 0:
            self.image = pygame.transform.rotate(self.image_dead_original, -self.angle+90)
            # TODO: send to server

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, addr):
        global S_ENEMY, S_ENEMY_DEAD
        super(Enemy, self).__init__()
        width = int(width)
        height = int(height)

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

        coords = data[self.addr]["coords"]

        self.x = coords[0]
        self.y = coords[1]

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.angle = data[self.addr]["angle"]

        self.image = pygame.transform.rotate(self.image_original, -self.angle+90)

    def dead(self):
        self.died = True
        self.image = pygame.transform.rotate(self.image_dead_original, -self.angle+90)

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        global S_WALL
        super(Wall, self).__init__()
        width = int(width)
        height = int(height)

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
        self.image = pygame.transform.rotate(self.image, -angle+90)

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
        self.x += sin(radians(-self.angle-90)) * time * self.speed
        self.y += cos(radians(-self.angle-90)) * time * self.speed

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


# Groups of objects
walls = pygame.sprite.Group()
bullets = pygame.sprite.Group()
enemies = pygame.sprite.Group()
bonuses = pygame.sprite.Group()

# Sprites
S_BACKGROUND = pygame.transform.scale(pygame.image.load("sprites/background.png"), SCREEN_SIZE)
S_WALL_ORIGINAL = pygame.image.load("sprites/wall.png")
# TODO: resize wall (S_WALL = )

S_HEALTH = pygame.image.load("sprites/bonus_hp.png")
S_HEALTH = pygame.transform.scale(S_HEALTH, (int(S_HEALTH.get_width() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width())), int(S_HEALTH.get_height() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width()))))

S_BULLET = pygame.image.load("sprites/bullet.png")
S_BULLET = pygame.transform.scale(S_BULLET, (int(S_BULLET.get_width() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width())), int(S_BULLET.get_height() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width()))))

S_PLAYER = pygame.image.load("sprites/player.png")
S_PLAYER = pygame.transform.scale(S_PLAYER, (int(S_PLAYER.get_width() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width())), int(S_PLAYER.get_height() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width()))))
S_PLAYER_DEAD = pygame.image.load("sprites/player_dead.png")
S_PLAYER_DEAD = pygame.transform.scale(S_PLAYER_DEAD, (int(S_PLAYER_DEAD.get_width() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width())), int(S_PLAYER_DEAD.get_height() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width()))))

S_ENEMY = pygame.image.load("sprites/enemy.png")
S_ENEMY = pygame.transform.scale(S_ENEMY, (int(S_ENEMY.get_width() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width())), int(S_ENEMY.get_height() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width()))))
S_ENEMY_DEAD = pygame.image.load("sprites/enemy_dead.png")
S_ENEMY_DEAD = pygame.transform.scale(S_ENEMY_DEAD, (int(S_ENEMY_DEAD.get_width() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width())), int(S_ENEMY_DEAD.get_height() * (S_WALL.get_width()/S_WALL_ORIGINAL.get_width()))))
