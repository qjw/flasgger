"""
What's the big idea?

An endpoint that traverses all restful endpoints producing a swagger 2.0 schema
If a swagger yaml description is found in the docstrings for an endpoint
we add the endpoint to swagger specification output

"""
import inspect
import yaml,json
import re
import os,sys
import jsonref

from collections import defaultdict
from flask import jsonify, Blueprint, url_for, current_app, Markup, request
from flask.views import MethodView
from jsonschema import ValidationError
from mistune import markdown
from werkzeug.utils import redirect

NO_SANITIZER = lambda text: text
BR_SANITIZER = lambda text: text.replace('\n', '<br/>') if text else text
MK_SANITIZER = lambda text: Markup(markdown(text)) if text else text

swagger_doc_root = None
doc_enable = True
validate_enable = True
custom_validators = None

def get_path_from_doc(full_doc):
    swag_path = full_doc.replace('file:', '').strip()
    swag_type = swag_path.split('.')[-1]
    return swag_path, swag_type


def json_to_yaml(content):
    """
    TODO: convert json to yaml
    """
    return content


def load_from_file(swag_path, swag_type='yml', root=None):
    if swag_type not in ('yaml', 'yml', 'json'):
        raise AttributeError("Currently only yaml or yml or json supported")

    try:
        return open(swag_path).read()
    except IOError:
        if root is None:
            swag_path = os.path.join(os.path.dirname(__file__), swag_path)
        else:
            swag_path = os.path.join(root, swag_path)
        return open(swag_path).read()

    # :
    # with open(swag_path) as swag_file:
    #     content = swag_file.read()
    #     if swag_type in ('yaml', 'yml'):
    #         return content
    #     elif swag_type  == 'json':
    #         return json_to_yaml(content)

def load_docstring(swag_path,swag_type,swag_subpath,root):
    full_doc = None
    if swag_path is None or swag_type is None:
        return None

    if swag_path is not None:
        full_doc = load_from_file(swag_path, swag_type,root=root)
    # elif swag_paths is not None:
    #     for key in ("{}_{}".format(endpoint, verb), endpoint, verb.lower()):
    #         if key in swag_paths:
    #             full_doc = load_from_file(swag_paths[key], swag_type,root=root)
    #             break
    # else:
    #     full_doc = inspect.getdoc(obj)
    else:
        return None

    if full_doc:

        if full_doc.startswith('file:'):
            full_doc = load_from_file(*get_path_from_doc(full_doc))
        try:
            swag = None
            if swag_type == 'yml':
                swag = yaml.load(full_doc)
            elif swag_type == 'json':
                if root is None:
                    swag = jsonref.loads(full_doc,
                                         base_uri='file:' + os.path.dirname(sys.modules['__main__'].__file__) + '/')
                else:
                    swag = jsonref.loads(full_doc,base_uri='file:' + root)

            if swag_subpath is not None:
                swag = swag.get(swag_subpath,None)

            return swag
        except Exception as e:
            return None
    return None

def _parse_docstring(obj, process_doc, endpoint=None, verb=None, root=None):
    first_line, other_lines, swag = None, None, None

    swag_path = getattr(obj, 'swag_path', None)
    swag_type = getattr(obj, 'swag_type', 'yml')
    swag_paths = getattr(obj, 'swag_paths', None)
    swag_subpath = getattr(obj,'swag_subpath',None)

    swag = load_docstring(swag_path,swag_type,swag_subpath,root)
    if swag is None:
        return '','',None

    summary = swag.get('summary', '')
    description = swag.get('description','')
    swag.pop("summary", None)
    swag.pop("description", None)
    return summary,description,swag
    #
    # if swag_path is not None:
    #     full_doc = load_from_file(swag_path, swag_type,root=root)
    # elif swag_paths is not None:
    #     for key in ("{}_{}".format(endpoint, verb), endpoint, verb.lower()):
    #         if key in swag_paths:
    #             full_doc = load_from_file(swag_paths[key], swag_type,root=root)
    #             break
    # else:
    #     full_doc = inspect.getdoc(obj)
    #
    # if full_doc:
    #
    #     if full_doc.startswith('file:'):
    #         full_doc = load_from_file(*get_path_from_doc(full_doc))
    #
    #
    #     try:
    #         swag = None
    #         if swag_type == 'yml':
    #             swag = yaml.load(full_doc)
    #         elif swag_type == 'json':
    #             if root is None:
    #                 swag = jsonref.loads(full_doc,
    #                                      base_uri='file:' + os.path.dirname(sys.modules['__main__'].__file__) + '/')
    #             else:
    #                 swag = jsonref.loads(full_doc,base_uri='file:' + root)
    #
    #         if swag_subpath is not None:
    #             swag = swag.get(swag_subpath,None)
    #
    #         summary = swag.get('summary','')
    #         description = swag.get('description','')
    #         swag.pop("summary", None)
    #         swag.pop("description", None)
    #         return summary,description,swag
    #     except Exception as e:
    #         return '', '', None
    #
    # return '', '', None


def _extract_definitions(alist, level=None, endpoint=None, verb=None):
    """
    Since we couldn't be bothered to register models elsewhere
    our definitions need to be extracted from the parameters.
    We require an 'id' field for the schema to be correctly
    added to the definitions list.
    """
    endpoint = endpoint or request.endpoint.lower()
    verb = verb or request.method.lower()
    endpoint = endpoint.replace('.', '_')

    def _extract_array_defs(source):
        # extract any definitions that are within arrays
        # this occurs recursively
        ret = []
        items = source.get('items')
        if items is not None and 'schema' in items:
            ret += _extract_definitions([items], level + 1, endpoint, verb)
        return ret

    # for tracking level of recursion
    if level is None:
        level = 0

    defs = list()
    if alist is not None:
        for item in alist:
            schema = item.get("schema")
            if schema is not None:
                schema_id = schema.get("id")
                if schema_id is not None:
                    # add endpoint_verb to schema id to avoid conflicts
                    schema['id'] = schema_id = "{}_{}_{}".format(endpoint,
                                                                 verb,
                                                                 schema_id)
                    defs.append(schema)
                    ref = {"$ref": "#/definitions/{}".format(schema_id)}
                    # only add the reference as a schema if we are in a
                    # response or
                    # a parameter i.e. at the top level
                    # directly ref if a definition is used within another
                    # definition
                    if level == 0:
                        item['schema'] = ref
                    else:
                        item.update(ref)
                        del item['schema']

                # extract any definitions that are within properties
                # this occurs recursively
                properties = schema.get('properties')
                if properties is not None:
                    defs += _extract_definitions(
                        properties.values(), level + 1, endpoint, verb
                    )

                defs += _extract_array_defs(schema)

            defs += _extract_array_defs(item)

    return defs


class SpecsView(MethodView):
    def __init__(self, *args, **kwargs):
        view_args = kwargs.pop('view_args', {})
        self.config = view_args.get('config')
        super(SpecsView, self).__init__(*args, **kwargs)

    def get(self):
        base_endpoint = self.config.get('endpoint', 'swagger')
        specs = [
            {
                "url": url_for(".".join((base_endpoint, spec['endpoint']))),
                "title": spec.get('title'),
                "version": spec.get("version"),
                "endpoint": spec.get('endpoint')
            }
            for spec in self.config.get('specs', [])
        ]
        return jsonify(
            {"specs": specs,
             "title": self.config.get('title', 'Flasgger')}
        )


def is_valid_dispatch_view(endpoint):
    klass = endpoint.__dict__.get('view_class', None)
    return klass and hasattr(klass, 'dispatch_request') \
        and hasattr(endpoint, 'methods')


class OutputView(MethodView):
    def __init__(self, *args, **kwargs):
        view_args = kwargs.pop('view_args', {})
        self.config = view_args.get('config')
        self.info = view_args.get('info')
        self.process_doc = view_args.get('sanitizer', BR_SANITIZER)
        self.template = view_args.get('template')
        self.app = view_args.get('app')

        super(OutputView, self).__init__(*args, **kwargs)

    def get_url_mappings(self, rule_filter=None):
        rule_filter = rule_filter or (lambda rule: True)
        app_rules = [
            rule for rule in current_app.url_map.iter_rules()
            if rule_filter(rule)
        ]
        return app_rules

    def get(self):
        base_url = self.config.get('base_url',None)
        data = {
            "swagger": self.config.get('swagger_version', "2.0"),
            "basePath": self.config.get('base_url',"/"),
            "info": {
                "version": self.info.get('version', "0.0.0"),
                "title": self.info.get('title', "A swagger API"),
                "description": self.info.get('description',"API description")
            },
            "paths": defaultdict(dict),
            "definitions": defaultdict(dict)
        }

        if self.config.get('host'):
            data['host'] = self.config.get('host')
        if self.config.get("basePath"):
            data["basePath"] = self.config.get('basePath')
        if self.config.get("securityDefinitions"):
            data["securityDefinitions"] = self.config.get(
                'securityDefinitions'
            )
        # set defaults from template
        if self.template is not None:
            data.update(self.template)

        paths = data['paths']
        definitions = data['definitions']
        ignore_verbs = set(("HEAD", "OPTIONS"))

        # technically only responses is non-optional
        optional_fields = [
            'tags', 'consumes', 'produces', 'schemes', 'security',
            'deprecated', 'operationId', 'externalDocs'
        ]

        for rule in self.get_url_mappings(None):
            endpoint = current_app.view_functions[rule.endpoint]
            methods = dict()
            for verb in rule.methods.difference(ignore_verbs):
                if is_valid_dispatch_view(endpoint):
                    endpoint.methods = endpoint.methods or ['GET']
                    if verb in endpoint.methods:
                        methods[verb.lower()] = endpoint
                elif hasattr(endpoint, 'methods') and verb in endpoint.methods:
                    verb = verb.lower()
                    methods[verb] = getattr(endpoint.view_class, verb)
                else:
                    methods[verb.lower()] = endpoint
            operations = dict()
            for verb, method in methods.items():
                klass = method.__dict__.get('view_class', None)
                if klass and hasattr(klass, 'dispatch_request'):
                    method = klass.__dict__.get('dispatch_request')
                if verb is None or method is None:
                    continue

                summary, description, swag = _parse_docstring(
                    method, self.process_doc, endpoint=rule.endpoint, verb=verb,root=swagger_doc_root
                )
                # we only add endpoints with swagger data in the docstrings
                if swag is not None:
                    defs = swag.get('definitions', [])
                    defs = _extract_definitions(defs, endpoint=rule.endpoint,
                                                verb=verb)

                    params = swag.get('parameters', [])
                    defs += _extract_definitions(params,
                                                 endpoint=rule.endpoint,
                                                 verb=verb)

                    responses = swag.get('responses', {})
                    responses = {
                        str(key): value
                        for key, value in responses.items()
                    }
                    if responses is not None:
                        defs = defs + _extract_definitions(
                            responses.values(),
                            endpoint=rule.endpoint,
                            verb=verb
                        )
                    for definition in defs:
                        def_id = definition.pop('id')
                        if def_id is not None:
                            definitions[def_id].update(definition)
                    operation = dict(
                        summary=summary,
                        description=description,
                        responses=responses
                    )
                    # parameters - swagger ui dislikes empty parameter lists
                    if len(params) > 0:
                        operation['parameters'] = params
                    # other optionals
                    for key in optional_fields:
                        if key in swag:
                            operation[key] = swag.get(key)
                    operations[verb] = operation

            if len(operations):
                rule = str(rule)
                if base_url is not None and rule.startswith(base_url):
                    rule = rule[len(base_url):]
                # old regex '(<(.*?\:)?(.*?)>)'
                for arg in re.findall('(<([^<>]*:)?([^<>]*)>)', rule):
                    rule = rule.replace(arg[0], '{%s}' % arg[2])
                paths[rule].update(operations)
        return jsonify(data)


def customValidatorDispatch(validator, value, instance, schema):
    global custom_validators
    if custom_validators is None: return

    if value not in custom_validators:
        err = '{} is unknown, we only know about: {}'
        yield ValidationError(err.format(value, ', '.join(custom_validators.keys())))
    else:
        errors = custom_validators[value](validator, value, instance, schema)
        for error in errors:
            yield error

class Swagger(object):

    DEFAULT_CONFIG = {
        "headers": [
        ],
        "info":
            {
                "version": "1.0.1",
                "title": "A swagger API",
                "description": "swagger document"
            },
        "url_prefix": "doc"
    }

    def __init__(self, app=None, config=None, sanitizer=None, template=None):
        self.endpoints = []
        self.sanitizer = sanitizer or BR_SANITIZER
        self.config = config or self.DEFAULT_CONFIG.copy()
        self.template = template
        self.swagger_static_url = 'apidocs'
        self.swagger_endpoint = 'swagger'
        self.swagger_static_folder = 'swaggerui'
        self.swagger_spec_url = 'spec'
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.load_config(app)
        self.load_doc_root(app)
        if doc_enable:
            self.register_views(app)
        self.add_headers(app)

    def load_config(self, app):
        self.config.update(app.config.get('SWAGGER', {}))
        global doc_enable
        global validate_enable
        global custom_validators
        doc_enable = self.config.get('doc_enable',True)
        validate_enable = self.config.get('validate_enable',True)
        custom_validators = self.config.get('custom_validators',None)

    def load_doc_root(self,app):
        if app is not None:
            doc_root = app.root_path
            global swagger_doc_root
            swagger_doc_root = self.config.get('doc_root',None)
            # 已经设置了变量
            if swagger_doc_root is not None:
                # 如果是相对路径，那么加上根目录
                if not swagger_doc_root.startswith('/'):
                    doc_root = os.path.join(doc_root,swagger_doc_root)
                else:
                    doc_root = swagger_doc_root
            if not doc_root.endswith('/'):
                doc_root += "/"
            swagger_doc_root = doc_root


    def register_views(self, app):
        blueprint = Blueprint(
            self.swagger_endpoint,
            __name__,
            static_folder=self.swagger_static_folder,
            static_url_path= '/' + self.swagger_static_url
        )

        @blueprint.route("/")
        def api_index():
            url = url_for(self.swagger_endpoint + '.api_index')
            return redirect(url + self.swagger_static_url + '/index.html?url=' + url + self.swagger_spec_url)

        blueprint.add_url_rule(
            '/' + self.swagger_spec_url,
            self.swagger_spec_url,
            view_func=OutputView().as_view(
                self.swagger_endpoint,
                view_args=dict(
                    app=app, config=self.config,
                    info=self.config['info'],
                    sanitizer=self.sanitizer,
                    template=self.template
                )
            )
        )

        app.register_blueprint(blueprint,url_prefix='/' + self.config.get('url_prefix', None))

    def add_headers(self, app):
        @app.after_request
        def after_request(response):  # noqa
            for header, value in self.config.get('headers'):
                response.headers[header] = value
            return response
