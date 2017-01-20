import libtcodpy as libtcod
import math
import textwrap
import shelve

#Actual size of window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

#Size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 43

#Sizes and coordinates relevant to GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50
LEVEL_SCREEN_WIDTH = 40
CHARACTER_SCREEN_WIDTH = 30

#Spell values
HEAL_AMOUNT = 4
ROCK_DAMAGE = 20
LIGHTNING_RANGE = 5
CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 8
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12

#Experience and Level stats
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150

LIMIT_FPS = 30

color_dark_wall = libtcod.Color(18, 17, 17)
color_light_wall = libtcod.Color(193, 77, 42)
color_dark_ground = libtcod.Color(32, 32, 32)
color_light_ground = libtcod.dark_gray #libtcod.Color(255, 171, 64)

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 5

FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = MAP_HEIGHT

##################################
# Generic Classes
##################################

class Tile:
    #Map tile and its properties
    def __init__(self, blocked, char = ' ', block_sight = None):
        self.blocked = blocked
        self.char = char

        #Tiles start unexplored
        self.explored = False

        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight

class Chunk:
    #Map chunk and its properties
    def __init__(self, longitude, latitude, objects):
        self.latitude = latitude
        self.longitude = longitude
        self.objects = objects
   
    def load(self):
        global objects
        objects = [] 
        objects = self.objects
        print str(len(objects))

class Object:
    #Generic object
    def __init__(self, x, y, char, name, color, blocks = False, 
            always_visible = False, fighter = None, ai = None, item = None, equipment = None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.always_visible = always_visible
        self.fighter = fighter
        if self.fighter:
            self.fighter.owner = self
        self.ai = ai
        if self.ai:
            self.ai.owner = self
        self.item = item
        if self.item:
            self.item.owner = self
        self.equipment = equipment
        if self.equipment:
            self.equipment.owner = self
            
            #There must be an Item component for the Equipment component to work properly
            self.item = Item()
            self.item.owner = self

    def move(self, dx, dy):
        #Move by given amount
        if self.name == 'player':
            if not is_map_edge(self.x + dx, self.y + dy):
                if not is_blocked(self.x + dx, self.y + dy):
                    self.x += dx
                    self.y += dy
            else:
                global latitude, longitude, chunks, trees, distance_from_center
                render_all()
                if self.x + dx >= MAP_WIDTH:
                    longitude = longitude + 1
                    for chunk in chunks:
                        print str(chunk.longitude) + ', ' + str(chunk.latitude)
                        if chunk.latitude == latitude and chunk.longitude == longitude:
                            self.x = 0
                            libtcod.console_clear(con)
                            chunk.load()
                            distance_from_center = abs(latitude) + abs(longitude)
                            return
                    self.x = 0
                    libtcod.console_clear(con)
                    make_forest()

                elif self.x + dx < 0:
                    longitude = longitude - 1
                    for chunk in chunks:
                        print str(chunk.longitude) + ', ' + str(chunk.latitude)
                        if chunk.latitude == latitude and chunk.longitude == longitude:
                            self.x = MAP_WIDTH - 1
                            chunk.load()
                            distance_from_center = abs(latitude) + abs(longitude)
                            return
                    self.x = MAP_WIDTH - 1
                    libtcod.console_clear(con)
                    make_forest()

                elif self.y + dy >= MAP_HEIGHT:
                    latitude = latitude + 1
                    for chunk in chunks:
                        print str(chunk.longitude) + ', ' + str(chunk.latitude)
                        if chunk.latitude == latitude and chunk.longitude == longitude:
                            self.y = 0
                            libtcod.console_clear(con)
                            chunk.load()
                            distance_from_center = abs(latitude) + abs(longitude)
                            return
                    self.y = 0
                    libtcod.console_clear(con)
                    make_forest()

                elif self.y + dy < 0:
                    latitude = latitude - 1
                    for chunk in chunks:
                        print str(chunk.longitude) + ', ' + str(chunk.latitude)
                        if chunk.latitude == latitude and chunk.longitude == longitude:
                            self.y = MAP_HEIGHT - 1
                            libtcod.console_clear(con)
                            chunk.load()
                            distance_from_center = abs(latitude) + abs(longitude)
                            return
                    self.y = MAP_HEIGHT - 1
                    libtcod.console_clear(con)
                    make_forest()
                distance_from_center = abs(latitude) + abs(longitude)
                print distance_from_center

        else:
            if not is_map_edge(self.x + dx, self.y + dy):
                if not is_blocked(self.x + dx, self.y + dy):
                    self.x += dx
                    self.y += dy
            else:
                if self.x + dx >= MAP_WIDTH:
                    message('The ' + self.name + ' flees!', libtcod.yellow)
                    self.clear()
                    objects.remove(self)
                elif self.x + dx < 0:
                    message('The ' + self.name + ' flees!', libtcod.yellow)
                    self.clear()
                    objects.remove(self)
                elif self.y + dy >= MAP_HEIGHT:
                    message('The ' + self.name + ' flees!', libtcod.yellow)
                    self.clear()
                    objects.remove(self)
                elif self.y + dy < 0:
                    message('The ' + self.name + ' flees!', libtcod.yellow)
                    self.clear()
                    objects.remove(self)

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
    
    def move_away(self, target_x, target_y):
        #Vector from this object away from the target
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        dx = (-1) * int(round(dx / distance))
        dy = (-1) * int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other):
        #Return distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def distance(self, x, y):
        #Return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def send_to_back(self):
        #Make this object draw first
        global objects
        objects.remove(self)
        objects.insert(0, self)

    def send_to_front(self):
        global objects
        objects.remove(self)
        objects.append(self)

    def draw(self):
        #Only show if it is in fov
        if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or
                (self.always_visible and map[self.x][self.y].explored)):
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
    def __init__(self, hp, defense, power, xp, inventory=None, death_function = None):
        self.base_max_hp = hp
        self.hp = hp
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.base_inventory = inventory
        self.death_function = death_function

    @property
    def power(self): #Return actual power, by adding bonuses from all equipped items
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
        return self.base_power + bonus
    
    @property
    def defense(self): #Return actual power, by adding bonuses from all equipped items
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
        return self.base_defense + bonus

    @property
    def max_hp(self): #Return actual power, by adding bonuses from all equipped items
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_hp + bonus

    @property
    def inventory(self): #Return actual inventory size, by adding bonuses from all equipped items
        bonus = sum(equipment.inventory_bonus for equipment in get_all_equipped(self.owner))
        return self.base_inventory + bonus

    def attack(self, target):
        #Simple formula for attack damage
        damage = self.power - target.fighter.defense

        if damage > 0:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' Hit points!')
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')

    def take_damage(self, damage):
        #Apply damage if possible
        if damage > 0:
            self.hp -= damage

            #Check for death
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)

                if self.owner != player: #Yield experience to the player
                    player.fighter.xp += self.xp

    def heal(self, amount):
        #Heal by the given amount without going over
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

class BasicMob:
    #AI for basic mob
    def take_turn(self):
        #A basic mob takes its turn. If you can see it, it can see you
        mob = self.owner
        if libtcod.map_is_in_fov(fov_map, mob.x, mob.y):

            #Move towards the player if far away
            if mob.distance_to(player) >= 2:
                mob.move_toward(player.x, player.y)
            
            #Close enough, attack (if player is alive)
            elif player.fighter.hp > 0:
                mob.fighter.attack(player)

class SkittishMob:
    #Ai for small easily frightened woodland creatures
    def take_turn(self):
        mob = self.owner
        if mob.distance_to(player) < 5:
            mob.move_away(player.x, player.y)            

class ConfusedMob:
    #AI for temporarily confused mob (Reverts to previous ai after a while)
    def __init__(self, old_ai, num_turns = CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns

    def take_turn(self):
        if self.num_turns > 0: #Still confused...
            #Move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns -= 1

        else: #Restore the previous ai (this one will be deleted because it's not anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)

class Item:
    #An item that can be picked up and used
    def __init__(self, use_function=None):
        self.use_function = use_function

    #An item that can be picked up and used
    def pick_up(self):
        #Add to player's inventory and remove from map
        if self.owner.equipment and get_equipped_in_slot(self.owner.equipment.slot) is None:
            inventory.append(self.owner)
            objects.remove(self.owner)
            self.owner.equipment.equip()            
        elif len(inventory) >= player.fighter.inventory:
            self.owner.send_to_front()
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up ' + self.owner.name + '!', libtcod.green)

            #Special case: automatically equip, if the corresponding equipment slot is unused
            equipment = self.owner.equipment
            if equipment and get_equipped_in_slot(equipment.slot) is None:
                equipment.equip()
    
    def drop(self):
        #Special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip()
        
        #Add to the map and remove from the player's inventory, also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        
        self.owner.x = player.x
        self.owner.y = player.y

        message('You dropped a ' + self.owner.name + '.', libtcod.yellow)

    def use(self):
        #Special case: if the object has the equipment component, the 'use' action is to equip/dequip
        if self.owner.equipment:
            self.owner.equipment.toggle_equip()
            return
        
        #Just call the "use function" if it is defined
        if self.use_function is None:
            message('The ', self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner) #Destroy after use

class Equipment:
    #An object that can be equipped, yielding bonuses, automatically adds the item component.
    def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0, inventory_bonus=0):
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus
        self.inventory_bonus = inventory_bonus

        self.slot = slot
        self.is_equipped = False

    def toggle_equip(self): #Toggle equip/dequip status
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()

    def equip(self):
        #If the slot is already being used, dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.slot)
        if old_equipment is not None:
            old_equipment.dequip()

        self.is_equipped = True
        message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)

    def dequip(self):
        #Dequip object and show a message about it
        self.is_equipped = False
        message('Dequipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_yellow)

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
    rubble_chances = {'space': 90, 'period': 5, 'comma': 5}
    #Make floor tiles passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            choice = random_choice(rubble_chances) #Picking random litter for the cave floor
            rubble = {'space': ' ', 'period': '.', 'comma': ','}
            map[x][y].blocked = False
            map[x][y].block_sight = False
            map[x][y].char = rubble[choice]

def create_h_tunnel(x1, x2, y):
    global map
    rubble_chances = {'space': 90, 'period': 5, 'comma': 5}
    for x in range(min(x1, x2), max(x1, x2) + 1):
        choice = random_choice(rubble_chances)
        rubble = {'space': ' ', 'period': '.', 'comma': ','}
        map[x][y].blocked = False
        map[x][y].block_sight = False
        map[x][y].char = rubble[choice]

def create_v_tunnel(y1, y2, x):
    global map
    rubble_chances = {'space': 90, 'period': 5, 'comma': 5}
    for y in range(min(y1, y2), max(y1, y2) + 1):
        choice = random_choice(rubble_chances)
        rubble = {'space': ' ', 'period': '.', 'comma': ','}
        map[x][y].blocked = False
        map[x][y].block_sight = False
        map[x][y].char = rubble[choice]

##################################
# GUI Elements
##################################

def menu(header, options, width):
    if len(options) > 26: ValueError('Cannot have a menu with more than 26 options.')
    #Calculate total height of the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    height = len(options) + header_height

    if header == '':
        header_height = 0

    #Create an offscreen console that represents the menu's window
    window = libtcod.console_new(width, height)

    #Print the header with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
    #Print all of the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1

    #Blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    #Present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)

    if key.vk == libtcod.KEY_ENTER and key.lalt: #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
    
    #Convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None

def inventory_menu(header):
    #Show a menu with each new item of the inventory as an option
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in inventory:
            text = item.name
            #Show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)

    index = menu(header, options, INVENTORY_WIDTH)

    #If an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory[index].item

def msgbox(text, width=50):
    menu(text, [], width) #Use menu() as a sort of message box

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #Render a bar (HP, XP, ETC), first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)

    #Render the background first
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    #Now render the bar on top
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    #Finally, some centered texts with values
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
            name + ': ' + str(value) + '/' + str(maximum))

def message (new_msg, color = libtcod.white):
    #Split message across lines if necessary
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        #if the buffer is full, remove the first one to make room for new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        #Add the new line as a tuple, with the text and color
        game_msgs.append( (line, color) )

def get_names_under_mouse():
    global mouse

    #Return a string with the names of all objects under the mouse
    (x, y) = (mouse.cx, mouse.cy)

    #Create a list with the names of all objects at the mouse's coordinates and in fov
    names = [obj.name for obj in objects 
            if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

    names = ', '.join(names)
    return names.capitalize()

##################################
# Functions
##################################

def make_forest():
    global map, objects
    global latitude, longitude

    objects = [player]

    map = [[ Tile(False)
        for y in range(MAP_HEIGHT) ]
        for x in range(MAP_WIDTH) ]
    place_objects(Rect(1, 1, MAP_WIDTH - 1, MAP_HEIGHT - 1))
    new_chunk = Chunk(longitude, latitude, objects)
    if not any(chunk.latitude == latitude for chunk in chunks) or not any(chunk.longitude == longitude for chunk in chunks):
        print 'New chunk: ' + str(new_chunk.latitude) + ', ' + str(new_chunk.longitude)
        chunks.append(new_chunk)
    print str(len(objects))

#def load_forest(Chunk):
#    objects = []
#    objects = chunk.object

#    render_all()

#def load_hub():

def make_map():
    global map, objects, stairs

    #The list of objects with just the player
    objects = [player]
    
    rubble_chances = {'space': 496, 'period': 2, 'comma': 2, 'backtick': 2, 'asterisk': 1}
    
    rubble = {'space': ' ', 'period': '.', 'comma': ',', 'backtick': '`', 'asterisk': '*'}
    
    #Fill map with "blocked" tiles
    map = [[ Tile(True)
    for y in range(MAP_HEIGHT) ]
        for x in range(MAP_WIDTH) ]
    
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            choice = random_choice(rubble_chances) #Picking random litter for the cave floor
            map[x][y].char = rubble[choice]

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

            #Throw in some mobs
            place_objects(new_room)

            rooms.append(new_room)
            num_rooms += 1

    #Create stairs at the center of the last room
    stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible = True)
    objects.append(stairs)
    stairs.send_to_back() #So it is drawn below the mobs

def random_choice_index(chances): #Choose one option from list of chances, returning its index
    #The dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))

    #Go throw all chances keeping, the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w

        #See if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1

def random_choice(chances_dict):
    #Choose one option from the dictionary, returning its keys
    chances = chances_dict.values()
    strings = chances_dict.keys()

    return strings[random_choice_index(chances)]

def from_distance(table):
    #Returns a value that depends on level, the table specifies what value occurs after each level, default is 0
    for (value, distance) in reversed(table):
        if distance_from_center >= distance:
            return value
    return 0

def place_objects(room):
    global trees
    #Choose random number of mobs
    num_mobs = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

    #Maximum number of mobs per room
    max_mobs = from_distance([[2, 1], [3, 4], [5, 6]])

    #Chance of each mob
    mob_chances = {}
    mob_chances['squirrel'] = 80 #Bear always shows up even if all other mobs have 0 chance
    mob_chances['bear'] = from_distance([[15, 3], [30, 5], [60, 7]])

    #Maximum number of items per room
    max_items = from_distance([[1, 1], [2, 4]])

    #Chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    item_chances['heal'] =      20 #Healing potion always shows up, even if all other items have 0 chance
    item_chances['rock'] =      35
    item_chances['fireball'] =  from_distance([[25, 6]])
    item_chances['confuse'] =   from_distance([[10, 2]])
    item_chances['sword'] =     from_distance([[5, 4]])
    item_chances['shield'] =    from_distance([[15, 8]])

    rubble_chances = {'tree': 1, 'none': 19}
    
    trees = []

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if (random_choice(rubble_chances) == 'tree'):
                tree = Object(x, y, 179, 'white spruce', libtcod.darker_sepia, blocks=True)
                trees.append(tree)
                objects.append(tree)
    
#    for i in range(1):
#        for tree in trees:
#            if get_neighbors(10, tree.x, tree.y) < 2: #Tree is lonely
#                tree.clear()
#                trees.remove(tree)
#                objects.remove(tree)
#            elif get_neighbors(6, tree.x, tree.y) == 4: #Tree is healthy
#                new_x = libtcod.random_get_int(0, tree.x - 3, tree.x - 3)
#                new_y = libtcod.random_get_int(0, tree.y - 3, tree.y - 3)
#                new_tree = Object(new_x, new_y, 't', 'tree', libtcod.darker_sepia, blocks=True)
#                trees.append(new_tree)
#                objects.append(new_tree)
#            elif get_neighbors(3, tree.x, tree.y) > 6: #Tree is overcrowded
#                tree.clear()
#                trees.remove(tree)
#                objects.remove(tree)
            #Else the tree is in balance

    for i in range(num_mobs):
        #Random position in room
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        if not is_blocked(x, y):
            choice = random_choice(mob_chances)
            if choice == 'squirrel':
                #Create a squirrel
                fighter_component = Fighter(hp = 10, defense = 0, power = 3, xp = 35, death_function = mob_death)
                ai_component = SkittishMob()
                
                mob = Object(x, y, 's', 'eastern fox squirrel', libtcod.Color(139, 69, 19), blocks = True, 
                        fighter = fighter_component, ai = ai_component)
            elif choice == 'bear':
                #Create a bear
                fighter_component = Fighter(hp = 16, defense = 10, power = 15, xp = 100, death_function = mob_death)
                ai_component = BasicMob()
                
                mob = Object(x, y, 'B', 'brown bear', libtcod.Color(139, 69, 19), blocks = True, 
                        fighter = fighter_component, ai = ai_component)

            objects.append(mob)

    #Choose random number of items
    num_items = libtcod.random_get_int(0, 0, MAX_ROOM_ITEMS)

    for i in range(num_items):
        #Choose random spot for this item
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        #Only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(item_chances)
            if choice == 'heal':
                #Create a healing potion(70% chance)
                item_component = Item(use_function = cast_heal)
                
                item = Object(x, y, '!', 'healing potion', libtcod.violet, item = item_component)
            
            elif choice == 'rock':
                #Create a lightning bolt scroll (10% chance)
                item_component = Item(use_function = throw_rock)

                item = Object(x, y, 'o', 'hefty rock', libtcod.grey, item=item_component)
            
            elif choice == 'fireball':
                #Create a fireball scroll (10% chance)
                item_component = Item(use_function = throw_rock)

                item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component)
            
            elif choice == 'confuse':
                #Create a confuse scroll (10% chance)
                item_component = Item(use_function = cast_confuse)

                item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component)

            elif choice == 'sword':
                #Create a sword
                equipment_component = Equipment(slot='right hand', power_bonus=3)
                item = Object(x, y, '/', 'sword', libtcod.sky, equipment=equipment_component)

            elif choice == 'shield':
                #Create a shield
                equipment_component = Equipment(slot='left hand', defense_bonus=1)
                item = Object(x, y, '[', 'shield', libtcod.darker_orange, equipment=equipment_component)
            
            objects.append(item)
            item.send_to_back() #Items appear below other items

def is_blocked(x, y):
    #First test map tile
    if map[x][y].blocked:
        return True

    #Now check Objects
    for object in objects:
    #    print
        if object.blocks and object.x == x and object.y == y:
            return True
    return False

def is_map_edge(x, y):
    if x == MAP_WIDTH or y == MAP_HEIGHT:
        return True
    elif x < 0  or y < 0:
        return True
    return False

def get_neighbors(size, x, y):
    neighbors = 0
    libtcod.console_set_char_background(con, x, y, libtcod.red, libtcod.BKGND_SET)
    for new_x in xrange(x - size, x + size):
        for new_y in xrange(y - size, y + size):
            for tree in trees:
                if tree.x == new_x and tree.y == new_y:
                    neighbors += 1
    return neighbors

def get_equipped_in_slot(slot): #Returns the equipment in a slot, or None if it's empty
    for obj in inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None

def get_all_equipped(obj): #Returns a list of equipped items
    if obj == player:
        equipped_list = []
        for item in inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)
        return equipped_list
    else:
        return [] #No other objects should have equipment

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

                distance_light = TORCH_RADIUS + 1 - player.distance(x, y) #Make the light dimmer further from player
                distance_dark = SCREEN_WIDTH - player.distance(x, y)
                distance_light = abs(distance_light) ** 0.5 #Square root to make transition non linear
                distance_dark = abs(distance_dark) ** 0.5
     
                if not visible:
                    #If it's not visible right now, the player can only see it if it is already explored
                    if map[x][y].explored:
                        #It is out of FOV
                        if wall:
                            libtcod.console_set_char_background(con, x, y, 
                                    color_dark_wall * (0.075) * distance_dark, libtcod.BKGND_SET)
                        else:
                            libtcod.console_set_char_background(con, x, y, 
                                    color_dark_ground * (0.075) * distance_dark, libtcod.BKGND_SET)
                            libtcod.console_set_char(con, x, y, ' ')
                else:
                    #It's visible
                    if wall:
                        libtcod.console_set_char_background(con, x, y, 
                                color_light_wall * (0.35) * distance_light, libtcod.BKGND_SET)
                    else:
                        libtcod.console_set_char_background(con, x, y, 
                                color_light_ground * (0.35) * distance_light, libtcod.BKGND_SET)
                        libtcod.console_set_char_foreground(con, x, y, libtcod.dark_orange)
                        libtcod.console_set_char(con, x, y, map[x][y].char)
                    #Since it is visible, explore it
                    map[x][y].explored = True

    #draw all objects in the list
    for object in objects:
        object.draw()
    player.draw()

    #Blit to con
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

    #Prepare to render GUI panel
    libtcod.console_set_default_background(panel, libtcod.darkest_grey)
    libtcod.console_clear(panel)

    #Print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    #Show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
            libtcod.light_red, libtcod.darker_red)
    
    level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
    render_bar(1, 2, BAR_WIDTH, 'XP', player.fighter.xp, level_up_xp,
            libtcod.darker_green, libtcod.darkest_green)

    #Print dungeon level
    libtcod.console_print_ex(panel, 1, 4, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon Level: ' + str(distance_from_center))
    libtcod.console_print_ex(panel, 1, 5, libtcod.BKGND_NONE, libtcod.LEFT, 'Player Level: ' + str(player.level))

    #Display names of objects under the mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

    #Blit the contents of panel to root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def player_move_or_attack(dx, dy):
    global fov_recompute

    #The coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy

    #Try to find an attackable object there
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break

    #Attack if target found
    if target is not None:
        player.fighter.attack(target)
    else:
        player.move(dx, dy)
        fov_recompute = True

def handle_keys():
    global fov_recompute
    global key
 
    if key.vk == libtcod.KEY_ENTER and key.lalt: #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
                     
    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  #exit game

    if game_state == 'playing':
        #Movement Keys
        if key.vk == libtcod.KEY_UP:
            player_move_or_attack(0, -1)

        elif key.vk == libtcod.KEY_DOWN:
            player_move_or_attack(0, 1)

        elif key.vk == libtcod.KEY_LEFT:
            player_move_or_attack(-1, 0)

        elif key.vk == libtcod.KEY_RIGHT:
            player_move_or_attack(1, 0)
        
        else:
            #Test for other keys
            key_char = chr(key.c)

            if key_char == 'g':
                #Pick up item
                for object in objects:
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up()
                        break

            if key_char == 'i':
                #Show the inventory; if an item is selected use it
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()

            if key_char == 'd':
                #Show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.drop()
            
            if key_char == 'e':
                #Go down stairs if player is standing on them
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()

            if key_char == 'c':
                #Show character information
                level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
                msgbox('Character information\n\nLevel: ' + str(player.level) +
                        '\nExperience: ' + str(player.fighter.xp) +
                        '\n\nMaximum HP: ' + str(player.fighter.max_hp) +
                        '\nAttack: ' + str(player.fighter.power) +
                        '\nDefense: ' + str(player.fighter.defense), CHARACTER_SCREEN_WIDTH)

            return 'didnt-take-turn'

def player_death(player):
    #The game ended
    global game_state
    message('You died!', libtcod.red)
    game_state = 'dead'
    
    #For added effect, transform the player into a corpse
    player.char = '%'
    player.color = libtcod.dark_red

def mob_death(mob):
    #Transform into corpse, remove blocking, can't be attacked or move
    message(mob.name.capitalize() + ' is dead! You gain ' + str(mob.fighter.xp) +
            ' experiecne points.' , libtcod.orange)
    mob.char = '%'
    mob.color = libtcod.dark_red
    mob.blocks = False
    mob.fighter = None
    mob.ai = None
    mob.name = 'remains of ' + mob.name
    mob.send_to_back()

def check_level_up():
    #See if the player's experience is enough to level up
    level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
    if player.fighter.xp >= level_up_xp:
        #Level up
        player.level += 1
        player.fighter.xp -= level_up_xp
        message('You grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)
    
        choice = None
        while choice == None: #Keep asking until a choice is made
            choice = menu('Level up! Choose a stat to focus:\n',
                    ['Constitution (+20 HP, from ' + str(player.fighter.max_hp) + ')',
                        'Strength (+1 attack, from ' + str(player.fighter.power) + ')',
                        'Agility (+1 defense, from ' + str(player.fighter.defense) + ')'], LEVEL_SCREEN_WIDTH)
            if choice == 0:
                player.fighter.base_max_hp += 20
                player.fighter.hp += 20
            elif choice == 1:
                player.fighter.base_power += 1
            elif choice == 2:
                player.fighter.base_defense += 1

def target_tile(max_range=None):
    #Return of a tile left-clicked in player's FOV (optionally in range), or (None, None) if right-clicked
    global key, mouse
    while True:
        #Render the screen, this erases the inventory and shows the name of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)
        render_all()

        (x, y) = (mouse.cx, mouse.cy)

        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            message('Attack canceled')
            return (None, None) #Cancel if the player right clicked or pressed escape
        #Accept the target if the player clicked in FOV
        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
                (max_range is None or player.distance(x, y) <= max_range)):
            return(x, y)

def target_mob(max_range=None):
    #Returns a clicked mob inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None: #Player cancelled
            return None

        #Returns the first clicked mob, otherwise continue looping
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj

def closest_mob(max_range):
    #Find the closest enemy, up to a maximum range, and in the players fov
    closest_enemy = None
    closest_dist = max_range + 1 #Start with slightly more than max range

    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #Calculate the distance between this object and the player
            dist = player.distance_to(object)
            if dist < closest_dist: #It's closer, so remember it
                closest_enemy = object
                closest_dist = dist
    return closest_enemy

def cast_heal():
    #Heal the player
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'
    
    message('Your wounds start to feel better', libtcod.light_violet)
    player.fighter.heal(HEAL_AMOUNT)

def throw_rock():
    #Throw a rock at a target and damage it
    
    mob = None

    message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
    (x, y) = target_tile()
    if x is None: return 'cancelled'
    for obj in objects:
        if obj.x == x and obj.y == y:
            mob = obj
    if mob is None: #No enemy within maximum range
        message('No enemy is close enough to strike.', libtcod.red)
        return 'cancelled'
    
    distance = mob.distance_to(player)
    distance = int(round(distance))

    hit_chances = {}
    hit_chances['hit'] = 1
    hit_chances['miss'] = 1 * distance
    choice = random_choice(hit_chances)
    
    if choice == 'hit':
        #Zap it
        message('A rock strikes the ' + mob.name + ' with a thud! The damage is ' + str(ROCK_DAMAGE) + ' hit points.', libtcod.light_blue)
        mob.fighter.take_damage(ROCK_DAMAGE)
    else:
        message('The rock misses!')
        

def cast_fireball():
    #Ask the player for a target tile to throw a fireball at
    message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
    (x, y) = target_tile()
    if x is None: return 'cancelled'
    message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)

    for obj in objects: #Damage every fighter in range, including the player
        if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
            message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
            obj.fighter.take_damage(FIREBALL_DAMAGE)

def cast_confuse():
    #Ask the player for a target to confuse
    message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
    mob = target_mob(CONFUSE_RANGE)
    if mob is None: return 'cancelled'

    #Replace the mob's AI with a "confused" one; after some turns it will restore the old AI
    old_ai = mob.ai
    mob.ai = ConfusedMob(old_ai)
    mob.ai.owner = mob #Tell the component who owns it
    message('The eyes of the ' + mob.name + ' look vacant and it begins to stumble around.', libtcod.green)

##################################
# Game functions
##################################

def new_game():
    global player, inventory, game_msgs, game_state, distance_from_center, latitude, longitude, chunks
    
    #Create object representing player
    fighter_component = Fighter(hp = 30, defense = 2, power = 5, xp = 0, inventory = 0, death_function = player_death)
    player = Object(25, 23, '@', 'player',  libtcod.black, blocks = True, fighter = fighter_component)

    player.level = 1

    latitude = 0
    longitude = 0
    chunks = []

    #Generate Map
    distance_from_center = 0
    make_forest()
    initialize_fov()

    game_state = 'playing'
    inventory = []

    #create the list of game messages and their colors, starts empty
    game_msgs = []

    #Warm welcoming message!
    message('Welcome stranger!, Prepare to perish in the tombs of ancient kings!', libtcod.red)

    #Initial equipment, jeans, hoodie, small pack 
    jeans_component = Equipment(slot='legs', inventory_bonus=3)
    jeans = Object(0, 0, 'N', 'blue jeans', libtcod.darkest_blue, equipment=jeans_component)
    inventory.append(jeans)
    jeans_component.equip()
    
    hoodie_component = Equipment(slot='torso', inventory_bonus=2)
    hoodie = Object(0, 0, 'T', 'grey hoodie', libtcod.darker_grey, equipment=hoodie_component)
    inventory.append(hoodie)
    hoodie_component.equip()
    
    toque_component = Equipment(slot='head', inventory_bonus=1)
    toque = Object(0, 0, 'D', 'light blue toque', libtcod.light_blue, equipment=toque_component)
    inventory.append(toque)
    toque_component.equip()

def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True

    #Create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
    
    libtcod.console_clear(con) #Unexplored areas start as black

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.console_set_char_background(con, x, y, libtcod.black)
            libtcod.console_set_char_foreground(con, x, y, libtcod.darker_grey)
            libtcod.console_set_char(con, x, y, map[x][y].char)
    
def next_level():
    #Advance to next level
    global dungeon_level
    message('You take a moment to rest and recover your strength.', libtcod.light_violet)
    player.fighter.heal(player.fighter.max_hp/2) #Heal the player by half of their max health

    message('You delve deeper into the dungeon.', libtcod.red)
    make_map() #Create a fresh new level
    initialize_fov()

    dungeon_level += 1

def play_game():
    global key, mouse

    player_action = None

    mouse = libtcod.Mouse()
    key = libtcod.Key()
    while not libtcod.console_is_window_closed():
        
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_RELEASE|libtcod.EVENT_MOUSE,key,mouse)
        render_all()

        libtcod.console_flush()

        #Level up if needed
        check_level_up()

        for object in objects:
            object.clear()

        #Player turn
        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break

        #Let mobs take their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    object.ai.take_turn()

def save_game():
    #Open a new empty shelve (possibly overwriting an old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    file['player_index'] = objects.index(player) #Index of player in object list
    file['inventory'] = inventory
    file['game_msgs'] = game_msgs
    file['game_state'] = game_state
#    file['stairs_index'] = objects.index(stairs) #Index of stairs in object list
    file['distance_from_center'] = distance_from_center
    file.close()

def load_game():
    #Open previously saved shelve and load game data
    global map, objects, player, inventory, game_msgs, game_state, stairs, distance_from_center

    file = shelve.open('savegame', 'r')
    map = file['map']
    objects = file['objects']
    player = objects[file['player_index']] #Get index of player in objects list and access it
    inventory = file['inventory']
    game_msgs = file['game_msgs']
    game_state = file['game_state']
#    stairs = objects[file['stairs_index']] #Get index of stairs in objects list and access it
    distance_from_center = file['distance_from_center']
    file.close()

    initialize_fov()

def main_menu():
    while not libtcod.console_is_window_closed():
        #Show the games title and some credits
        libtcod.console_set_default_foreground(0, libtcod.light_yellow)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 4, libtcod.BKGND_NONE, libtcod.CENTER, 'Toque')
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT - 2, libtcod.BKGND_NONE, libtcod.CENTER,'By Lenix')
        
        #Show the options and wait for the player's choice
        choice = menu('', ['New Game', 'Load', 'Quit'], 24)

        if choice == 0:
            new_game()
            play_game()
        elif choice == 1:
            try:
                load_game()
            except:
                msgbox('\n\n\n\nNo saved game to load. \n', 24)
                continue
            play_game()
        elif choice == 2:
            break

##################################
# Main Loop
##################################

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Rogue', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

main_menu()
