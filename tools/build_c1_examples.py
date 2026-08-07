# -*- coding: utf-8 -*-
"""Claude Opus로 C1 고정 few-shot 예시(c1_examples.json) 생성.

각 권역별로 방언 전문성이 높은 표준어→방언 예시 문장 쌍을 생성한다.
생성 결과는 data/c1_examples.json에 저장.

사용:
  python tools/build_c1_examples.py
"""
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO))

import run  # noqa: E402

OUT = _REPO / "data" / "c1_examples.json"
MODEL = "claude-opus-4-8"

REGIONS = {
    "경상": {
        "display": "경상도",
        "features": "종결어미 ~심더/~니더/~라예/~어예, 연결어미 ~가(서→가), 의문 ~교/~낀교, 부정 몬(못), ~기라(것이다), ~데이",
    },
    "전라": {
        "display": "전라도",
        "features": "종결어미 ~당께요/~랑께요/~구만요, 연결어미 ~응께(으니까), ~부러(버려), 감탄 ~잉, ~소/~겠소",
    },
    "충청": {
        "display": "충청도",
        "features": "종결어미 ~유/~슈/~겨/~여, 의문 ~겨요, 완료 ~어유, ~남/~감(의문 종결)",
    },
    "강원": {
        "display": "강원도",
        "features": "종결어미 ~래요(판단·확인), ~소/~겠소, 청유 ~주소. 주의: 강원 방언은 억양 중심이라 텍스트 표지가 매우 적음 — 표준어와 거의 유사하게 표기되는 것이 정상",
    },
    "제주": {
        "display": "제주도",
        "features": "종결어미 ~수다/~우다/~마씀/~마씨, 청유 ~줍서, 연결 ~엉/~난, 어휘 하영(많이)·아이덜(아이들)·이셔(있어)",
    },
}

PROMPT_TMPL = """\
너는 한국어 {display} 방언 전문가다.
아래 조건에 맞는 악취 민원 전화 상황의 표준어→방언 예시 문장 쌍 7개를 만들어라.

[방언 특징]
{features}

[조건]
- **standard 필드는 반드시 순수 표준어(서울말)로 작성할 것. 어떤 방언 표지도 포함하면 절대 안 됨.**
- dialect 필드는 standard 필드의 문장을 {display} 방언으로 변환한 것
- 민원인이 악취 민원을 신고하는 상황의 자연스러운 구어체 문장
- 존댓말 유지 (반말 금지)
- 표준어와 방언형이 뚜렷하게 구분되도록 (방언 표지를 반드시 포함)
- 표준어와 철자가 같은 일반 단어는 철자 그대로 유지 (소리나는 대로 억지로 변형 금지)
- 예시끼리 어미·표현이 겹치지 않도록 다양하게

[출력 형식 — JSON 배열만 출력, 다른 텍스트 없이]
[
  {{"standard": "표준어 문장", "dialect": "방언 문장"}},
  ...
]
"""


def generate(region_key: str, info: dict) -> list:
    prompt = PROMPT_TMPL.format(
        display=info["display"],
        features=info["features"],
    )
    result = run.call_anthropic(MODEL, prompt, max_tokens=1500, timeout=60)
    if not result["ok"]:
        print(f"  [{region_key}] 실패: {result['error'][:80]}")
        return []
    text = result["text"].strip()
    # JSON 배열 파싱
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        print(f"  [{region_key}] JSON 파싱 실패:\n{text[:200]}")
        return []
    try:
        examples = json.loads(text[start:end + 1])
        print(f"  [{region_key}] {len(examples)}개 생성")
        return examples
    except json.JSONDecodeError as e:
        print(f"  [{region_key}] JSON 오류: {e}")
        return []


def main():
    run.load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[중단] ANTHROPIC_API_KEY 없음. .env 확인 필요.")
        sys.exit(1)

    print(f"모델: {MODEL}\n출력: {OUT}\n")
    result = {}
    for key, info in REGIONS.items():
        print(f"[{info['display']}] 생성 중...")
        examples = generate(key, info)
        result[key] = examples if examples else []

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n저장 완료: {OUT}")
    for k, v in result.items():
        print(f"  {k}: {len(v)}개")


if __name__ == "__main__":
    main()
