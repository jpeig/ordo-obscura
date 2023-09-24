from flask import Blueprint, g
from . import socketio
import textwrap

actions = Blueprint('actions', __name__,
                        template_folder='templates',
                        static_folder="static")

@socketio.on('updated_output')
def handle_updated_output(data):
    try:
        g.story_json = textwrap.dedent(data['updated_story_json'])
    except:
        pass
    try:
        g.analysis_text = textwrap.dedent(data['updated_analysis_text'])
    except:
        pass
    try:
        g.game_state_text = textwrap.dedent(data['updated_state_text'])
    except:
        pass