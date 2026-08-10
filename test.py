import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

BASE_URL = "http://192.168.100.1:8001/v1"
API_KEY = os.environ.get("VLLM_API_KEY", "")

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)

try:
    # 서버에 올라간 모델 확인
    models = client.models.list()

    if not models.data:
        raise RuntimeError("서버에서 사용 가능한 모델을 찾지 못했습니다.")

    model_name = models.data[0].id
    print(f"연결 성공: {model_name}")

    # 간단한 추론 요청
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": "안녕하세요. 한 문장으로 자기소개해 주세요.",
            }
        ],
        max_tokens=100,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

    print("\n모델 응답:")
    print(response.choices[0].message.content)

except Exception as error:
    print(f"요청 실패: {error}")