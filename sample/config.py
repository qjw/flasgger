from sample.validator import custom_validators

Config = {
    "SWAGGER": {
        "doc_root": '../doc',
        "base_url": "/api/v123456",
        "custom_validators": custom_validators,
        "custom_headers": [
           "api_key1",
           "api_key2",
        ],
        "info":
            {
                "version": "v1",
                "title": "Swagger测试",
                "description": "测试各种参数，规则"
            }
    }
}