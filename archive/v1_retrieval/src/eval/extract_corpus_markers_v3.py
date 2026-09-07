# -*- coding: utf-8 -*-
"""방언성 표지 v3 — 5권역 1인발화 + 2인발화 통합 추출 (재현 스크립트)

v2(2인발화만) 대비 개선: 강원처럼 2인발화가 약한 권역을 위해 1인발화도 통합.
- 2인발화: transcription.segments의 (standard,dialect) 세그먼트쌍(주석자 정렬, 깨끗).
- 1인발화: transcription.standard/dialect 문장쌍 → 어절 수 같을 때만 위치정렬
           (difflib 오정렬 노이즈 차단), 숫자 포함 어절 제외(119='일일구' 오탐 방지).
공통: 표준 어절을 kiwi로 형태소 분석해 어미·조사(E*/J*) 경계 이후 변화만 '문법 표지'로.
집계: (표준꼬리→방언꼬리) 5권역 교차 → 변별력. 출력: docs/dialect_markers_v3.csv

입력(외부, gitignore):
  ../dialect_corpus/aihub/*2인발화*.zip   (5권역)
  ~/139-1.*(강원,경상).zip  ~/139-2.*(충청,전라,제주).zip  (1인발화 중첩 zip)
재현: python src/eval/extract_corpus_markers_v3.py
"""
import zipfile, io, json, glob, re, collections, csv, os
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ZDIR = os.path.abspath(os.path.join(ROOT, "..", "dialect_corpus", "aihub"))
HOME = os.path.expanduser("~")
OUT  = os.path.join(ROOT, "docs", "dialect_markers_v3.csv")
REGIONS = ["경상", "강원", "충청", "전라", "제주"]
AGE = {"경상": "고령(69)", "강원": "고령(65)", "충청": "중년(49)", "전라": "중년(49)", "제주": "중년(49)"}
ONE_ZIPS = [os.path.join(HOME, "139-1.중·노년층 한국어 방언 데이터 (강원도, 경상도).zip"),
            os.path.join(HOME, "139-2.중·노년층 한국어 방언 데이터 (충청도, 전라도, 제주도).zip")]

kiwi = Kiwi(); _c = {}
_DIGIT = re.compile(r"[0-9]")

def gts(std):
    if std in _c: return _c[std]
    try: toks = kiwi.tokenize(std)
    except Exception: _c[std] = len(std); return len(std)
    end = 0
    for t in toks:
        if t.tag[0] not in ("E", "J"): end = max(end, t.start + t.len)
    _c[std] = end; return end

def lcp(a, b):
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]: i += 1
    return i

def region_of(name):
    for r in REGIONS:
        if r in name: return r
    return None

def add_pair(gram, ex, s, dd):
    """어절쌍 (표준 s, 방언 dd) → 문법꼬리 변화 추출."""
    if s == dd or _DIGIT.search(s) or _DIGIT.search(dd): return
    k = lcp(s, dd); g = gts(s)
    if g < len(s) and k >= g:                 # 어간 보존 + 문법꼬리 변화
        key = (s[k:], dd[k:]); gram[key] += 1; ex.setdefault(key, (s, dd))

def extract_2in(zip_path, gram, ex):
    zf = zipfile.ZipFile(zip_path)
    for n in zf.namelist():
        if not n.endswith(".json"): continue
        d = json.loads(zf.read(n).decode("utf-8"))
        for seg in d.get("transcription", {}).get("segments", []):
            sd = (seg.get("standard") or "").strip(); di = (seg.get("dialect") or "").strip()
            if not sd or not di or sd == di: continue
            sw, dw = sd.split(), di.split()
            if len(sw) != len(dw): continue      # 세그먼트도 위치정렬만(안전)
            for s, dd in zip(sw, dw): add_pair(gram, ex, s, dd)

def extract_1in(outer_zip, region, gram, ex):
    """중첩 zip에서 특정 권역 1인발화 문장쌍 → 위치정렬 추출."""
    outer = zipfile.ZipFile(outer_zip)
    # ⚠️ region 매칭은 내부 zip 파일명(basename)으로만 — 상위 폴더명이 "강원도, 경상도"라
    #    전체 경로로 매칭하면 권역 교차 오염됨.
    inners = [n for n in outer.namelist()
              if region in os.path.basename(n) and "1인발화" in n and "VL_" in n and n.endswith(".zip")]
    for tgt in inners:
        inner = zipfile.ZipFile(io.BytesIO(outer.read(tgt)))
        for jn in inner.namelist():
            if not jn.endswith(".json"): continue
            tr = json.loads(inner.read(jn)).get("transcription", {})
            sd = (tr.get("standard") or "").strip(); di = (tr.get("dialect") or "").strip()
            if not sd or not di or sd == di: continue
            sw, dw = sd.split(), di.split()
            if len(sw) != len(dw): continue      # 문장 위치정렬만(difflib 노이즈 차단)
            for s, dd in zip(sw, dw): add_pair(gram, ex, s, dd)

def discrim(rf):
    tot = sum(rf.values()); top = max(rf, key=rf.get); share = rf[top] / tot
    if share >= 0.6: lab = f"변별({top})"
    elif len(rf) >= 3: lab = "광역공유"
    else: lab = "일부공유"
    return top, round(share, 2), len(rf), lab, tot

_POL  = re.compile(r'(예|유|슈|라예|십니다|읍니다|마씀|수다|수과|우꽈|애요|시래요|이래요|라$)')
_CONN = re.compile(r'(가$|가꼬$|가주고$|믄|먼|므$|문$|만$|모$|머$|디$|께|난$|응께|엉$|멍$|당$|젠$|은$|네$|버텅$)')
def register(dcol):
    if _POL.search(dcol):  return "존대"
    if _CONN.search(dcol): return "중립"
    return "반말"

def main():
    per = {r: (collections.Counter(), {}) for r in REGIONS}
    # 2인발화
    for z in glob.glob(os.path.join(ZDIR, "*2인발화*.zip")):
        r = region_of(z)
        if not r: continue
        gram, ex = per[r]; extract_2in(z, gram, ex)
        print(f"  [2인] {r}: 누적 표지토큰 {sum(gram.values()):,}")
    # 1인발화
    for oz in ONE_ZIPS:
        if not os.path.isfile(oz): continue
        for r in REGIONS:
            if r not in per: continue
            gram, ex = per[r]; before = sum(gram.values())
            extract_1in(oz, r, gram, ex)
            after = sum(gram.values())
            if after > before: print(f"  [1인] {r}: +{after-before:,} (누적 {after:,})")

    # 교차 집계
    freq = collections.defaultdict(dict); ex_all = {}
    for r in REGIONS:
        gram, ex = per[r]
        for key, c in gram.items():
            freq[key][r] = c; ex_all.setdefault(key, ex[key])

    rows = []
    for key, rf in freq.items():
        sd, dcol = key; top, share, nreg, lab, tot = discrim(rf)
        rows.append({
            "표준꼬리": sd, "방언꼬리": dcol, "총빈도": tot, "주권역": top, "주권역비율": share,
            "출현권역수": nreg, "변별력": lab, "레지스터추정": register(dcol),
            "연령경향": AGE.get(top, "?"),
            "권역별빈도": ";".join(f"{r}:{rf[r]}" for r in REGIONS if r in rf),
            "예시": f"{ex_all[key][0]}→{ex_all[key][1]}",
            "근거방식": "코퍼스(AIHub 1인+2인발화)", "검토필요": "Y",
        })
    rows.sort(key=lambda x: -x["총빈도"])
    cols = ["표준꼬리","방언꼬리","총빈도","주권역","주권역비율","출현권역수","변별력",
            "레지스터추정","연령경향","권역별빈도","예시","근거방식","검토필요"]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"\nv3 저장: {os.path.relpath(OUT, ROOT)} ({len(rows)}개 표지쌍)")

if __name__ == "__main__":
    main()
