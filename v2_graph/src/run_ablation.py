# -*- coding: utf-8 -*-
"""v2-graph ablation 실험: 표준→경상 방언 변환, 3조건 대조.
  (1) 치환만          : 어휘 치환 + 문법flat
  (2) 치환+KG         : (1) + 종결어미 focused 서브그래프 + 음운규칙
  (3) 치환+덤프        : (1) + 전체 종결어미 규칙 덤프 + 음운 (focusing 없음)
각 입력 문장을 3조건으로 LLM 변환 → results/ablation_*.jsonl 저장.

사용: python run_ablation.py [N]   (N=문장 수 제한, 기본 전체)
"""
import sys, os, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert_prototype import extract, lookup            # 자질추출, 종결어미 조회
from substitution import load_lexicon, load_grammar_flat, get_substitutions

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
KB = os.path.join(HERE, "..", "data", "kg_rules.jsonl")
DATA = os.path.join(HERE, "..", "data")
DEFAULT_IN = os.path.join(DATA, "eval_pairs.jsonl")   # AI-Hub 실제 (표준,방언_ref) 쌍

LLM_URL = "http://192.168.100.1:8001/v1/chat/completions"
MODEL = "Qwen/Qwen3.6-27B"
SYS = "너는 표준 한국어를 경상북도(경북) 방언으로 바꾸는 변환기다. 의미는 그대로 두고 방언 문장 한 줄만 출력한다."


def call_llm(prompt, max_tokens=120, timeout=60):
    body = {"model": MODEL, "messages": [{"role": "system", "content": SYS},
            {"role": "user", "content": prompt}], "max_tokens": max_tokens,
            "temperature": 0.3, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(LLM_URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {os.environ.get('VLLM_API_KEY','')}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def load_kb():
    rows = [json.loads(l) for l in open(KB, encoding="utf-8") if l.strip()]
    jong = [r for r in rows if r.get("domain") == "종결어미"]
    phon = [r for r in rows if r.get("domain") == "음운"]
    return jong, phon


def subs_block(sent, lex):
    hits = get_substitutions(sent, lex)
    if not hits:
        return "(해당 어휘 없음)"
    return "\n".join(f"- {h['표준']} → {'/'.join(h['방언'][:3])}" for h in hits)


def ending_focused(sent, jong):
    f = extract(sent)
    if not f:
        return "(어미 규칙 미검색)", None
    res = lookup(jong, f)
    lines = []
    for rid, dia in res:
        if dia:
            lines.append(f"- [{f['종결법']}·{f['높임']}] 종결어미 {'/'.join(dia[:3])}")
    return ("\n".join(lines) or "(해당 어미 없음)"), f


def endings_dump(jong):
    forms = []
    for r in jong:
        forms += [e["form"] for e in r["어미"] if e["유형"] == "방언"]
    return ", ".join(sorted(set(forms)))


def phon_block(phon):
    return "\n".join(f"- {p['변환']['from']}→{p['변환']['to']} ({p['예']})"
                     for p in phon if p["검증"] == "①")   # 신뢰 높은 것만


def prompt(sent, lex, jong, phon, mode):
    head = (f"다음 표준어 문장을 경북 방언으로 바꿔라. 의미 유지, 방언 문장 한 줄만.\n\n"
            f"[어휘 치환]\n{subs_block(sent, lex)}\n")
    if mode == "치환만":
        body = ""
    elif mode == "치환+KG":
        ef, _ = ending_focused(sent, jong)
        body = f"\n[적용 어미규칙(이 문장에 해당)]\n{ef}\n\n[음운규칙]\n{phon_block(phon)}\n"
    elif mode == "치환+덤프":
        body = (f"\n[전체 어미규칙 — 알맞은 것 선택]\n{endings_dump(jong)}\n\n"
                f"[음운규칙]\n{phon_block(phon)}\n")
    return head + body + f"\n[표준어] {sent}\n[경북 방언]"


def main():
    args = sys.argv[1:]
    inp = next((a for a in args if a.endswith(".jsonl")), DEFAULT_IN)
    n = next((int(a) for a in args if a.isdigit()), 10**9)
    base = os.path.splitext(os.path.basename(inp))[0]
    OUT = os.path.join(HERE, "..", "results", f"ablation_{base}.jsonl")
    lex = load_lexicon()
    jong, phon = load_kb()
    inputs = [json.loads(l) for l in open(inp, encoding="utf-8") if l.strip()][:n]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    results = []
    for i, item in enumerate(inputs, 1):
        sent = item["표준"]
        row = {**item, "출력": {}}
        for mode in ("치환만", "치환+KG", "치환+덤프"):
            try:
                row["출력"][mode] = call_llm(prompt(sent, lex, jong, phon, mode))
            except Exception as e:
                row["출력"][mode] = f"[ERR {e}]"
        results.append(row)
        print(f"[{i}/{len(inputs)}] {sent}")
        for m in ("치환만", "치환+KG", "치환+덤프"):
            print(f"    {m:<8} → {row['출력'][m]}")
    with open(OUT, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n저장: {OUT} ({len(results)}건)")


if __name__ == "__main__":
    main()
