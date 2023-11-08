from flask import Blueprint, g
from . import socketio, emitter
from .models import game, journal, player, gametime
import re
import textwrap

actions = Blueprint('actions', __name__,
                        template_folder='templates',
                        static_folder="static")

@socketio.on('commandKeyPressed')
def handle_updated_output(data):
    def is_property(obj, attr):
        """Check if an attribute is a @property method."""
        attr_obj = getattr(obj, attr)
        return callable(attr_obj) and hasattr(attr_obj, '__code__') and len(attr_obj.__code__.co_varnames) == 1

    object = None
    print(data['message'])
    
    match data['message']:
        case 'game.journal':
            object = journal
        case 'game.player':
            object = player
        case 'game.gametime':
            object = gametime
        case 'game.gm':
            object = game
    
    # Print attributes and properties of the game object
    for attr in dir(object):
        if not attr.startswith("__"):
            val = getattr(object, attr)
            if isinstance(val, str) and (not callable(val) or is_property(object, attr)):
                print(f"{attr}: {val}\n")
    for attr in dir(object):
        if not attr.startswith("__"):
            val = getattr(object, attr)
            if isinstance(val, int) or isinstance(val, float) and (not callable(val) or is_property(object, attr)):
                print(f"{attr}: {val}\n")

@socketio.on('execute_option')
def handle_updated_output(event_id, option_id):
    proposal = {
    'event_id': int(event_id),
    'option_id': int(option_id),
    'action': 'execute_option'
    }
    game.present(proposal)

@socketio.on('change_stat')
def handle_updated_output(data):
    proposal = {
    'values': data,
    'action': 'change_stat'
    }
    game.present(proposal)

@socketio.on('change_speed')
def handle_change_speed(speed):
    speed = float(speed)
    if speed < 1.0:
        speed = 0.0
    proposal = {
    'speed': speed,
    'action': 'change_speed'
    }
    game.present(proposal)

@socketio.on('init_app')
def handle_app_init():
    proposal = {
    'action': 'init_app'
    }
    game.present(proposal)

@emitter.on('lock_time')
def handle_lock_time():
    game.present({'action': 'lock_time'})

@emitter.on('generate_action')
def handle_updated_output(data):
    print(("been here"))
    proposal = {
    'action': data.get('action'),
    'queue': data.get('queue')
    }
    game.present(proposal)

@socketio.on('load_game')
def handle_updated_output(data):
    # Extract people and objects dynamically
    existing_dict = {item['name']: item['value'] for item in data}

    people = [v for k, v in existing_dict.items() if re.fullmatch(r'peopleList-item\d+', k)]
    objects = [v for k, v in existing_dict.items() if re.fullmatch(r'objectsList-item\d+', k)]
    places = [v for k, v in existing_dict.items() if re.fullmatch(r'placesList-item\d+', k)]

    # Transform into the new format
    proposal = {
    'name': existing_dict['name'],
    'age': existing_dict['age'],
    'occupation': existing_dict['occupation'],
    'background': existing_dict['storyInput'],
    'lifestyle': existing_dict['lifestyleInput'],
    'relations': existing_dict['relationsInput'],
    'people': people,
    'places': places,
    'objects': objects,
    'action': 'load_game',
    }

    print(proposal)

    game.present(proposal)