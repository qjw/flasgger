## 运行Sample
```
virtualenv -p python3 venv
. venv/bin/activate
pip install -r requirements.txt
cd sample
python main.py
```
访问<http://127.0.0.1:5000/doc>即可测试

## 定义文档
原版本的flasgger使用yaml来编写文档，本项目改成json格式

> yaml没有找到跨文件ref的方案

下面是一个简单的**json schema**

```json
{
   "summary": "登陆",
    "tags": [
        "我的"
    ],
    "parameters": [
        {
            "name": "id",
            "in": "formData",
            "type": "integer",
            "description": "联系人ID",
            "required": true
        },
        {
            "name": "name",
            "in": "formData",
            "type": "string",
            "description": "联系人名字",
            "required": true
        }
    ],
    "responses": {
        "200": {
            "schema": {
                "properties": {
                    "code": {
                        "type": "integer",
                        "description": "返回码",
                        "default": 0
                    },
                    "message": {
                        "type": "string",
                        "description": "返回字符串描述",
                        "default": "ok"
                    },
                    "data": {

                    }
                }
            }
        }
    }
}
```

### parameters

支持query参数，path参数，json格式和普通的form。在GET方法中提交form不支持[swagger ui不支持，没去查]

json格式的in为body，下面的schema存在一个对当前文件[**#definitions/update**]的引用

```json
[
    {
        "name": "name",
        "in": "formData",
        "type": "string",
        "description": "联系人名字",
        "required": true
    },
    {
        "name": "id",
        "in": "path",
        "type": "integer",
        "description": "联系人ID",
        "required": true
    },
    {
        "in": "body",
        "name":"body",
        "description": "需要修改的内容",
        "required": true,
        "schema": {
            "type": "object",
            "properties": {
                "default": {
                    "type": "boolean",
                    "description": "是否设置默认",
                    "default":true
                },
                "contact": {
                    "$ref": "#/definitions/update"
                }
            },
            "required": [
                "contact"
            ]
        }
    },
    {
        "name": "page",
        "in": "query",
        "type": "integer",
        "description": "页码",
        "required": true
    }
]
```


### 引用

为了减少代码重复，提高json定义的复用程度，json支持**$ref引用**，为了支持跨文件引用，本项目做了大量优化。

在全局配置中定义一个**doc_root**的变量，用来指定存放json文档的根目录，可以使用**绝对路径，这方便多个工程共享**json文档，也可以使用**相对路径**，相对路径基于**app.root_path**

例如下面的定义，其中**file:**前缀不可省略，该路径表示引用**doc_root**目录下的文件definitions.json的【子key】 car_lite，而不是和它相同的目录的文件。

记住：**所有的$ref**路径都基于**doc_root**定义。

```json
{
    "summary": "设置默认车辆",
    "tags": [
        "我的 - 车辆"
    ],
    "parameters": [
    ],
    "responses": {
        "200": {
            "schema": {
                "properties": {
                    "code": {
                        "type": "integer",
                        "description": "返回码",
                        "default": 0
                    },
                    "data": {
                        "$ref": "file:definitions.json#/car_lite"
                    }
                }
            }
        }
    }
}
```

## 配置

```python
Config = {
    SWAGGER: {
        "doc_root": '../doc/json',
        "base_url": "/api/v1",
        "info":
            {
                "version": "v1",
                "title": "swagger",
                "description": "swagger document"
            }
        },
        "url_prefix": "apidoc"
}
```
``` python
app = Flask(__name__)
app.config.update(Config or {})
```

### doc_root
定义文档根目录，可以相对路径或者绝对路径，相对路径基于**app.root_path**

### base_url
定义所有api的base地址，通常都会以诸如**/api/v1**之类的开头，定义本变量的好处在于，swagger文档页不会显示这个前缀，例如接口/api/v1/me/default会显示/me/default，但是提交时，会自动附上base_url已确保提交测试的正确。

### info
版本，标题和描述

### url_prefix
默认是doc，用来定义swagger ui的定义，例如api的地址是<http://www.example.com/api/v1/me/default>,那么swagger ui的地址是<http://www.example.com/doc>，为了避免和已有的api url冲突，可以通过本变量修改url

### custom_headers
自定义的全局header，参考<https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#securityDefinitionsObject>

```
"custom_headers": [
   "api_key1",
   "api_key2",
],
```

## 代码使用
初始化，留意**Swagger(app)**
```python
def create_app(env):
    app = Flask(__name__)
    conf = config.of_env(env)
    conf.init_app(app)
    app.config.from_object(conf)
    Swagger(app)
```

添加注解，注入具体的API，留意**swag_from**

> 跨文件引用，限定只能ref根级，例如[**customer_solicittion/car.json#/car**]，car section就是根节点的key，不支持类似[**customer_solicittion/car.json#/car/type**]之类的引用。

```python
@api.route('/car/<int:id>')
@swag_from('customer_solicittion/car.json#/car')
def get_car(id):
    return jsonify(code=0, message='ok', data={})
```

### 不做校验
swag_from注解添加【**validate_flag=False**】参数即可禁用校验，只保留doc

```
@api.route('/14', methods=['GET'])
@swag_from('api.json#/14',validate_flag=False)
def f14():
    return jsonify(code=0, message='ok')
```

### 校验错误处理
定义全局错误处理函数，留意**handle_bad_request**

> schema可以定义key为**error**的string字段，用于自定义错误输出
为了方便调试，开发环境建议将**schema打印出来**

```python
@app.errorhandler(jsonschema.ValidationError)
def handle_bad_request(e):
  return make_response(jsonify(code=400,
                               message=e.schema.get('error', '参数校验错误'),
                               details=e.message,
                               schema=str(e.schema)), 200)
```

### 文档和校验配置
默认开启文档和校验，可以通过全局和局部配置修改选项

swag_from参数validate_flag可以单独关闭api的自动校验
```python
@api.route('/contact',methods=['PUT'])
@swag_from('customer_solicittion/contact.json#/contact_update',validate_flag=False)
def update_contact():
    return jsonify(code=0, message='ok', data={})
```

可以使用下面的全局配置定义文档和校验默认开启属性（默认开启）
```python
SWAGGER = {
    "validate_enable":True,
    "doc_enable":False
    }
```

若未定义doc_enable或者为true，则生成文档，其他情况不生成文档

在swag_from注解未配置validate_flag选项的情况下，
1. 若未定义validate_enable或者为true，则开启校验
2. 其他情况不校验

若swag_from注解配置了validate_flag选项，则根据选项来开启/关闭校验

原flasgger有一个工具类注解**validate**，本项目并未用到所以代码已经删除，在选项开启的情况下，只要添加了swag_from就自动赋予了校验规则，若校验失败会抛出异常**jsonschema.ValidationError**。

本项目使用 **[jsonschema](https://pypi.python.org/pypi/jsonschema)** 做校验，理论上前者支持的规则，这里都能支持。

## 其他

在flask中，query参数和form参数中所有的value都是string类型，若doc声明类型为[integer],flasgger内部会自动转换成int。最终的结果存放在

1. json - request.json_dict (老版本是request.json)
2. formData/form - request.form_dict
3. query - request.query_dict
4. path - request.view_args

多个api共享文档

swag_from注解可以关联一个文件，或者文件的某一个key。但是不支持多级key，例如**@swag_from('contact.json')**或者**@swag_from('contact.json#/aaa')**
```json
{
    "aaa":{
        "summary": "设置默认车辆",
        "tags": [
            "我的 - 车辆"
        ],
        "parameters": [
        ],
        "responses": {
            "200": {
                "schema": {
                    "properties": {
                        "code": {
                            "type": "integer",
                            "description": "返回码",
                            "default": 0
                        },
                        "data": {
                            "$ref": "file:definitions.json#/car_lite"
                        }
                    }
                }
            }
        }
    }
}
```

# 自定义错误提示

> 留意error key的字段以及**handle_bad_request**处理函数

```json
{
    "in": "body",
    "name":"body",
    "description": "需要修改的内容",
    "required": true,
    "schema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "需要修改的内容",
                "maxLength": 140,
                "error": "限140字"
            }
        },
        "required":[
            "description"
        ]
    }
}
```

错误处理

```python
@app.errorhandler(jsonschema.ValidationError)
def handle_bad_request(e):
  return make_response(jsonify(code=400,
                               message=e.schema.get('error', '参数校验错误'),
                               details=e.message,
                               schema=str(e.schema)), 200)
```

# 自动删除字段
可以配置一个config字段**empty_value**，若字段存在，并且不为空，那么json中所有value和它相等的值会自动删除。

这个需求为了方便前端在作参数拼装时，简化代码，但是会增加服务器负担

# 自定义校验规则
正则表达式是万能的规则，但相比一个让人印象深刻的名称，正则表达式还是比较让人费解。另外的问题是，正则规则通常不只是一个地方用到，那么需要更新的时候可能要改很多地方，容易遗漏，*当然用变量抽出来会好一些*。

```python
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
```

然后，将对象至于config的**custom_validators**字段即可。使用时，使用key【**customvalidator**】

```xml
"mobile": {
    "type": "string",
    "description": "手机号码",
    "custom": "mobile",
    "error_tip":"请输入正确的客户手机1"
}
```

# json schema层面支持null
``` json
"created_at": {
    "error": "fuck",
    "anyOf": [
        {
            "type": "string",
            "description": "创建时间",
            "default": "2017-1-1 19:11:11",
            "format": "date"
        },
        {
            "type": "null"
        }
    ]
}
```

最终方法使用所有类型，不过swagger-ui无法设置显示正确的类型，取而代之的是一个{}，一种变通的办法是

``` json
"name": {
    "type": ["string","null"],
    "description": "客户名称",
    "default": "张三",
    "minLength": 1,
    "maxLength": 20
}
```

## 合并对象
``` json
"data": {
    "type": "object",
    "properties": {
        "default": {
            "type": "boolean",
            "description": "是否已设置默认"
        },
        "contact": {
            "allOf": [
                {
                    "$ref": "file:definitions.json#/car_model"
                },
                {
                    "type": "object",
                    "properties": {
                        "extra": {
                            "type": "string",
                            "description": "额外合并的",
                            "default": "随便"
                        }
                    }
                }
            ]
        }
    }
}
```

最终的结果是
``` json
{
    "contact": {
      "brand": "奔驰",
      "model": "尊贵型",
      "series": "S600",
      "extra": "随便"
    }
}
```


## date-time

默认情况下，string类型支持format:date，格式如[2017-8-3 19:35:43]，在<https://spacetelescope.github.io/understanding-json-schema/reference/string.html>有提到date-time，这种情况下，需要安装
``` bash
pip install strict_rfc3339
```

格式如【2017-04-13T14:34:23+00:00】

或者 [pip install isodate] **优先级低于strict_rfc3339**

格式如【2017-04-13T14:34】，也支持上述的格式

完整的实现见

``` python
try:
    import strict_rfc3339
except ImportError:
    try:
        import isodate
    except ImportError:
        pass
    else:
        @_checks_drafts("date-time", raises=(ValueError, isodate.ISO8601Error))
        def is_date(instance):
            if not isinstance(instance, str_types):
                return True
            return isodate.parse_datetime(instance)
else:
        @_checks_drafts("date-time")
        def is_date(instance):
            if not isinstance(instance, str_types):
                return True
            return strict_rfc3339.validate_rfc3339(instance)
```

为了支持【2017-04-13 14:34:11】格式，系统自动注入了datetime标签

``` json
{
    "type": "string",
    "description": "创建时间",
    "default": "2017-1-1 19:11:11",
    "format": "datetime"
}
```

另外也支持内置的自定义校验器

``` json
{
    "type": "string",
    "description": "创建时间",
    "default": "2017-1-1 19:11:11",
    "internal": "datetime"
}
```

> 受限于jsonschema库的能力，若自定义校验器名字写错了（不存在）无法报错。实际逻辑是忽略错误