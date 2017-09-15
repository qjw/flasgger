from jsonschema import ValidationError


def property_validator_maker(cls):
    def property_validator(validator, value, instance, schema):
        if (
                    validator.is_type(instance, "integer") and
                    cls.code_of(instance) == cls.STATUS_CODES[cls.UNKNOWN]
        ):
            yield ValidationError("%r does not in %r" % (instance, cls.__name__))
    return property_validator

class CarColor:
    UNKNOWN = 0
    WHITE = 1
    ORANGE = 2
    GRAY = 3
    BLACK = 4
    BROWN = 5
    YELLOW = 6
    CHAMPAGNE = 7
    BLUE = 8
    GREEN = 9
    PURPLE = 10
    RED = 11

    STATUS_NAMES = {
        UNKNOWN: '未知',
        WHITE: '白色',
        ORANGE: '橙色',
        GRAY: '灰色',
        BLACK: '黑色',
        BROWN: '棕色',
        YELLOW: '黄色',
        CHAMPAGNE: '香槟色',
        BLUE: '蓝色',
        GREEN: '绿色',
        PURPLE: '紫色',
        RED: '红色',
    }

    STATUS_CODES = {
        UNKNOWN: 'unknown',
        WHITE: 'white',
        ORANGE: 'orange',
        GRAY: 'gray',
        BLACK: 'black',
        BROWN: 'brown',
        YELLOW: 'yellow',
        CHAMPAGNE: 'champagne',
        BLUE: 'blue',
        GREEN: 'green',
        PURPLE: 'purple',
        RED: 'red',
    }

    @classmethod
    def code_of(cls, status):
        return cls.STATUS_CODES.get(status, cls.STATUS_CODES[cls.UNKNOWN])


custom_validators = {
        "CarColor": property_validator_maker(CarColor),
    }