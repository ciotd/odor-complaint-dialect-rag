# -*- coding: utf-8 -*-
"""규칙 DB(grammar_rules.jsonl) → 사람 전수 검수용 CSV.

294개 규모라 사람이 전수 검수 가능. 의심 항목을 자동 플래그해 검수 부담을 줄인다.
출력 CSV는 방언 파생 데이터라 .gitignore(data/dialect_kb/) — 스크립트만 커밋한다.

플래그 종류:
  malformed     : dialect_form 칸에 형태가 아니라 서술문이 든 필드 어긋남
                  (예: '동남방언은 성조방언...', '표준어 -와/-과에 대응...')
                  → LLM 구조화 실패분. 주입하면 해로움. 제거/수정 대상.
  templated_exp : explanation이 '...에 대응하는 ... 형태소 ... 입니다' 류 자동 템플릿
                  → 형태쌍은 맞지만 설명 정보량이 낮음. 보강 여지.
  question_only : standard_form이 의문형뿐 → 평서문 쿼리에 안 걸림(경상 편중 진단용).
  (빈칸)        : 특이사항 없어 보임(그래도 사람 확인 권장).
"""
import argparse
import csv
import json
import re
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
DEFAULT_IN = _REPO / "data" / "dialect_kb" / "grammar_rules.jsonl"
DEFAULT_OUT = _REPO / "data" / "dialect_kb" / "grammar_rules_review.csv"

# dialect_form 칸에 있으면 '형태'가 아니라 '설명'이라는 신호
_DESC_MARK = ["표준어", "대응", "출처", "사용합니다", "발음", "일반적", "방언은"]
_TEMPLATED = re.compile(r"대응하는.*형태소.*입니다")


def flag_rule(r):
    df = str(r.get("dialect_form", "")).strip()
    sf = str(r.get("standard_form", "")).strip()
    exp = str(r.get("explanation", "")).strip()
    if any(m in df for m in _DESC_MARK) or len(df) > 35:
        return "malformed"
    if _TEMPLATED.search(exp):
        return "templated_exp"
    if sf.endswith("?") and "?" in sf and "," not in sf:
        return "question_only"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DEFAULT_IN))
    ap.add_argument("--output", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.input, encoding="utf-8") if l.strip()]
    # 검수 편의: 권역 → category → 순서로 정렬
    rows.sort(key=lambda r: (r.get("region", ""), r.get("category", "")))

    cols = ["idx", "region", "category", "standard_form", "dialect_form",
            "explanation", "keywords", "flag", "검수의견(직접입력)"]
    stat = {}
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, r in enumerate(rows, 1):
            fl = flag_rule(r)
            stat[fl or "ok"] = stat.get(fl or "ok", 0) + 1
            w.writerow([
                i, r.get("region"), r.get("category"),
                r.get("standard_form"), r.get("dialect_form"),
                r.get("explanation"),
                " | ".join(r.get("keywords") or []),
                fl, "",
            ])

    print(f"입력: {args.input}")
    print(f"출력: {args.output}  (총 {len(rows)}행)")
    print("플래그 분포:")
    for k in ["ok", "malformed", "templated_exp", "question_only"]:
        if k in stat:
            print(f"  {k:14} {stat[k]}")


if __name__ == "__main__":
    main()
