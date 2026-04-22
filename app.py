from openai import OpenAI
import os
from dotenv import load_dotenv
from tools.weather_tool import get_weather
from tools.calculator_tool import calculator
from utils.calculate_usage import calculate_usage
from tools.tools import tools
import json

load_dotenv()
client = OpenAI()


input_list = [
    {
        "role": "user",
        "content": "Tell me today's latest news about AI"
    }
]

response = client.responses.create(
    model="gpt-5-nano",
    input=input_list,
    tools=tools,
    stream=True,
)

tool_call = None
usage_response_1 = None


for event in response:

    # Stream text
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)

    # Capture tool call
    elif event.type == "response.output_item.done":
        item = event.item
        if item.type == "function_call":
            tool_call = item

    elif event.type == "response.completed":
        usage_response_1 = event.response


if tool_call:
    print("\n\n--- TOOL CALLED ---")
    print(tool_call)

    args = json.loads(tool_call.arguments)

    if tool_call.name == "get_weather":
        result = get_weather(**args)

    elif tool_call.name == "calculator":
        result = calculator(**args)

    else:
        result = "Unknown tool"

    input_list.append(tool_call)

    input_list.append({
        "type": "function_call_output",
        "call_id": tool_call.call_id,
        "output": json.dumps(result)
    })


final_response = client.responses.create(
    model="gpt-5-nano",
    input=input_list,
    tools=tools,
    stream=True,
)

usage_response_2 = None

print("\n\n--- FINAL ANSWER ---\n")

for event in final_response:

    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)

    elif event.type == "response.completed":
        usage_response_2 = event.response


usage1 = calculate_usage(usage_response_1)
usage2 = calculate_usage(usage_response_2)

total_usage = {
    "input_tokens": usage1["input_tokens"] + usage2["input_tokens"],
    "output_tokens": usage1["output_tokens"] + usage2["output_tokens"],
    "total_tokens": usage1["total_tokens"] + usage2["total_tokens"],
    "total_cost": usage1["total_cost"] + usage2["total_cost"]
}

print("\n\n--- USAGE ---")
print(total_usage)