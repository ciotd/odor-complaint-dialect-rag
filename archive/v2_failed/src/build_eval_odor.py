# -*- coding: utf-8 -*-
"""v1 표준 악취 민원 대화 → 민원인 발화 40개 추출 (v2 보조 테스트, 도메인 적용).

v1 S2 결과의 standard_dialogue(표준 대화)에서 민원인 발화를 시나리오마다 골고루 뽑음.
gold 방언 정답 없음(v1 방언은 결함 RAG) → judge 전용 테스트.

출력: archive/v2_failed/data/eval_odor.jsonl  {id, 표준, 도메인:"악취"}
      ※ v1 생성물 파생 → gitignore(스크립트 재현).
"""
import json, os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
V1_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "v1_retrieval"))
sys.path.insert(0, V1_ROOT)
sys.path.insert(0, os.path.join(V1_ROOT, "src", "eval"))
from eval_conditions import complainant_turns  # noqa: E402

SRC = os.path.join(V1_ROOT, "results", "s2_20260818_135335.jsonl")
OUT = os.path.join(HERE, "..", "data", "eval_odor.jsonl")

_GREET = re.compile(r"안녕하세요|신고하려고|전화(를)? (드|걸)")


def _near_dup(t, picked, thr=0.6):
    """이미 뽑힌 것과 단어 겹침(Jaccard)이 thr 이상이면 유사중복."""
    w = set(t.split())
    for p in picked:
        pw = set(p.split())
        if w and pw and len(w & pw) / len(w | pw) >= thr:
            return True
    return False


def main(target=40):
    recs = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
    picked, seen = [], set()
    for r in recs:
        turns = [t.strip() for t in complainant_turns(r.get("standard_dialogue", ""))]
        # 인사말 제외, 내용 있는 발화(길이 18~70) 중 첫 후보 1개 (정확·유사중복 제외)
        cand = [t for t in turns if 18 <= len(t) <= 70 and not _GREET.search(t)]
        for t in cand:
            if t not in seen and not _near_dup(t, picked):
                picked.append(t)
                seen.add(t)
                break                      # 시나리오당 1개
        if len(picked) >= target:
            break
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for i, t in enumerate(picked, 1):
            f.write(json.dumps({"id": f"O{i:03d}", "표준": t, "도메인": "악취"},
                               ensure_ascii=False) + "\n")
    print(f"저장: {OUT} ({len(picked)}발화, {len(recs)}시나리오 중)")
    for t in picked[:8]:
        print("  ", t)


if __name__ == "__main__":
    main()
