# -*- coding: utf-8 -*-
"""조건별 어휘 방언율 — 검색축(RAG 고유) 평가.

어미 방언율(eval_conditions.py)은 종결어미를 재므로 '고정 주입' 파트를 본다.
반대로 이 지표는 '권역 방언 어휘'가 생성문에 얼마나 실현됐나를 재어, 질의 조건부
어휘 검색(진짜 RAG 파트)의 효과를 조건별로 비교한다.

- 참조 집합: 각 권역 vocab KB의 방언형 중 (방언형 != 표제어) & (한글 2자+) &
  (방언형이 그 권역 표준 표제어와 겹치지 않음) → 명백히 방언적인 형태만.
- 어휘 방언율 = 생성문(민원인 발화)에 등장한 참조 방언형 종류 수 / 총어절.
- 모든 조건(c0/c1/c_kb/c_kb_c1/...)에 동일 참조로 적용 → 공정.

주의: 표면 부분문자열 매칭이라 근사. 조건 간 상대 비교용.

사용: python src/eval/vocab_dialect_rate.py results/s1_*.jsonl results/s2_*.jsonl
"""
import sys, os, json, re, collections

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)
sys.path.insert(0, _HERE)

from eval_conditions import complainant_turns, words_of  # noqa: E402
from src.retrieval.kb_retriever import KBRetriever  # noqa: E402

_NONHAN = re.compile(r"[^가-힣]")
CONDS = ["c0", "c1", "c_kb", "c_kb_plus", "c_kb_c1"]

# kiwi 표준어 필터 — 통짜 단일 형태소로 인식되는 형태 = 표준어로 보고 참조에서 제외.
_MORPH = set("NVMXJEI")  # 정상 한국어 형태소 태그 머리글자(S*=기호, UN*=미등록 제외)
_kiwi = None


def _is_standard(form):
    """kiwi가 form 전체를 '알려진 단일 표준 형태소'로 분석하면 True(→표준어로 제외).
    억수로(억수+로, 2형태소)·미등록어는 False로 유지."""
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    toks = _kiwi.tokenize(form)
    return (len(toks) == 1 and toks[0].form == form
            and toks[0].tag[:1] in _MORPH)


def build_ref(retr, kiwi_filter=True):
    """권역 -> 명백히 방언적인 방언형 집합.
    kiwi_filter=True면 표준어로 인식되는 형태를 객관 규칙으로 제외(오탐 청소)."""
    ref = {}
    cache = {}
    for region, hidx in retr.head_index.items():
        heads = set(hidx.keys())
        forms = set()
        for head, entries in hidx.items():
            for e in entries:
                d = _NONHAN.sub("", str(e.get("dialect") or ""))
                if len(d) < 2 or d == head or d in heads:
                    continue
                if kiwi_filter:
                    if d not in cache:
                        cache[d] = _is_standard(d)
                    if cache[d]:
                        continue  # 표준어로 인식 → 제외
                forms.add(d)
        ref[region] = forms
    return ref


def word_hits(forms, turns):
    """어절 단위 매칭: 어절이 참조 방언형과 같거나 그것으로 시작(어간+조사)하면 적중.
    부분문자열(그때'부터') 오탐을 배제. 적중한 방언형 종류 집합 반환."""
    hit = set()
    for t in turns:
        for w in t.split():
            w = _NONHAN.sub("", w)
            if not w:
                continue
            for f in forms:
                if w == f or w.startswith(f):
                    hit.add(f)
    return hit


def main():
    files = [f for f in sys.argv[1:] if os.path.exists(f)]
    if not files:
        print("사용: python vocab_dialect_rate.py results/s1_*.jsonl results/s2_*.jsonl")
        sys.exit(1)

    print("KB 색인 중...")
    retr = KBRetriever()
    ref = build_ref(retr)
    print("참조 방언어휘 수: " + ", ".join(f"{r}={len(v)}" for r, v in ref.items()))

    # (pipeline, cond) -> [hits], [words]
    acc = collections.defaultdict(lambda: collections.defaultdict(
        lambda: dict(hits=0, words=0, n=0)))

    for path in files:
        pl = "S1" if "/s1_" in path or os.path.basename(path).startswith("s1_") else "S2"
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            region = r.get("region", "?")
            forms = ref.get(region, set())
            gen = r.get("generated") or r.get("converted") or {}
            for cond, text in gen.items():
                turns = complainant_turns(text)
                words = words_of(turns)
                hit = len(word_hits(forms, turns))
                a = acc[pl][cond]
                a["hits"] += hit
                a["words"] += len(words)
                a["n"] += 1

    print("\n" + "=" * 52)
    print("조건별 어휘 방언율 (검색축)")
    print("=" * 52)
    print(f"{'파이프':<7}{'조건':<11}{'어휘방언율':>10}{'적중/대화':>11}{'n':>5}")
    print("-" * 52)
    for pl in ("S1", "S2"):
        for cond in CONDS:
            if cond not in acc[pl]:
                continue
            a = acc[pl][cond]
            rate = a["hits"] / a["words"] if a["words"] else 0.0
            per = a["hits"] / a["n"] if a["n"] else 0.0
            print(f"{pl:<7}{cond:<11}{rate:>10.4f}{per:>11.2f}{a['n']:>5}")
        print("-" * 52)
    print("\n어휘방언율 = 참조 방언어휘 종류 적중 / 총어절 (민원인 발화)")
    print("c_kb > c1 이면 RAG가 어휘축에서 few-shot을 이김(검색 고유 효과).")


if __name__ == "__main__":
    main()
