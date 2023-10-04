from flask import Blueprint, render_template, abort, request, jsonify, redirect, url_for, g, current_app as app
from jinja2 import TemplateNotFound
from . import socketio
import os
from typing import Dict
from config import Config
import asyncio
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

URI_WS = Config.OOB_URI_WS
state = Blueprint('state', __name__,
                        template_folder='templates',
                        static_folder="static")

class GameState():
    def can_init_game():
        return False
    def can_change_speed():
        return True
    def transition(game, accepted_proposal=None):
        print("Transitioning to next state")

class WIZARD_WAIT(GameState):
    def can_init_game():
        return True
    def can_change_speed():
        return False
    def transition(game, accepted_proposal=None):
        asyncio.run(stop_ticker(game))
        print(game.__dict__)
    
class WIZARD_CALCULATE(GameState):
    def can_init_game():
        return True
    def can_change_speed():
        return False
    def transition(game, accepted_proposal=None):
        calculate_stats(game, accepted_proposal)

class SELECT_MISSION_INIT(GameState):
    def can_init_game():
        return True
    def transition(game, accepted_proposal):
        compute_mission_selection(game, accepted_proposal)

class CALCULATE_RESPONSE(GameState):
    def transition(game, accepted_proposal: Dict):
        asyncio.run(stop_ticker(game))
        compute_event_response(game, accepted_proposal)
    
class GAME_INIT(GameState):
    def transition(game, accepted_proposal):
        launch_game_ui(game)
        compute_next_event(game, accepted_proposal)

class GAME_WAIT(GameState):
    def transition(game, accepted_proposal):
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(stop_ticker(game))
        except RuntimeError:
            # If no event loop is running, start one temporarily
            asyncio.run(stop_ticker(game))
    
class GAME_TICKING(GameState):
    def transition(game, accepted_proposal):
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(start_ticker(game, accepted_proposal['speed']))
        except RuntimeError:
            asyncio.run(start_ticker(game, accepted_proposal['speed']))

# class RepeatingTimer(Timer):
#     def run(self):
#         while not self.finished.wait(self.interval):
#             self.function(*self.args, **self.kwargs)


def calculate_stats(game, accepted_proposal):
    # Extract perks and assets dynamically
    worldview_key = accepted_proposal['values']['worldview']
    s_class_key = accepted_proposal['values']['class']
    personality_key = accepted_proposal['values']['personality']

    filename = os.path.join(app.static_folder, '', 'stats.json')
    with open(filename) as f:
        data = json.load(f)
    worldview = data['worldview'][worldview_key]
    s_class = data['s_class'][s_class_key]
    personality = data['personality'][personality_key]

    # Calculate stats
    dominance = round(math.pow(worldview['Dominance'] * s_class['Dominance'] * personality['Dominance'],0.5))
    influence = round(math.pow(worldview['Influence'] * s_class['Influence'] * personality['Influence'],0.5))
    insight = round(math.pow(worldview['Insight'] * s_class['Insight'] * personality['Insight'],0.5))
    wealth = math.pow((worldview['Wealth'] + personality['Wealth']),0.7)*s_class['Wealth']/2
    debt_ratio = (s_class['Debt']/s_class['Wealth'])
    debt = round(wealth * debt_ratio)
    wealth = round(wealth)

    game.com_style = worldview['com_style'] + ", " + s_class['com_style'] + ", " + personality['com_style']

    print("com_style: " + str(game.com_style))

    game.player_hidden_pos_traits = worldview['pos_trait'] + ", " + s_class['pos_trait'] + ", " + personality['pos_trait']
    game.player_hidden_neg_traits = worldview['pos_trait'] + ", " + s_class['pos_trait'] + ", " + personality['pos_trait']

    print("player_hidden_pos_traits: " + str(game.player_hidden_pos_traits))

    game.player_dominance = dominance
    game.player_influence = influence
    game.player_insight = insight

    modifier = random.uniform(0.9500, 1.0500)

    game.player_worldview = worldview['name'] + ": " + worldview['description']
    game.player_s_class = s_class['name'] + ": " + s_class['description']
    game.player_personality = personality['name'] + ": " + personality['description']

    print(personality)

    print("player_worldview: " + str(game.player_worldview))
    print("player_s_class: " + str(game.player_s_class))
    print("player_personality: " + str(game.player_personality))

    game.player_wealth = round(800*(2^wealth)*modifier)
    game.player_debt = round(800*(2^debt)*modifier)

    socketio.emit('update_statmenu', {'dominance': game.player_dominance, 'influence': game.player_influence, 'insight': game.player_insight, 'wealth': str(game.player_wealth)+" fl.", 'debt': str(game.player_debt)+" fl."})

          
def launch_game_ui(game):
    ticker_template = render_template(
    'ticker.html', 
    time = game.datetime.strftime('%H:%M'),
    date = game.datetime.strftime('%d.%m'),
    year = game.datetime.strftime('%Y AD')
    )
    socketio.emit('blank_canvas', {'new_html_content': ticker_template})

def change_state(next_state, game, accepted_proposal: Dict):
    game.state = next_state
    next_state.transition(game, accepted_proposal)

# Using partial to encapsulate the argument (game)
async def start_ticker(game, speed):
    try:
        if game.ticker:
                game.ticker.cancel()
        game.ticker = asyncio.create_task(tick(game, speed))
        await game.ticker  # Await the new task
    except (asyncio.exceptions.CancelledError):
        pass

async def stop_ticker(game):
    print("Stopping ticker")
    if game.ticker:
        try:
                game.ticker.cancel()
                await game.ticker
        except:
            game.ticker = None
        socketio.emit('stop_time')

async def tick(game, speed):
    tick_speed = 1 / math.pow(speed,0.75)
    while True:
        await asyncio.sleep(tick_speed)
        await update_time(game, speed)

async def update_time(game, speed):
    modifier = max(round(speed / 15.13,2),3) - 2
    modifier = math.pow(modifier,3)
    game.datetime += timedelta(minutes=modifier)
    game.time_status = check_datetime(game.datetime)

    time = game.datetime.strftime('%H:%M')
    date = game.datetime.strftime('%d.%m')
    year = game.datetime.strftime('%Y AD')

    if (game.triggerdate <= game.datetime):
        mission_event_template = render_template(
        'mission_event.html', 
        name=game.player_name,
        event=game.next_event
        )
        socketio.emit('drop_event', {'new_html_content': mission_event_template, 'actions': game.next_event['actions']})
        game.triggerdate = datetime.strptime('1922-01-01 19:20:00', '%Y-%m-%d %H:%M:%S')
        game.player_location = game.next_event['location']
        proposal = {
            'action': 'change_speed',
            'speed': float(0.0)
        }
        game.present(proposal)


    socketio.emit('update_time', {'time': time, 'date': date, 'year': year})

# FETCH RESPONSE OOGABOOGA

async def get_ws_result(prompt, json_schema=None, emit_progress=0):
    result = await gen_ws_result(prompt, json_schema,emit_progress)
    return result
    
async def gen_ws_result(prompt,json_schema, emit_progress):
    result = ""
    async for response in get_ws_response(prompt,json_schema):
        if(response == "stream_end"):
            print("stream_end")
            return result
        result += response
        if (emit_progress!=0):
            result_length = len(result)
            progress = round(result_length / emit_progress * 100,0)
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
        'temperature': 1.2,
        'top_p': 0.37,
        'typical_p': 1,
        'epsilon_cutoff': 0,  # In units of 1e-4
        'eta_cutoff': 0,  # In units of 1e-4
        'tfs': 1,
        'top_a': 0,
        'repetition_penalty': 1.18,
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

        'seed': -1,
        'add_bos_token': True,
        'truncation_length': 6144,
        'ban_eos_token': False,
        'custom_token_bans': '',
        'skip_special_tokens': True,
        'stopping_strings': []
    }
    return request

def compute_event_response(game, accepted_proposal: Dict):

    event = game.next_event

    print(event)

    event.pop('actions')
    event['executed_action'] = accepted_proposal['executed_action']
    event['date'] = game.datetime

    game.player_journal.append(event)

    json_schema = textwrap.dedent("""{
    "type": "object",
    "properties": {
        "action_analysis": {
            "type": "string",
            "description": "A brief analysis of the action, outlining the potential risks and rewards."
        },
        "likelihood_positive_outcome": {
            "type": "number",
            "description": "A numerical representation (percentage) of the likelihood of a positive outcome."
        },
        "critical_positive_outcome": {
            "type": "object",
            "properties": {
                "player_message": {
                    "type": "string",
                    "description": "A message to the player describing a critical positive outcome."
                },
                "requires_urgent_player_actions": {
                    "type": "boolean",
                    "description": "Indicates whether further player actions are required."
                }
            }
        },
        "positive_outcome": {
            "type": "object",
            "properties": {
                "player_message": {
                    "type": "string",
                    "description": "A message to the player describing a positive outcome."
                },
                "requires_urgent_player_actions": {
                    "type": "boolean",
                    "description": "Indicates whether further player actions are required."
                }
            }
        },
        "negative_outcome": {
            "type": "object",
            "properties": {
                "player_message": {
                    "type": "string",
                    "description": "A message to the player describing a negative outcome."
                },
                "requires_urgent_player_actions": {
                    "type": "boolean",
                    "description": "Indicates whether further player actions are required."
                }
            }
        },
        "critical_negative_outcome": {
            "type": "object",
            "properties": {
                "player_message": {
                    "type": "string",
                    "description": "A message to the player describing a critical negative outcome."
                },
                "requires_urgent_player_actions": {
                    "type": "boolean",
                    "description": "Indicates whether further player actions are required."
                }
            }
        }
    }
}""")
    
    prompt = generate_action_analysis(game)
    print("generating event")
    result_analysis = asyncio.run(get_ws_result(prompt, json_schema))

    result_analysis = json.loads(result_analysis)
    odds = float(result_analysis['likelihood_positive_outcome'])/100
    negative_odds = 1 - odds

    critical_negative_odds = negative_odds * 0.2
    positive_odds = odds * 0.8 + negative_odds

    random_value = random.uniform(0, 1)

    if (random_value < critical_negative_odds):
        result_analysis_outcome = result_analysis['critical_negative_outcome']
    elif (random_value < negative_odds):
        result_analysis_outcome = result_analysis['negative_outcome']
    elif (random_value < positive_odds):
        result_analysis_outcome = result_analysis['positive_outcome']
    else:
        result_analysis_outcome = result_analysis['critical_positive_outcome']

    if (result_analysis_outcome['requires_urgent_player_actions']):
        prompt = generate_event_response(game)
        #result_response = asyncio.run(get_ws_result(prompt, json_schema))
    else:
        prompt = generate_mission_evaluation(game)

    
def generate_event_response(game):
    print("generating event response")

def generate_mission_evaluation(game):
    print("generating mission evaluation")

def generate_action_analysis(game):
    date = game.player_journal[-1]['date']
    time_of_day = check_datetime(date)
    prompt = textwrap.dedent("""### Input:
    You are an expert scenario analyst for grand strategy games. You are tasked with the analysis of a player's actions for a a mission in JSON format.
    The theme of the game is the golden age of the renaissance, and the player is being tasked by a hidden society.

    Consider the following EXAMPLE event (just a guideline to better parse the format -> so do not output this):{
"action_analysis": "You stand at the crossroads of enlightenment. The shorter alleyway might lead you directly to the hidden society's meeting place, accelerating your journey into the secrets of the golden age. However, treacherous plots could ensnare and cause the loss of invaluable insights. This decision teeters between unveiling artful masterpieces or descending into obscurity.": 40,
"critical_positive_outcome": {
"player_message": "As the cobblestones echo gently beneath your steps, a burst of insight guides your way. You discover a concealed door leading directly to the society's chamber, where luminous paintings and golden relics glow under the soft candlelight. Relief and awe surge within you, realizing the vast knowledge now accessible, the wisdom of the golden age at your fingertips.",
"requires_urgent_player_actions": false
},
"positive_outcome": {
"player_message": "You tread with discernment, navigating the alleyways of the bustling city. The walls murmur tales of ancient guilds and ingenious craftsmen. Finally, you emerge closer to the heart of the hidden society, the candlelit glow of their secrets casting a gentle shadow on the brick facades.",
"requires_urgent_player_actions": false
},
"negative_outcome": {
"player_message": "The intricate streets of the city confound your direction. Despite your attempts, you find yourself ensnared in a web of deceit and misinformation. Moments turn to hours, and with dwindling clues, the society's hidden chamber seems more elusive. The pathway to understanding requires renewed vigor and focus.",
"requires_urgent_player_actions": true
},
"critical_negative_outcome": {
"player_message": "Dusk falls as you delve deeper into the city's maze. Unexpected conspiracies emerge, leading to significant loss of time and credibility. The once inviting tales of the golden age now echo with doubt and mistrust. The society's secrets grow fainter, as the city's complexities challenge your determination, demanding sharp wit and perseverance.",
"requires_urgent_player_actions": true
}
}"""+f""" 

    !!!DO NOT USE THE ABOVE EXAMPLE!!!

    The following is the gamestate that you may need to analyze this event:
                                
    Player state:
    Your name: {game.player_name}
    Your location: {game.player_location}
    Your age: {game.player_age}
    Your occupation: {game.player_occupation}
    Your perks: {game.player_perks}
    Your holdings: {game.player_holdings}
    Your relations: {game.relations_background}

    The mission the player is on:
    {game.mission}

    The event that the player received:
    {game.player_journal[-1]['event_body']}

    How the player responded to the event:
    {game.player_journal[-1]['executed_action']['action']}

    Possible success effect:
    {game.player_journal[-1]['executed_action']['Possible success effect']}

    Possible failure effect:
    {game.player_journal[-1]['executed_action']['Possible failure effect']}

    Relevant gamestate pointers you can use to determine the outcome:
    {game.player_journal[-1]['relevant_gamestate_pointers']}

    The time and date of the event:
    {game.player_journal[-1]['date']}

    The time of day:
    {time_of_day}
                         
    ### Instruction:
    Here are some specific guidelines you must follow:
    1. Understand the the player's current location and mission, player attributes, perks, conditions and characteristics, player holdings, gear and assets, player relationships.
    2. Generate an analysis of the chosen player action that is based on the player's current state, including their relevant characteristics, the action they picked, the time of day and and the event itself.
    3. The response must include the likelihood of a positive outcome, the effect of the action on the player, and whether the action requires further player actions.
    6. ALWAYS write in the SECOND perspective - as if written for the player. E.g. "You have.." or "You are.." or "You need to.." or "Your x.." or "You are facing..".
    7. NEVER use the example event from the example JSON above. Be be creative and think outside the box.

    ### Response:""")

    return prompt

def compute_next_event(game, accepted_proposal: Dict):
    game.mission = accepted_proposal['mission']
    json_schema = textwrap.dedent("""{
    "type": "object",
    "description": "an event the player may receive in their mission,
    "properties": {
        "title": {"type": "string"},
        "location": {"type": "string"},
        "event_body": {"type": "string"},
        "relevant_gamestate_pointers": {
            "type": "array",
            "items": {"type": "string"}
            },
        "trigger_conditionals": {
            "type": "object",
            "properties": {
                "must_trigger_now": {"type": "boolean"},
                "can_trigger_now": {"type": "boolean"},
                "must_trigger_today": {"type": "boolean"},
                "can_trigger_today": {"type": "boolean"},
                "must_trigger_tomorrow": {"type": "boolean"},
                "can_trigger_tomorrow": {"type": "boolean"},
                "must_trigger_this_week": {"type": "boolean"},
                "can_trigger_this_week": {"type": "boolean"},
                "must_trigger_in_morning": {"type": "boolean"},
                "can_trigger_in_morning": {"type": "boolean"},
                "must_trigger_in_afternoon": {"type": "boolean"},
                "can_trigger_in_afternoon": {"type": "boolean"},
                "must_trigger_in_evening": {"type": "boolean"},
                "can_trigger_in_evening": {"type": "boolean"},
                "must_trigger_at_night": {"type": "boolean"},
                "can_trigger_at_night": {"type": "boolean"}
            }
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "Possible success effect": {"type": "string"},
                    "Possible failure effect": {"type": "string"}
                }
            }
        }                          
    }
}""")
    if (Config.SKIP_GEN_EVENT):
        result = Config.SKIP_VAL2
    else:
        print("generating event")
        prompt = generate_event(game)
        result = asyncio.run(get_ws_result(prompt, json_schema))
    event = json.loads(result)



    # parse trigger conditionals into a better format

    trigger_conditionals = event['trigger_conditionals']
    event.pop('trigger_conditionals')

    # extract data starting with 'must_trigger' into array
    must_trigger = {k: v for k, v in trigger_conditionals.items() if k.startswith('must_trigger')}

    must_time = retrieve_must_time(must_trigger)
    must_date = retrieve_must_date(must_trigger)
    
    # extract data starting with 'can_trigger'
    can_trigger = {k: v for k, v in trigger_conditionals.items() if k.startswith('can_trigger')}
    print(can_trigger)

    can_time_array = retrieve_can_time_array(can_trigger)
    can_date_array = retrieve_can_date_array(can_trigger)

    weights = [2,4,2,1]

    if len(weights) > len(can_time_array):
        weights = weights[:len(can_time_array)]
    elif len(weights) < len(can_time_array):
        weights.extend([1] * (len(can_time_array) - len(weights)))

    if (must_time==False):
        est_time = random.choices(can_time_array, weights=weights, k=1)[0]
    else:
        est_time = must_time  

    weights = [1,2,2,8]   
    
    if len(weights) > len(can_date_array):
        weights = weights[:len(can_date_array)]
    elif len(weights) < len(can_date_array):
        weights.extend([1] * (len(can_date_array) - len(weights)))

    if (must_date==False):
        est_date = random.choices(can_date_array, weights=weights, k=1)[0]
    else:
        est_date = must_date

    game.next_event = event
    game.triggerdate = get_trigger_datetime(game,est_date, est_time, can_time_array)
    print(game.triggerdate)

    # Send the result to the client
    print("proceeding")
    proposal = {
    'action': 'wait_for_input'
    }
    game.present(proposal)

def retrieve_can_time_array(can_trigger):
    possible_times = []
    if (can_trigger['can_trigger_in_morning']):
        possible_times.append('morning')
    if (can_trigger['can_trigger_in_afternoon']):
        possible_times.append('afternoon')
    if (can_trigger['can_trigger_in_evening']):
        possible_times.append('evening')
    if (can_trigger['can_trigger_at_night']):
        possible_times.append('night')
    return possible_times
    
def retrieve_can_date_array(can_trigger):
    possible_dates = []
    if (can_trigger['can_trigger_now']):
        possible_dates.append('now')
    if (can_trigger['can_trigger_today']):
        possible_dates.append('today')
    if (can_trigger['can_trigger_tomorrow']):
        possible_dates.append('tomorrow')
    if (can_trigger['can_trigger_this_week']):
        possible_dates.append('this_week')
    return possible_dates

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
    
def check_datetime(dt):   
    # Check the time
    hour = dt.time().hour  # get the hour as an integer
    if 6 <= hour < 12:
        time_status = 'morning'
    elif 12 <= hour < 18:
        time_status = 'afternoon'
    elif 18 <= hour < 24:
        time_status = 'evening'
    else:
        time_status = 'night'
    
    return time_status

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

def get_trigger_datetime(game,date_status, time_status, can_time_array):

    timesequence = ['morning','afternoon','evening','night']
    # get index for each item in can_time_array from timesequence
    possible_time_indices = [timesequence.index(i) for i in can_time_array]

    print(date_status)
    # get index for the current game time status
    game_time_status_index = timesequence.index(game.time_status)

    # remaining time slots in the day (get all indices that are greater or equal than the current game time status)
    remaining_time_slots = [i for i in possible_time_indices if i >= game_time_status_index]

     # If in the same part of the day, add a random amount of minutes to triggerdate

    if (date_status == 'now'):
        if (game.time_status in can_time_array):
            time = (game.datetime + timedelta(minutes=random.randint(1, 7))).time()
            date = game.datetime.date()
        elif (remaining_time_slots != []):
            next_time_today = timesequence[min(remaining_time_slots)]
            time = get_random_time(next_time_today)
            date = game.datetime.date()
        else:
            date_status = 'today'
    
    if date_status == 'today':
        if time_status == game.time_status:
            time = (game.datetime + timedelta(minutes=random.randint(1, 119))).time()
            date = game.datetime.date()
        elif time_status in remaining_time_slots:
            time = get_random_time(time_status)
            date = game.datetime.date()
        elif (remaining_time_slots != []):
            time = get_random_time(timesequence[random.choice(remaining_time_slots)])
            date = game.datetime.date()
        else:
            date_status = 'tomorrow'
    
    if date_status == 'tomorrow':
        time = get_random_time(time_status)
        date = (game.datetime + timedelta(days=1)).date()

    if date_status == 'this_week':
        time = get_random_time(time_status)
        date = (game.datetime + timedelta(days=random.randint(2, 7))).date()
    
    # Combine date and time
    trigger_datetime = datetime.combine(date, time)
    
    return trigger_datetime

def generate_event(game):
    prompt = ""
    player_perks = ', '.join([str(game.player_perks[i]) for i in range(len(game.player_perks))])
    player_holdings = ', '.join([str(game.player_holdings[i]) for i in range(len(game.player_holdings))])
    player_places = ', '.join([str(game.player_places[i]) for i in range(len(game.player_places))])

    prompt = textwrap.dedent("""### Input:
    You are an expert event writer for grand strategy games. You are tasked with generating a player event for a a mission in JSON format that is consistent with the current gamestate.
    The theme of the game is the golden age of the renaissance, and the player is being tasked by a hidden society.

    Consider the following example event (just a guideline to help you understand the format):{
"properties": {
"title": "The Whispering Library",
"location": "In a hidden corridor within the city",
"event_body": "As you navigate the bustling streets of the renaissance city, you stumble upon a concealed library. Whispers of ancient tales and hidden knowledge beckon you closer. Manuscripts suggest this place may reveal secrets of the hidden society, but muffled voices behind ornate bookshelves hint at clandestine plots and dangers.",
"relevant_gamestate_pointers": [
"intellect",
"historical knowledge"
],
"trigger_conditionals": {
"must_trigger_now": false,
"can_trigger_now": true,
"must_trigger_today": false,
"can_trigger_today": true,
"must_trigger_tomorrow": false,
"can_trigger_tomorrow": false,
"must_trigger_this_week": false,
"can_trigger_this_week": true,
"must_trigger_in_morning": false,
"can_trigger_in_morning": true,
"must_trigger_in_afternoon": false,
"can_trigger_in_afternoon": true,
"must_trigger_in_evening": false,
"can_trigger_in_evening": true,
"must_trigger_at_night": false,
"can_trigger_at_night": true
},
"actions": [
{
"action": "Dive into the ancient manuscripts",
"Possible success effect": "Unearth valuable insights about the hidden society, advancing you closer to its heart.",
"Possible failure effect": "Misinterpret the texts, leading you further away from the true knowledge and potential confrontation with those who guard it."
},
{
"action": "Heed the whispers and discreetly exit",
"Possible success effect": "Evade the lurking dangers of the library, discovering another clue outside that aids your search.",
"Possible failure effect": "Miss out on critical information within the library, making your quest for the society even more challenging."
},
{
"action": "Use a cipher from your belongings to decipher coded messages",
"Possible success effect": "Decode secrets that reveal the society's next meeting, granting you a golden opportunity to infiltrate.",
"Possible failure effect": "Misunderstand the cipher, attracting unwanted attention and potential threats."
}
]
}
}"""+f"""                 

    The following is the gamestate that you need to craft your event:

    #World state:
    Your journal: {game.player_journal}
    State complexity: 
    {game.complexity}
    State significance: 
    {game.significance}

    #Your PII:
    Your name: {game.player_name}
    Your age: {game.player_age}
    Your occupation: {game.player_occupation}
    Your location: {game.player_location}
    
    #Your holdings:
    Your wealth (in florins): {game.player_wealth}
    Your debt (in florins): {game.player_debt}
    Your possessions: {player_holdings}

    #Your relationships:
    Your significant people & places: {player_places}
    Your relationships described in more detail: {game.relations_background}

    #Your characteristics:
    Your worldview: {game.player_worldview}
    Your social class: {game.player_s_class}
    Your personality: {game.player_personality}
    Your other traits / perks: {player_perks}

    #Your backstory:
    Your origin: {game.world_background}
    Your lifestyle: {game.player_lifestyle}

    And most importantly the current mission you are on:
    {game.mission}
                         
    ### Instruction:
    Here are some specific guidelines you must follow:
    1. Understand the gamestate fully and generate an event that is consistent with the current gamestate.
    2. Generate an event that is primarily warranted by the mission, state complexity and narrative urgency.
    3. Decide on the scope of the trigger (triggerscope). Opt for short triggerscope if the event is urgent and long triggerscope if the event is not urgent.
    6. ALWAYS write in the SECOND perspective - as if written for the player. E.g. "You have.." or "You are.." or "You need to.." or "Your x.." or "You are facing..".
    7. NEVER use the example event from the example JSON above. Be be creative and think outside the box.

    ### Response:""")

    print(prompt)
    return prompt
    
def compute_mission_selection(game, accepted_proposal: Dict):
    game.player_name = accepted_proposal['player_state']['name']
    game.player_age = accepted_proposal['player_state']['age']
    game.player_occupation = accepted_proposal['player_state']['occupation']
    game.player_places = accepted_proposal['player_relations']['places']
    game.player_perks = accepted_proposal['player_state']['perks']
    game.player_holdings = accepted_proposal['player_holdings']
    game.relations_background = accepted_proposal['player_relations']['background']
    game.player_lifestyle = accepted_proposal['world_state']['lifestyle']
    game.world_background = accepted_proposal['world_state']['background']
    game_loader_template = render_template(
    'game_loader.html', 
    name=game.player_name
    )

    # Prepare HTML content and send to the client
    socketio.emit('message_story_init', {'new_html_content': game_loader_template})

    json_schema = textwrap.dedent("""{
    "type": "object",
    "properties": {
        "state_complexity": {"type": "string"},
        "state_significance": {"type": "string"},
        "missions": {
            "type": "object",
            "description": "The missions you (=the player) are facing (always write in the second perspective)",
            "properties": {
                "mission_1": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "narrative": {"type": "string"},
                        "closure_conditions": {"type": "string"}
                    }
                },
                "mission_2": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "narrative": {"type": "string"},
                        "closure_conditions": {"type": "string"}
                    }
                },
                "mission_3": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "narrative": {"type": "string"},
                        "closure_conditions": {"type": "string"}
                    }
                }
            }
        }
    }
}""")


    if (Config.SKIP_GEN_MISSION):
        result = Config.SKIP_VAL1
    else:
        prompt = generate_mission(game)

        # Run the async function in a new event loop
        result = asyncio.run(get_ws_result(prompt, json_schema, emit_progress=1750))
    result = json.loads(result)    

    # Extract the missions object and convert it to an array
    missions_array = [value for key, value in result['missions'].items()]

    # Create a new JSON object with the original array-based structure
    stories = {
        "state_complexity": result['state_complexity'],
        "state_significance": result['state_significance'],
        "missions": missions_array
    }

    game.complexity = stories['state_complexity']
    game.significance = stories['state_significance']

    mission_picker_template = render_template(
    'mission_picker.html', 
    name=game.player_name,
    stories=stories['missions']
    )

    socketio.emit('message_story', {'new_html_content': mission_picker_template, 'stories': stories['missions']})

def generate_mission(game):

    prompt = ""
    player_perks = ', '.join([str(game.player_perks[i]) for i in range(len(game.player_perks))])
    player_holdings = ', '.join([str(game.player_holdings[i]) for i in range(len(game.player_holdings))])
    player_places = ', '.join([str(game.player_places[i]) for i in range(len(game.player_places))])

    prompt = textwrap.dedent("""
    ### Input:
    You are an expert quest/scenario writer for grand strategy games. You are tasked with generating a player quest in JSON format that is consistent with the current gamestate.
    The theme of the game is the golden age of the renaissance, and the player is being tasked by a hidden society.

    Consider the following example array of missions (just a guideline to help you understand the format):
    {
    "state_complexity": "The player faces a paradox of choice between different life paths, each with its own set of challenges and moral dilemmas. Time is a complicating factor as certain opportunities may be fleeting.",
    "state_significance": "An impending prophetic event and the village's increasing need for a hero, master chef, or guardian add urgency. The player's choices will have long-lasting effects on their influence and the village's future.",
    "missions": {
        "mission_1": {
            "title": "The Brave Adventurer",
            "narrative": "You dream of becoming a legendary adventurer and you can't ignore the calling any longer. With a heart full of determination, you embark on a perilous journey into the dense jungle. The whispers of a fabled lost city entice your adventurous spirit. Challenges await you at every turn—from dangerous wildlife lurking in the shadows to rival treasure hunters eager to claim the glory for themselves. Undeterred, you push forward. Your eyes are set on the prize, your will unbreakable.",
            "closure_conditions": "You finally discover the legendary lost city and the treasures hidden within its ancient walls."
        },
        "mission_2": {
            "title": "The Master Chef",
            "narrative": "You've always had a knack for culinary arts. This time, you decide to take it up a notch by competing in a renowned international cooking competition. With every dash of spice and swirl of sauce, you express your soul. You're up against the best chefs in the world, each a maestro in their own right. The stakes are high and the pressure is on.",
            "closure_conditions": "You not only win the competition, but your dish becomes the talk of the culinary world, setting a new standard in gastronomic excellence."
        },
        "mission_3": {
            "title": "The Unseen Guardian",
            "narrative": "Though you've always lived a humble life in your small village, you possess a rare gift—you can communicate with animals. When a natural disaster threatens the village, it's the animals who bring you the news. You don't hesitate. Rallying the creatures of the forest and field, you orchestrate a daring rescue operation.",
            "closure_conditions": "Your heroism remains a secret, known only to the creatures you've saved, but the village survives, and so do you, the unseen guardian."
        }
    }
}"""+f"""                 

    The following is the gamestate that you need to analyze:
                                
    #World state:
    Your journal: {game.player_journal}

    #Your PII:
    Your name: {game.player_name}
    Your age: {game.player_age}
    Your occupation: {game.player_occupation}
    Your location: {game.player_location}
    
    #Your holdings:
    Your wealth (in florins): {game.player_wealth}
    Your debt (in florins): {game.player_debt}
    Your possessions: {player_holdings}

    #Your relationships:
    Your significant people & places: {player_places}
    Your relationships described in more detail: {game.relations_background}

    #Your characteristics:
    Your worldview: {game.player_worldview}
    Your social class: {game.player_s_class}
    Your personality: {game.player_personality}
    Your other traits / perks: {player_perks}

    #Your backstory:
    Your origin: {game.world_background}
    Your lifestyle: {game.player_lifestyle}

    ### Instruction:
    Here are some specific guidelines you must follow:
    1. Understand the gamestate fully.
    2. Distill challenges, paradoxes, urgent situations, significant event and complicated situations faced by the player in 'state_complexity' and 'state_significance'.
    3. Generate THREE engaging missions that are preferably warranted by the state complexity and state significance.
    5. Ensure that the generated missions BRANCH from the current gamestate and are NOT SEQUENTIAL TO EACH OTHER.
    6. ALWAYS write missions in the SECOND perspective - as if written for the player. E.g. "You have.." or "You are.." or "You need to.." or "Your x.." or "You are facing..".
    7. NEVER use the example storylines or information/concepts from the example JSON above. Be be creative and think outside the box.

    ### Response:""")
    
    print(prompt)
    return prompt