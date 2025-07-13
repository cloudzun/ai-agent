# --- 1. 导入所有必要的库 ---
import os
import json
import random
import string
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage

# --- 2. 加载环境变量并配置客户端 ---
# 确保您的 .env 文件与此脚本位于同一目录
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)
model_name = os.getenv("OPENAI_MODEL_NAME")

# --- 3. 定义可供 AI 调用的本地“工具”函数 ---
def create_support_ticket(email: str, description: str) -> str:
    """
    根据用户提供的电子邮件和问题描述创建支持工单。
    """
    ticket_id = ''.join(random.choices(string.hexdigits.lower(), k=6))
    filename = f"ticket-{ticket_id}.txt"

    print(f"--- [函数调用]: 正在创建工单 {ticket_id}... ---")

    try:
        with open(filename, "w") as f:
            f.write(f"Support ticket: {ticket_id}\n")
            f.write(f"Submitted by: {email}\n")
            f.write("Description:\n")
            f.write(description)
        
        return f"您的支持票已成功提交！您的票证 ID 是 **{ticket_id}**，相关细节已保存在文件 **{filename}** 中。我们的团队将会尽快与您联系。"

    except IOError as e:
        print(f"--- [错误]: 无法写入文件 {filename}: {e} ---")
        return "创建支持工单文件时发生错误。"

# --- 4. 配置 AI ---

# 4.1. 工具描述
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Creates a support ticket with the user's email and a description of their problem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "The user's email address."},
                    "description": {"type": "string", "description": "A detailed description of the technical problem."}
                },
                "required": ["email", "description"]
            }
        }
    }
]

# 4.2. 函数映射
available_functions = {
    "create_support_ticket": create_support_ticket
}

# 4.3. 系统指令
system_prompt = """
You are a helpful support agent. Your primary goal is to create a support ticket for the user 
by calling the `create_support_ticket` function.

Follow these rules strictly:
1.  Do NOT call the function until you have collected BOTH the user's email address AND a description of their problem.
2.  If you don't have the user's email, ask for it first.
3.  Once you have the email, and only then, ask for the problem description.
4.  Once you have both pieces of information, call the `create_support_ticket` function with the collected details.
"""

# --- 5. 主交互循环 ---
def main():
    """主函数，运行 AI 代理交互循环。"""
    print("Support Agent is running...")
    messages = [{"role": "system", "content": system_prompt}]

    while True:
        user_input = input("Enter a prompt (or type 'quit' to exit): ")
        if user_input.lower() == 'quit':
            print("\nQuitting agent...")
            print("\n--- Conversation Log ---")
            
            # --- START OF FIX ---
            # 修正了日志打印逻辑，以处理混合类型列表（字典和对象）
            for msg in messages:
                # 从字典或对象中安全地获取角色和内容
                role = msg.get('role') if isinstance(msg, dict) else msg.role
                
                # 跳过系统指令和工具返回信息，使日志更干净
                if role in ['system', 'tool']:
                    continue

                # 根据角色确定发言人
                speaker = "USER" if role == 'user' else "AGENT"

                # 从字典或对象中安全地获取内容或工具调用信息
                content = ""
                if isinstance(msg, dict):
                    content = msg.get('content')
                    # 手动创建的消息不会有tool_calls
                else: # 是 ChatCompletionMessage 对象
                    content = msg.content
                    if msg.tool_calls:
                        function_name = msg.tool_calls[0].function.name
                        content = f"[Agent decided to call function: {function_name}]"
                
                print(f"MessageRole.{speaker}: {content}")
            # --- END OF FIX ---
            break

        messages.append({"role": "user", "content": user_input})

        try:
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
                    
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )

                second_response = client.chat.completions.create(model=model_name, messages=messages)
                final_message = second_response.choices[0].message
                print(f"Last Message: {final_message.content}")
                messages.append(final_message)
            else:
                print(f"Last Message: {response_message.content}")

        except Exception as e:
            print(f"An error occurred: {e}")
            break

# --- 6. 运行程序 ---
if __name__ == "__main__":
    main()