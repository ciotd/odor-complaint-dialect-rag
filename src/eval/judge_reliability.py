# -*- coding: utf-8 -*-
"""LLM judge(Opus) 신뢰성 검증 — 방언 자연스러움을 분별하는가.

A단계 교란 산출물(원본/표준어화/타권역화)을 재활용한 '알려진 정답' 테스트.
제대로 된 judge라면 블라인드 쌍대비교에서:
  - 원본(방언) > 표준어화(방언 제거)   를 고른다
  - 원본(맞는 권역) > 타권역화(틀린 권역) 를 고른다
정답률이 높아야 judge를 조건 비교에 쓸 수 있다. (쉬운 관문 — 통과=필요조건, 미통과=judge 폐기)

위치 편향 차단: 제시 순서를 시드로 무작위화. 파싱: 응답에서 '1'/'2'.

사용: python src/eval/judge_reliability.py results/llm_perturb_s1_*.jsonl [--model=claude-opus-4-8] [--n=88]
"""
import sys, os, json, random, re
from concurrent.futures import ThreadPoolExecutor, as_completed

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)
sys.path.insert(0, _HERE)

import run  # noqa: E402
from eval_conditions import complainant_turns  # noqa: E402

SEED = 20260820


def cmpl(text):
    return " / ".join(complainant_turns(text)) or text.strip()[:200]


def prompt_pair(region, t1, t2):
    return (f"다음은 악취 민원 상담에서 '민원인'의 발화 두 가지입니다. "
            f"어느 쪽이 더 자연스러운 {region} 지역 방언입니까? "
            f"방언 특성(종결어미·어휘)이 더 잘 살아있는 쪽을 고르세요.\n\n"
            f"[발화 1]\n{t1}\n\n[발화 2]\n{t2}\n\n"
            f"'1' 또는 '2'로만 답하세요. 다른 말은 하지 마세요.")


def pick(model, region, a, b, rng):
    """a=원본, b=교란. 순서 무작위. 반환: 원본을 골랐으면 1, 교란이면 0, 파싱실패 None."""
    swap = rng.random() < 0.5
    t1, t2 = (b, a) if swap else (a, b)
    r = run.call_anthropic(model, prompt_pair(region, t1, t2), 10, 60.0)
    if not r.get("ok"):
        return None
    m = re.search(r"[12]", r.get("text", ""))
    if not m:
        return None
    chose = m.group()
    orig_pos = "2" if swap else "1"
    return 1 if chose == orig_pos else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    model = "claude-opus-4-8"
    nmax = 10**9
    for o in [a for a in sys.argv[1:] if a.startswith("--")]:
        if o.startswith("--model="):
            model = o.split("=", 1)[1]
        if o.startswith("--n="):
            nmax = int(o.split("=", 1)[1])
    if not args:
        print("사용: python judge_reliability.py results/llm_perturb_s1_*.jsonl")
        sys.exit(1)
    run.load_env()
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("[중단] ANTHROPIC_API_KEY 없음")
        sys.exit(1)

    rows = [json.loads(l) for l in open(args[0], encoding="utf-8")]
    rows = [r for r in rows
            if not str(r.get("standardized", "")).startswith("[ERR")
            and not str(r.get("crossregion", "")).startswith("[ERR")][:nmax]
    print(f"[judge 신뢰성] 모델={model} 항목={len(rows)}\n")

    rng = random.Random(SEED)
    tasks = []
    for r in rows:
        region = r.get("region", "?")
        orig = cmpl(r.get("original", ""))
        std = cmpl(r.get("standardized", ""))
        cross = cmpl(r.get("crossregion", ""))
        tasks.append(("표준어화", region, orig, std, random.Random(rng.random())))
        tasks.append(("타권역화", region, orig, cross, random.Random(rng.random())))

    res = {"표준어화": [], "타권역화": []}
    def work(t):
        kind, region, a, b, r_ = t
        return kind, pick(model, region, a, b, r_)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(work, t) for t in tasks]
        for i, f in enumerate(as_completed(futs), 1):
            kind, v = f.result()
            if v is not None:
                res[kind].append(v)
            print(f"  진행 {i}/{len(tasks)}", end="\r")
    print()

    print("\n=== judge 정답률 (원본을 더 자연스러운 방언으로 고른 비율) ===")
    for kind in ("표준어화", "타권역화"):
        v = res[kind]
        acc = sum(v) / len(v) if v else 0.0
        print(f"  원본 vs {kind}: {acc:.1%}  (n={len(v)})")
    allv = res["표준어화"] + res["타권역화"]
    print(f"  전체: {sum(allv)/len(allv):.1%}  (n={len(allv)})")
    print("\n해석: 두 정답률 모두 높으면(≈80%+) judge가 방언을 분별함 = 조건 비교에 사용 가능.")
    print("      낮으면 judge 폐기.")


if __name__ == "__main__":
    main()
