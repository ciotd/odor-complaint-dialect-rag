# -*- coding: utf-8 -*-
"""조건별 자연스러움 LLM judge(Opus) — 블라인드 쌍대비교.

judge_reliability로 검증된 judge를 실제 조건 비교에 적용한다.
각 시나리오에서 두 조건의 민원인 발화를 블라인드·순서무작위로 제시하고
"어느 쪽이 더 자연스러운 {region} 방언인가"를 물어 승률을 집계한다.

기본 쌍: c_kb:c1(핵심), c1:c0(앵커). 파이프라인 S1·S2 각각.

사용: python src/eval/judge_conditions.py results/s1_*.jsonl results/s2_*.jsonl \
        [--pairs=c_kb:c1,c1:c0] [--model=claude-opus-4-8] [--n=100]
"""
import sys, os, json, random, re, collections
from concurrent.futures import ThreadPoolExecutor, as_completed

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)
sys.path.insert(0, _HERE)

import run  # noqa: E402
from eval_conditions import complainant_turns  # noqa: E402

SEED = 20260820


def cmpl(text):
    return " / ".join(complainant_turns(text)) or (text or "").strip()[:200]


def prompt_pair(region, t1, t2):
    return (f"다음은 악취 민원 상담에서 '민원인'의 발화 두 가지입니다. "
            f"어느 쪽이 더 자연스러운 {region} 지역 방언입니까? "
            f"방언 특성(종결어미·어휘)이 더 잘 살아있는 쪽을 고르세요.\n\n"
            f"[발화 1]\n{t1}\n\n[발화 2]\n{t2}\n\n"
            f"'1' 또는 '2'로만 답하세요. 다른 말은 하지 마세요.")


def judge(model, region, a, b, rng):
    """a,b 조건 텍스트. 순서 무작위. 반환: a가 이기면 1, b면 0, 실패 None."""
    swap = rng.random() < 0.5
    t1, t2 = (b, a) if swap else (a, b)
    r = run.call_anthropic(model, prompt_pair(region, t1, t2), 10, 60.0)
    if not r.get("ok"):
        return None
    m = re.search(r"[12]", r.get("text", ""))
    if not m:
        return None
    a_pos = "2" if swap else "1"
    return 1 if m.group() == a_pos else 0


def main():
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    model, nmax = "claude-opus-4-8", 10**9
    pairs = [("c_kb", "c1"), ("c1", "c0")]
    for o in [a for a in sys.argv[1:] if a.startswith("--")]:
        if o.startswith("--model="):
            model = o.split("=", 1)[1]
        if o.startswith("--n="):
            nmax = int(o.split("=", 1)[1])
        if o.startswith("--pairs="):
            pairs = [tuple(p.split(":")) for p in o.split("=", 1)[1].split(",")]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        print("사용: python judge_conditions.py results/s1_*.jsonl results/s2_*.jsonl")
        sys.exit(1)
    run.load_env()
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("[중단] ANTHROPIC_API_KEY 없음")
        sys.exit(1)

    rng = random.Random(SEED)
    tasks = []   # (file_label, pairkey, region, a_text, b_text, rng)
    for path in files:
        name = os.path.basename(path)
        pl = "S1" if name.startswith("s1_") else "S2"
        rows = [json.loads(l) for l in open(path, encoding="utf-8")][:nmax]
        for r in rows:
            region = r.get("region", "?")
            gen = r.get("generated") or r.get("converted") or {}
            for A, B in pairs:
                if A in gen and B in gen:
                    tasks.append((pl, f"{A}>{B}", region,
                                  cmpl(gen[A]), cmpl(gen[B]),
                                  random.Random(rng.random())))
    print(f"[judge 조건비교] 모델={model} 비교수={len(tasks)}\n")

    agg = collections.defaultdict(list)   # (pl, pairkey) -> [1/0]
    def work(t):
        pl, pk, region, a, b, r_ = t
        return (pl, pk), judge(model, region, a, b, r_)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(work, t) for t in tasks]
        for i, f in enumerate(as_completed(futs), 1):
            key, v = f.result()
            if v is not None:
                agg[key].append(v)
            print(f"  진행 {i}/{len(tasks)}", end="\r")
    print()

    print("\n=== 자연스러움 승률 (A>B: A가 더 자연스러운 방언으로 뽑힌 비율) ===")
    print(f"{'파이프':<7}{'비교':<12}{'A승률':>8}{'n':>5}")
    print("-" * 36)
    for (pl, pk) in sorted(agg.keys()):
        v = agg[(pl, pk)]
        print(f"{pl:<7}{pk:<12}{sum(v)/len(v):>7.1%}{len(v):>5}")
    print("\n해석: c_kb>c1 이 50%보다 유의하게 높으면 RAG가 더 자연스러운 방언 = 품질축 긍정.")
    print("      c1>c0 은 앵커(few-shot이 기준선 이기는지, 우리 데이터서 judge 검증).")


if __name__ == "__main__":
    main()
