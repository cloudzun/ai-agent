# agent.py - 完整更新版

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from IPython import get_ipython
from IPython.terminal.interactiveshell import TerminalInteractiveShell

# --- 1. 配置和初始化 ---

# 加载 .env 文件中的环境变量
load_dotenv()

# 从环境变量中获取 API 配置
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model_name = os.getenv("OPENAI_MODEL_NAME")

# 检查配置是否存在，如果不存在则抛出错误
if not all([api_key, base_url, model_name]):
    raise ValueError(
        "请确保 .env 文件中包含了 OPENAI_API_KEY, OPENAI_BASE_URL, 和 OPENAI_MODEL_NAME"
    )

# 初始化 OpenAI 客户端
client = OpenAI(api_key=api_key, base_url=base_url)

# --- 2. 使用 IPython 作为代码执行器 (改进版) ---

def execute_python_code(code: str) -> str:
    """
    改进版代码执行器 - 处理换行符问题并提供更好的错误反馈
    
    Args:
        code: 要执行的 Python 代码字符串
        
    Returns:
        执行结果字符串
    """
    if not code.strip():
        return "错误：收到了空代码。"
    
    # 获取或创建 IPython 实例
    ipython = get_ipython()
    if ipython is None:
        ipython = TerminalInteractiveShell.instance()
    
    # 修正换行符问题
    code = code.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
    
    try:
        # 执行代码并获取结果
        result = ipython.run_cell(code)
        
        # 处理执行结果
        if result.success:
            output = ""
            if result.result is not None:
                output += str(result.result)
            if result.output.strip():
                if output: output += "\n"
                output += result.output
            
            return output if output else "代码执行成功，但没有产生输出。"
        else:
            error = str(result.error_in_exec) if result.error_in_exec else "未知错误"
            return f"代码执行错误: {error}"
    
    except Exception as e:
        return f"执行时发生意外错误: {str(e)}"

# --- 3. 为 OpenAI API 定义工具的 Schema ---

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "执行一段 Python 代码来处理数据、进行计算或生成分析。此代码可以读取本地的 data.txt 文件进行分析，并可以使用 pandas, matplotlib 等库。代码执行结果会返回给你用于生成最终答案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的 Python 代码字符串。",
                    },
                },
                "required": ["code"],
            },
        },
    }
]

# --- 4. 设置代理的行为和上下文 (改进版 RAG) ---

def load_data():
    """改进的数据加载函数，包含示例数据"""
    from io import StringIO
    import pandas as pd
    
    sample_data = """Category,Cost
Transportation,2301.00
Accommodation,674.56
Meals,267.89
Misc.,34.50"""
    
    try:
        with open('data.txt', 'r') as f:
            content = f.read()
            
        # 尝试解析数据
        try:
            if content.strip().startswith('{'):
                # 假设是JSON格式
                data = pd.DataFrame.from_dict(json.loads(content), orient='index').reset_index()
                data.columns = ['Category', 'Cost']
            else:
                # 假设是CSV格式
                data = pd.read_csv(StringIO(content))
        except:
            # 如果解析失败，使用示例数据
            data = pd.read_csv(StringIO(sample_data))
            
        return data.to_string(), sample_data
    except FileNotFoundError:
        return "数据文件 'data.txt' 未找到。", sample_data

data_content, sample_data = load_data()

system_prompt = f"""
你是一个高效的AI数据分析助手。你的任务是根据用户的请求，通过执行Python代码来分析数据并直接回答问题。
使用你拥有的 'execute_python_code' 工具来分析数据。代码执行结果会直接返回给你。

数据说明:
1. 主要数据文件是 data.txt (CSV或JSON格式)
2. 如果文件不存在或格式错误，将使用示例数据

当前数据内容:
---
{data_content if isinstance(data_content, str) else data_content.to_string()}
---

示例数据(备用):
---
{sample_data}
---

请遵循以下规则:
1. 生成图表时优先使用文本格式
2. 数值显示应包含千位分隔符和货币符号(如 $2,301.00)
3. 如果请求无法完成，提供数据摘要而非直接报错
"""

# --- 5. 主交互循环 (改进版) ---

def main():
    print("AI 数据分析代理已启动。输入 'exit' 来退出程序。")
    print("-" * 30)
    messages = [{"role": "system", "content": system_prompt}]

    while True:
        try:
            user_input = input("你: ").strip()
        except EOFError:
            break
            
        if user_input.lower() == 'exit':
            print("正在退出代理...")
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            response_message = response.choices[0].message

            if response_message.tool_calls:
                messages.append(response_message)
                for tool_call in response_message.tool_calls:
                    if tool_call.function.name == "execute_python_code":
                        function_args = json.loads(tool_call.function.arguments)
                        code_to_run = function_args.get("code", "")
                        
                        print(f"\n[正在执行代码]:\n---\n{code_to_run}\n---")
                        tool_output = execute_python_code(code_to_run)
                        print(f"[代码执行结果]:\n{tool_output}\n")

                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "execute_python_code",
                            "content": tool_output,
                        })
                
                # 获取最终响应
                final_response = client.chat.completions.create(
                    model=model_name,
                    messages=messages
                )
                final_answer = final_response.choices[0].message.content
                print(f"AI 助手: {final_answer}")
                messages.append({"role": "assistant", "content": final_answer})
            else:
                answer = response_message.content
                print(f"AI 助手: {answer}")
                messages.append({"role": "assistant", "content": answer})
                
        except Exception as e:
            error_msg = f"系统错误: {str(e)}"
            print(f"AI 助手: {error_msg}")
            messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()