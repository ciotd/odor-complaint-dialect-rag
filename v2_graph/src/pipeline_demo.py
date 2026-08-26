# -*- coding: utf-8 -*-
"""v2-graph (b) 전체 파이프라인 데모: 표준→경북 방언, ①추출→②KG조회→③주입→④LLM생성.
KG-focused(서브그래프만) vs Dump(전체 규칙) 대조. 실제 로컬 Qwen 호출.

사용: python v2_graph/src/pipeline_demo.py "뭐 먹었니?"
"""
import sys, os, json, urllib.request
from convert_prototype import load_kb, extract, lookup  # 같은 폴더

LLM_URL = "http://192.168.100.1:8001/v1/chat/completions"
MODEL = "Qwen/Qwen3.6-27B"
SYS = "너는 표준 한국어를 경상북도(경북) 방언으로 바꾸는 변환기다. 의미는 그대로 두고 방언 문장 한 줄만 출력한다."


def call_llm(prompt, max_tokens=120, timeout=60):
    body = {"model": MODEL,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(LLM_URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {os.environ.get('VLLM_API_KEY','')}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def rule_to_text(rule):
    c = rule["conditions"]
    dia = ", ".join(e["form"] for e in rule["어미"] if e["유형"] == "방언")
    cond = f"종결법={c['종결법']}, 상대높임={c['높임']}"
    if c.get("의문종류"): cond += f", 의문종류={c['의문종류']}"
    if c.get("결합환경"): cond += f", 서술어={c['결합환경']}"
    return f"- {cond} → 종결어미 {dia}  ({rule.get('사용양상') or ''})"


def kg_prompt(sent, subgraph):
    rules = "\n".join(rule_to_text(r) for r in subgraph)
    return (f"다음 표준어 문장을 경북 방언으로 바꿔라.\n"
            f"아래 '적용 문법'(이 문장에 해당하는 규칙)을 반드시 사용한다.\n\n"
            f"[적용 문법]\n{rules}\n\n[표준어] {sent}\n[경북 방언]")


def dump_prompt(sent, kb):
    forms = []
    for r in kb:
        forms += [e["form"] for e in r["어미"] if e["유형"] == "방언"]
    forms = sorted(set(forms))
    return (f"다음 표준어 문장을 경북 방언으로 바꿔라.\n"
            f"아래 방언 종결어미 목록 중 알맞은 것을 골라 사용한다.\n\n"
            f"[방언 어미 목록]\n{', '.join(forms)}\n\n[표준어] {sent}\n[경북 방언]")


def main():
    sent = sys.argv[1] if len(sys.argv) > 1 else "뭐 먹었니?"
    kb = load_kb()

    print("=" * 66)
    print("입력(표준):", sent)
    print("\n─ ① 자질 추출 (kiwi) ─")
    f = extract(sent)
    print(" ", {k: v for k, v in f.items() if v is not None})

    print("\n─ ② KG 조회 → 서브그래프 ─")
    res = lookup(kb, f)
    ids = [rid for rid, _ in res]
    subgraph = [r for r in kb if r["id"] in ids]
    for r in subgraph:
        print("  ", json.dumps({"id": r["id"], "conditions": r["conditions"],
                                "방언어미": [e["form"] for e in r["어미"] if e["유형"] == "방언"]},
                               ensure_ascii=False))

    print("\n─ ③ KG-focused 프롬프트 ─")
    kp = kg_prompt(sent, subgraph)
    print("  " + kp.replace("\n", "\n  "))

    print("\n─ ④ LLM 생성 (KG-focused) ─")
    try:
        print("  →", call_llm(kp))
    except Exception as e:
        print("  [LLM 호출 실패]", e)

    print("\n" + "─" * 66)
    print("[대조] Dump(전체 규칙 덤프) 프롬프트로 생성")
    dp = dump_prompt(sent, kb)
    print("  (주입 어미 개수:", dp.count(",") + 1, "개 나열 — 파편 덤프)")
    try:
        print("  →", call_llm(dp))
    except Exception as e:
        print("  [LLM 호출 실패]", e)


if __name__ == "__main__":
    main()
