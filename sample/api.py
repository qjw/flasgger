from flask import Blueprint, jsonify
from flask import request

from flasgger import swag_from

api = Blueprint('api', __name__,template_folder='templates')

@api.route('/p/<id>', methods=['DELETE'])
@api.route('/p', defaults={'id': None}, methods=['DELETE'])
@swag_from('api.json#/2')
def car_delete(id):
    if request.json_dict:
        id = request.json_dict["id"]

    if not id:
        return jsonify(
            code=0, message='error'
        )

    return jsonify(
        code=0, message='ok',
        id=id
    )

@api.route('/car/<id>')
@swag_from('api.json#/1')
def car(id):
    return jsonify(
        code=0, message='ok',
        id=id,
    )

@api.route('/car', methods=['PUT'])
@swag_from('api.json#/3')
def car_update():
    return jsonify(code=0, message='ok')

@api.route('/car', methods=['POST'])
@swag_from('api.json#/4')
def car_create():
    return jsonify(code=0, message='ok')

@api.route('/6', methods=['GET'])
@swag_from('api.json#/6')
def f6():
    return jsonify(code=0, message='ok')

@api.route('/7', methods=['GET'])
@swag_from('api.json#/7')
def f7():
    return jsonify(code=0, message='ok')

@api.route('/8', methods=['POST'])
@swag_from('api.json#/8')
def f8():
    return jsonify(code=0, message='ok')

@api.route('/9', methods=['POST'])
@swag_from('api.json#/9')
def f9():
    return jsonify(code=0, message='ok')

@api.route('/10', methods=['POST'])
@swag_from('api.json#/10')
def f10():
    return jsonify(code=0, message='ok')

@api.route('/11', methods=['GET'])
@swag_from('api.json#/11')
def f11():
    return jsonify(code=0, message='ok')

@api.route('/12', methods=['GET'])
@swag_from('api.json#/12')
def f12():
    return jsonify(code=0, message='ok')

@api.route('/13', methods=['GET'])
@swag_from('api.json#/13')
def f13():
    return jsonify(code=0, message='ok')

@api.route('/14', methods=['GET'])
@swag_from('api.json#/14',validate_flag=False)
def f14():
    return jsonify(code=0, message='ok')

@api.route('/15', methods=['POST'])
@swag_from('api.json#/15')
def f15():
    name = None
    for fn in request.files:
        name = fn
        break

    if not name:
        return jsonify(code=404, message='name不存在')

    storage = request.files[name]

    filename = storage.filename
    storage.save("/tmp/" + filename)
    return jsonify(code=0, message='ok',filename=filename)

@api.route('/16', methods=['GET'])
@swag_from('api.json#/16')
def f16():
    from flask import send_file
    return send_file("logo.png", mimetype='image/gif')