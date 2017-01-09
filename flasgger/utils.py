# coding: utf-8

import os
import jsonschema
from flask import request,abort
from functools import wraps

from jsonschema import Draft4Validator
from jsonschema import ValidationError, validate as _validate
from jsonschema.validators import extend
from werkzeug.datastructures import ImmutableMultiDict

from .base import _extract_definitions, yaml, load_from_file,load_docstring, customValidatorDispatch, stripNone
from jsonschema import FormatChecker


def swag_from(filepath, filetype=None, endpoint=None, methods=None,validate_flag=None):
    """
    filepath is complete path to open the file
    filetype is yml, json, py
       if None will be inferred
    If endpoint or methods is defined the definition will be
    exclusive
    """

    def resolve_path(function, filepath):
        # if not filepath.startswith('/'):
        #     if not hasattr(function, 'root_path'):
        #         function.root_path = os.path.dirname(
        #             function.__globals__['__file__'])
        #     return os.path.join(function.root_path, filepath)
        return filepath

    def load_validate_schema(function,schema):
        swag = None
        if schema is not None:
            swag = schema.get('parameters', None)
        if swag is None or type(swag) != list:
            return

        swag_param_query = {}
        swag_param_query_required = []
        swag_param_path = {}
        swag_param_path_required = []
        swag_param_formdata = {}
        swag_param_formdata_required = []

        for item in swag:
            if type(item) != dict:
                continue
            item_name = item.get('name', None)
            item_type = item.get('in', None)
            if not isinstance(item_name, str) or not item_name or \
                            item_type is None:
                continue

            # json 校验
            if item_type == 'body':
                swag_param_body = item.get('schema', None)
                if swag_param_body is not None:
                    function.swag_param_body = swag_param_body
            elif item_type == 'query':
                required = item.get('required',False)
                if not isinstance(required,bool):
                    continue

                item.pop('in',None)
                item.pop('name',None)
                item.pop('required',None)
                swag_param_query[item_name] = item
                if required:
                    swag_param_query_required.append(item_name)
            elif item_type == 'path':
                required = item.get('required',False)
                if not isinstance(required,bool):
                    continue

                item.pop('in',None)
                item.pop('name',None)
                item.pop('required',None)
                swag_param_path[item_name] = item
                if required:
                    swag_param_path_required.append(item_name)
            elif item_type == 'formData':
                required = item.get('required',False)
                if not isinstance(required,bool):
                    continue

                item.pop('in',None)
                item.pop('name',None)
                item.pop('required',None)
                swag_param_formdata[item_name] = item
                if required:
                    swag_param_formdata_required.append(item_name)

        if swag_param_query and len(swag_param_query) > 0:
            function.swag_param_query = {
                'properties' : swag_param_query,
                'type':'object'
            }
            if len(swag_param_query_required) > 0:
                function.swag_param_query['required'] = swag_param_query_required

        if swag_param_path and len(swag_param_path) > 0:
            function.swag_param_path = {
                'properties': swag_param_path,
                'type':'object'
            }
            if len(swag_param_path_required) > 0:
                function.swag_param_path['required'] = swag_param_path_required

        if swag_param_formdata and len(swag_param_formdata) > 0:
            function.swag_param_formdata = {
                'properties': swag_param_formdata,
                'type':'object'
            }
            if len(swag_param_formdata_required) > 0:
                function.swag_param_formdata['required'] = swag_param_formdata_required

    def translate_string_data(schema,data):
        if not isinstance(data,ImmutableMultiDict):
            abort(500)
        rdict = data.to_dict(flat=True)

        properties = schema.get('properties',None)
        if not isinstance(properties,dict):
            abort(500)
        for name, property in properties.items():
            if not isinstance(property,object):
                abort(500)
            type = property.get('type',None)
            if type is None:
                abort(500)
            if type == 'integer':
                value = rdict.get(name,None)
                if value is None or isinstance(value, int):
                    continue

                # 尝试转成int，若失败，则肯定校验不过，直接return
                try:
                    value_int = int(value)
                    rdict[name] = value_int
                except TypeError as te:
                    return rdict
                except ValueError as ve:
                    return rdict
            elif type == 'number':
                value = rdict.get(name, None)
                if value is None or isinstance(value, float):
                    continue
                try:
                    value_float = float(value)
                    rdict[name] = value_float
                except TypeError as te:
                    return rdict
                except ValueError as ve:
                    return rdict
            elif type == 'string':
                value = rdict.get(name, None)
                if value == '' :
                    rdict.pop(name, None)

        return rdict


    def decorator(function):
        # function.__code__.co_filename # option to access filename

        final_filepath = resolve_path(function, filepath)

        if filepath.rfind('#') >= 0:
            function.swag_subpath = filetype or filepath.split('#')[-1]
        else:
            function.swag_subpath = None

        if function.swag_subpath is not None:
            if not function.swag_subpath.startswith('/'):
                raise AttributeError("invalid json sub path")
            # 去掉前面的‘/’
            function.swag_subpath = function.swag_subpath[1:]
            # 不支持多级
            if function.swag_subpath.find('/') >= 0:
                raise AttributeError("invalid json sub path,only one depth")
            length = - (len(function.swag_subpath) + 2)
            final_filepath = final_filepath[0:length]



        function.swag_type = filetype or final_filepath.split('.')[-1]

        if function.swag_type not in ('yaml', 'yml', 'json'):
            raise AttributeError("Currently only yaml or yml or json supported")

        if endpoint or methods:
            if not hasattr(function, 'swag_paths'):
                function.swag_paths = {}

        if not endpoint and not methods:
            function.swag_path = final_filepath
        elif endpoint and methods:
            for verb in methods:
                key = "{}_{}".format(endpoint, verb.lower())
                function.swag_paths[key] = final_filepath
        elif endpoint and not methods:
            function.swag_paths[endpoint] = final_filepath
        elif methods and not endpoint:
            for verb in methods:
                function.swag_paths[verb.lower()] = final_filepath

        from .base import validate_enable
        local_validate = validate_enable if validate_flag is None else validate_flag
        if local_validate:
            from .base import swagger_doc_root
            swag = load_docstring(function.swag_path,
                                  function.swag_type,
                                  function.swag_subpath,
                                  swagger_doc_root)
            load_validate_schema(function,swag)




        @wraps(function)
        def wrapper(*args, **kwargs):
            validate_instance = getattr(function, 'validate_instance', None)
            if validate_instance is None:
                customValidator = extend(Draft4Validator, {'customvalidator': customValidatorDispatch}, 'FlasggerSchema')
                function.validate_instance = customValidator
                validate_instance = customValidator

            swag_param_body = getattr(function, 'swag_param_body', None)
            if swag_param_body is not None:
                request.json_dict = stripNone(request.json)

                # _validate(request.json_dict, swag_param_body, format_checker=FormatChecker())
                validate_instance(swag_param_body, format_checker=FormatChecker()).validate(request.json_dict)

                # http://stackoverflow.com/questions/17404348/simple-python-validation-library-which-reports-all-validation-errors-instead-of
                # validator = customValidator(schema)
                # errors = [e for e in validator.iter_errors(input_dict)]
                # if len(errors):
                #     return errors

            swag_param_query = getattr(function, 'swag_param_query', None)
            request.query_dict = {}
            if swag_param_query is not None:
                data = translate_string_data(swag_param_query,request.args)
                if data is None:
                    abort(500)
                request.query_dict = data
                # _validate(data, swag_param_query, format_checker=FormatChecker())
                validate_instance(swag_param_query, format_checker=FormatChecker()).validate(data)

            swag_param_path = getattr(function, 'swag_param_path', None)
            if swag_param_path is not None:
                # _validate(request.view_args, swag_param_path, format_checker=FormatChecker())
                validate_instance(swag_param_path, format_checker=FormatChecker()).validate(request.view_args)

            swag_param_formdata = getattr(function, 'swag_param_formdata', None)
            request.form_dict = {}
            if swag_param_formdata is not None:
                data = translate_string_data(swag_param_formdata,request.form)
                if data is None:
                    abort(500)
                request.form_dict = data
                # _validate(data, swag_param_formdata, format_checker=FormatChecker())
                validate_instance(swag_param_formdata, format_checker=FormatChecker()).validate(data)

            return function(*args, **kwargs)
        return wrapper
    return decorator


def validate(data, schema_id, filepath, root=None):
    """
    This method is available to use YAML swagger definitions file
    to validate data against its jsonschema.
    example:
    validate({"item": 1}, 'item_schema', 'defs.yml', root=__file__)
    If root is not defined it will try to use absolute import so path
    should start with /
    """

    endpoint = request.endpoint.lower().replace('.', '_')
    verb = request.method.lower()

    full_schema = "{}_{}_{}".format(endpoint, verb, schema_id)

    if not filepath.startswith('/'):
        final_filepath = os.path.join(os.path.dirname(root), filepath)
    else:
        final_filepath = filepath
    full_doc = load_from_file(final_filepath)
    yaml_start = full_doc.find('---')
    swag = yaml.load(full_doc[yaml_start if yaml_start >= 0 else 0:])
    params = [
        item for item in swag.get('parameters', [])
        if item.get('schema')
    ]

    definitions = {}
    main_def = {}
    raw_definitions = _extract_definitions(
        params, endpoint=endpoint, verb=verb)

    for defi in raw_definitions:
        if defi['id'] in [schema_id, full_schema]:
            main_def = defi.copy()
        else:
            definitions[defi['id']] = defi

    main_def['definitions'] = definitions

    for key, value in definitions.items():
        del value['id']

    jsonschema.validate(data, main_def)
