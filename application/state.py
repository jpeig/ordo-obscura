from flask import Blueprint, render_template, abort, request, jsonify, redirect, url_for, g, current_app as app
from jinja2 import TemplateNotFound, Template
from . import socketio, rq, emitter, redis
from .models import *
import os
from typing import Dict
from config import Config
import numpy as np
import asyncio
import re
import textwrap
import math
import threading
import json
import sys
import random
import websockets
import requests
from functools import partial
from threading import Timer
from datetime import datetime, timedelta, time
from rq import Worker

URI_WS = Config.OOB_URI_WS
state = Blueprint('state', __name__,
                        template_folder='templates',
                        static_folder="static")

high_queue = rq.get_queue('high')
default_queue = rq.get_queue('default')

@emitter.on('accepted_proposal')
def handle_accepted_proposal(proposal):
    next_state = compute_next_state(proposal)
    if proposal.get('queue') != None:
        print("Queued state: ", next_state)
        Game().state = next_state
        if (proposal.get('queue') == 'default'):
            default_queue.enqueue(next_state.enqueue, args=(proposal))
        elif (proposal.get('queue') == 'high'):
            high_queue.enqueue(next_state.enqueue, args=(proposal))
    else:
        print("Next state: ", next_state)
        Game().state = next_state
        next_state.transition(proposal)
      
def compute_next_state(accepted_proposal: Dict):
    if (accepted_proposal['action'] == "init_app"):
        return WIZARD_WAITING()
    if (accepted_proposal['action'] == "execute_option"):
        return RESPONSE_COMPUTING()
    if (accepted_proposal['action'] == "lock_time"):
        return TIME_LOCKED()
    if (accepted_proposal['action'] == "load_game"):
        return GAME_LOADING()
    if (accepted_proposal['action'] == "change_stat"):
        return WIZARD_UPDATING()
    if (accepted_proposal['action'] == "select_mission"):
        return MISSION_COMPUTING()
    if (accepted_proposal['action'] == "compute_event"):
        return EVENT_COMPUTING()
    if (accepted_proposal['action'] == "compute_concept"):
        return CONCEPT_COMPUTING()
    if (accepted_proposal['action'] == "change_speed"):
        if accepted_proposal['speed'] >= 1.0:
            return GAME_TICKING()
        if accepted_proposal['speed'] < 1.0:
            return GAME_PAUSING()
    else:
        return ("Invalid")

class GameState():
    def can_init_game(self):
        return False
    def can_change_speed(self):
        return True
    def transition(self, game, accepted_proposal=None):
        print("Transitioning to next state")
    def enqueue(self, game, accepted_proposal):
        print("Enqueuing next state")

class WIZARD_WAITING(GameState):
    def can_init_game(self):
        return True
    def can_change_speed(self):
        return False
    def transition(self, accepted_proposal=None):
        journal = Journal()
        player = Player()

        journal.counter = 0
        journal.datetime = datetime.now()
        journal.ticker = None
        journal.scheduled: Dict[int, Dict] = {}
        journal.active: Dict[int, Dict] = {}
        journal.completed: Dict[int, Dict] = {}

        player.diplomacy = 0
        player.force = 0
        player.insight = 0
        player.start_commerce = 0

        player.wealth = 0
        player.debt = 0
        player.income = 0
        player.expenses = 0

        player.health = 15
        player.notoriety = 1
        
        player.name = ""
        player.location = "At a resting place."
        player.age = ""
        player.occupation = ""

        player.relations = ""
        player.background = ""
        player.lifestyle = ""
        player.standing = ""

        player.people = []
        player.objects = []
        player.places = []

        player.personality = []
        player.worldview = []
        player.socialclass = []

        player.stability = 100
        player.traits = []
        player.communication = []
    
class WIZARD_UPDATING(GameState):
    def can_init_game(self):
        return True
    def can_change_speed(self):
        return False
    def transition(self, accepted_proposal=None):
        calculate_stats(accepted_proposal)

class TIME_LOCKED(GameState):
    def can_init_game(self):
        return False
    def can_change_speed(self):
        return False
    def transition(self, accepted_proposal):
        print("Time locked")
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(stop_ticker())
        except RuntimeError:
            # If no event loop is running, start one temporarily
            asyncio.run(stop_ticker())

class GAME_LOADING(GameState):
    def can_init_game(self):
        return True
    def transition(self, accepted_proposal):
        load_game(accepted_proposal)
        launch_game_ui()

class RESPONSE_COMPUTING(GameState):
    def transition(self, accepted_proposal: Dict):
        complete_event(accepted_proposal)

class GAME_PAUSING(GameState):
    def transition(self, accepted_proposal):
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(stop_ticker())
        except RuntimeError:
            # If no event loop is running, start one temporarily
            asyncio.run(stop_ticker())

class MISSION_COMPUTING(GameState):
    def enqueue(self, accepted_proposal):
        print("computing mission")
        compute_mission()

class EVENT_COMPUTING(GameState):
    def enqueue(self, accepted_proposal):
        compute_event()

class CONCEPT_COMPUTING(GameState):
    def enqueue(self, accepted_proposal):
        compute_concept()

class REFLECT_COMPUTING(GameState):
    def transition(self, accepted_proposal):
        return
    
class GAME_TICKING(GameState):
    def transition(self, accepted_proposal):
        try:
            print("Create loop")
            loop = asyncio.get_event_loop()
            loop.create_task(start_ticker(accepted_proposal['speed']))
        except RuntimeError:
            print("RuntimeError")
            asyncio.run(start_ticker(accepted_proposal['speed']))

# class RepeatingTimer(Timer):
#     def run(self):
#         while not self.finished.wait(self.interval):
#             self.function(*self.args, **self.kwargs)


def calculate_stats(accepted_proposal):
    # Extract people and assets dynamically
    worldview_key = accepted_proposal['values']['worldview']
    socialclass_key = accepted_proposal['values']['socialclass']
    personality_key = accepted_proposal['values']['personality']

    filename = os.path.join(app.root_path, 'templates', 'data', 'stats.json')
    with open(filename) as f:
        data = json.load(f)
    worldview = data['worldview'][worldview_key]
    socialclass = data['socialclass'][socialclass_key]
    personality = data['personality'][personality_key]

    # Calculate stats
    force = round(math.pow(worldview['force'] * socialclass['force'] * personality['force'],0.5))
    diplomacy = round(math.pow(worldview['diplomacy'] * socialclass['diplomacy'] * personality['diplomacy'],0.5))
    insight = round(math.pow(worldview['insight'] * socialclass['insight'] * personality['insight'],0.5))
    commerce = math.pow((worldview['commerce'] * personality['commerce']),0.5)*socialclass['commerce']/2
    debt_score = round(commerce * (socialclass['debt']/socialclass['commerce']))
    commerce = round(commerce)

    Player().traits = [
        worldview['pos_trait'],
        socialclass['pos_trait'],
        personality['pos_trait'],
        worldview['neg_trait'],
        socialclass['neg_trait'],
        personality['neg_trait']
    ]

    Player().communication = [
        worldview['communication'].split(', ')[0],
        socialclass['communication'].split(', ')[0],
        personality['communication'].split(', ')[0],
        worldview['communication'].split(', ')[1],
        socialclass['communication'].split(', ')[1],
        personality['communication'].split(', ')[1]
    ]    

    Player().force = force
    Player().diplomacy = diplomacy
    Player().insight = insight

    modifier = random.uniform(0.9500, 1.0500)

    Player().worldview = worldview
    Player().socialclass = socialclass
    Player().personality = personality

    Player().wealth = round(500*(2^commerce)*modifier-900)
    Player().debt = round(500*(2^debt_score)*modifier-900)

    print(f"Player wealth: {Player().wealth}")
    print(f"Player debt: {Player().debt}")
    

    socketio.emit('update_statmenu', {'force': Player().force, 'diplomacy': Player().diplomacy, 'insight': Player().insight, 'wealth': str(Player().wealth)+" fl.", 'debt': str(Player().debt)+" fl."})


def compute_concept():
    print("computing concept")
    
    # compute around concept
    # determine significance of concept
    # include interactions

    # compute around character
    # ambition, mission, events

    # compute around events
    # update people disposition
    # update journal
    # update standing
    # update lifestyle


    # compute actions


def launch_game_ui():
    ticker_template = render_template(
    'ticker.html', 
    time = Journal().datetime.strftime('%H:%M'),
    date = Journal().datetime.strftime('%d.%m'),
    year = Journal().datetime.strftime('%Y AD')
    )
    socketio.emit('blank_canvas', {'new_html_content': ticker_template})
    socketio.emit('update_statmenu', {'force': Player().force, 'diplomacy': Player().diplomacy, 'insight': Player().insight, 'wealth': str(Player().wealth)+" fl.", 'debt': str(Player().debt)+" fl."})
    
    json_schema_narrative_state = get_jsonschema('narrative_state_schema.jinja')
    
    if Config.SKIP_GEN_NARRATIVE:
        state_narrative = json.loads(Config.SKIP_VAL_NARRATIVE)
    else:
        prompt = generate_state_narrative()
        result = asyncio.run(get_ws_result(prompt, json_schema_narrative_state))
        state_narrative = json.loads(result)
    
    Player().standing = state_narrative['player_standing']
    Player().lifestyle = state_narrative['player_lifestyle']

    background = {
        'type': 'background',
        'story': Player().background,
        'triggerdate': Journal().datetime - timedelta(days=(int(365.24*Player().age*0.2)))
    }

    Journal().completed['background']= background

    asyncio.run(action_generator())

def has_running_jobs(queue_name):
    # Get all the workers
    workers = Worker.all(connection=default_queue.connection)
    
    # Filter workers based on the queue_name
    relevant_workers = [worker for worker in workers if queue_name in worker.queue_names()]
    
    for worker in relevant_workers:
        # Check if the worker is currently working on a job
        if worker.get_current_job() is not None:
            return True
    return False

async def action_generator():
    while True:
        print("generating action1")
        print(len(default_queue.jobs))
        print(len(high_queue.jobs))

        print(Journal().scheduled.items())
        
        default_has_running = has_running_jobs('default')
        high_has_running = has_running_jobs('high')

        print(default_has_running)
        print(high_has_running)

        if (len(default_queue.jobs) + default_has_running == 0 and len(high_queue.jobs) + high_has_running == 0):
            print("generating action2")
            if not Journal().active and not any(event['type'] == 'mission_select' for event_id, event in Journal().scheduled.items()):
                print("generating mission")
                emitter.emit('generate_action', {'action': 'select_mission', 'queue': 'high'})
            else:
                print("generating event3")
                odds_events = (0.6)**len(Journal().scheduled)
                odds_concepts = (0.6)**(len(Player().items)/8)
                if (odds_events > 0.1):
                    decide = random.choices(['compute_event','compute_concept'], weights=[odds_events, odds_concepts], k=1)[0]
                    emitter.emit('generate_action', {'action': decide, 'queue': 'default'})
        await asyncio.sleep(5)  # async sleep

# Using partial to encapsulate the argument ()
async def start_ticker(speed):
    try:
        if Journal().ticker:
                Journal().ticker.cancel()
        Journal().ticker = asyncio.create_task(tick(speed))
        await Journal().ticker  # Await the new task
    except (asyncio.exceptions.CancelledError):
        pass

async def stop_ticker():
    if Journal().ticker:
        Journal().ticker.cancel()
        socketio.emit('stop_time')

async def tick(speed):
    tick_speed = 1 / math.pow(speed,0.75)
    while True:
        await asyncio.sleep(tick_speed)
        await update_time(speed)

async def update_time(speed):
    modifier = max(round(speed / 15.13,2),3) - 2
    modifier = math.pow(modifier,3)
    game = Game()
    Journal().datetime += timedelta(minutes=modifier)
    
    time = Journal().datetime.strftime('%H:%M')
    date = Journal().datetime.strftime('%d.%m')
    year = Journal().datetime.strftime('%Y AD')

    # for each event in scheduled_events, check if triggerdate is less than datetime
    for event_id, event in Journal().scheduled.items():
        if event['triggerdate'] <= Journal().datetime:
            emitter.emit('lock_time')
            if event.get('location', False) != False:
                Player().location = event['location']
            socketio.emit('drop_event', {'new_html_content': event['html']})
    socketio.emit('update_time', {'time': time, 'date': date, 'year': year})

# FETCH RESPONSE OOGABOOGA

async def get_ws_result(prompt, json_schema=None, emit_progress_start=0, emit_progress_max=0):
    # while game.socket_occupied:
    #     await asyncio.sleep(0.1)  # wait for 1 second before checking again
    
    # game.socket_occupied = True
    result = await gen_ws_result(prompt, json_schema, emit_progress_start, emit_progress_max)
    # game.socket_occupied = False

    return result
    
async def gen_ws_result(prompt,json_schema,emit_progress_start, emit_progress_max):
    result = ""
    async for response in get_ws_response(prompt,json_schema):
        if(response == "stream_end"):
            print("stream_end")
            return result
        result += response
        if (emit_progress_max!=0):
            result_length = len(result)
            progress = round((result_length+emit_progress_start) / emit_progress_max * 100,0)
            socketio.emit('update_progress', {'progress': progress})
        print(response, end='')
        sys.stdout.flush()  # If we don't flush, we won't see tokens in realtime.

async def get_ws_response(prompt,json_schema):
    request = build_request(prompt,json_schema)
    try:
        async with websockets.connect(URI_WS, ping_interval=None) as websocket:
            await websocket.send(json.dumps(request))

            while True:
                incoming_data = await websocket.recv()
                incoming_data = json.loads(incoming_data)

                match incoming_data['event']:
                    case 'text_stream':
                        yield incoming_data['text']
                    case 'stream_end':
                        yield "stream_end"
                        return
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection error: {e}")
        # Handle the error or re-raise it to inform the caller
        # For now, we'll just return an empty list to indicate no data
def build_request(prompt,json_schema):
    request = {
        'prompt': prompt,
        'json_schema': json_schema,
        'max_new_tokens': 3000,
        'auto_max_new_tokens': False,
        'max_tokens_second': 0,
        # Generation params. If 'preset' is set to different than 'None', the values
        # in presets/preset-name.yaml are used instead of the individual numbers.
        'preset': 'None',
        'do_sample': True,
        'temperature': 0.2,
        'top_p': 0.37,
        'typical_p': 1,
        'epsilon_cutoff': 0,  # In units of 1e-4
        'eta_cutoff': 0,  # In units of 1e-4
        'tfs': 1,
        'top_a': 0,
        'repetition_penalty': 1.2,
        'repetition_penalty_range': 0,
        'top_k': 100,
        'min_length': 0,
        'no_repeat_ngram_size': 0,
        'num_beams': 1,
        'penalty_alpha': 0,
        'length_penalty': 1,
        'early_stopping': False,
        'mirostat_mode': 0,
        'mirostat_tau': 5,
        'mirostat_eta': 0.1,
        'guidance_scale': 1,
        'negative_prompt': '',

        'seed': 123,
        'add_bos_token': True,
        'truncation_length': 8192,
        'ban_eos_token': False,
        'custom_token_bans': '',
        'skip_special_tokens': True,
        'stopping_strings': []
    }
    return request


def get_random_value_from_label(difficulty):
    difficulty_ranges = {
        'routine': (1, 1),
        'easy': (2, 2),
        'fair': (3, 4),
        'tricky': (5, 6),
        'challenging': (7, 9),
        'strenuous': (10, 14),
        'hard': (15, 20),
        'very hard': (21, 30),
        'extreme': (31, 41),
        'hardcore': (42, 55),
        'impossible': (56, 70)  # using infinity to capture all higher values
    }

    if difficulty not in difficulty_ranges:
        raise ValueError(f"Unknown difficulty level: {difficulty}")
    low, high = difficulty_ranges[difficulty]
    return random.randint(low, high)

def dice_counts_for_level(level):
    dice_types = [2, 4, 6, 8, 10, 12]
    counts = {2:0, 4:0, 6:0, 8:0, 10:0, 12:0}

    # Add the counts for the d12 die
    counts[12] = (int(level)) // 6

    if level % 6 > 0:
        counts[dice_types[level % 6 - 1]] = 1

    return counts

def roll_dice_for_level(level):    
    counts = dice_counts_for_level(level)
    total = sum(random.randint(1, die) for die, count in counts.items() for _ in range(count))

    return total

def roll_all_dice_for(player,choice):

    difference = 0
    challenges = choice.get('challenges')
    challenge_rolls = {}

    if(challenges.get('perform_insight_check')):
        challenge_roll = roll_dice_for_level(choice['difficulty'])
        challenge_rolls['Insight'] = challenge_roll
        stat_roll = roll_dice_for_level(player.insight)
        difference += stat_roll - challenge_roll

        print(f"Total for Challenge level {choice['difficulty']}: {challenge_roll}")
        print(f"Total for Player insight level {player.insight}: {stat_roll}")

    if(challenges.get('perform_diplomacy_check')):
        challenge_roll = roll_dice_for_level(choice['difficulty'])
        challenge_rolls['Diplomacy'] = challenge_roll
        stat_roll = roll_dice_for_level(player.diplomacy)
        difference += stat_roll - challenge_roll

        print(f"Total for Challenge level {choice['difficulty']}: {challenge_roll}")
        print(f"Total for Player diplomacy level {player.diplomacy}: {stat_roll}")

    if(challenges.get('perform_force_check')):
        challenge_roll = roll_dice_for_level(choice['difficulty'])
        challenge_rolls['Force'] = challenge_roll
        stat_roll = roll_dice_for_level(player.force)
        difference += stat_roll - challenge_roll

        print(f"Total for Challenge level {choice['difficulty']}: {challenge_roll}")
        print(f"Total for Player force level {player.force}: {stat_roll}")

    return difference, challenge_rolls

def update_character():
    return

def update_standing():
    return

def update_objects():
    return

def summarize_journal():
    return

def complete_event(accepted_proposal: Dict):
    event_id = accepted_proposal['event_id']
    event = Journal().scheduled.get(event_id)
    event['decision'] = accepted_proposal['option_id']
    if event['type'] == 'mission_select':
        Journal().active[event_id] = event
    else:
        Journal().completed[event_id] = event
        compute_event_response(event_id, event)
    Journal().scheduled.pop(event_id)
    socketio.emit('remove_event_modal', {'event_id': event_id})

def compute_event_response(event_id, event):
    choice = event['options'][event['decision']]
    
    if event['type'] == 'event_challenge':
        # perform checks
        outcome, challenge_rolls = roll_all_dice_for(Player(),choice)
        # create response event
        response = {}
        response['parent_id'] = event_id
        response['outcome'] = outcome
        if (outcome > 0):
            effects = choice['success_effects']
            response['title'] = "Success!"
        if (outcome <= 0):
            effects = choice['failure_effects']
            response['title'] = "Failure!"
        response['event_body'] = effects['narrative_effects']
        response['options'] = [
            {"player_option": "Continue"}
        ]

        resolved_effects, tooltip = resolve_gameplay_effects(Player(),effects['gameplay_effects'], challenge_rolls, choice['difficulty'])

        response['options'][0]['tooltip_message'] = tooltip
        response['options'][0]['gameplay_effects'] = resolved_effects

        load_event(response, Journal().datetime + timedelta(minutes=random.randint(10, 60)), 'event_confirmation')

    if event['type'] == 'event_confirmation':
        for key, value in choice.items():
            match key:
                case 'wealth_change':
                    Player().wealth += value
                case 'notoriety_change':
                    Player().notoriety += value
                # case 'character_change':
                #     update_character()
                # case 'standing_change':
                #     update_standing()
                # case 'item_change':
                #     update_objects()
                #     pass
        summarize_journal()

    # json_schema = get_jsonschema('event_response_schema.jinja')
    # prompt = generate_prompt_action_analysis(event_id)
    # print("generating event")
    # result_analysis = asyncio.run(get_ws_result(prompt, json_schema))

def resolve_gameplay_effects(gameplay_effects, challenge_rolls, difficulty):
    #calculate effects
    resolved_effects = {}
    tooltip_message = "Your actions have consequences:\n"

    if (gameplay_effects.get('direct_wealth_increase')):
        resolved_effects['wealth_change'] = round((5*roll_dice_for_level(difficulty) * roll_dice_for_level(Player().commerce)))
        tooltip_message += f"Your wealth increases with: {resolved_effects['wealth_change']} fl."

    if (gameplay_effects.get('direct_wealth_decrease')):
        resolved_effects['wealth_change'] = round((5*roll_dice_for_level(difficulty) * roll_dice_for_level(Player().commerce)))
        tooltip_message += f"Your wealth decreases with: {resolved_effects['wealth_change']} fl."
        resolved_effects['wealth_change'] *= -1

    if(resolved_effects.get('wealth_change') == False):
        resolved_effects['wealth_change'] = 0

    if (gameplay_effects.get('notoriety_increase')):
        resolved_effects['notoriety_change']  = roll_dice_for_level(difficulty)
        tooltip_message += f"Your notoriety increases with: {resolved_effects['notoriety_change']}"

    if (gameplay_effects.get('notoriety_decrease')):
        resolved_effects['notoriety_change']  = roll_dice_for_level(difficulty)
        tooltip_message += f"Your notoriety decreases with: -{resolved_effects['notoriety_change']}"
        resolved_effects['notoriety_change'] *= -1

    if(resolved_effects.get('notoriety_change') == False):
        resolved_effects['notoriety_change'] = 0

    if (gameplay_effects.get('character_change')):
        tooltip_message += f"You are developing some new quirks. Who knows what you may become?"
    else:
        resolved_effects['character_change'] = 0

    if (gameplay_effects.get('standing_change')):
        tooltip_message += f"People will are starting to view you differently."
    else:
        resolved_effects['standing_change'] = 0

    if gameplay_effects.get('item_gained'):
        resolved_effects['item_change'] = 1
        tooltip_message += f"You received a new item! Let's see what we can do with it. \n"

    if gameplay_effects.get('item_lost'):
        resolved_effects['item_change'] = -1
        tooltip_message += f"You lost an item! Let's investigate the damage. \n"
    
    if(resolved_effects.get('item_change') == False):
        resolved_effects['item_change'] = 0

    for key, value in challenge_rolls.items():
        if (key != 'payment'):
            resolved_effects[f'{key}_experience'] = value
            tooltip_message += f"{key} experience gain: {value}\n"

    return resolved_effects, tooltip_message.replace("\n", "<br/>")
    
def generate_prompt_event_response():
    print("generating event response")

def generate_prompt_mission_evaluation():
    print("generating mission evaluation")

def generate_prompt_action_analysis(event_id):

    instructions = f"""   
    - Understand the the player's current location and mission, player attributes, people, conditions and characteristics, player holdings, gear and assets, player relationships.
    - Generate an analysis of the chosen player action that is based on the player's current state, including their relevant characteristics, the action they picked, the time of day and and the event itself.
    - The response must include the likelihood of a positive outcome, the effect of the action on the player, and whether the action requires further player actions.
    - NEVER use the example event from the example JSON above. Be be creative and think outside the box.
    """
    prompt = textwrap.dedent(f"""
    {return_intro("scenario analyst", "the analysis of a player's actions for a a mission in JSON format")}
    {return_profile()}
    {return_character()}
    {return_connections()}
    {return_habitus()}
    {return_mission(event_id=event_id)}
    {return_event(event_id)}
    {return_instructions(instructions)}
    """)

    print(prompt)
    return prompt


def get_difficulty_from(target):

    difficulty_ranges = {
        'routine': (1, 1),
        'easy': (2, 2),
        'fair': (3, 4),
        'tricky': (5, 6),
        'challenging': (7, 9),
        'strenuous': (10, 14),
        'hard': (15, 20),
        'very hard': (21, 30),
        'extreme': (31, 41),
        'hardcore': (42, 55),
        'impossible': (56, float('inf'))  # using infinity to capture all higher values
    }

    for difficulty, (min_val, max_val) in difficulty_ranges.items():
        if min_val <= target <= max_val:
            return difficulty
        
def get_nearby_difficulty_from(target_difficulty):
    difficulty_labels = ['routine', 'easy', 'fair', 'tricky', 'challenging', 'strenuous', 'hard', 'very hard', 'extreme', 'hardcore', 'impossible']

    difficulty_index = difficulty_labels.index(target_difficulty)

    weights = np.ones(len(difficulty_labels))

    # Assign more emphasis on the difficulty index
    for i in range(len(difficulty_labels)):
        weights[i] = 1 / (1 + abs(i - difficulty_index)**2)

    # Normalize the weights to make them sum to 1
    weights /= sum(weights)

    return np.random.choice(difficulty_labels, p=weights)

def compute_event():

    print("computing event")

    number_of_choices = random.randint(2, 3)

    event_difficulty = get_difficulty_from(Player().strength)
    event_difficulty = get_nearby_difficulty_from(event_difficulty)

    # Generate the array of keys
    keys_array = []
    for i in range(number_of_choices):
        key = f"option-{i+1}"
        keys_array.append(key)

    json_event_schema = get_jsonschema('event_schema.jinja',keys_array)

    if (Config.SKIP_GEN_EVENT):
        result = Config.SKIP_VAL2
    else:
        mission_ids = list(Journal().active.keys())
        print(f"Mission ids: {mission_ids}")
        if len(mission_ids) == 0:
            mission_id = -1
        else:
            count_mission_events = 0
            for mission_id in mission_ids:
                for event_id, event in Journal().scheduled.items():
                    if (event['type'] == 'event_challenge' and event.get('parent_id') == mission_id):
                        count_mission_events += 1
                        mission_ids.remove(mission_id)
                        break
            print(f"Mission events: {count_mission_events}")
            if (len(mission_ids)>0):
                odds_mission_events = (0.8)**count_mission_events
                count_random_events = sum(1 for event_id, event in Journal().scheduled.items() if (event['type'] == 'event_challenge' and event.get('parent_id') == False))
                odds_random_events = (0.8)**count_random_events
                chosen = random.choices(['mission','random'], weights=[odds_mission_events, odds_random_events], k=1)[0]
                if chosen == 'mission':
                    mission_id = random.choice(mission_ids)
                else:
                    mission_id = -1
        prompt = generate_prompt_event(event_difficulty, mission_id)
        result = asyncio.run(get_ws_result(prompt, json_event_schema))
    event = json.loads(result)

    event['difficulty'] = event_difficulty
    event['options'] = []
    event['parent_id'] = mission_id

    # Iterate over the keys in the object
    for key in list(event.keys()):  # We use list() to create a copy of the keys since we'll be modifying the dictionary
        if "option-" in key:
            event["options"].append(event[key])
            del event[key]

    for option in event['options']:
        multiplier = ((len(event['options'])/2)-event['options'].index(option))*-0.15+1
        option['difficulty'] = round(get_random_value_from_label(event_difficulty)*multiplier)
        option['difficulty_str'] = get_difficulty_from(option['difficulty'])
        if option.get('challenges').get('perform_payment', False):
            option['amount'] = roll_dice_for_level(option['difficulty']) * 10

    est_time, est_date = generate_schedule(event)
    triggerdate = get_trigger_datetime(est_date, est_time)

    load_event(event, triggerdate, 'event_challenge')


def load_event(event, triggerdate, template):

    # append triggerdate to event
    
    event_id = generate_event_id(Game())

    event['triggerdate'] = triggerdate
    event['type'] = template
    event['html'] = render_template(
            f'{template}.html', 
            name=Player().name,
            event=event,
            event_id=event_id
            )
     
    # append event to Game() scheduled_events
    Journal().scheduled[event_id] = event


def generate_schedule(event):
    trigger_conditionals = event['trigger_conditionals']
    event.pop('trigger_conditionals')

    # extract data starting with 'must_trigger' into array
    must_trigger = {k: v for k, v in trigger_conditionals.items() if k.startswith('must_trigger')}

    must_time = retrieve_must_time(must_trigger)
    must_date = retrieve_must_date(must_trigger)

    return must_time, must_date


def retrieve_must_time(must_trigger):
    if (must_trigger['must_trigger_in_morning']):
        return 'morning'
    if (must_trigger['must_trigger_in_afternoon']):
        return 'afternoon'
    if (must_trigger['must_trigger_in_evening']):
        return 'evening'
    if (must_trigger['must_trigger_at_night']):
        return 'night'
    else:
        return False
    
def retrieve_must_date(must_trigger):
    if (must_trigger['must_trigger_now']):
        return 'now'
    if (must_trigger['must_trigger_today']):
        return 'today'
    if (must_trigger['must_trigger_tomorrow']):
        return 'tomorrow'
    if (must_trigger['must_trigger_this_week']):
        return 'this_week'
    else:
        return False   
    

def get_random_time(time_status):
    # Handling time
    if time_status == 'morning':
        hour = random.randint(6, 11)
    elif time_status == 'afternoon':
        hour = random.randint(12, 17)
    elif time_status == 'evening':
        hour = random.randint(18, 23)
    elif time_status == 'night':
        hour = random.randint(0, 5)
    else:
        raise ValueError("Invalid time_status")

    minute = random.randint(0, 59)
    return time(hour, minute)

def get_trigger_datetime(date_status, time_status, can_time_array = ['morning','afternoon','evening','night']):

    timesequence = ['morning','afternoon','evening','night']
    # get index for each item in can_time_array from timesequence
    time_status_index = timesequence.index(time_status)
    game_time_status_index = timesequence.index(Journal().status)

     # If in the same part of the day, add a random amount of minutes to triggerdate

    if (date_status == 'now'):
        if (Journal().status == time_status):
            time = (Journal().datetime + timedelta(minutes=random.randint(1, 7))).time()
            date = Journal().datetime.date()
        else:
            date_status = 'today'
    
    if date_status == 'today':
        if (Journal().status == time_status):
            time = (Journal().datetime + timedelta(minutes=random.randint(1, 119))).time()
            date = Journal().datetime.date()
        elif time_status_index > game_time_status_index:
            time = get_random_time(time_status)
            date = Journal().datetime.date()
        else:
            date_status = 'tomorrow'
    
    if date_status == 'tomorrow':
        time = get_random_time(time_status)
        date = (Journal().datetime + timedelta(days=1)).date()

    if date_status == 'this_week':
        time = get_random_time(time_status)
        date = (Journal().datetime + timedelta(days=random.randint(2, 7))).date()
    
    # Combine date and time
    trigger_datetime = datetime.combine(date, time)
    
    return trigger_datetime


def generate_prompt_event(challenge_type,mission_id=-1):

    if (mission_id != -1):
        rule_1 = "- Generate an event that is entirely warranted by the mission progression (important) and narrative, using hooks from the current game state."
        rule_2 = '- Write the event for the set time of day and location that is consistent with the current gamestate, with the aim of further progressing the current mission.'
    else:
        rule_1 = '- Generate an singular event based on the player state that disconnected from current mission, using hooks from the current game state.'
        rule_2 = '- Write the event for the set time of day and location that is consistent with the current gamestate, with the aim of introducing new narrative elements to the player.'

    match challenge_type:
        case 'routine':
            rule_3 = """- Design an event that requires the player to carry out a simple task, involving minimal thought or effort. For example, making a familiar meal."""
        case 'easy':
            rule_3 = """- Construct an event that demands from the player a bit of contemplation and effort. It should be manageable with a few minor obstacles. """
        case 'fair':
            rule_3 = """- Develop an event where the player is faced with a challenge that needs careful thought to overcome tangible obstacles. For example, navigating through an unfamiliar city without a map."""
        case 'tricky':
            rule_3 = """- Designate an event that tests the player's skills and insights intensely. It should demand strategy and a deeper understanding. For example, organizing a complex event with multiple moving parts."""
        case 'challenging':
            rule_3 = """- Construct an event that exerts the player significantly both mentally and physically. For example, completing a rigorous obstacle course under a time limit."""
        case 'strenuous':
            rule_3 = """- Compose an event that appears formidable for the player, demanding thorough preparation and determination. For example, learning and mastering a new skill in a short period."""
        case 'hard':
            rule_3 = """- Produce an event that necessitates the player to go well beyond their usual capabilities, facing what seems nearly overwhelming. For example, leading a team in adverse conditions to achieve a challenging goal."""
        case 'very hard':
            rule_3 = """- Design an event that pushes the player into the unknown, urging them to challenge established conventions and boundaries. For example, developing a groundbreaking solution to a significant problem."""
        case 'extreme':
            rule_3 = """- Script an event at the boundary of what's conceivable, where the player aims to achieve what's seen as a legendary feat. For example, scaling the highest peaks with minimal equipment."""
        case 'hardcore':
            rule_3 = """- Craft an event that appears almost insurmountable to most. The sheer undertaking itself should be a testament to the player's extreme ambition. For example, revolutionizing global perspectives on a deeply entrenched issue."""
        case 'impossible':
            rule_3 = """- Design an event that stretches the imagination of what's possible, an event that no one has ever thought or dared to attempt. For example, fundamentally altering the course of human history through a singular act."""  
        case 'update':
            rule_3 = """- The goal of this event is to update the player on the evolving state of the game."""

    instructions = f"""   
    {rule_1}
    - Decide on the event location. Ensure it is not too far away from the current location.
    - Decide on the time of day it should trigger. This can be either morning, afternoon, evening or night.
    {rule_2}
    {rule_3}
    - Important: write the event_body briefly and succinctly (max 100 words), and keep it easy to read. Lead the story towards a pivotal moment where a player decision or action needs to be made/taken. But never end the event with rhetorical questions for the player (e.g. "What will you do?").
    - Write the player_options in the order of the difficulty level, from easiest to hardest. The player must pick only 1 option.
    - Always directly branch off the options from the event_body. Write in the present tense and second person.
    - For each option determine whether or not (True or False) the player should perform a skill check, or a payment to perform the action. Do not mention this anywhere else.
    - For the gameplay effects/consequences of each option, determine whether or not (True or False) the player's stats or financial situation would change. Do not mention this anywhere else.
    - Ensure the booleans for each option are in line with the narrative consequences of executing the option.
    - For each option/decision write a short line of internal dialogue for the player, that is consistent with the player communication style, character and the consequences of the option. Write in the present tense and second person.

     """
    prompt = textwrap.dedent(f"""
    {return_intro("event writer", "generating a player event for a a mission in JSON format")}
    
    Use this info to determine whether or not the player needs to perform a skill check:
    'Insight' revolves around the realm of deep intellectual exploration and esoteric wisdom. Rooted in the synthesis of intuitive perception with structured thought, it captures the essence of understanding phenomena that often transcend conventional boundaries.
    'Force' is the confluence of physical might with the ideals of principled leadership. It emphasizes the exertion of authority driven by both inner strength and a commitment to honorable action.
    'Diplomacy', at its core, is the art of navigating and harmonizing interpersonal relationships. It accentuates the importance of building bridges, fostering communal bonds, and skillfully managing social dynamics.
    
    {return_profile()}
    {return_character()}
    {return_connections()}
    {return_habitus()}
    {return_mission(mission_id=mission_id)}    
    {return_instructions(instructions)}
    """)

    print(prompt)
    return prompt

def load_game(accepted_proposal: Dict):
    background = f"""Your background: {accepted_proposal['background']}
    """
    relationships = f"""Your relationships: {accepted_proposal['relations']}
    """
    Player().starting_data = f"{background if len(accepted_proposal['background']) > 0 else ''}{relationships if len(accepted_proposal['relations']) > 0 else ''}"
    Player().name = accepted_proposal['name']
    Player().age = int(accepted_proposal['age'])
    Player().occupation = accepted_proposal['occupation']
    Player().lifestyle = accepted_proposal['lifestyle']
    Player().people = accepted_proposal['people']
    Player().objects = accepted_proposal['objects']
    Player().places = accepted_proposal['places']

    # generate trink items
    print("Is app context:", app.app_context())
    print("Current app:", app._get_current_object())
    game_loader_template = render_template(
        'game_loader.html', 
        name=Player().name
        )

    socketio.emit('deploy_loader', {'new_html_content': game_loader_template})

    if (Config.SKIP_GEN_STATE):
        data = Config.SKIP_VAL_STATE
        Player().people = Config.SKIP_VAL_PEOPLE
        Player().objects = Config.SKIP_VAL_OBJECTS
        Player().places = Config.SKIP_VAL_PLACES

    else:    
        prompt = generate_item_concepts_start('places')
        Player().places.extend([f'location-{i}' for i in range(len(Player().places)+1, 5)])
        wrapper = {
            "items" : Player().places,
            "type" : "places"
        }
        json_state_schema = get_jsonschema('state_schema.jinja',wrapper)
        result = asyncio.run(get_ws_result(prompt, json_state_schema,emit_progress_start=0, emit_progress_max=4500))
        Player().places = {item['name']: {"significance": item['significance'], "owner": item['owner'], "significant": True} for item in json.loads(result).values()}

        print(Player().places)

        prompt = generate_item_concepts_start('people')
        Player().people.extend([f'entity-{i}' for i in range(len(Player().people)+1, 7)])
        wrapper = {
            "items" : Player().people,
            "type" : "people"
        }
        json_state_schema = get_jsonschema('state_schema.jinja',wrapper)
        result = asyncio.run(get_ws_result(prompt, json_state_schema,emit_progress_start=1500, emit_progress_max=4500))
        Player().people = {item['name']: {"significance": item['significance'], "location": item['location'], "disposition": item['disposition_towards_player'], "significant": True} for item in json.loads(result).values()}

        print(Player().people)

        prompt = generate_item_concepts_start('objects')
        Player().objects.extend([f'object-{i}' for i in range(len(Player().objects)+1, 4)])
        wrapper = {
            "items" : Player().objects,
            "type" : "objects"
        }
        json_state_schema = get_jsonschema('state_schema.jinja',wrapper)
        result = asyncio.run(get_ws_result(prompt, json_state_schema,emit_progress_start=3000, emit_progress_max=4500))
        Player().objects = {item['name']: {"significance": item['significance'],"location": item['location'],"owner": item['owner'], "significant": True} for item in json.loads(result).values()}

        print(Player().objects)

        data = transform()
        
    print(data)
    
    socketio.emit('deploy_start_data', {'data': data})
    
def get_jsonschema(filename, items=None):
    file = os.path.join(app.root_path, 'templates', 'schemas', filename)
    with open(file, 'r') as f:
        template_str = f.read()
    template = Template(template_str)
    if items is None:
        return template.render()
    else:
        return template.render(items=items)
    
def transform():
    result = {
        "name": "My Empire",
        "children": []
    }
    
    dicts_to_iterate = [
        {"dict": Player().places, "type": "Location"},
        {"dict": Player().objects, "type": "Object"},
        {"dict": Player().people, "type": "Entity"}
    ]

    for d in dicts_to_iterate:
        for key, value in d["dict"].items():
            child = {
                "name": key,
                "type": d["type"],
                "significance": value["significance"],
            }
            result["children"].append(child)
    return result

def generate_state_narrative(brainstorm_results = None):
    instructions = """
    - Understand the gamestate fully and constellate items from your background, relationships, occupation and lifestyle into interconnected narratives and themes.
    - Distill the narrative into three interconnected sections: player's background, player's lifestyle and player's standing. 
    - For the player's background, focus on player's important locations, their origin and hooks to the present and future.
    - For the player's lifestyle, focus on job & occupation and daily activities and expenses.
    - For the player's standing, focus on describing the player's reputation among communities, groups and organizations.
    - Be sure to write critically, holistically and realistically.
    - Do not use anything from the example JSON above. Be be creative and think outside the box. Go for a different take, structure and approach.
    - Be sure to write in second person, always considering everything from the perspective of the player.        
    """
    prompt = textwrap.dedent(f"""
    {return_intro("expert game state conceptualizer / narrative writer", "generating a narrative summary in JSON format")}
    {return_profile()}
    {return_character()}
    {Player().starting_data}
    {return_connections()}
    {return_habitus()}
    {return_instructions(instructions)}
    """)
    
    print(prompt)
    return prompt
    
    
def generate_item_concepts_start(type):

    places = """{
            "location-[i]": "Your [REDACTED] in [REDACTED]",
            "location-[i]": "Your [REDACTED] room",
            "location-[i]": "[REDACTED]",
            "location-[i]": "[REDACTED] Port",
            "location-[i]": "[REDACTED] Castle",
            etc...
        }"""
    
    people = """[
        "person-[i]": "Your [REDACTED] [REDACTED]",
        "person-[i]": "[REDACTED] [REDACTED]",
        "person-[i]": "[REDACTED]",
        "person-[i]": "[REDACTED] working on your [REDACTED]",
        etc...
    ]"""

    objects = """[
            "object-[i]": "Your [REDACTED] in [REDACTED]",
            "object-[i]": "[REDACTED]",
            "object-[i]": "Your [REDACTED]",
            "object-[i]": "Your [REDACTED] of [REDACTED]",
            "object-[i]": "[REDACTED] the [REDACTED]",
            "object-[i]": "Your [REDACTED] 'The [REDACTED] of [REDACTED]'",
            etc...
        ]"""
    
    match type:
        case 'places':
            definition = "specific places, whether natural or constructed that are of interest to the player. Examples: Cities, your house, natural landscapes, man-made structures, mystical realms."
            samples = places
            rule = '- Be sure to include: 1) one or more of your resting places OR your home AND 2) the place(s) where you earn money and spend your wealth.'
            location_format= ""

        case 'people':
            definition = "humans (EXCLUDING YOURSELF), animals, or sentient beings that are of interest to the player. Examples: Family members, friends, rivals, historical figures, pets, mythical creatures."
            samples = people
            rule = '- Be sure to include at least one nemesis OR individual OR faction OR group challenging the player.'
            location_format= f""", at a town, city or points of interest,"""

        case 'objects':
            definition = "tangible, inanimate items that are of interest to the player. These are typically interactable items that have a physical presence. Examples: Tools, weapons, vehicles, consumables, documents."
            samples = objects
            location_format= f""", at a town, city or points of interest,"""
            rule = '- Be sure to list at least some of the more important gear, outfit and possessions of the player. Do not list locations or places.'

    instructions = f"""
    - Aim for {type} with flavor that touch upon the player's characteristics, relationships, worldview, personality, social class, occupation and background.
    - Ensure that the {type} are significant to the player in the sense that the player can interact with them.
    - Exclude {type} that do not align with the player's social class or wealth disposition.
    - Assign specific relatable English or Dutch names to the {type}. Never use jargon, sample or generic names (e.g. "entity-x", "[REDACTED]").
    - For all {type} in the provided array, expand on their significance to the player, and how the player can interact with it.
    - Take into account the player's background, relationships and lifestyle when writing the significance of the item.
    - Be sure to write in second person, always considering the {type} from the perspective of the player. E.g. "You have.." or "You are.." or "You own.." or "Your x..".
    - Never mention the player in the {type} attributes, instead always refer to the player as 'you' or 'your'.
    - For all {type} in the provided array, ensure each can exist in the baroque era{location_format} and are of significance to the player.
    {rule}
    
    {type} can exclusively be {definition}
    """
    prompt = textwrap.dedent(f"""
    {return_intro("expert game state generator/brainstormer", "generating an array of game items in JSON format")}  
    An example of json output (this is just an example so do not use - ignore the redacted parts):
    {samples}
    {return_profile()}
    {return_character()}
    {Player().starting_data}
    {return_connections()}
    {return_habitus()}
    {return_instructions(instructions)}
    """)
    
    print(prompt)
    return prompt
    
    
def compute_mission():
    game = game.load()
    json_schema = get_jsonschema('mission_schema.jinja')

    if (Config.SKIP_GEN_MISSION):
        result = Config.SKIP_VAL_MISSION
    else:
        prompt = generate_prompt_mission()
        print(prompt)
        result = asyncio.run(get_ws_result(prompt, json_schema))
    event = json.loads(result)    

    event['missions'] = [value for key, value in event['missions'].items()]

    # Create a new JSON object with the original array-based structure

    print(event['missions'])

    load_event(event, Journal().datetime + timedelta(hours=3), 'mission_select', game)
    game.save()


def generate_prompt_mission():
    instructions = f"""
    - Generate THREE missions that are warranted by the player state and game state.
    - Ensure that the generated missions BRANCH from the current gamestate and are NOT SEQUENTIAL TO EACH OTHER.
    - Ensure the missions are concrete, clear, interesting and easy to understand. Write in the present tense and second person.
    - Keep the plot of each mission mysterious and open-ended. Do not reveal the outcome of the missions.
    - Ensure the missions are consistent with the player's character, relationships & reputation, occupation and worldview.
    - Write missions that are significant to the player and resolve the player's current challenges.
    """
    prompt = textwrap.dedent(f"""
    {return_intro("expert mission writer", "generating a player mission in JSON format")}
    {return_profile()}
    {return_character()}
    {return_connections()}
    {return_habitus()}
    {return_instructions(instructions)}
    """)
    return prompt
    
def generate_event_id():
    event_id = Journal().counter
    Journal().counter += 1
    return int(event_id)

def return_profile(event = None):
    profile = f"""
    Your name: {Player().name} (this is you - don't refer to yourself from the third perspective!)
    Your age: {Player().age}
    Your occupation: {Player().occupation}
    Your location:{Player().location}
    """
    if event is None:
        return profile
    else:
        location = f"""The time of day: {event['trigger_time_of_day']}
        """
        profile += location
    return profile

def return_character():
    character = f"""
    Your worldview: {Player().worldview_str}
    Your social class: {Player().socialclass_str}
    Your personality: {Player().personality_str}
    Your traits: {Player().traits_str}
    Your communication style: {Player().communication_str}
    """
    return character

def return_connections():
    people = ""
    standing = ""
    notoriety = f"Your notoriety: {Player().notoriety_str}\n\n"
    if len(Player().standing) > 1:
        standing= f"Your standing: {Player().standing}\n\n"
    if len(Player().sig_people_str) > 1:
        people = f"Your significant people:\n{Player().sig_people_str}\n"
    return notoriety + standing + people

def return_journal():
    # summary + last events/actions
    summary = ""
    if len(Journal().summary) > 1:
        summary = f"Your journal: {Player().background}\n\n"
    return summary

def return_habitus():
    lifestyle = ""
    objects = ""
    places = ""
    finance = f"Your financial health: {Player().financial_health_str}\n\n"
    if len(Player().lifestyle) > 1:
        lifestyle = f"Your lifestyle: {Player().lifestyle}\n\n"
    if len(Player().sig_places_str) > 1:
        places = f"Your significant places:\n{Player().sig_places_str}\n\n"
    if len(Player().sig_objects_str) > 1:
        objects = f"Your significant objects:\n{Player().sig_objects_str}\n\n"
    return places + objects + finance + lifestyle

def return_mission(mission_id = -1, event_id = -1):
    if (event_id != -1):
        mission_id = int(Journal().scheduled.get(event_id).get('parent_id',-1))
    if (mission_id == -1):
        mission = None
        return ""
    else:
        mission = Journal().active.get(mission_id)
        print(mission)
        mission = mission['missions'][mission['decision']]
        mission = mission['title'] + ":  " + mission['narrative']
        mission = f"# The current active mission (important):\n{mission}"
        counter = 0
        progress = "\n\nYou made the following progress on this mission (important):\n"
        for event in Journal().readme:
            if (event.get('mission_id') == mission_id):
                progress += event.get('story') + "\n"
                counter += 1
        if counter == 0:
            progress = ""
        return mission + progress

def return_event(event = None, executed_option = None):
    if not Journal().scheduled or event is None:
        event = None
    else:
        event = f"""# The event that was triggered (important):\n {event['title']}": "{event['event_body']}\n\n
        # The option the player picked (important):\n {executed_option}"""
    return event

def return_intro(role, task):
    intro = f"""### Input:
    You are a {role} for grand strategy games. 
    The theme of the game is the (Dutch) Golden Age of the Baroque era.              
    You are tasked with {task} that is consistent with the current gamestate.

    The following is the gamestate that you need to analyze:"""
    return intro

def return_instructions(input):
    instructions = f"""
    ### Instruction:
    Here are some specific guidelines you must follow:
    - Always write in English in the SECOND perspective - as if written for the player. E.g. "You have.." or "You are.." or "You need to.." or "Your x.." or "You are facing..".
    {input}
    
    ### Response:"""
    return instructions