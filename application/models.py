from . import socketio
from flask import Blueprint, g
from typing import List, Dict
from .state import *
from datetime import datetime

models = Blueprint('models', __name__,
                        template_folder='templates',
                        static_folder="static")


class Game:
    def __init__(self):
        self.state: GameState = None
        self.scheduled_events = []
        self.player_mission = {}
        self.player_journal = []
        self.event_loop = None
        self.timeline = 0
        self.significance = ""
        self.complexity = ""
        self.s_class = {'status': 'impoverised', 'value': 0}
        self.player_influence = {'status': 'impoverised', 'value': 0}
        self.player_dominance = {'status': 'impoverised', 'value': 0}
        self.player_insight = {'status': 'impoverised', 'value': 0}
        self.player_wealth = 0
        self.player_income = 0
        self.player_com_style = {'status': 'impoverised', 'value': 0}
        self.player_debt = 0
        self.player_expenses = 0
        self.player_personality = ""
        self.player_name: str = ""
        self.player_location: str = "Not defined"
        self.player_age: str = ""
        self.player_occupation: str = ""
        self.player_perks: List[str] = []
        self.player_holdings: List[str] = []
        self.player_lifestyle: str = ""
        self.player_relations: str = ""
        self.player_background: str = ""
        self.player_journal: List[str] = []
        self.datetime = datetime.now()
        self.time_status = 'morning'
        self.ticker = None

    def present(self, proposal):
        print(proposal)
        if self.decide(proposal):
            next_state = compute_next_state(proposal)
            change_state(next_state,self, proposal)
        
    def decide(self, proposal):
        if proposal['action'] == 'execute_action':
            return True
        if proposal['action'] == 'game_init':
            try:
                if not self.state.can_init_game:
                    print("Can't init game")
                    return False
                if not proposal['mission']:
                    print("Mission is empty")
                    return False
                if self.complexity == "":
                    print("Complexity is empty")
                    return False
                return True
            except KeyError:
                print("KeyError")
                return False
        if proposal['action'] == 'app_init':
            print("game:", self.ticker)
            return True
        if proposal['action'] == 'stat_change':
            #if worldview and personality and class not emppty
            print(proposal)

            if proposal and 'values' in proposal:
                values = proposal['values']
                if all(key in values and values[key] != "" for key in ['worldview', 'personality', 'class']):
                    return True
            return False
        if proposal['action'] == 'change_speed':
            try:
                if not self.state.can_change_speed:
                    print(self.state)
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
            try:
                # if self.next_event is an empty object return true
                if self.next_event == {}:
                    return True
                return False

            except KeyError:
                print("KeyError")
                return False

        if proposal['action'] == 'wizard_to_story':
            try:
                # Validate player name (can't be empty)
                if not proposal['player_state']['name']:
                    print("Name is empty")
                    return False
                
                # Validate occupation (can't be empty)
                if not proposal['player_state']['occupation']:
                    print("Occupation is empty")
                    return False

                # Validate world background (can't be empty)
                if not proposal['player_state']['age']:
                    print("Age is empty")
                    return False
                return True
            
            
            except KeyError:  # Handle cases where expected keys are not present
                print("KeyError")
                return False


def compute_next_state(accepted_proposal: Dict):
    if (accepted_proposal['action'] == "app_init"):
        return WIZARD_WAIT
    if (accepted_proposal['action'] == "execute_action"):
        return CALCULATE_RESPONSE
    if (accepted_proposal['action'] == "wizard_to_story"):
        return GAME_LOADING
    if (accepted_proposal['action'] == "stat_change"):
        return WIZARD_CALCULATE
    if (accepted_proposal['action'] == "game_init"):
        return GAME_INIT
    if (accepted_proposal['action'] == "wait_for_input"):
        return GAME_WAIT
    if (accepted_proposal['action'] == "change_speed"):
        if accepted_proposal['speed'] >= 1.0:
            return GAME_TICKING
        if accepted_proposal['speed'] < 1.0:
            print("Pause state")
            return GAME_WAIT
    else:
        return ("Invalid")

game = Game()