from . import socketio, redis, emitter
from flask import Blueprint, g
from typing import List, Dict
import math
from datetime import datetime
import pickle

models = Blueprint('models', __name__,
                        template_folder='templates',
                        static_folder="static")


class AttributeDictProxy:
    def __init__(self, parent, name):
        self._parent = parent
        self._name = name

    def __getitem__(self, key):
        return self._parent._attributes[self._name][key]

    def __setitem__(self, key, value):
        self._parent._attributes[self._name][key] = value
        self._parent.save_to_redis()

    def __contains__(self, key):
        return key in self._parent._attributes[self._name]

    def items(self):
        return self._parent._attributes[self._name].items()

    def keys(self):
        return self._parent._attributes[self._name].keys()

    def values(self):
        return self._parent._attributes[self._name].values()
    
    def __len__(self):
        return len(self._parent._attributes[self._name])
    
    def __or__(self, other):
        if not isinstance(other, AttributeDictProxy):
            return NotImplemented
        new_dict = AttributeDictProxy(self._parent, self._name)
        combined_attributes = {**self._parent._attributes[self._name], **other._parent._attributes[other._name]}
        self._parent._attributes[self._name] = combined_attributes
        return new_dict
    
    def get(self, key, default=None):
        return self._parent._attributes[self._name].get(key, default)
    
    def pop(self, key, default=None):
        value = self._parent._attributes[self._name].pop(key, default)
        self._parent.save_to_redis()
        return value

class Player:
    notoriety_levels = {
        1: "You're practically invisible to the world; no one knows your name.",
        2: "A few people might recognize you, but you're mostly overlooked.",
        3: "You have a small degree of recognition; a few people know of you.",
        4: "Your name is occasionally whispered in some circles. You're starting to get noticed.",
        5: "You've earned a good reputation; many people know and respect you.",
        6: "Your influence is growing. You're a well-known figure in certain circles.",
        7: "Your fame has spread wide; crowds gather, and fans celebrate you.",
        8: "Your name is known, but not always for good reasons. You're a figure of controversy.",
        9: "Tales of your deeds are shared far and wide; you're the stuff of legends.",
        10: "Your very existence seems otherworldly. People speak of you with awe, as if you're from myths."
    }

    financial_health_table = {
        (1, 1): "You live hand-to-mouth, scraping by with what little you have, but thankfully with minimal debt to weigh you down.",
        (1, 2): "You're at the bottom rung, living frugally while the specter of debt casts a constant shadow.",
        (1, 3): "Desperation defines your days as you're destitute and sinking further into the quagmire of debt.",

        (2, 1): "With meager possessions, you've managed to keep your debt at bay, making small but sure steps forward.",
        (2, 2): "Your limited assets barely keep pace with the bills piling up, making every financial decision a juggling act.",
        (2, 3): "Though you have some belongings, they're overshadowed by the heavy cloud of crippling debt.",

        (3, 1): "You maintain a middle-class life, balancing expenses comfortably with minimal debt to your name.",
        (3, 2): "Living an average life, you find yourself constantly budgeting to keep up with the growing debt payments.",
        (3, 3): "While you live modestly, your expenses often outpace your income due to mounting debts.",

        (4, 1): "You've carved out a decent life for yourself, enjoying some luxuries without the burden of heavy debt.",
        (4, 2): "Although you've accumulated some wealth, your lifestyle is tempered by the monthly reminders of significant debt.",
        (4, 3): "Your decent lifestyle is offset by the stress of large debt payments, always stretching your budget thin.",

        (5, 1): "You enjoy many comforts of an upscale life with minimal debt to mar the experience.",
        (5, 2): "Your lifestyle is a mix of luxury and caution as you enjoy finer things, but also manage a looming debt.",
        (5, 3): "With an upscale life, you often find that your lavish spending is not quite matched by your income, leading to increasing debts.",

        (6, 1): "Leading a life of luxury, your assets are vast and your worries about debt are few.",
        (6, 2): "In the world of the well-off, you maneuver between enjoying your wealth and strategically managing your sizable debts.",
        (6, 3): "While indulging in the finer things, the costs often catch up, making you rethink some of your extravagant choices.",

        (7, 1): "Your immense wealth places you among the elite, living large with almost no financial concerns.",
        (7, 2): "Surrounded by opulence, you also navigate the complexities of sizable debts, always ensuring they don't overshadow your assets.",
        (7, 3): "Living the high life comes with its pressures, as your high rolling is occasionally checked by considerable debts.",

        (8, 1): "At the zenith of affluence, your life is an epitome of luxury with negligible financial worries.",
        (8, 2): "You're the talk of the town, living grandly, though some expenses are funded by strategic debts.",
        (8, 3): "Your extravagant life, while awe-inspiring, also hides the tightrope you walk, balancing massive debts."
    }

    def __init__(self):
        self._attributes = {
            'diplomacy': 0,
            'force': 0,
            'insight': 0,
            'start_commerce': 0,
            'wealth': 0,
            'debt': 0,
            'income': 0,
            'expenses': 0,
            'health': 15,
            'notoriety': 1,
            'name': "",
            'location': "At a resting place.",
            'age': "",
            'occupation': "",
            'relations': "",
            'background': "",
            'lifestyle': "",
            'standing': "",
            'people': [],
            'objects': [],
            'places': [],
            'personality': [],
            'worldview': [],
            'socialclass': [],
            'stability': 100,
            'traits': [],
            'communication': []
        }
        self.save_to_redis()
        
    def save_to_redis(self):
        redis.set(f'player', pickle.dumps(self._attributes))
    
    def __getattr__(self, name):
        player_data = redis.get('player')
        if player_data:
            self._attributes = pickle.loads(player_data)
        # First, check if the attribute is a class property or method
        if name in self.__class__.__dict__:
            return object.__getattribute__(self, name)
        # Then check the _attributes dictionary
        try:
            value = self._attributes[name]
            if isinstance(value, dict):
                return AttributeDictProxy(self, name)
            return value
        except KeyError:
            raise AttributeError(f"'Player' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        # To avoid recursion, only use _attributes for storing player attributes
        if name in ['_attributes']:
            super().__setattr__(name, value)
        else:
            self._attributes[name] = value
            self.save_to_redis()

    @property
    def items(self):
        print(self.people)
        print(self.objects)
        print(self.places)
        return self.people | self.objects | self.places

    @property
    def financial_health_str(self):        
        # Calculate debt ratio
        ratio = self.debt / self.wealth
        if ratio < 0.3:
            debt_ratio = 1  # Low
        elif ratio < 0.8:
            debt_ratio = 2  # Medium
        else:
            debt_ratio = 3  # High

        return self.financial_health_table[(self.commerce, debt_ratio)]

    @property
    def strength(self):
        return round((self.force + self.diplomacy + self.insight)/3)
    
    @property
    def power(self):
        return self.strength*(1+self.commerce/10+self.notoriety/10)

    @property
    def notoriety_str(self):
        return self.notoriety_levels[round(self.notoriety)]

    @property
    def personality_str(self):
        if len(self.personality) == []:
            return ""
        else:
            return self.personality['name'] + ": " + self.personality['description']
        
    @property
    def worldview_str(self):
        if len(self.worldview) == []:
            return ""
        else:
            return self.worldview['name'] + ": " + self.worldview['description']
        
    @property
    def socialclass_str(self):
        if len(self.socialclass) == []:
            return ""
        else:
            return self.socialclass['name'] + ": " + self.socialclass['description']
        
    @property
    def commerce(self):
        if (self.wealth > 0):
            return round(math.log2((self.wealth+900) / 500))
        else:
            return 0
    
        
    @property
    def commerce_delta(self):
        delta = self.commerce - self.start_commerce
        if delta < 0:
            return delta * -1
        if delta >= 0:
            return delta
        
    @property
    def sig_people_str(self):
        try:
            return '\n'.join([f"{person}: {details['significance']} {details['disposition'].capitalize()}" for person, details in self.people.items() if details.get('significant', False)])
        except:
            try:
                return self.people[0]
            except:
                return ""
        
    @property
    def sig_objects_str(self):
        try:
            return '\n'.join([f"{obj}: {details['significance']}" for obj, details in self.objects.items() if details.get('significant', False)])
        except:
            try:
                return self.objects[0]
            except:
                return ""
        
    @property
    def sig_places_str(self):
        try:
            return '\n'.join([f"{place}: {details['significance']}" for place, details in self.places.items() if details.get('significant', False)])
        except:
            try:
                return self.places[0]
            except:
                return ""
        
    @property
    def traits_str(self):
        if len(self.traits) == 1:
            return self.traits[0]
        else:
            return ', '.join([str(self.traits[i]) for i in range(len(self.traits))])
        
    @property
    def communication_str(self):
        if len(self.communication) == []:
            return ""
        else:
            return ', '.join([str(self.communication[i]) for i in range(len(self.communication))])

class Time:
    def __init__(self):
        self.ticker = None
        self.datetime = datetime.now()

    @property
    def status(self):  
        # Check the time
        hour = self.datetime.time().hour  # get the hour as an integer
        if 6 <= hour < 12:
            time_status = 'morning'
        elif 12 <= hour < 18:
            time_status = 'afternoon'
        elif 18 <= hour < 24:
            time_status = 'evening'
        else:
            time_status = 'night'
        
        return time_status

class Journal:
    def __init__(self):
        self._attributes = {
            'counter': 0,
            'scheduled': {},
            'active': {},
            'completed': {}
        }
        self.save_to_redis()
            
    def save_to_redis(self):
        redis.set('journal', pickle.dumps(self._attributes))
    
    def __getattr__(self, name):
        # First, check if the attribute is a class property or method
        self._attributes = pickle.loads(redis.get('journal'))

        if name in self.__class__.__dict__:
            return object.__getattribute__(self, name)
        
        # Then check the _attributes dictionary
        try:
            value = self._attributes[name]
            if isinstance(value, dict):
                return AttributeDictProxy(self, name)
            return value
        except KeyError:
            raise AttributeError(f"'Journal' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        # To avoid recursion, only use _attributes for storing player attributes
        if name in ['_player_id', '_attributes']:
            super().__setattr__(name, value)
        else:
            self._attributes[name] = value
            self.save_to_redis()

    @property
    def readme(self):
        log = []
        for event_id, event in self.completed.items():
            if (event.get('type') == 'background'):
                item = {
                    'event_confirmation_id': -1,
                    'event_challenge_id': -1,
                    'mission_id': -1,
                    'datetime': event['triggerdate'],
                    'story': event['story'],
                    'character_change': 0,
                    'standing_change': 0
                }
                log.append(item)

            if (event.get('type') == 'event_confirmation'):
                if event['outcome'] > 0:
                    outcome = "successful"
                else:
                    outcome = "unsuccessful"
                event_challenge_id = event.get('parent_id',-1)
                event_challenge = self.completed.get(event_challenge_id)
                player_option = event_challenge['options'][event_challenge['decision']]['player_option']
                mission_id = event_challenge.get('parent_id',-1)
                story = f"""{event_challenge['title']}
                {event_challenge['location']}, {(gametime.datetime - event_challenge['triggerdate']).days} days ago:

                {event_challenge['event_body']}
                
                You decided to: "{player_option}"
                
                You were {outcome}, leading to the following outcome: "{event['event_body']}"
                """
                item = {
                    'event_confirmation_id': event_id,
                    'event_challenge_id': event_challenge_id,
                    'mission_id': mission_id,
                    'datetime': event_challenge['triggerdate'],
                    'story': story,
                    'character_change': event['options'][0]['gameplay_effects'].get('character_change'),
                    'standing_change': event['options'][0]['gameplay_effects'].get('standing_change')
                }

                log.append(item)
        return sorted(log, key=lambda x: x['datetime'], reverse=True)
    
class Game:
    def __init__(self):
        self._attributes = {
            'state': None,
        }
        self.save_to_redis()
            
    def save_to_redis(self):
        redis.set(f'game', pickle.dumps(self._attributes))
    
    def __getattr__(self, name):
        self._attributes = pickle.loads(redis.get('game'))
        if name in self.__class__.__dict__:
            return object.__getattribute__(self, name)
        # Then check the _attributes dictionary
        return self._attributes.get(name, None)  # Return None if attribute not found
    
    def __setattr__(self, name, value):
        # To avoid recursion, only use _attributes for storing player attributes
        if name in ['_game_id', '_attributes']:
            super().__setattr__(name, value)
        else:
            self._attributes[name] = value
            self.save_to_redis()

    def present(self, proposal):
        if self.decide(proposal):
            emitter.emit('accepted_proposal', proposal)
        
    def decide(self, proposal):
        if proposal['action'] == 'execute_option':
            return True
        if proposal['action'] == 'select_mission':
            return True
        if proposal['action'] == 'compute_event':
            return True
        if proposal['action'] == 'compute_concept':
            return True
        if proposal['action'] == 'init_app':
            return True
        if proposal['action'] == 'lock_time':
            return True
        if proposal['action'] == 'change_stat':
            #if worldview and personality and class not emppty
            if proposal and 'values' in proposal:
                values = proposal['values']
                if all(key in values and values[key] != "" for key in ['worldview', 'personality', 'socialclass']):
                    return True
            return False
        if proposal['action'] == 'change_speed':
            try:
                if not self.state.can_change_speed():
                    socketio.emit('stop_time')
                    return False
                # if speed is not int
                if not isinstance(proposal['speed'], float):
                    print("Speed is not float")
                    return False
                print("Changing speed")
                return True
            except KeyError:
                print("KeyError")
                return False
        if proposal['action'] == 'wait_for_input':
            return True

        if proposal['action'] == 'load_game':
            return True
        
gametime = Time()
player = Player()
game = Game()
journal = Journal()