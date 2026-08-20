# -*- coding: utf-8 -*-
"""어휘 방언율 통계 검정 + 육안검증.

vocab_dialect_rate.py의 조건별 어휘 방언율에 대해 시나리오 짝지은 부트스트랩
검정(c_kb vs c1, c_kb vs c0)을 수행하고, 실제 적중 어휘를 표본 출력한다.

사용: python src/eval/vocab_stats.py results/s1_*.jsonl results/s2_*.jsonl
"""
import sys, os, json
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)
sys.path.insert(0, _HERE)

from eval_conditions import complainant_turns, words_of  # noqa: E402
from vocab_dialect_rate import build_ref, word_hits  # noqa: E402
from stats_test import boot_ci, paired_test  # noqa: E402
from src.retrieval.kb_retriever import KBRetriever  # noqa: E402

CONDS = ["c0", "c1", "c_kb", "c_kb_c1"]
PAIRS = [("c_kb", "c0"), ("c_kb", "c1"), ("c_kb_c1", "c1")]
SEED = 20260612


def scenario_rates(path, ref):
    """파일 → {cond: np.array(시나리오별 어휘방언율)} + 적중표본."""
    per = {c: [] for c in CONDS}
    samples = []  # (region, cond, [적중형])
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        region = r.get("region", "?")
        forms = ref.get(region, set())
        gen = r.get("generated") or r.get("converted") or {}
        for c in CONDS:
            if c not in gen:
                per[c].append(np.nan)
                continue
            turns = complainant_turns(gen[c])
            words = words_of(turns)
            hit_forms = sorted(word_hits(forms, turns))
            tot = max(len(words), 1)
            per[c].append(len(hit_forms) / tot)
            if c == "c_kb" and hit_forms:
                samples.append((region, r.get("scenario_id"), hit_forms))
    return {c: np.array(v, float) for c, v in per.items()}, samples


def main():
    files = [f for f in sys.argv[1:] if os.path.exists(f)]
    if not files:
        print("사용: python vocab_stats.py results/s1_*.jsonl results/s2_*.jsonl")
        sys.exit(1)
    print("KB 색인 중...")
    ref = build_ref(KBRetriever())
    rng = np.random.default_rng(SEED)

    for path in files:
        name = os.path.basename(path)
        pl = "S1" if name.startswith("s1_") else "S2"
        per, samples = scenario_rates(path, ref)
        print(f"\n{'='*58}\n[{pl}] {name}  어휘 방언율\n{'='*58}")
        print(f"{'조건':<9}{'어휘방언율':>10}{'95% CI':>22}")
        print("-" * 42)
        for c in CONDS:
            m, lo, hi = boot_ci(per[c], rng)
            print(f"{c:<9}{m:>10.4f}   [{lo:.4f}, {hi:.4f}]")
        print(f"\n{'비교(A−B)':<16}{'평균차':>9}{'95% CI':>21}{'p':>8}{'유의':>5}")
        print("-" * 60)
        for a, b in PAIRS:
            md, lo, hi, p, nn = paired_test(per[a], per[b], rng)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            print(f"{a+'−'+b:<16}{md:>+9.4f}   [{lo:+.4f}, {hi:+.4f}]{p:>8.3f}{sig:>5}")

        # 육안검증: c_kb 적중 어휘 표본
        print(f"\n[육안검증] {pl} c_kb 적중 어휘 표본(앞 10 시나리오):")
        for region, sid, forms in samples[:10]:
            print(f"  s{sid} {region}: {', '.join(forms[:12])}")


if __name__ == "__main__":
    main()
