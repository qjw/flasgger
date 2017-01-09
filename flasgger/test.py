import re

import jsonschema
from flask import Flask, jsonify, request
from flask import flash
from flask import make_response
from flask import render_template
from flask import url_for
from flask.views import MethodView
from jsonschema import ValidationError
from werkzeug.utils import redirect

from flasgger import Swagger
from flasgger.utils import swag_from
from flask import Blueprint


def mobile_validator(validator, value, instance, schema):
    patrn = "^1[3|4|5|7|8]\\d{9}$"
    if (
        validator.is_type(instance, "string") and
        not re.search(patrn, instance)
    ):
        yield ValidationError("%r does not match %r" % (instance, patrn))

custom_validators = {
    'mobile': mobile_validator
}

app = Flask(__name__)
app.secret_key = 'd41d8cd98f00b204e9800998ecf8427e'
app.config['SWAGGER'] = {
    "headers": [
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', "GET, POST, PUT, DELETE, OPTIONS"),
        ('Access-Control-Allow-Credentials', "true"),
    ],
    "doc_root": '../sampledoc/',
    "base_url": "/api/v1",
    "info":
        {
            "version": "v1",
            "title": "Flasgger 结构文档",
            "description": "说些什么呢"
        },
    "custom_validators":custom_validators,
    "empty_value":"__null__"
}



swagger = Swagger(app)  # you can pass config here Swagger(config={})
api = Blueprint('api', __name__,template_folder='.')

@app.after_request
def allow_origin(response):
    # response.headers['Access-Control-Allow-Origin'] = 'http://example.com'
    response.headers['Access-Control-Allow-Origin'] = 'http://*'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# 错误处理
@app.errorhandler(jsonschema.ValidationError)
def handle_bad_request(e):
    redirect_url = e.schema.get('redirect_url', None)
    if redirect_url is not None:
        flash(e.schema.get('error_tip', e.message))
        return redirect(url_for(redirect_url))
    return make_response(jsonify(code=400, message=e.schema.get('error_tip', '参数校验错误'), details=e.message), 200)

@api.route('/a1/<int:id>')
@swag_from('sample.json#/1')
def func1(id):
    return jsonify(code=0, message='ok')

@api.route('/a2')
def func2():
    return render_template('test.html')

@api.route('/a3',methods=['PUT'])
@swag_from('sample.json#/3')
def func3():
    return jsonify(code=0, message='ok')

@api.route('/a4',methods=['POST'])
@swag_from('sample.json#/4')
def func4():
    return jsonify(code=0, message='ok')

app.register_blueprint(api, url_prefix='/api/v1')
if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",port=9999)