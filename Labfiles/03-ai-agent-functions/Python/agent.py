import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# 从我们自己的文件中导入工具函数
from user_functions import create_support_ticket

# --- 1. 初始化和配置 ---
load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)
model_name = os.getenv("OPENAI_MODEL_NAME")

# --- 2. 向AI描述我们的工具 ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Creates a support ticket with the user's email and a description of their problem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "The user's email address."
                    },
                    "description": {
                        "type": "string",
                        "description": "A detailed description of the technical problem the user is facing."
                    }
                },
                "required": ["email", "description"]
            }
        }
    }
]

# 将函数名映射到真实的Python函数对象
available_functions = {
    "create_support_ticket": create_support_ticket
}

# --- 3. 定义AI代理的行为 (System Prompt) ---
system_prompt = """
You are a helpful support agent. Your primary goal is to create a support ticket for the user 
by calling the `create_support_ticket` function.

Follow these rules strictly:
1.  Do NOT call the function until you have collected BOTH the user's email address AND a description of their problem.
2.  If you don't have the user's email, ask for it first.
3.  Once you have the email, and only then, ask for the problem description.
4.  Once you have both pieces of information, confirm with the user and then call the `create_support_ticket` function with the collected details.
"""

# --- 4. 主交互循环 ---
def main():
    print("Support Agent is running...")
    messages = [{"role": "system", "content": system_prompt}]

    while True:
        user_input = input("Enter a prompt (or type 'quit' to exit): ")
        if user_input.lower() == 'quit':
            print("\nConversation Log:\n")
            for msg in messages[1:]: # Skip system prompt for cleaner log
                print(f"MessageRole.{msg['role'].upper()}: {msg.get('content') or 'Called function ' + (msg.get('tool_calls')[0].function.name if msg.get('tool_calls') else '') }")
            break

        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        response_message = response.choices[0].message
        messages.append(response_message)

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                
                function_response = function_to_call(**function_args)
                
                # 将工具的执行结果发回给模型
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )

            # 让模型基于工具返回的结果进行总结
            second_response = client.chat.completions.create(
                model=model_name,
                messages=messages
            )
            final_message = second_response.choices[0].message
            print(f"Last Message: {final_message.content}")
            messages.append(final_message)
        else:
            print(f"Last Message: {response_message.content}")

if __name__ == "__main__":
    main()