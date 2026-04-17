import os
import time
import random

MOCK_RESPONSES = [
    "Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.",
    "Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.",
    "Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.",
]


def ask(question: str, delay: float = 0.1) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    max_tokens = int(os.getenv("MAX_TOKENS", "500"))

    if api_key:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    time.sleep(delay + random.uniform(0, 0.05))
    return random.choice(MOCK_RESPONSES)
