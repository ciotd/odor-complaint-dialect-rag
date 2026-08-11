# -*- coding: utf-8 -*-
"""A단계 — 합성 교란으로 B 지표(방언율/누수율)의 민감도 검증.

인간 라벨 없이, 정상 생성문에 '알려진 오류'를 통제 주입해 B 지표가 그 오염을
탐지하는지 측정한다. 지표가 방언성 변화에 반응하면 민감도가 높다.

교란 2종 (정상문의 타깃권역 방언 어미(+적중)에만 적용):
  (A) 표준어 역치환 : 방언 어미 → 표준 어미  (방언 제거)  → 방언율 하락 기대
  (B) 타권역 어미 교체: 방언 어미 → 타권역 어미            → 방언율 하락 + 누수율 상승 기대

민감도:
  Sensitivity = (D(정상) - D(교란)) / D(정상)     (방언율 D, 대화별 D(정상)>0만)

사용:
  python src/eval/perturb_sensitivity.py results/s1_YYYYMMDD_HHMMSS.jsonl [조건]
  (조건 기본값 c_kb_c1 — 방언이 충분히 실현된 조건에서 검증)
"""
import sys, os, csv, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_conditions import (  # noqa: E402
    load_markers, complainant_turns, words_of, score_surface, SCORING,
)

WHITELIST_1 = {"유", "슈", "믄", "예"}

# 수동 보완 마커의 표준형(역치환용) — CSV에 없으므로 여기서 지정
MANUAL_STD = {
    "유": "요", "슈": "어요", "믄": "면", "예": "요",
    "당께요": "어요", "당께": "어", "랑께요": "어요", "랑께": "어",
    "여라": "어요", "겄소": "겠어요", "부러": "버려",
}


def load_std_map():
    """방언꼬리 → 표준꼬리 매핑 (역치환용)."""
    std = {}
    for r in csv.DictReader(open(SCORING, encoding="utf-8-sig")):
        if r["채점포함_존댓말"] != "Y":
            continue
        d, s = r["방언꼬리"].strip(), r["표준꼬리"].strip()
        if d:
            std[d] = s
    std.update(MANUAL_STD)  # 수동 마커 우선
    return std


def _no_jongseong(ch: str) -> bool:
    c = ord(ch)
    return 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28 == 0


def target_tails(region: str, tbl: dict) -> list:
    """해당 권역의 매칭 가능한 방언꼬리(긴 것 우선)."""
    return sorted(
        (t for t, regs in tbl.items()
         if region in regs and (len(t) >= 2 or t in WHITELIST_1)),
        key=len, reverse=True,
    )


def match_tail(word: str, tails: list) -> str | None:
    """단어가 끝나는 타깃 방언꼬리(score_surface와 동일 규칙)."""
    for t in tails:
        min_len = len(t) + 2 if len(t) == 1 else len(t) + 1
        pre_ok = (len(t) >= 2 or len(word) < len(t) + 1
                  or _no_jongseong(word[-(len(t) + 1)]))
        if word.endswith(t) and len(word) >= min_len and pre_ok:
            return t
    return None


def foreign_tail_for(region: str) -> str:
    """타권역 어미 교체용 — 타깃과 다른 권역의 대표 2자 어미(안정적 매칭)."""
    # 전라 '랑께요'를 기본 침입자로, 타깃이 전라면 경상 '가주고' 사용
    return "가주고" if region == "전라" else "랑께요"


def perturb_words(words: list, region: str, tbl: dict, std_map: dict):
    """정상 어절 → (표준화, 타권역치환) 어절 리스트 생성."""
    tails = target_tails(region, tbl)
    foreign = foreign_tail_for(region)
    w_std, w_swap = [], []
    for w in words:
        t = match_tail(w, tails)
        if t is None:                      # 방언 어미 아님 → 그대로
            w_std.append(w)
            w_swap.append(w)
        else:
            stem = w[: len(w) - len(t)]
            w_std.append(stem + std_map.get(t, ""))   # 표준화
            w_swap.append(stem + foreign)              # 타권역 침입
    return w_std, w_swap


def rate(sc: dict) -> tuple:
    """(방언율, 누수율)."""
    tot = max(sc["total_words"], 1)
    return sc["plus"] / tot, sc["minus"] / tot


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print("사용: python perturb_sensitivity.py results/s1_*.jsonl [조건]")
        sys.exit(1)
    path = args[0]
    cond = args[1] if len(args) > 1 else "c_kb_c1"

    tbl = load_markers()
    std_map = load_std_map()
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]

    # 대화별 방언율(정상/표준화/타권역치환)
    agg = collections.Counter()
    n_eval = 0
    sens_std, sens_swap, leak_rise = [], [], []
    print(f"[A단계] 소스={os.path.basename(path)} 조건={cond}")
    print(f"{'권역':<5}{'D정상':>8}{'D표준화':>9}{'D타권역':>9}{'누수정상':>9}{'누수타권역':>10}")
    print("-" * 52)

    per_region = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        region = r.get("region", "?")
        text = (r.get("generated") or {}).get(cond, "")
        if not text:
            continue
        words = words_of(complainant_turns(text))
        sc0 = score_surface(words, region, tbl)
        d0, l0 = rate(sc0)
        if sc0["plus"] == 0:      # 정상문에 방언이 없으면 민감도 정의 불가 → 제외
            continue
        n_eval += 1
        w_std, w_swap = perturb_words(words, region, tbl, std_map)
        scA = score_surface(w_std, region, tbl)
        scB = score_surface(w_swap, region, tbl)
        dA, lA = rate(scA)
        dB, lB = rate(scB)
        sens_std.append((d0 - dA) / d0)
        sens_swap.append((d0 - dB) / d0)
        leak_rise.append(lB - l0)
        pr = per_region[region]
        pr["p0"] += sc0["plus"]; pr["pA"] += scA["plus"]; pr["pB"] += scB["plus"]
        pr["m0"] += sc0["minus"]; pr["mB"] += scB["minus"]; pr["w"] += sc0["total_words"]
        pr["n"] += 1

    for region, pr in sorted(per_region.items()):
        w = max(pr["w"], 1)
        print(f"{region:<5}{pr['p0']/w:>8.3f}{pr['pA']/w:>9.3f}{pr['pB']/w:>9.3f}"
              f"{pr['m0']/w:>9.3f}{pr['mB']/w:>10.3f}")

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    print("\n=== 민감도 요약 (대화별 평균, D정상>0인 %d개) ===" % n_eval)
    print(f"  표준어 역치환 민감도  : {mean(sens_std):.3f}  (1.0=방언율 완전 소거)")
    print(f"  타권역 교체 민감도    : {mean(sens_swap):.3f}  (방언율 하락 비율)")
    print(f"  타권역 교체 누수 상승 : +{mean(leak_rise):.4f}  (누수율 증가폭)")


if __name__ == "__main__":
    main()
