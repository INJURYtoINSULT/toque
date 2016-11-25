import libtcodpy as libtcod
import math

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

MAP_WIDTH = 80
MAP_HEIGHT = 45

LIMIT_FPS = 20

color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3

FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

##################################
# Generic Classes
##################################

class Tile:
    #Map tile and its properties
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked
        
        #Tiles start unexplored
        self.explored = False

        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight

class Object:
    #Generic object
    def __init__(self, x, y, char, name, color, blocks = False, fighter = None, ai = None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:
            self.fighter.owner = self
        self.ai = ai
        if self.ai:
            self.ai.owner = self

    def move(self, dx, dy):
        #Move by given amount
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def move_toward(self, target_x, target_y):
        #Vector from this object to the target
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #Normalize it to length 1 (preserving direction) , then round it and
        #convert it to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other):
        #Return distance to another object
        dx = other.x - self.y
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def draw(self):
        #Only show if it is in fov
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            #set color, draw character
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        #erase the character that represents this object
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

#################################
# Object Children
#################################

class Fighter:
    #Combat-related properties and methods
    def __init__(self, hp, defense, power):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power

class BasicMonster:
    #AI for basic monster
    def take_turn(self):
        #A basic monster takes its turn. If you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):

            #Move towards the player if far away
            if monster.distance_to(player):
                monster.move_toward(player.x, player.y)
            
            #Close enough, attack (if player is alive)
            elif player.fighter.hp > 0:
                print 'The attack of ' + monster.name + ' bounces off of your shiny metal armor!'

def is_blocked(x, y):
    #First test map tile
    if map[x][y].blocked:
        return True

    #Now check Objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True
    
    return False

##################################
# Dungeon parts
##################################

class Rect:
    #A rectangle for creating a room
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
    
    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        #Returns true if this rect intersects with another
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)

def create_room(room):
    global map
    #Make floor tiles passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
    global map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

##################################
# Functions
##################################

def make_map():
    global map

    #Fill map with "blocked" tiles
    map = [[ Tile(True)
    for y in range(MAP_HEIGHT) ]
        for x in range(MAP_WIDTH) ]
            
    #Generate rooms     
    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        #Random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #Random position without going out of boundaries
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)
    
        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)

        #Run through the other rooms and see if they intersect with the others
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            create_room(new_room)
    
            (new_x, new_y) = new_room.center()
        
            if num_rooms == 0:
                player.x = new_x
                player.y = new_y
            else:
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                #Flip a coin
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #First move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    #First move vertically, then horizonally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            #Throw in some monsters
            place_objects(new_room)

            rooms.append(new_room)
            num_rooms += 1

def place_objects(room):
    #Choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

    for i in range(num_monsters):
        #Random position in room
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        if not is_blocked(x, y):
            if libtcod.random_get_int(0, 0, 100) < 80: #80% chance of rolling orc
                #Create an orc
                fighter_component = Fighter(hp = 10, defense = 0, power = 3)
                ai_component = BasicMonster()
                
                monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green, blocks = True, 
                        fighter = fighter_component, ai = ai_component)
            else:
                #Create a troll
                fighter_component = Fighter(hp = 16, defense = 1, power = 4)
                ai_component = BasicMonster()
                
                monster = Object(x, y, 'T', 'troll', libtcod.darker_green, blocks = True, 
                        fighter = fighter_component, ai = ai_component)

            objects.append(monster)

def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute

    if fov_recompute:
        #Recompute FOV
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = map[x][y].block_sight
                if not visible:
                    #If it's not visible right now, the player can only see it if it is already explored
                    if map[x][y].explored:
                        #It is out of FOV
                        if wall:
                            libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                        else:
                            libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                else:
                    #It's visible
                    if wall:
                        libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
                    else:
                        libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
                    #Since it is visible, explore it
                    map[x][y].explored = True

    #draw all objects in the list
    for object in objects:
        object.draw()

    #Blit to con
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

def player_move_or_attack(dx, dy):
    global fov_recompute

    #The coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy

    #Try to find an attackable object there
    target = None
    for object in objects:
        if object.x == x and object.y == y:
            target = object
            break

    #Attack if target found
    if target is not None:
        print 'The ' + target.name + ' laughs at your efforts to attack it!'
    else:
        player.move(dx, dy)
        fov_recompute = True

def handle_keys():
    global fov_recompute

    key = libtcod.console_wait_for_keypress(True)
    
    if key.vk == libtcod.KEY_ENTER and key.lalt: #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
                     
    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  #exit game

    if game_state == 'playing':
        #Movement Keys
        if libtcod.console_is_key_pressed(libtcod.KEY_UP):
            player_move_or_attack(0, -1)

        elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
            player_move_or_attack(0, 1)

        elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
            player_move_or_attack(-1, 0)

        elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
            player_move_or_attack(1, 0)
        
        else:
            return 'didnt-take-turn'

##################################
# Initializations
##################################

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Rogue', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

#Create objects representing the player
fighter_component = Fighter(hp = 30, defense = 2, power = 5)
player = Object(25, 23, '@', 'player',  libtcod.white, blocks = True, fighter = fighter_component)

#The list of objects of those two
objects = [player]

#Generate Map
make_map()

#Create FOV Map
fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

fov_recompute = True
game_state = 'playing'
player_action = None

##################################
# Main Loop
##################################

while not libtcod.console_is_window_closed():
    
    render_all()

    libtcod.console_flush()

    for object in objects:
        object.clear()

    #Player turn
    player_action = handle_keys()
    if player_action == 'exit':
        break

    #Let monsters take their turn
    if game_state == 'playing' and player_action != 'didnt-take-turn':
        for object in objects:
            if object.ai:
                object.ai.take_turn()
