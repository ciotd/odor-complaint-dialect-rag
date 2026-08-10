# -*- coding: utf-8 -*-
"""
조건별 방언성 자동 평가 (B stage) — S1/S2 JSONL 공통 지원.

S1: generated 필드(직접 생성). 표준 참조 없이 표면 접미 매칭으로 채점.
S2: converted 필드(방언 변환). standard_dialogue 정렬쌍 사용(더 정확).

출력:
  - 시나리오별 방언성 점수 (방언 마커 적중, 누수, 총 어절 수)
  - 조건×권역 집계표
  - 조건 랭킹 요약

사용:
  python src/eval/eval_conditions.py results/s1_YYYYMMDD_HHMMSS.jsonl
  python src/eval/eval_conditions.py results/s2_YYYYMMDD_HHMMSS.jsonl
  python src/eval/eval_conditions.py results/s1_*.jsonl results/s2_*.jsonl
"""
import sys, os, json, csv, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCORING = os.path.join(ROOT, "docs", "dialect_markers_scoring.csv")

CONDITIONS = ["c0", "c1", "c_kb", "c_kb_c1"]


# ── 마커 테이블 로드 ──────────────────────────────────────────
def load_markers():
    """방언꼬리 → 소속 권역 집합 매핑 (채점포함=Y만).
    접미 매칭용: {방언꼬리: {권역, ...}}"""
    tbl = collections.defaultdict(set)  # 방언꼬리 → 권역 집합
    # 표준어와 표면형이 겹쳐 오탐을 유발하는 마커 제외 (재현성 위해 코드에 고정)
    #   어서: 표준 연결어미(작아서 등)와 동일 → 전라 마커지만 오탐 과다
    #   가지고: 표준어(가지고)와 동일 → 경상 마커지만 오탐 과다
    BLOCK = {"어서", "가지고"}
    for r in csv.DictReader(open(SCORING, encoding="utf-8-sig")):
        if r["채점포함_존댓말"] != "Y":
            continue
        if r["방언꼬리"].strip() in BLOCK:
            continue
        # 권역별 빈도에서 주도 권역 계산
        rf = {}
        for tok in r["권역별빈도"].split(";"):
            if ":" in tok:
                reg, c = tok.split(":")
                rf[reg] = int(c)
        mx = max(rf.values()) if rf else 0
        regs = {reg for reg, c in rf.items() if c >= 0.3 * mx}
        if not regs:
            regs = {r["주권역"]}
        tail = r["방언꼬리"].strip()
        if tail:
            tbl[tail] |= regs

    # 수동 보완 — 코퍼스에서 변별력 확인됐으나 1자라 자동 필터에서 제외된 마커
    # 충청: 요→유(빈도54), 어요→슈(빈도13) — 존댓말 핵심 마커
    # 강원: 면→믄(빈도783) — 강원 최빈 문법 표지
    # 전라 핵심 어미: 정렬쌍 추출이 놓친 대표 방언 종결형 (코퍼스에서 다수 확인)
    #   당께(요)/랑께(요): "-단 말이야" 계열, 표준 대응 불명확해 자동 추출 실패
    #   여라/겄소: 서남 방언 대표 존댓말 종결형 / 부러: "-어 버리다" 축약
    MANUAL = {
        "유": {"충청"},
        "슈": {"충청"},
        "믄": {"강원"},
        "예": {"경상"},   # 요→예 (빈도236, 경상 존댓말 핵심)
        "당께": {"전라"}, "당께요": {"전라"},
        "랑께": {"전라"}, "랑께요": {"전라"},
        "여라": {"전라"}, "겄소": {"전라"}, "부러": {"전라"},
    }
    for tail, regs in MANUAL.items():
        tbl[tail] |= regs

    return dict(tbl)


# ── 텍스트 처리 유틸 ─────────────────────────────────────────
def complainant_turns(dialogue: str) -> list:
    """대화 텍스트에서 '민원인:' 발화만 추출."""
    turns, cur = [], None
    for line in str(dialogue).splitlines():
        s = line.strip()
        if s.startswith("민원인:"):
            cur = "민"
            turns.append(s.split(":", 1)[1].strip())
        elif s.startswith("상담원:"):
            cur = "상"
        elif cur == "민" and s and turns:
            turns[-1] += " " + s
    return turns


_STRIP = re.compile(r'[ .,?!~"\'()·…\-]+')

def words_of(turns: list) -> list:
    """발화 리스트에서 어절(공백 단위) 추출·정규화."""
    out = []
    for t in turns:
        for w in t.split():
            w = _STRIP.sub("", w)
            if w:
                out.append(w)
    return out


# ── S1 채점: 표면 접미 매칭 ──────────────────────────────────
def score_surface(words: list, region: str, marker_tbl: dict) -> dict:
    """어절이 방언꼬리로 끝나는지 검사.
    타깃권역 꼬리 → plus, 타권역 꼬리 → minus."""
    plus = minus = 0
    hits = []
    # 1자 마커 중 수동 화이트리스트 (조사 오탐 위험 낮고 변별력 높은 것만)
    # 충청: 유(요→유), 슈(어요→슈) / 강원: 믄(면→믄)
    WHITELIST_1 = {"유", "슈", "믄", "예"}

    def _no_jongseong(ch: str) -> bool:
        """한글 음절이 받침(종성) 없이 끝나는지 확인."""
        c = ord(ch)
        return 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28 == 0

    # 긴 꼬리 우선 매칭 (greedy)
    # - 2자 이상: 전체 사용
    # - 1자: 화이트리스트만, 오탐 방지로 단어 길이 3자 이상 요구
    #   + 앞 음절이 받침 없어야 함 (한자 복합명사 오탐 차단: 윤활유, 보건소 등)
    tails = sorted(
        (t for t in marker_tbl if len(t) >= 2 or t in WHITELIST_1),
        key=len, reverse=True
    )
    for w in words:
        matched = False
        for tail in tails:
            min_word_len = len(tail) + 2 if len(tail) == 1 else len(tail) + 1
            pre_ok = (len(tail) >= 2 or
                      len(w) < len(tail) + 1 or
                      _no_jongseong(w[-(len(tail) + 1)]))
            if w.endswith(tail) and len(w) >= min_word_len and pre_ok:
                regs = marker_tbl[tail]
                if region in regs:
                    plus += 1
                    hits.append((w, tail, "+"))
                else:
                    minus += 1
                    hits.append((w, tail, "-"))
                matched = True
                break
    return {"plus": plus, "minus": minus, "total_words": len(words), "hits": hits}


# ── S2 채점: 정렬 어절쌍 기반 ────────────────────────────────
import difflib

def _norm(w):
    return _STRIP.sub("", w)

def aligned_pairs(std_dlg: str, dia_dlg: str) -> list:
    """표준↔방언 민원인 턴을 diff로 정렬해 변환 어절쌍만 추출."""
    st = complainant_turns(std_dlg)
    di = complainant_turns(dia_dlg)
    pairs = []
    for s, d in zip(st, di):
        sw = [w for w in (_norm(x) for x in s.split()) if w]
        dw = [w for w in (_norm(x) for x in d.split()) if w]
        sm = difflib.SequenceMatcher(None, sw, dw, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "replace":
                for a, b in zip(sw[i1:i2], dw[j1:j2]):
                    pairs.append((a, b))
    return pairs

def _gram_tail(std: str, dia: str):
    """어절쌍에서 공통 어간 이후 (표준꼬리, 방언꼬리) 추출. 불일치면 None."""
    if not std or not dia or std == dia:
        return None
    i = 0
    while i < len(std) and i < len(dia) and std[i] == dia[i]:
        i += 1
    if i == 0:
        return None
    return (std[i:], dia[i:])

def score_pairs(pairs: list, region: str, marker_tbl: dict) -> dict:
    """정렬 어절쌍 기반 채점."""
    plus = minus = 0
    hits = []
    tails_set = set(marker_tbl.keys())
    for std, dia in pairs:
        t = _gram_tail(std, dia)
        if not t:
            continue
        std_tail, dia_tail = t
        regs = marker_tbl.get(dia_tail)
        if regs:
            if region in regs:
                plus += 1
                hits.append((f"{std_tail}→{dia_tail}", "+"))
            else:
                minus += 1
                hits.append((f"{std_tail}→{dia_tail}", "-"))
    return {"plus": plus, "minus": minus, "total_words": len(pairs), "hits": hits}


# ── 파일 타입 판별 ────────────────────────────────────────────
def is_s1(row: dict) -> bool:
    return "generated" in row and "converted" not in row


# ── 메인 ─────────────────────────────────────────────────────
def main():
    marker_tbl = load_markers()
    print(f"방언 마커 {len(marker_tbl)}개 로드.\n")

    files = [f for f in sys.argv[1:] if os.path.exists(f)]
    if not files:
        print("사용: python eval_conditions.py results/s1_*.jsonl")
        sys.exit(1)

    rows = []
    for f in files:
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            r["_source"] = os.path.basename(f)
            rows.append(r)
    print(f"총 {len(rows)}개 시나리오 채점\n")

    # 집계: {(region, cond): Counter}
    agg = collections.defaultdict(lambda: collections.Counter())
    detail_rows = []

    print(f"{'파일':<30} {'sc':>3} {'권역':<4} {'조건':<8} {'마커+':>6} {'누수-':>6} {'어절':>6}  예시")
    print("-" * 90)

    for r in rows:
        region = r.get("region", "?")
        sid = r.get("scenario_id", "?")
        src = r.get("_source", "")
        pipeline = "s1" if is_s1(r) else "s2"

        if pipeline == "s1":
            cond_texts = r.get("generated", {})
            for cond in CONDITIONS:
                if cond not in cond_texts:
                    continue
                text = cond_texts[cond]
                words = words_of(complainant_turns(text))
                sc = score_surface(words, region, marker_tbl)
                ex = ", ".join(f"{w}({t})" for w, t, _ in sc["hits"][:3])
                print(f"{src:<30} {sid:>3} {region:<4} {cond:<8} "
                      f"{sc['plus']:>6} {sc['minus']:>6} {sc['total_words']:>6}  {ex}")
                agg[(region, cond)]["plus"] += sc["plus"]
                agg[(region, cond)]["minus"] += sc["minus"]
                agg[(region, cond)]["words"] += sc["total_words"]
                agg[(region, cond)]["n"] += 1
                detail_rows.append({
                    "source": src, "pipeline": pipeline,
                    "scenario_id": sid, "region": region, "condition": cond,
                    "plus": sc["plus"], "minus": sc["minus"],
                    "total_words": sc["total_words"],
                    "dialect_rate": round(sc["plus"] / max(sc["total_words"], 1), 4),
                    "leak_rate": round(sc["minus"] / max(sc["total_words"], 1), 4),
                })

        else:  # s2
            std_dlg = r.get("standard_dialogue", "")
            cond_texts = r.get("converted", {})
            for cond in CONDITIONS:
                if cond not in cond_texts:
                    continue
                pairs = aligned_pairs(std_dlg, cond_texts[cond])
                sc = score_pairs(pairs, region, marker_tbl)
                ex = ", ".join(f"{h}({s})" for h, s in sc["hits"][:3])
                print(f"{src:<30} {sid:>3} {region:<4} {cond:<8} "
                      f"{sc['plus']:>6} {sc['minus']:>6} {sc['total_words']:>6}  {ex}")
                agg[(region, cond)]["plus"] += sc["plus"]
                agg[(region, cond)]["minus"] += sc["minus"]
                agg[(region, cond)]["words"] += sc["total_words"]
                agg[(region, cond)]["n"] += 1
                detail_rows.append({
                    "source": src, "pipeline": pipeline,
                    "scenario_id": sid, "region": region, "condition": cond,
                    "plus": sc["plus"], "minus": sc["minus"],
                    "total_words": sc["total_words"],
                    "dialect_rate": round(sc["plus"] / max(sc["total_words"], 1), 4),
                    "leak_rate": round(sc["minus"] / max(sc["total_words"], 1), 4),
                })

    # 조건×권역 집계
    print("\n" + "=" * 70)
    print("=== 조건 × 권역 집계 (방언율 = 마커+ / 총어절) ===")
    print(f"{'권역':<5} {'조건':<8} {'마커+/대화':>10} {'방언율':>8} {'누수율':>8} {'n':>4}")
    print("-" * 50)
    for (region, cond), c in sorted(agg.items()):
        n = c["n"]
        dr = c["plus"] / max(c["words"], 1)
        lr = c["minus"] / max(c["words"], 1)
        print(f"{region:<5} {cond:<8} {c['plus']/n:>10.2f} {dr:>8.4f} {lr:>8.4f} {n:>4}")

    # 조건별 전체 랭킹
    print("\n=== 조건별 전체 방언율 랭킹 ===")
    cond_agg = collections.defaultdict(lambda: collections.Counter())
    for (region, cond), c in agg.items():
        cond_agg[cond]["plus"] += c["plus"]
        cond_agg[cond]["words"] += c["words"]
        cond_agg[cond]["minus"] += c["minus"]
    ranking = sorted(cond_agg.items(), key=lambda x: x[1]["plus"] / max(x[1]["words"], 1), reverse=True)
    for i, (cond, c) in enumerate(ranking, 1):
        dr = c["plus"] / max(c["words"], 1)
        lr = c["minus"] / max(c["words"], 1)
        print(f"  {i}위 {cond:<8}  방언율={dr:.4f}  누수율={lr:.4f}")

    # CSV 저장
    out_csv = os.path.join(ROOT, "results", "eval_conditions.csv")
    if detail_rows:
        with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=detail_rows[0].keys())
            w.writeheader()
            w.writerows(detail_rows)
        print(f"\n[저장] {out_csv}")


if __name__ == "__main__":
    main()
