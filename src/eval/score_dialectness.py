# -*- coding: utf-8 -*-
"""
B. 방언성 채점기 (규칙기반) + 코퍼스 교차검증.

원리: (표준↔방언) 정렬 어절쌍에서 각 변환(표준꼬리→방언꼬리)이 어느 권역의 표지인지
      손목록(docs/dialect_markers_scoring.csv, 코퍼스 1차 근거)에 대조.
      타깃권역 R 표지 → +(방언성), 타권역 표지 → −(누수). 표면 문자열 매칭이 아니라
      '정렬된 변환'을 보므로 조사 '가' 같은 단형 오탐을 피한다(S2 파이프라인이 정렬 제공).

검증: 5권역 코퍼스(2인발화)를 각 권역 잣대로 채점 → 혼동행렬. 대각선(자기권역)이 지배하면
      지표가 방언 권역을 변별한다는 실증(경량 A). 사람 라벨 없이 성립.

재현: python src/eval/score_dialectness.py
"""
import csv, os, glob, json, zipfile, collections, re
from kiwipiepy import Kiwi
kiwi = Kiwi()
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,"..",".."))
SCORING=os.path.join(ROOT,"docs","dialect_markers_scoring.csv")
ZDIR=os.path.abspath(os.path.join(ROOT,"..","dialect_corpus","aihub"))
REGIONS=["경상","강원","충청","전라","제주"]
SAMPLE=150   # 권역당 표본 파일 수(검증용)

# ── 손목록 로드: (표준꼬리,방언꼬리) -> 표지 소속 권역 집합 ──
def load_markers():
    tbl={}
    for r in csv.DictReader(open(SCORING,encoding="utf-8-sig")):
        if r["채점포함_존댓말"]!="Y": continue
        rf={}
        for tok in r["권역별빈도"].split(";"):
            if ":" in tok:
                reg,c=tok.split(":"); rf[reg]=int(c)
        mx=max(rf.values()) if rf else 0
        regs={reg for reg,c in rf.items() if c>=0.3*mx}   # 잡음꼬리 제외, 공용 포함
        if not regs: regs={r["주권역"]}
        tbl[(r["표준꼬리"], r["방언꼬리"])]=regs
    return tbl

_c={}
def gram_tail_start(std):
    if std in _c: return _c[std]
    try: toks=kiwi.tokenize(std)
    except Exception: _c[std]=len(std); return len(std)
    end=0
    for t in toks:
        if t.tag[0] not in ("E","J"): end=max(end,t.start+t.len)
    _c[std]=end; return end
def transform(std,dia):
    """정렬 어절쌍 → (표준꼬리, 방언꼬리). 문법 꼬리 변화가 아니면 None."""
    if not std or not dia or std==dia: return None
    i=0
    while i<len(std) and i<len(dia) and std[i]==dia[i]: i+=1
    g=gram_tail_start(std)
    if g<len(std) and i>=g: return (std[i:], dia[i:])
    return None

def score(pairs, region, tbl):
    """pairs=[(표준어절,방언어절),...], region=타깃권역. return dict."""
    plus=minus=ndia=0
    for std,dia in pairs:
        t=transform(std,dia)
        if not t: continue
        ndia+=1
        regs=tbl.get(t)
        if not regs: continue
        if region in regs: plus+=1
        else: minus+=1
    return dict(plus=plus, minus=minus, ndia=ndia)

# ── 2차 잣대(②): RAG-KB(grammar_rules) 파생 어미·조사 표지 ──
KB=os.path.join(ROOT,"data","dialect_kb","grammar_rules.jsonl")
def load_kb_markers():
    """KB의 어미·조사 규칙에서 방언 어미 문자열을 권역별로 추출(음운·어휘 제외)."""
    tbl=collections.defaultdict(set)
    if not os.path.exists(KB): return tbl
    for line in open(KB,encoding="utf-8"):
        r=json.loads(line); cat=str(r.get("category",""))
        if "음운" in cat: continue                      # 음운·어휘 규칙 제외(어미/조사만)
        reg=r.get("region"); df=str(r.get("dialect_form") or "")
        for tok in re.split(r"[,\s/·]+", df):
            e=tok.strip(" -~()?!.")
            if len(e)>=2: tbl[reg].add(e)               # 단형(오탐) 제외
    return tbl

def score_kb(pairs, region, kb):
    """②: 방언 어절이 KB 방언어미로 끝나면 매칭(표면 접미). 정렬쌍 동일 분모."""
    plus=minus=0
    for std,dia in pairs:
        hit_self=any(w.endswith(e) for w in dia.split() for e in kb.get(region,()))
        hit_other=any(w.endswith(e) for w in dia.split()
                      for rr in REGIONS if rr!=region for e in kb.get(rr,()))
        if hit_self: plus+=1
        elif hit_other: minus+=1
    return dict(plus=plus, minus=minus)

# ── 코퍼스에서 권역별 정렬쌍 표본 로드 ──
def region_zip(r):
    for z in glob.glob(os.path.join(ZDIR,"*2인발화*.zip")):
        if r in os.path.basename(z): return z
    return None
def load_pairs(zip_path, sample):
    zf=zipfile.ZipFile(zip_path); js=[n for n in zf.namelist() if n.endswith(".json")][:sample]
    pairs=[]; nseg=0
    for n in js:
        d=json.loads(zf.read(n).decode("utf-8"))
        for seg in d.get("transcription",{}).get("segments",[]):
            nseg+=1
            sd=(seg.get("standard") or "").strip(); di=(seg.get("dialect") or "").strip()
            if sd and di and sd!=di: pairs.append((sd,di))
    return pairs, nseg

def main():
    tbl=load_markers()
    print(f"손목록 표지쌍 {len(tbl)}개 로드.\n")
    corpus={}
    for r in REGIONS:
        z=region_zip(r)
        if not z: continue
        corpus[r]=load_pairs(z, SAMPLE)
        print(f"  {r}: 표본 정렬쌍 {len(corpus[r][0]):,} (세그먼트 {corpus[r][1]:,})")
    kb=load_kb_markers()
    print(f"\n② KB 파생 잣대: " + ", ".join(f"{r}:{len(kb.get(r,()))}" for r in REGIONS) + " (제주=KB 부재)")

    def matrix(scorer, title):
        print(f"\n=== {title} (행=코퍼스 권역, 열=잣대, 값=+표지/1000세그먼트) ===")
        print("        " + "".join(f"{c:>8}" for c in REGIONS))
        diag=0
        for rrow in REGIONS:
            pairs,nseg=corpus[rrow]
            cells=[1000*scorer(pairs,rcol)["plus"]/max(nseg,1) for rcol in REGIONS]
            best=REGIONS[cells.index(max(cells))]
            ok = (best==rrow and max(cells)>0)
            diag+= 1 if ok else 0
            print(f"  {rrow:<5}"+"".join(f"{v:>8.1f}" for v in cells)+f"   대각최대? {'✓' if ok else f'✗(→{best})'}")
        print(f"  → 대각지배 {diag}/{len(REGIONS)}권역")
        return diag

    d1=matrix(lambda p,r: score(p,r,tbl), "① 코퍼스 손목록 잣대")
    d2=matrix(lambda p,r: score_kb(p,r,kb), "② RAG-KB 파생 잣대")
    print(f"\n=== 이중추정 요약 ===")
    print(f"  ① 코퍼스 대각지배 {d1}/5, ② KB 대각지배 {d2}/5.")
    print(f"  두 독립 잣대가 방언 권역 변별에 수렴하면 지표 신뢰↑. 불일치 권역(특히 경상=KB가 음운편중,")
    print(f"  제주=KB 부재)은 진단 신호 — 근거 보강 우선순위.")

if __name__=="__main__":
    main()
