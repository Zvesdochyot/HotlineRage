import socket
import pickle
from os import system


def send_to_client(data, client):
    server.sendto(pickle.dumps(data), client)


def recieve_from_client(server):
    data, addr = server.recvfrom(2048)
    return (pickle.loads(data), addr)


HOST, PORT = 'localhost', 7777
GAMEEND = False

addr = (HOST, PORT)
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(addr)

# -------------------------------------------------------

# Map of the game. ALWAYS SAME SIZE (10x10, 20x20, 30x30 etc.)
# # - wall
#   - void
# X - player
mp = '''
##########
#    #   #
#  X #   #
#        #
#        #
#  #######
#  #     #
#  #     #
#    X   #
#        #
##########
'''

mp = mp.strip()

gamemap = []

for yi, y in enumerate(mp.split("\n")):
    cur_y = []

    for xi, x in enumerate(y):
        if x == '#':
            cur_y.append(1)
        elif x == ' ':
            cur_y.append(0)
        elif x.lower() == 'x':
            cur_y.append(5)

    gamemap.append(cur_y)

mapsize = [len(gamemap[0]), len(gamemap)]
SCREEN_SIZE = [600, 600]
tilesize = [int(SCREEN_SIZE[0]/mapsize[0]), int(SCREEN_SIZE[1]/mapsize[1])]

players_coords = []

for yi, y in enumerate(gamemap):
    for xi, x in enumerate(y):
        if x == 5:
            players_coords.append((xi, yi))

system("CLS")
# -------------------------------------------------------

print("Server started, waiting for players...")
PLAYERS = []


while len(PLAYERS) < len(players_coords):
    data, addr = recieve_from_client(server)
    print(f'Player connected {addr}')
    PLAYERS.append((addr, players_coords[len(PLAYERS)], data["nickname"]))
    send_to_client({"code": "CONNECT_OK", "ip": addr}, addr)
