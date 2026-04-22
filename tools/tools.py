tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Get the current weather for a given city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The name of the city to get the weather for."
                }
            },
            "required": ["city"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "calculator",
        "description": "Evaluate a mathematical expression.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate."
                }
            },
            "required": ["expression"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "web_search",
    },
]