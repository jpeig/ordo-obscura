from flask import Flask, g
from flask_redis import FlaskRedis
from flask_socketio import SocketIO

class EventEmitter:
    def __init__(self):
        self._events = {}

    def on(self, event):
        def decorator(func):
            if event not in self._events:
                self._events[event] = []
            self._events[event].append(func)
            return func
        return decorator

    def emit(self, event, *args, **kwargs):
        if event in self._events:
            for callback in self._events[event]:
                callback(*args, **kwargs)

# Globally accessible libraries
redis = FlaskRedis()
socketio = SocketIO()
emitter = EventEmitter()

def init_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')

    # Initialize Plugins
    redis.init_app(app)
    socketio.init_app(app, message_queue=app.config['REDIS_URL'])

    with app.app_context():

        # Include our Routes
        from . import state, actions, models, routes

        # Register Blueprints
        app.register_blueprint(routes.routes)
        app.register_blueprint(models.models)
        app.register_blueprint(state.state)
        app.register_blueprint(actions.actions)

        return app