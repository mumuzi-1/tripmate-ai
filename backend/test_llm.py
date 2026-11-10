
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def main():
    load_dotenv()

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL")

    if not all([api_key, base_url, model_name]):
        print("LLM 配置不完整")
        return

    print("正在测试大模型连接...")
    print("模型：", model_name)

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.2,
        timeout=60,
        max_retries=1,
    )

    response = llm.invoke(
        "请用一句中文介绍杭州西湖，不超过30个字。"
    )

    print("模型回答：")
    print(response.content)

    print("LLM Connection OK")


if __name__ == "__main__":
    main()
