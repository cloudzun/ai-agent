import random
import string

def create_support_ticket(email: str, description: str) -> str:
    """
    根据用户提供的电子邮件和问题描述创建支持工单。

    Args:
        email (str): 用户的电子邮件地址。
        description (str): 用户遇到的技术问题的详细描述。

    Returns:
        str: 一条确认消息，包含新的工单ID和保存详情的文件名。
    """
    # 生成一个6位的随机十六进制工单ID
    ticket_id = ''.join(random.choices(string.hexdigits.lower(), k=6))
    filename = f"ticket-{ticket_id}.txt"

    print(f"--- [函数调用]: 正在创建工单 {ticket_id}... ---")

    # 创建工单文件并写入信息
    try:
        with open(filename, "w") as f:
            f.write(f"Support ticket: {ticket_id}\n")
            f.write(f"Submitted by: {email}\n")
            f.write("Description:\n")
            f.write(description)
        
        # 返回成功信息给AI模型
        return f"Your support ticket has been submitted successfully! Your ticket ID is **{ticket_id}**, and the details have been saved in the file **{filename}**. Our team will get back to you shortly."

    except IOError as e:
        print(f"--- [错误]: 无法写入文件 {filename}: {e} ---")
        return "There was an error creating the support ticket file."