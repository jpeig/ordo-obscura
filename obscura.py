from application import init_app, socketio

app = init_app()

if __name__ == '__main__':
    socketio.run(
        app,
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )