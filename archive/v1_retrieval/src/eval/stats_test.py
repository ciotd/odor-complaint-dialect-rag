# -*- coding: utf-8 -*-
"""조건 간 방언율 차이의 통계 검정 (부트스트랩, scipy 불필요).

- 조건별 방언율 평균 + 95% 부트스트랩 CI (시나리오 재표집).
- 시나리오 짝지은(paired) 차이 검정: 같은 시나리오의 (조건A, 조건B) 방언율 차를
  부트스트랩해 평균차 CI와 양측 p값 근사. CI가 0을 포함하지 않으면 유의.

시나리오를 재표집 단위로 삼아(권역·시드 고정) 조건 효과만 비교한다.

사용:
  python src/eval/stats_test.py results/s1_*.jsonl [results/s2_*.jsonl]
"""
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_conditions import (  # noqa: E402
    load_markers, complainant_turns, words_of, score_surface,
    aligned_pairs, score_pairs, is_s1,
)

CONDITIONS = ["c0", "c1", "c_kb", "c_kb_c1"]
PAIRS = [("c0", "c_kb"), ("c0", "c1"), ("c_kb", "c1"),
         ("c1", "c_kb_c1"), ("c_kb", "c_kb_c1")]
B = 10000
SEED = 20260811


def dialect_rate_rows(path, tbl):
    """파일 → {cond: np.array(시나리오별 방언율)}. 시나리오 순서로 정렬."""
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    per = {c: [] for c in CONDITIONS}
    for r in rows:
        region = r.get("region", "?")
        s1 = is_s1(r)
        texts = r.get("generated") if s1 else r.get("converted")
        texts = texts or {}
        std = r.get("standard_dialogue", "")
        for c in CONDITIONS:
            if c not in texts:
                per[c].append(np.nan)
                continue
            if s1:
                sc = score_surface(words_of(complainant_turns(texts[c])), region, tbl)
            else:
                sc = score_pairs(aligned_pairs(std, texts[c]), region, tbl)
            tot = max(sc["total_words"], 1)
            per[c].append(sc["plus"] / tot)
    return {c: np.array(v, float) for c, v in per.items()}, len(rows)


def boot_ci(x, rng, b=B):
    """평균의 95% 부트스트랩 CI (nan 제외)."""
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        return 0.0, 0.0, 0.0
    means = x[rng.integers(0, n, size=(b, n))].mean(axis=1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def paired_test(a, b_, rng, b=B):
    """짝지은 차(a-b)의 평균차·95% CI·양측 p 근사. 둘 다 유효한 시나리오만."""
    m = ~(np.isnan(a) | np.isnan(b_))
    d = a[m] - b_[m]
    n = len(d)
    if n == 0:
        return 0.0, 0.0, 0.0, 1.0, 0
    idx = rng.integers(0, n, size=(b, n))
    bmeans = d[idx].mean(axis=1)
    lo, hi = np.percentile(bmeans, [2.5, 97.5])
    # 양측 p 근사: 0을 넘는 비율의 2배
    p = 2 * min((bmeans <= 0).mean(), (bmeans >= 0).mean())
    return float(d.mean()), float(lo), float(hi), float(min(p, 1.0)), n


def analyze(path, tbl):
    rng = np.random.default_rng(SEED)
    per, n = dialect_rate_rows(path, tbl)
    name = os.path.basename(path)
    pl = "S1" if "s1_" in name else "S2"
    print(f"\n{'='*60}\n[{pl}] {name}  (시나리오 {n}개)\n{'='*60}")

    print(f"{'조건':<9}{'방언율':>9}{'95% CI':>20}")
    print("-" * 40)
    for c in CONDITIONS:
        mean, lo, hi = boot_ci(per[c], rng)
        print(f"{c:<9}{mean:>9.4f}   [{lo:.4f}, {hi:.4f}]")

    print(f"\n{'비교(A−B)':<16}{'평균차':>9}{'95% CI':>20}{'p':>8}{'유의':>5}")
    print("-" * 60)
    for a, b_ in PAIRS:
        md, lo, hi, p, nn = paired_test(per[a], per[b_], rng)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(f"{a+'−'+b_:<16}{md:>+9.4f}   [{lo:+.4f}, {hi:+.4f}]{p:>8.3f}{sig:>5}")


def main():
    files = [f for f in sys.argv[1:] if os.path.exists(f)]
    if not files:
        print("사용: python stats_test.py results/s1_*.jsonl [results/s2_*.jsonl]")
        sys.exit(1)
    tbl = load_markers()
    for f in files:
        analyze(f, tbl)
    print("\n* CI가 0을 포함하지 않으면 유의. p<0.05(*), <0.01(**), <0.001(***), ns=비유의.")


if __name__ == "__main__":
    main()
