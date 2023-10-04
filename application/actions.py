from flask import Blueprint, g
from . import socketio
from .models import game
import re
import textwrap

actions = Blueprint('actions', __name__,
                        template_folder='templates',
                        static_folder="static")

@socketio.on('game_init')
def handle_updated_output(data):
    print('received message: ' + str(data))
    proposal = {
    'mission': data,
    'action': 'game_init'
    }
    game.present(proposal)

@socketio.on('execute_action')
def handle_updated_output(data):
    print('received message: ' + str(data))
    proposal = {
    'executed_action': data,
    'action': 'execute_action'
    }
    game.present(proposal)

@socketio.on('stat_change')
def handle_updated_output(data):
    print('received message: ' + str(data))
    proposal = {
    'values': data,
    'action': 'stat_change'
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

@socketio.on('app_init')
def handle_app_init():
    proposal = {
    'action': 'app_init'
    }
    game.present(proposal)


@socketio.on('wizard_to_story')
def handle_updated_output(data):
    # Extract perks and assets dynamically
    existing_dict = {item['name']: item['value'] for item in data}

    perks = [v for k, v in existing_dict.items() if re.fullmatch(r'perksList-item\d+', k)]
    assets = [v for k, v in existing_dict.items() if re.fullmatch(r'assetsList-item\d+', k)]
    places = [v for k, v in existing_dict.items() if re.fullmatch(r'placesList-item\d+', k)]

    # Transform into the new format
    proposal = {
    'player_state': {
        'name': existing_dict['name'],
        'age': existing_dict['age'],
        'occupation': existing_dict['occupation'],
        'perks': perks
    },
    'world_state': {
        'background': existing_dict['storyInput'],
        'lifestyle': existing_dict['lifestyleInput'],
    },
    'player_relations': {
        'background': existing_dict['relationsInput'],
        'places': places
    },
    'player_holdings': assets,
    'action': 'wizard_to_story'
    }

    print(proposal)

    game.present(proposal)