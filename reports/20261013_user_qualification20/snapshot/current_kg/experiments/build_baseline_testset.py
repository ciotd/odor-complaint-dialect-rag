"""AI-Hub 경상도 2인발화에서 baseline 진단용 표준어-방언 문장쌍 100개를 구성한다.

원본 zip은 저장소 밖(~/dialect_corpus/aihub)에 있으며 읽기만 한다.
산출물은 AI-Hub 파생물이므로 Git 추적 대상이 아니다. 이 스크립트로 재현한다.

용법: python3 current_kg/experiments/build_baseline_testset.py
"""
import json, zipfile, random, difflib, argparse
from pathlib import Path

ZIP = Path.home() / "dialect_corpus/aihub/VL_02. 경상도_03. 2인발화.zip"
OUT = Path(__file__).resolve().parent / "inputs/baseline_testset_100.jsonl"
GAP = 0.8          # 문장 경계로 볼 무음 간격(초)
MIN_EOJEOL, MAX_EOJEOL = 5, 25
MIN_DIST = 0.1     # 정규화 Levenshtein 하한 (박근형 외 2026의 방언 표본 기준)
N = 100
SEED = 20260915


def t2s(x):
    h, m, s = x.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def lev(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def sentences(segs):
    """무음 간격으로 세그먼트(어절)를 문장으로 묶는다."""
    cur, prev_end = [], None
    for s in segs:
        a, b = t2s(s["startTime"]), t2s(s["endTime"])
        if prev_end is not None and a - prev_end > GAP:
            if cur:
                yield cur
            cur = []
        cur.append(s)
        prev_end = b
    if cur:
        yield cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default=str(ZIP))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--n", type=int, default=N)
    args = ap.parse_args()

    cands = []
    with zipfile.ZipFile(args.zip) as z:
        for name in z.namelist():
            if not name.endswith(".json"):
                continue
            d = json.loads(z.read(name))
            for group in sentences(d["transcription"]["segments"]):
                toks = [s for s in group if (s.get("dialect") or "").strip()]
                if not (MIN_EOJEOL <= len(toks) <= MAX_EOJEOL):
                    continue
                n_dia = sum(1 for s in toks if s.get("standard"))
                if n_dia == 0:
                    continue
                dia = " ".join(s["dialect"].strip() for s in toks)
                std = " ".join((s.get("standard") or s["dialect"]).strip() for s in toks)
                dist = lev(std, dia) / max(len(std), len(dia))
                if dist < MIN_DIST:
                    continue
                cands.append(dict(
                    source_file=Path(name).name,
                    표준=std, 방언_ref=dia,
                    어절수=len(toks), 방언어절수=n_dia,
                    유사도=round(difflib.SequenceMatcher(None, std, dia).ratio(), 4),
                    거리=round(dist, 4),
                ))

    # 방언 어절 수로 층화 추출
    random.seed(SEED)
    strata = {"1": [], "2": [], "3": [], "4+": []}
    for c in cands:
        strata[str(c["방언어절수"]) if c["방언어절수"] <= 3 else "4+"].append(c)
    per = args.n // len(strata)
    picked = []
    for k in ("1", "2", "3", "4+"):
        pool = strata[k]
        picked += random.sample(pool, min(per, len(pool)))
    rest = [c for c in cands if c not in picked]
    picked += random.sample(rest, args.n - len(picked))
    random.shuffle(picked)

    with open(args.out, "w") as f:
        for i, c in enumerate(picked, 1):
            f.write(json.dumps(dict(id=f"T{i:03d}", **c), ensure_ascii=False) + "\n")

    print(f"후보 {len(cands):,}개 → 선정 {len(picked)}개")
    print("층별 후보 수:", {k: len(v) for k, v in strata.items()})
    print("저장:", args.out)


if __name__ == "__main__":
    main()
