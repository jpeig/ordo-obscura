from flask import Blueprint, render_template, abort, request, jsonify, redirect, url_for, g
from jinja2 import TemplateNotFound
from . import socketio
from config import Config
import asyncio
import textwrap
import json
import sys
import websockets

URI = Config.OOB_URI
state = Blueprint('state', __name__,
                        template_folder='templates',
                        static_folder="static")

@state.route('/')
def main():
    return redirect(url_for('state.gen_state'))

@state.route('/wizard', methods=['GET', 'POST'])
def gen_state():
    g.analysis_text = ""
    if g.analysis_text != "":
        analysis_text_insert = f"""

            Consider the following analysis:
            {g.analysis_text}

            """

    if request.method == 'POST':

        output_type = request.form.get('output')
        user_input = request.form.get('storyInput')
        function_req = request.form.get('function')

        context = ""
        json_schema = ""

        if output_type == "text":
            if function_req == "input_toStateAnalysis":
                context = textwrap.dedent("""
                ### Input:
                You are an expert scenario and game state analyst. You distill stories into facts that are meaningful to the player. Your analysis will be used to generate a game state for a grand strategy game.
                
                The following is the scenario that you need to analyze:

                """+user_input+"""

                ### Instruction:

                Follow the steps exactly:
                
                1. Distill the facts from the story and group them into the following categories (more important to be accurate than to be creative):
                1a. Player state: identify the player and all player traits, interests, passions, personality, perks, conditions, characteristics. Include at least the player's name, current physical location and goals.
                1b. Player holdings: identify all assets, debts, finances and resources owned by the player. Quantify them.
                1c. Player relationships: identify all agents (e.g. individuals, factions, groups) in the world and then analyze/quantify their relationships with the player.
                1d. World state: identify all relevant facts and events about the world that are meaningful to the player.

                2. Situation Analysis: to derrive which event or story needs to be generated, provide an exploratory analysis of the gamestate complexity, gamestate significance and narrative urgency (be creative and think outside the box):
                2a. List the items that make the gamestate complex. E.g. "The player is in a complex situation because he has to struggle with conflicting x and y."
                2b. List the items that make the gamestate significant. E.g. "The player has no x and y."
                2c. List the items that are urgent to the player. E.g. "The player is in a dangerous location and needs to escape."

                General guidelines:
                - A perk, condition or characteristic is NEVER OWNED by the player and NEVER DESCRIBES A RELATIONSHIP, so put it in 'Player state'.
                - An asset, company, debt, loan, house, resource or anything the player owns NEVER DESCRIBES A RELATIONSHIP and is NEVER A CONDITION OR PERK CHARACTERIZING the player, so put it in 'Player holdings'.
                - A relationship (including descriptive terms such as "Ally", "Wife", "Enemy", "Relationship", "Alliance") is NEVER OWNED by the player and is NEVER A CONDITION CHARACTERIZING the player, so put it in 'Player relationships'.
                - Be meticulous and precise, and aim for specificity and relevance. E.g. "The player is location {x/}" is more specific and relevant than "The player is in the world".
                - Analyze/distill from the player's perspective and quantify where possible (e.g. the strength of a relationship or the amount of money). E.g. "50" is a quantified value for the relationship with an actor or agent.

                ### Response:""")
        
        elif output_type == "json":

            if function_req == "input_toState":
                json_schema = textwrap.dedent("""{
                    "type": "object",
                    "properties": {
                        "player_state": {
                            "type": "array",
                            "description": "a list containing the current location and goals as well as ALL player attributes, perks, conditions and characteristics.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "value": {"type": "string"},
                                    "description": {"type": "string"}
                                }
                            }
                        },
                        "player_holdings": {
                            "type": "array",
                            "description": "a list of all finances, assets and debts OWNED by the player and their values",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "value": {"type": "string"},
                                    "description": {"type": "string"}
                                }
                            }
                        },
                        "player_relations": {
                            "type": "array",
                            "description": "a list describing all RELATIONSHIPS between the player and other agents (e.g. individuals, factions, groups) in the world)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "value": {"type": "string"},
                                    "description": {"type": "string"}
                                }
                            }
                        },
                        "world_state": {
                            "type": "array",
                            "description": "a list describing the state of the world that is meaningful to the player",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "value": {"type": "string"},
                                    "description": {"type": "string"}
                                }
                            }
                        },
                        "meta": {
                            "type": "object",
                            "description": "a holistic analysis of the game state (player_holdings, player_relations, player_state, world_state, storyline)",
                            "properties": {
                                "state_complexity": {"type": "string"},
                                "state_significance": {"type": "string"},
                                "narrative_urgency": {"type": "string"}
                            }
                        }
                    }
                }""")

                context = textwrap.dedent("""
                ### Input:
                You are an expert scenario and game state custodian. Your task is to transform narratives into a structured game state dictionary and knowledge base in JSON format. This game state will inform a player narrative for a grand strategy game.                                          
                                                                                                    
                Consider the following output example:
                                          
                {
                    "player_state": [
                        {"key": "Name", "value": "Jorrit Velzeboer", "description": "Your full name"},
                        {"key": "Location", "value": "At the village", "description": "Your current location"},
                        {"key": "Dream", "value": "Become a great adventurer", "description": "Your lifelong goal"},
                        {"key": "Achievement", "value": "Discovered the lost city and its treasures", "description": "Your major accomplishments"}
                    ],
                    "player_holdings": [
                        {"key": "Food", "value": "Essential for the journey", "description": "Your nourishment"},
                        {"key": "Compass", "value": "To stay oriented", "description": "Your tool for navigation"},
                        {"key": "Treasures", "value": "Gold, jewels, and other precious items found in the hidden cave", "description": "Your collected valuables"}
                    ],
                    "player_relations": [
                        {"key": "Villagers", "value": "50", "description": "Your standing with the local villagers"},
                        {"key": "Villagers.Opinion", "value": "Skeptical of Jack's journey", "description": "The villagers' opinion of you"},
                        {"key": "Rival treasure hunters", "value": "They are nearby, also searching for the lost city and its treasures", "description": "Others who are after the same goals as you"}
                    ],
                    "world_state": [
                        {"key": "Jungle", "value": "The jungle is 1km from the village", "description": "A treacherous area you must navigate"},
                        {"key": "Ancient Temple", "value": "The temple is in the jungle", "description": "An ancient site you can explore"},
                        {"key": "Hidden Cave", "value": "The cave is in the jungle", "description": "A perilous location you must face"}
                    ],
                    "meta": {
                        "state_complexity": "Your journey into the unknown jungle in search of the legendary lost city and its treasures, encountering dangerous animals, rival treasure hunters, and navigating ancient structures.",
                        "state_significance": "Your discovery of the lost city and its treasures, proving your bravery and turning you into a legendary adventurer in your village.",
                        "narrative_urgency": "Your overcoming of the treacherous paths, defeating the dragon guarding the treasures, and returning home with the bounty to earn respect and recognition."
                    }
                }
                                          
                The output JSON has five main DICTIONARY categories:

                'player_state': 
                INCLUDES characteristics, conditions, and intrinsic traits of the player.
                DOES NOT INCLUDE any tangible assets, resources, or finances, or relationships with other entities.
                
                'player_holdings': 
                INCLUDES tangible assets, resources, and finances of the player.
                DOES NOT INCLUDE any characteristics, conditions, or intrinsic traits of the player, or relationships with other entities.
                
                'player_relations': 
                INCLUDES relationships and interactions of the player with other entities.
                DOES NOT INCLUDE any characteristics, conditions, or intrinsic traits, tangible assets, resources, or finances of the player.
                
                'world_state': 
                INCLUDES global events and elements that impact the player.
                DOES NOT INCLUDE any characteristics, conditions, or intrinsic traits, tangible assets, resources, or finances of the player, or relationships with other entities.
                
                'meta': 
                A holistic analysis of the game state (player_holdings, player_relations, player_state, world_state, storyline).
                          
                Consider the following narrative:
                                          
                """+user_input+"""

                ### Instruction:

                Follow the steps and guidelines below to ensure accuracy and completeness:

                DISTILL the facts from the analysis and narrative into the DICTIONARY categories:
                - List all intrinsic traits, interests, passions, personality aspects, perks, and conditions characterizing the player in 'player_state'. Must include at least the player's name, current location, and goals. Example (do not use in output): "key": "Name", "value": "Susan", "description": "Your name"
                - List all tangible assets, real estate, companies, resources, or finances owned by the player in 'player_holdings'. Quantify them where possible. Example (do not use in output): "key": "Money", "value": "5000", "description": "Amount of money owned by you"
                - List all agents (e.g., individuals, factions, groups) with whom the player has some kind of relationship in 'player_relations'. Quantify the relationship where possible. Example (do not use in output): "key": "Town Guard", "value": "70", "description": "Your standing with the town guard"
                - List all pertinent facts and events about the world that have implications for the player in 'world_state'. If information is not explicitly mentioned, hypothesize based on available data. Example (do not use in output): "key": "Political Climate", "value": "Unstable", "description": "The political climate of the world"

                DISTILL the gamestate complexity, gamestate significance and narrative urgency:
                - Explicitly note the challenges faced by the player in 'state_complexity'. If not explicitly mentioned, hypothesize on possible challenges.
                - Identify the factors giving significance to the player's actions in 'state_significance'. If not explicitly mentioned, hypothesize on possible significances.
                - Point out matters needing immediate attention from the player in 'narrative_urgency'. If not explicitly mentioned, state as "N/A".

                FOLLOW THESE GUIDELINES (failure to follow will result in a failed submission): 
                - NEVER USE THE EXAMPLES PROVIDED! Derrive content only from the narrative and analysis.
                - In case of conflicting information between the story and the analysis, the story is always considered more accurate.
                - If information is not explicitly mentioned or cannot be accurately hypothesized, label it as "N/A."
                - Specificity and relevance to the player are PARAMOUNT and should be prioritized over creativity. E.g. "The player is location {x/}" is more specific and relevant than "The player is in the world".
                - The 'description' field should be a short description of the 'key' field WRITTEN IN THE SECOND PERSPECTIVE. E.g. "Your name" or "Your current location" or "Your goal".
                - A perk, condition or characteristic is NEVER OWNED by the player and NEVER DESCRIBES A RELATIONSHIP, so put it in 'Player state'.
                - An asset, company, debt, loan, house, resource or anything the player owns NEVER DESCRIBES A RELATIONSHIP and is NEVER A CONDITION OR PERK CHARACTERIZING the player, so put it in 'Player holdings'.
                - A relationship (including descriptive terms such as "Ally", "Wife", "Enemy", "Relationship", "Alliance") is NEVER OWNED by the player and is NEVER A CONDITION CHARACTERIZING the player, so put it in 'Player relationships'.

                ### Response:""")

            elif function_req == "json_toStory":
                json_schema = textwrap.dedent("""{
                    "type": "array",
                    "description": "the missions you (=the player) are facing (always write in the second perspective)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "narrative": {"type": "string"},
                            "closure_conditions": {"type": "string"}
                        }
                    }}""")
            
                context = textwrap.dedent("""
                ### Input:
                You are an expert quest/scenario writer for grand strategy games. You are tasked with generating a player quest in JSON format that is consistent with the current gamestate. The player quest will be used to generate a player narrative for a grand strategy game.

                Consider the following example array of quests (just a guideline to help you understand the format):
                [
                        {
                            "title": "The Brave Adventurer",
                            "narrative": "You dream of becoming a legendary adventurer and you can't ignore the calling any longer. With a heart full of determination, you embark on a perilous journey into the dense jungle. The whispers of a fabled lost city entice your adventurous spirit. Challenges await you at every turn—from dangerous wildlife lurking in the shadows to rival treasure hunters eager to claim the glory for themselves. Undeterred, you push forward. Your eyes are set on the prize, your will unbreakable.",
                            "closure_conditions": "You finally discover the legendary lost city and the treasures hidden within its ancient walls."
                        },
                        {
                            "title": "Guardian of the Treasure",
                            "narrative": "Deep within the heart of the jungle, you stumble upon a hidden cave. Your heart races as you sense the presence of something magnificent, and terrifying— a fierce dragon guards the entrance. To claim the treasures that lie within, you know you must summon every ounce of your courage and skill. It's a face-off between you and the mythical beast, a test of your mettle.",
                            "closure_conditions": "You summon your courage and skills to defeat the dragon, gaining access to the priceless treasures guarded within the cave."
                        },
                        {
                            "title": "Return of the Hero",
                            "narrative": "With the treasures safely in your possession, you make your way back to your village. As you step through its gates, you're hailed as a hero. Your daring journey has turned you into an inspiration for all, your name becoming synonymous with bravery and exploration.",
                            "closure_conditions": "You are recognized and celebrated by your villagers, your name forever etched as a symbol of courage and adventure."
                        }
                ]                 

                The following is the gamestate that you need to analyze:
                                          
                """+g.game_state_text+"""

                ### Instruction:
                Here are some specific guidelines you must follow:
                0. Understand the gamestate fully, specifically the player's current location and goals, player attributes, perks, conditions and characteristics, player holdings, player relationships, and world context.
                1. Generate quests that are warranted by the state complexity, state significance and narrative urgency. 
                2. ALWAYS write quests in the SECOND perspective - as if written for the player. E.g. "You have.." or "You are.." or "You need to.." or "Your x.." or "You are facing..".
                2. NEVER use the example storylines or information/concepts from the example JSON above. Be be creative and think outside the box.

                ### Response:""")
                print(json_schema)
            

        if len(context) > 0:
            print(context)
            asyncio.run(send_response_to_frontend(context,output_type,json_schema,function_req))
        
    return render_template('event.html')

async def send_response_to_frontend(prompt,output_type,json_schema,function_req):

    async for response in get_api_response(prompt,output_type,json_schema):
        if(function_req == "input_toStateAnalysis"):
            socketio.emit('message_debug', {'data': response})
        if(function_req == "json_toStory"):
            socketio.emit('message_story', {'data': response})
        elif(function_req == "input_toState"):
            socketio.emit('message_state', {'data': response})
        print(response, end='')
        sys.stdout.flush()  # If we don't flush, we won't see tokens in realtime.

async def get_api_response(context,output_type,json_schema):
    request = {
        'prompt': context,
        'output_type': output_type,
        'json_schema': json_schema,
        'max_new_tokens': 1000,
        'auto_max_new_tokens': False,
        'max_tokens_second': 0,
        # Generation params. If 'preset' is set to different than 'None', the values
        # in presets/preset-name.yaml are used instead of the individual numbers.
        'preset': 'None',
        'do_sample': True,
        'temperature': 0.98,
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
    try:
        async with websockets.connect(URI, ping_interval=None) as websocket:
            await websocket.send(json.dumps(request))

            while True:
                incoming_data = await websocket.recv()
                incoming_data = json.loads(incoming_data)

                match incoming_data['event']:
                    case 'text_stream':
                        yield incoming_data['text']
                    case 'stream_end':
                        return
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection error: {e}")
        # Handle the error or re-raise it to inform the caller
        # For now, we'll just return an empty list to indicate no data