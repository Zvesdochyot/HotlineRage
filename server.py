import sys
import socket
import threading
import pickle
import random
from os import system
from copy import deepcopy

BONUS_HP_CHANCE = 0.0008 / 100  # 0.00001% per frame


def receive_data_from_players(server, game_data, players):
    print("Started receiving data from players")
    while True:
        data, addr = receive_from_client(server)
        if data["code"] == "PLAYER_DEAD":
            print(f"Player {addr} died")

            for p in players:
                send_to_client({"code": "PLAYER_DEAD", "addr": addr}, p[0])

        else:
            game_data[addr] = data
            game_data["bullets"].extend(data["bullets"])


def send_new_data_to_players(data, players):
    global GAME_END

    print("Started sending data to players")
    bullets_sent = False

    while True:
        is_winner = {p: True if d["hp"] > 0 else False for p, d in
                     {k: v for k, v in data.items() if k != "bullets"}.items()}

        # Check if someone won
        if list(is_winner.values()).count(True) == 1:
            winner = None
            for p, w in is_winner.items():
                if w:
                    for pl in players:
                        if pl[0] == p:
                            winner = pl[2]
                    break

            for p in players:
                send_to_client({"code": "GAME_FINISHED", "winner": winner}, p[0])

            print(f"Player {winner} won")
            GAME_END = True
            sys.exit()

        # Bonuses
        bonuses = {}

        if random.random() <= BONUS_HP_CHANCE:
            bonuses["regen"] = (random.randint(tile_size[0], (map_size[0] - 1) * tile_size[0]),
                                random.randint(tile_size[1], (map_size[1] - 1) * tile_size[0]))

        # Send current game data
        if len(data["bullets"]) != 0:
            bullets_sent = True

        gd = deepcopy(data)  # Copy data before sending for sync
        for p in players:
            send_to_client({"code": None, **gd, **bonuses}, p[0])

        if bullets_sent:
            data["bullets"] = []
            bullets_sent = False


def send_to_client(data, client):
    server.sendto(pickle.dumps(data), client)


def receive_from_client(server):
    data, addr = server.recvfrom(2048)
    return pickle.loads(data), addr


HOST, PORT = 'localhost', 7777
GAME_END = False

addr = (HOST, PORT)
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(addr)

# Map of the game. Must be same size (10x10, 20x20, 30x30 etc.)
# # - wall
#   - void
# X - player
mp = '''
####################
#     #    #   X   #
#  X  #    #       #
#                  #
#                  #
#  #################
#  #               #
#  #               #
#  # X             #
#                  #
#  #               #
#  ####### #########
#                  #
#                  #
#                  #
#   ################
#                  #
#           X      #
#                  #
####################
'''

mp = mp.strip()
game_map = []

for yi, y in enumerate(mp.split("\n")):
    cur_y = []

    for xi, x in enumerate(y):
        if x == '#':
            cur_y.append(1)
        elif x == ' ':
            cur_y.append(0)
        elif x.lower() == 'x':
            cur_y.append(5)

    game_map.append(cur_y)

map_size = [len(game_map[0]), len(game_map)]
SCREEN_SIZE = [600, 600]
tile_size = [int(SCREEN_SIZE[0] / map_size[0]), int(SCREEN_SIZE[1] / map_size[1])]

players_coordinates = []

for yi, y in enumerate(game_map):
    for xi, x in enumerate(y):
        if x == 5:
            players_coordinates.append((xi, yi))

system("CLS")

print("Server started, waiting for players...")
PLAYERS = []

while len(PLAYERS) < len(players_coordinates):
    data, addr = receive_from_client(server)
    print(f'Player connected {addr}')
    PLAYERS.append((addr, players_coordinates[len(PLAYERS)], data["nickname"]))

    send_to_client({"code": "CONNECT_OK", "ip": addr}, addr)

print("\n\nAll players are connected. Game started")

for player in PLAYERS:
    send_to_client({"code": "START_GAME", "map": game_map, "player_coords": player[1], "player_address": player[0],
                    "enemies": PLAYERS}, player[0])

GAME_DATA = {"bullets": []}
for p in PLAYERS:
    GAME_DATA[p[0]] = {"coords": p[1], "angle": 0, "hp": 100}

print(PLAYERS)
recv_thread = threading.Thread(target=receive_data_from_players, args=(server, GAME_DATA, PLAYERS))
send_thread = threading.Thread(target=send_new_data_to_players, args=(GAME_DATA, PLAYERS))

recv_thread.start()
send_thread.start()

if GAME_END:
    server.close()
