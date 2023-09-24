from flask import Flask, g
from flask_redis import FlaskRedis
from flask_socketio import SocketIO


# Globally accessible libraries
redis = FlaskRedis()
socketio = SocketIO()


def init_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')

    # Initialize Plugins
    redis.init_app(app)
    socketio.init_app(app)

    with app.app_context():
        # Include our Routes
        from . import state, actions

        # Set global variables
        g.analysis_text = ""
        g.game_state_text = ""
        g.story_json = ""

        # Register Blueprints
        app.register_blueprint(state.state)
        app.register_blueprint(actions.actions)

        return app