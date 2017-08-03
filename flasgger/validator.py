from datetime import datetime

from jsonschema import ValidationError
from jsonschema._format import _checks_drafts


@_checks_drafts("datetime")
def is_email(instance):
    if not isinstance(instance, str):
        return False
    try:
        datetime.strptime(instance, '%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False

def datetime_validator(validator, value, instance, schema):
    if not validator.is_type(instance, "string"):
        yield ValueError("datetime must be string")

    try:
        datetime.strptime(instance, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        yield ValidationError("Incorrect datatime format, should be YYYY-MM-DD HH:mm:SS")

# 内部的校验器
internal_validators = {
    "datetime": datetime_validator
}

# 内置传入的validator
def internalValidatorDispatch(validator, value, instance, schema):
    global internal_validators
    if internal_validators is None or \
                    value not in internal_validators:
        err = '{} is unknown, we only know about: {}'
        yield ValidationError(err.format(value, ', '.join(internal_validators.keys())))
    else:
        errors = internal_validators[value](validator, value, instance, schema)
        for error in errors:
            yield error