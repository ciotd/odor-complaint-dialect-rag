# -*- coding: utf-8 -*-
"""
채점용 방언성 표지 손목록 생성 (근거 우선순위: 코퍼스 최우선, 우리말샘 최후 보조).

입력: docs/dialect_markers_v2.csv (코퍼스 v2 백본)  +  docs/dialect_markers.csv (v1, 우리말샘 보조)
선별(존댓말 악취 민원 채점용):
  - 변별력 = 변별(권역) 또는 일부공유  (광역공유=저변별 제외)
  - 레지스터 ∈ {존대, 중립}            (반말은 기록하되 채점 제외)
  - 총빈도 >= THRESHOLD                (노이즈 꼬리 제거)
출력: docs/dialect_markers_scoring.csv  (주권역을 +표지로; − 누수는 채점 코드가 자동계산)
재현: python src/eval/build_scoring_markers.py
"""
import csv, os, collections
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
# v3(1인+2인발화 통합)이 있으면 우선 사용, 없으면 v2(2인발화)
_V3=os.path.join(ROOT,"docs","dialect_markers_v3.csv")
V2=_V3 if os.path.exists(_V3) else os.path.join(ROOT,"docs","dialect_markers_v2.csv")
V1=os.path.join(ROOT,"docs","dialect_markers.csv")
OUT=os.path.join(ROOT,"docs","dialect_markers_scoring.csv")
THRESHOLD=8

# 우리말샘 [출처있음] 보조 인덱스 (최후 대조용)
umal={}
if os.path.exists(V1):
    for r in csv.DictReader(open(V1,encoding="utf-8-sig")):
        if r.get("tier")=="[출처있음]":
            m=r.get("marker","").lstrip("~").strip()
            if m: umal[m]=r.get("source","")[:60]
def umal_hit(dcol):
    return dcol if dcol in umal else ""   # 정확일치만 (당께↔께 오매칭 방지)

def register_std(std):
    """레지스터를 '표준 꼬리' 기준으로 판정 (방언 꼬리 모양이 아니라)."""
    if std.endswith(("요","죠")) or "습니" in std or "세요" in std or "십시오" in std:
        return "존대"
    if std.endswith(("서","면","니까","까","고","데","면서","다가","려","려고","지만","든","는데","면은","니깐","면서")):
        return "중립"   # 연결어미·조사
    return "반말"

import re as _re
_NONHAN=_re.compile(r"[^가-힣]")          # 구두점·공백·숫자 포함 = 정렬/전사 노이즈
# 명백한 노이즈(원본 대조로 확인): 더거=말더듬 아티팩트, 새그럽다=어휘(음운변이)
NOISE_BLOCK={"더거","새그러워서","새그라워서","새구라워서"}

rows=list(csv.DictReader(open(V2,encoding="utf-8-sig")))
sel=[]; i=0
for r in rows:
    if int(r["총빈도"])<THRESHOLD: continue
    if r["변별력"]=="광역공유": continue
    if not r["방언꼬리"].strip() or not r["표준꼬리"].strip(): continue   # 빈 이형태(아티팩트) 제거
    if _NONHAN.search(r["방언꼬리"]) or r["방언꼬리"] in NOISE_BLOCK: continue   # 노이즈 제거
    reg=register_std(r["표준꼬리"])          # 표준 꼬리 기준 레지스터
    include = "Y" if reg in ("존대","중립") else "N"   # 반말=기록만
    i+=1
    sel.append({
        "id":f"M{i:03d}", "표지족":f"{r['주권역']}/{r['표준꼬리']}",
        "주권역":r["주권역"], "방언꼬리":r["방언꼬리"], "표준꼬리":r["표준꼬리"],
        "레지스터":reg, "채점포함_존댓말":include,
        "변별력":r["변별력"], "주권역비율":r["주권역비율"], "총빈도":r["총빈도"],
        "권역별빈도":r["권역별빈도"], "예시":r["예시"],
        "근거방식":"코퍼스(1차)", "우리말샘보조":umal_hit(r["방언꼬리"]), "검토필요":"Y",
    })
cols=["id","표지족","주권역","방언꼬리","표준꼬리","레지스터","채점포함_존댓말","변별력","주권역비율",
      "총빈도","권역별빈도","예시","근거방식","우리말샘보조","검토필요"]
with open(OUT,"w",encoding="utf-8-sig",newline="") as fo:
    w=csv.DictWriter(fo,fieldnames=cols); w.writeheader(); w.writerows(sel)

from collections import Counter
inc=[s for s in sel if s["채점포함_존댓말"]=="Y"]
print(f"임계 빈도 {THRESHOLD} · 변별/일부공유 · 존대+중립 → 채점포함 {len(inc)}개 (기록 총 {len(sel)})")
print("채점포함 권역 분포:", dict(Counter(s['주권역'] for s in inc)))
print(f"저장: {os.path.relpath(OUT,ROOT)}\n")
for R in ["경상","강원","충청","전라","제주"]:
    sub=[s for s in inc if s["주권역"]==R]
    fams=collections.defaultdict(list)
    for s in sub: fams[(s["표준꼬리"],s["레지스터"])].append(s)
    print(f"■ {R} ({len(fams)}개 표지족 / {len(sub)}개 이형태)")
    for (std,reg),g in sorted(fams.items(), key=lambda kv:-sum(int(x['총빈도']) for x in kv[1])):
        variants="/".join(dict.fromkeys(x["방언꼬리"] for x in g))
        tot=sum(int(x["총빈도"]) for x in g)
        u=[x["우리말샘보조"] for x in g if x["우리말샘보조"]]
        us=f" [우리말샘:{','.join(u)}]" if u else ""
        print(f"    {std}→[{variants}]  ({reg}) 총{tot}{us}")
