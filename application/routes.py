from flask import Blueprint, render_template, abort, request, jsonify, redirect, url_for, g,  current_app as app
import os
import json

routes = Blueprint('routes', __name__,
                        template_folder='templates',
                        static_folder="static")

@routes.route('/')
def main():
    return redirect(url_for('routes.gen_state'))

@routes.route('/wizard', methods=['GET', 'POST'])
def gen_state():
    filename = os.path.join(app.static_folder, '', 'stats.json')
    with open(filename) as f:
        data = json.load(f)

    worldviews = data['worldview']
    s_classes = data['s_class']
    personalities = data['personality']

    return render_template(
    'content.html',
    worldviews=worldviews,
    s_classes=s_classes,
    personalities=personalities
    )