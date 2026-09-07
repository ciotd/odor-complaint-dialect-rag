# -*- coding: utf-8 -*-
"""S1 C_kb 주입 활용률(injection utilization) 분석.

질문: C_kb에서 프롬프트에 '주입한' 방언 어휘·규칙 중 실제로 생성문에 '등장한'
비율은 얼마인가? (모델이 준 지식을 실제로 썼는가)

- 검색은 결정적이므로 저장된 질의(smell_type + 위치)로 주입 목록을 재현한다.
- 활용률(utilization)   = 주입형 중 c_kb 생성문에 등장한 비율
- 귀속 상승분(attrib)   = c_kb엔 등장하나 같은 시나리오 c0엔 없는 비율
                          (모델이 원래 쓸 것 제외 → '주입 덕분'의 근사)

주의:
  - 어휘형은 2자 이상만(짧은 형태 오탐 방지).
  - 규칙 dialect_form은 '-' 접두 제거 후 한글 2자 이상만. 방언율 지표와 일부 겹침.
  - S1만 대상(질의가 키워드라 복원이 깨끗). S2는 별도.

사용: python src/eval/injection_utilization.py results/s1_YYYYMMDD_HHMMSS.jsonl
"""
import sys, os, json, re, collections

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)
sys.path.insert(0, _HERE)

from eval_conditions import complainant_turns  # noqa: E402
from src.retrieval.kb_retriever import KBRetriever  # noqa: E402

_NONHAN = re.compile(r"[^가-힣]")


def norm_forms(raw):
    """'-어예/-어여' 같은 문자열 → ['어예','어여'] (한글 2자+만)."""
    out = []
    for part in re.split(r"[/,]", str(raw or "")):
        p = _NONHAN.sub("", part)
        if len(p) >= 2:
            out.append(p)
    return out


def injected_forms(retr, query, region):
    """파이프라인과 동일 파라미터로 주입 목록 재현 → (어휘형set, 규칙형set)."""
    hits = retr.retrieve(query, region, use_lex=True, use_rule=True,
                         k_lex=5, k_rule=3)
    lex = hits["lexicon"][:20]
    rules = hits["rules"][:10]
    vocab_forms = set()
    for g in lex:
        for d in g.get("dialects", []):
            vocab_forms.update(norm_forms(d))
    rule_forms = set()
    for r in rules:
        rule_forms.update(norm_forms(r.get("dialect_form")))
    return vocab_forms, rule_forms


def used(forms, text):
    return {f for f in forms if f in text}


def main():
    files = [f for f in sys.argv[1:] if os.path.exists(f)]
    if not files:
        print("사용: python injection_utilization.py results/s1_*.jsonl")
        sys.exit(1)

    print("KB 색인 중...")
    retr = KBRetriever()

    # 집계 그릇: region -> counters
    def new_acc():
        return dict(n=0, vinj=0, vuse=0, vatt=0, rinj=0, ruse=0, ratt=0,
                    v_zero_inj=0)
    per = collections.defaultdict(new_acc)
    tot = new_acc()

    for path in files:
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            region = r.get("region", "?")
            gen = r.get("generated", {})
            if "c_kb" not in gen:
                continue
            inp = r.get("input", {})
            query = f"{inp.get('smell_type','')} {inp.get('complainant_location_text','')}".strip()

            vforms, rforms = injected_forms(retr, query, region)
            kb_text = " ".join(complainant_turns(gen.get("c_kb", "")))
            c0_text = " ".join(complainant_turns(gen.get("c0", "")))

            v_used = used(vforms, kb_text)
            r_used = used(rforms, kb_text)
            v_att = {f for f in v_used if f not in c0_text}
            r_att = {f for f in r_used if f not in c0_text}

            for acc in (per[region], tot):
                acc["n"] += 1
                acc["vinj"] += len(vforms)
                acc["vuse"] += len(v_used)
                acc["vatt"] += len(v_att)
                acc["rinj"] += len(rforms)
                acc["ruse"] += len(r_used)
                acc["ratt"] += len(r_att)
                if not vforms:
                    acc["v_zero_inj"] += 1

    def rate(a, b):
        return (a / b) if b else 0.0

    hdr = (f"{'권역':<6}{'n':>4}{'어휘주입':>8}{'어휘활용%':>9}{'어휘귀속%':>9}"
           f"{'규칙주입':>8}{'규칙활용%':>9}{'규칙귀속%':>9}{'무주입시나리오':>12}")
    print("\n" + "=" * len(hdr))
    print("S1 C_kb 주입 활용률")
    print("=" * len(hdr))
    print(hdr)
    print("-" * len(hdr))
    for region in list(per.keys()) + ["__ALL__"]:
        a = tot if region == "__ALL__" else per[region]
        name = "전체" if region == "__ALL__" else region
        print(f"{name:<6}{a['n']:>4}"
              f"{rate(a['vinj'],a['n']):>8.2f}"
              f"{rate(a['vuse'],a['vinj'])*100:>9.1f}"
              f"{rate(a['vatt'],a['vinj'])*100:>9.1f}"
              f"{rate(a['rinj'],a['n']):>8.2f}"
              f"{rate(a['ruse'],a['rinj'])*100:>9.1f}"
              f"{rate(a['ratt'],a['rinj'])*100:>9.1f}"
              f"{a['v_zero_inj']:>12}")
    print("\n해석:")
    print("  어휘주입/규칙주입 = 시나리오당 평균 주입 형태 수")
    print("  활용% = 주입형 중 c_kb 생성문 등장 비율")
    print("  귀속% = c_kb엔 있고 같은 시나리오 c0엔 없는 비율(주입 순기여 근사)")
    print("  무주입시나리오 = 어휘가 하나도 주입되지 않은 시나리오 수(검색 미발화)")


if __name__ == "__main__":
    main()
