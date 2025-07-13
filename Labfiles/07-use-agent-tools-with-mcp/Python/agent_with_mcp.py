# agent_with_mcp.py (Corrected Version)

import os
import json
import requests
import threading
import uvicorn
import time
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# --- 0. 全局配置和初始化 ---
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
MCP_SERVER_HOST = "127.0.0.1"
MCP_SERVER_PORT = 8000
MCP_SERVER_URL = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}"


# ==============================================================================
# --- 1. MCP 服务器逻辑 (已修正) ---
# ==============================================================================

app = FastAPI(title="In-Process MCP Tool Server")

# --- 工具函数 (修正：移除了无效的 @app.tool 装饰器) ---
def get_inventory_levels() -> dict:
    """Returns current inventory for all products."""
    return {
        "Moisturizer": 6, "Shampoo": 8, "Body Spray": 28, "Hair Gel": 5,
        "Lip Balm": 12, "Skin Serum": 9, "Cleanser": 30, "Conditioner": 3,
        "Setting Powder": 17, "Dry Shampoo": 45
    }

# --- 工具函数 (修正：移除了无效的 @app.tool 装饰器) ---
def get_weekly_sales() -> dict:
    """Returns number of units sold last week."""
    return {
        "Moisturizer": 22, "Shampoo": 18, "Body Spray": 3, "Hair Gel": 2,
        "Lip Balm": 14, "Skin Serum": 19, "Cleanser": 4, "Conditioner": 1,
        "Setting Powder": 13, "Dry Shampoo": 17
    }

# --- 工具注册表 (现在是唯一链接工具实现和schema的地方) ---
tools_registry = {
    "get_inventory_levels": {
        "function": get_inventory_levels,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_inventory_levels",
                "description": "获取所有产品的当前库存水平。",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    },
    "get_weekly_sales": {
        "function": get_weekly_sales,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_weekly_sales",
                "description": "获取所有产品上周的销售数量。",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    },
}

# MCP 端点 (无变化)
@app.get("/", summary="Tool Discovery Endpoint")
def discover_tools_endpoint():
    return [details["schema"] for details in tools_registry.values()]

class ToolExecutionRequest(BaseModel):
    args: dict

@app.post("/tools/{tool_name}", summary="Tool Execution Endpoint")
def execute_tool_endpoint(tool_name: str, request: ToolExecutionRequest):
    if tool_name in tools_registry:
        result = tools_registry[tool_name]["function"](**request.args)
        return {"result": result}
    return {"error": "Tool not found"}, 404

def run_mcp_server():
    uvicorn.run(app, host=MCP_SERVER_HOST, port=MCP_SERVER_PORT, log_level="warning")


# ==============================================================================
# --- 2. 客户端逻辑 (无变化) ---
# ==============================================================================

SYSTEM_PROMPT = """
You are an expert inventory management AI assistant.
Your goal is to provide recommendations based on data from your available tools.

Here are the rules you must follow for your analysis:
1.  **Restocking Rule**: A product needs to be restocked if its current inventory is LESS than its weekly sales.
2.  **Clearance Rule**: A product is a candidate for clearance if its current inventory is GREATER than 20 AND its weekly sales are LESS than 5.
3.  **Best Sellers Rule**: The best sellers are the products with the highest weekly sales. List the top 3.

When asked a question, first determine which tools you need to call to get the necessary data.
Then, analyze the data from the tools according to the rules above and provide a clear, concise answer.
If asked for a general inventory list, call the appropriate tool and present the data clearly.
"""

def discover_tools_from_mcp(server_url: str):
    print(f"Connecting to MCP server at {server_url} to discover tools...")
    try:
        response = requests.get(server_url)
        response.raise_for_status()
        discovered_tools = response.json()
        print(f"Success! Discovered {len(discovered_tools)} tools: {[t['function']['name'] for t in discovered_tools]}")
        return discovered_tools
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not connect to MCP server. {e}")
        return None

def execute_mcp_tool(server_url: str, tool_name: str, tool_args: dict):
    print(f"--> Requesting MCP server to execute tool: {tool_name}")
    url = f"{server_url}/tools/{tool_name}"
    response = requests.post(url, json={"args": tool_args})
    response.raise_for_status()
    return response.json().get("result")

def run_client_conversation():
    openai_tools = discover_tools_from_mcp(MCP_SERVER_URL)
    if not openai_tools:
        print("Exiting due to failure in tool discovery.")
        return

    print("\nAgent is ready. Ask about inventory, restocks, clearance, or best sellers.")
    print('Type "quit" to exit.')
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        user_input = input("User > ")
        if user_input.lower() == "quit":
            print("Exiting...")
            break
        
        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=openai_tools, tool_choice="auto"
        )
        response_message = response.choices[0].message

        if response_message.tool_calls:
            messages.append(response_message)
            tool_outputs = []
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                function_response = execute_mcp_tool(MCP_SERVER_URL, function_name, function_args)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(function_response),
                })
            
            messages.extend(tool_outputs)
            
            second_response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
            final_answer = second_response.choices[0].message.content
        else:
            final_answer = response_message.content

        print(f"Agent > {final_answer}")
        messages.append({"role": "assistant", "content": final_answer})


# ==============================================================================
# --- 3. 主程序入口 (无变化) ---
# ==============================================================================

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_mcp_server, daemon=True)
    server_thread.start()
    
    print("MCP server starting in the background...")
    time.sleep(2)
    
    try:
        run_client_conversation()
    except Exception as e:
        print(f"An error occurred in the client: {e}")
    finally:
        print("\nClient conversation has ended.")