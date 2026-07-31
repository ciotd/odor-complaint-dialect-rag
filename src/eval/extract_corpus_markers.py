# -*- coding: utf-8 -*-
"""
방언성 표지 손목록 v2 백본 — 코퍼스 주도 추출 (재현 스크립트)

입력: AI-Hub '중·노년 한국어 방언 데이터 (2인발화)' 라벨링 zip (권역별),
      경로 = ../dialect_corpus/aihub/*2인발화.zip  (외부 데이터, gitignore)
방법: 각 발화 segment의 (dialect, standard) 쌍에서, 표준형을 형태소 분석(kiwipiepy)해
      어미·조사(E*/J*) 경계를 찾고, 변화가 그 문법 꼬리에서 일어난 것만 '문법 표지'로 추출.
      어간/음운·어휘 변화는 제외(별도 어휘 축).
집계: (표준꼬리→방언꼬리) 변환을 5권역 교차 집계 → 점유율 기반 변별력 + 레지스터 추정.
출력: docs/dialect_markers_v2.csv

주의: 표지는 [코퍼스] 근거의 '후보'다. 레지스터/보유 여부 최종 판단은 사람 검토(검토필요=Y).
      2인발화 연령: 경상·강원=고령(65·69), 충청·전라·제주=중년(≈49) — 연령경향 열 참고.
재현: python src/eval/extract_corpus_markers.py
"""
import zipfile, json, glob, re, collections, csv, os
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ZDIR = os.path.abspath(os.path.join(ROOT, "..", "dialect_corpus", "aihub"))
OUT  = os.path.join(ROOT, "docs", "dialect_markers_v2.csv")
REGIONS = ["경상", "강원", "충청", "전라", "제주"]
AGE = {"경상": "고령(69)", "강원": "고령(65)", "충청": "중년(49)", "전라": "중년(49)", "제주": "중년(49)"}

kiwi = Kiwi()
_c = {}
def gram_tail_start(std):
    """표준 어절에서 어미(E*)·조사(J*)가 시작되는 문자 오프셋 = 마지막 내용형태소의 끝."""
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
    return "?"

# 레지스터 추정 (방언 꼬리 형태 기반; 최종은 사람 검토)
_POL  = re.compile(r'(예|유|슈|라예|십니다|읍니다|마씀|수다|수과|우꽈|애요|라$)')
_CONN = re.compile(r'(가$|가꼬$|가주고$|가지고$|갖고$|믄|먼|므$|문$|만$|모$|머$|디$|께|난$|응께|이께|엉$|멍$|당$|젠$|은$|네$)')
def register(dcol):
    if _POL.search(dcol):  return "존대"
    if _CONN.search(dcol): return "중립"   # 연결어미·조사
    return "반말"

def extract_region(zip_path):
    zf = zipfile.ZipFile(zip_path)
    gram = collections.Counter(); ex = {}
    for n in zf.namelist():
        if not n.endswith(".json"): continue
        d = json.loads(zf.read(n).decode("utf-8"))
        for seg in d.get("transcription", {}).get("segments", []):
            sd = (seg.get("standard") or "").strip(); di = (seg.get("dialect") or "").strip()
            if not sd or not di or sd == di: continue
            k = lcp(sd, di); g = gram_tail_start(sd)
            if g < len(sd) and k >= g:               # 어간 보존 + 문법 꼬리 변화
                key = (sd[k:], di[k:]); gram[key] += 1; ex.setdefault(key, (sd, di))
    return gram, ex

def discrim(rf):
    tot = sum(rf.values()); top = max(rf, key=rf.get); share = rf[top] / tot
    if share >= 0.6:      lab = f"변별({top})"        # 점유율 기반(꼬리 잡음 무시)
    elif len(rf) >= 3:    lab = "광역공유"
    else:                 lab = "일부공유"
    return top, round(share, 2), len(rf), lab, tot

def main():
    freq = collections.defaultdict(dict); ex_all = {}
    for z in glob.glob(os.path.join(ZDIR, "*2인발화*.zip")):
        r = region_of(z)
        if r == "?": continue
        gram, ex = extract_region(z)
        for key, c in gram.items():
            freq[key][r] = c; ex_all.setdefault(key, ex[key])
        print(f"  {r}: 문법표지 토큰 {sum(gram.values()):,} (고유 {len(gram)})")

    rows = []
    for key, rf in freq.items():
        sd, dcol = key; top, share, nreg, lab, tot = discrim(rf)
        rows.append({
            "표준꼬리": sd, "방언꼬리": dcol, "총빈도": tot, "주권역": top, "주권역비율": share,
            "출현권역수": nreg, "변별력": lab, "레지스터추정": register(dcol),
            "연령경향": AGE.get(top, "?"),
            "권역별빈도": ";".join(f"{r}:{rf[r]}" for r in REGIONS if r in rf),
            "예시": f"{ex_all[key][0]}→{ex_all[key][1]}",
            "근거방식": "코퍼스(AIHub 2인발화)", "검토필요": "Y",
        })
    rows.sort(key=lambda x: -x["총빈도"])
    cols = ["표준꼬리","방언꼬리","총빈도","주권역","주권역비율","출현권역수","변별력",
            "레지스터추정","연령경향","권역별빈도","예시","근거방식","검토필요"]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"\nv2 백본 저장: {os.path.relpath(OUT, ROOT)} ({len(rows)}개 표지쌍)")

if __name__ == "__main__":
    main()
