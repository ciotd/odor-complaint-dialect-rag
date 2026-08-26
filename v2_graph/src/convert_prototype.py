# -*- coding: utf-8 -*-
"""v2-graph (b) 변환 프로토타입: 표준 발화 → 경북 방언 (종결어미 중심).

파이프라인:
  ① 자질 추출 (kiwi): 종결어미 형태 · 서술어 품사(용언/계사) · 의문사 유무
     + 표준어미→(종결법,높임) 매핑표(STD_ENDING; KG 표준형 + 표준문법 유래, 프로토타입 starter)
  ② KG 조회 (kg_rules.jsonl): (종결법·높임·의문종류·결합환경) 일치 규칙 → 방언 어미
  ③ (naive) 어미 교체

주의: 프로토타입. STD_ENDING은 시범 커버(확장 필요). 표면 재구성은 naive(형태음운 미처리).
"""
import json, os, re
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
KB = os.path.join(HERE, "..", "data", "kg_rules.jsonl")

kiwi = Kiwi()

# 표준어미(kiwi form) → (종결법, 높임).  KG 표준형 역색인 + 표준문법 starter.
# 높임 정렬: 표준 하십시오체→하이소체, 해요체→해요체, 해라체→해라체.
STD_ENDING = {
    "습니다": ("서술", "하이소체"), "ㅂ니다": ("서술", "하이소체"),
    "습니까": ("의문", "하이소체"), "ㅂ니까": ("의문", "하이소체"),
    "니": ("의문", "해라체"), "냐": ("의문", "해라체"), "느냐": ("의문", "해라체"),
    "다": ("서술", "해라체"), "ㄴ다": ("서술", "해라체"), "는다": ("서술", "해라체"),
    "라": ("명령", "해라체"), "아라": ("명령", "해라체"), "어라": ("명령", "해라체"), "거라": ("명령", "해라체"),
    "자": ("청유", "해라체"),
    "ㅂ시다": ("청유", "하이소체"), "읍시다": ("청유", "하이소체"),
    "어요": ("서술", "해요체"), "아요": ("서술", "해요체"), "요": ("서술", "해요체"),
}
_UITAG = ["뭐", "무엇", "무슨", "누구", "누가", "어디", "왜", "언제", "어떻게", "어느", "어떤", "몇"]


def load_kb():
    return [json.loads(l) for l in open(KB, encoding="utf-8") if l.strip()]


def extract(sent):
    """자질 추출: (종결법, 높임, 의문종류, 결합환경, 표준어미)."""
    toks = kiwi.tokenize(sent)
    # 종결어미 후보: 뒤에서부터 EF/EC 중 STD_ENDING에 있는 형태
    ending = None
    for t in reversed(toks):
        if t.tag in ("EF", "EC") and t.form in STD_ENDING:
            ending = t.form
            break
    if ending is None:
        return None
    j_type, honor = STD_ENDING[ending]
    # 문장부호로 서술/의문 보정(해요체 등 억양의존)
    if "?" in sent and j_type == "서술":
        j_type = "의문"
    # 의문종류: 의문사 유무
    ui = any(w in sent for w in _UITAG)
    q_kind = None
    if j_type == "의문":
        q_kind = "설명" if ui else "판정"
    # 결합환경: 서술어가 계사(VCP)냐 용언(VV/VA)이냐
    comb = None
    if any(t.tag == "VCP" for t in toks):
        comb = "계사"
    elif any(t.tag in ("VV", "VA") for t in toks):
        comb = "용언"
    return dict(종결법=j_type, 높임=honor, 의문종류=q_kind, 결합환경=comb, 표준어미=ending)


def lookup(kb, f):
    """자질 → 방언 어미(규칙 매칭). 방언형 우선."""
    cand = [r for r in kb if r["conditions"]["종결법"] == f["종결법"]
            and r["conditions"]["높임"] == f["높임"]]
    if f["종결법"] == "의문":
        # 의문종류: 정확 일치 우선, 없으면 미구분
        exact = [r for r in cand if r["conditions"].get("의문종류") == f["의문종류"]]
        if f["결합환경"]:
            e2 = [r for r in exact if r["conditions"].get("결합환경") == f["결합환경"]]
            if e2:
                exact = e2
        cand = exact or [r for r in cand if r["conditions"].get("의문종류") == "미구분"] or cand
    out = []
    for r in cand:
        dia = [e["form"] for e in r["어미"] if e["유형"] == "방언"]
        out.append((r["id"], dia))
    return out


def main():
    kb = load_kb()
    tests = ["밥 먹었니?", "뭐 먹었니?", "이 사람이 주인이니?",
             "밥 먹었습니다", "빨리 가라", "우리 같이 가자", "어디 가십니까?"]
    for s in tests:
        print("=" * 60)
        print("입력:", s)
        f = extract(s)
        if not f:
            print("  [표준어미 미인식 — STD_ENDING 확장 필요]")
            continue
        print("  자질:", {k: v for k, v in f.items() if v is not None})
        res = lookup(kb, f)
        if not res:
            print("  [매칭 규칙 없음]")
            continue
        for rid, dia in res:
            print(f"  → {rid}: 방언어미 {dia}")


if __name__ == "__main__":
    main()
