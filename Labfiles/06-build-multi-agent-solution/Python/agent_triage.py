import os
from openai import OpenAI
from dotenv import load_dotenv

# --- 1. 配置和初始化 (与之前相同) ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model_name = os.getenv("OPENAI_MODEL_NAME")

if not all([api_key, base_url, model_name]):
    print("错误：请确保 .env 文件中已配置 OPENAI_API_KEY, OPENAI_BASE_URL, 和 OPENAI_MODEL_NAME。")
    exit()

try:
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
except Exception as e:
    print(f"错误：无法初始化 OpenAI 客户端 - {e}")
    exit()

# --- 2. 定义 "代理" 函数 (与之前相同，无需改动) ---

def get_priority_assessment(ticket_description: str) -> str:
    system_prompt = """
    你是一位经验丰富的 IT 支持团队经理。你的任务是评估用户提交的技术支持工单的优先级。
    请从以下选项中选择一个优先级：Low, Medium, High。
    你的回答格式必须是：[优先级] — [简短的理由说明]。
    """
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ticket_description}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"获取优先级评估时出错: {e}"

def get_team_assignment(ticket_description: str) -> str:
    system_prompt = """
    你是一位 IT 支持工单分派专家。你的任务是根据工单描述，将其分配给最合适的团队。
    可选团队包括：Frontend, Backend, Mobile App, Infrastructure, DevOps。
    你的回答格式必须是：[团队名称] — [简短的理由说明]。
    """
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ticket_description}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"获取团队分配时出错: {e}"

def get_effort_estimation(ticket_description: str) -> str:
    system_prompt = """
    你是一位资深的软件开发经理。你的任务是评估解决一个技术工单所需的工作量。
    请从以下选项中选择一个工作量级别：Low, Medium, High。
    你的回答格式必须是：[工作量级别] — [简短的解释，并预估所需时间]。
    """
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ticket_description}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"获取工作量评估时出错: {e}"

# --- 3. 主程序：改为交互式输入 ---
if __name__ == "__main__":
    
    print("欢迎使用 AI 工单评估系统 (输入 'exit' 或 'quit' 退出)")
    
    # 使用一个循环来持续接收用户输入
    while True:
        # 从用户那里获取输入
        user_ticket = input("\n请输入您遇到的问题: ")

        # 检查用户是否想退出
        if user_ticket.lower() in ['exit', 'quit']:
            print("程序已退出。")
            break

        # 检查输入是否为空
        if not user_ticket:
            print("输入不能为空，请重新输入。")
            continue

        print("\n正在处理，请稍候...")
        print("开始处理代理线程...\n")

        # 依次调用各个代理函数
        priority = get_priority_assessment(user_ticket)
        team = get_team_assignment(user_ticket)
        effort = get_effort_estimation(user_ticket)

        # 打印用户输入
        print("MessageRole.USER:")
        print(f"{user_ticket}\n")

        # 格式化并打印代理的最终评估报告
        print("MessageRole.AGENT:")
        print("### Ticket Assessment\n")
        print(f"- **Priority:** {priority}")
        print(f"- **Assigned Team:** {team}")
        print(f"- **Effort Required:** {effort}\n")

        print("清理代理：任务完成。")