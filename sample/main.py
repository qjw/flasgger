import logging

import jsonschema
from flask import Flask, jsonify
from flask import make_response

from flasgger import Swagger
from sample.config import Config


def init_logging(app):
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(pathname)s:%(lineno)s] - %(message)s'))

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    if app.debug:
        sa_logger = logging.getLogger('sqlalchemy.engine')
        sa_logger.setLevel(logging.INFO)
        sa_logger.addHandler(handler)

app = Flask(__name__)
app.config.update(Config or {})
init_logging(app)
Swagger(app)


@app.errorhandler(jsonschema.ValidationError)
def handle_bad_request(e):
  return make_response(jsonify(code=400,
                               message=e.schema.get('error', '参数校验错误'),
                               details=e.message,
                               schema=str(e.schema)), 200)


from sample.api import api
app.register_blueprint(api, url_prefix='/api/v123456')


if __name__=='__main__':
  app.run()