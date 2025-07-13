
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

# --- 1. 定义可供 AI 调用的本地“工具” ---
def send_email(to: str, subject: str, body: str) -> str:
    """
    根据提供的收件人、主题和正文内容，模拟发送一封邮件。
    实际中这里会是真正的邮件发送代码，现在我们只打印到控制台。
    """
    # 这个打印输出就是我们期望看到的“副作用”，与预期输出完全一致
    print(f"\nTo: {to}")
    print(f"Subject: {subject}")
    print(body)
    # 将成功信息返回给 AI，以便它生成最终的回复
    return "Expense claim email has been sent successfully."

# --- 2. 将本地工具转换为 OpenAI API 能理解的格式 ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Sends an email with a subject and body to a recipient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "The email address of the recipient."
                    },
                    "subject": {
                        "type": "string",
                        "description": "The subject line of the email."
                    },
                    "body": {
                        "type": "string",
                        "description": "The main content (body) of the email. This should be a detailed summary of the expenses, including a calculated total."
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
    }
]

# 创建一个从函数名到真实 Python 函数的映射
available_functions = {
    "send_email": send_email
}

# --- 3. 主程序 ---
def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    # 加载 .env 文件并初始化 OpenAI 客户端
    load_dotenv()
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    model_name = os.getenv("OPENAI_MODEL_NAME")

    # 加载数据文件
    try:
        script_dir = Path(__file__).parent
        file_path = script_dir / 'data.txt'
        with file_path.open('r') as file:
            data = file.read()
    except FileNotFoundError:
        print("Error: data.txt not found. Please make sure the file exists.")
        return

    # 获取用户初始指令
    user_prompt = input(f"Here is the expenses data in your file:\n\n{data}\nWhat would you like me to do with it?\n\n")

    # 定义系统指令
    system_prompt = """
You are an AI assistant for expense claim submission. Your only goal is to use the provided tools to send an email to submit an expense claim.
1.  Analyze the user's request and the provided data.
2.  Your task is to call the `send_email` function.
3.  The email **must** be sent to `expenses@contoso.com`.
4.  The subject **must** be `Expense Claim`.
5.  For the body, you **must** first calculate the total of all expenses. Then, create a body containing a clearly itemized list of each expense and the final total.
6.  After the `send_email` function is called successfully, you **must** generate a final confirmation message for the user that summarizes the details from the function call.
"""

    print("\nProcessing your request...")

    # 准备发送给 API 的消息列表
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{user_prompt}\n\nData:\n{data}"}
    ]

    try:
        # 第一次调用：让模型决定调用工具
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        response_message = response.choices[0].message
        messages.append(response_message)

        # 检查模型是否决定调用工具
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                
                function_response = function_to_call(**function_args)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })

            # 第二次调用：让模型生成最终总结
            second_response = client.chat.completions.create(model=model_name, messages=messages)
            final_response = second_response.choices[0].message.content
            print(f"\n# expenses_agent:\n{final_response}\n")
        else:
            print(f"\n# expenses_agent:\n{response_message.content}\n")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()