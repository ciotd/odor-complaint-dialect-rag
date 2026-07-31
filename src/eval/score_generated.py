# -*- coding: utf-8 -*-
"""
step3: 생성물(S2 × C0/C_kb)에 B 방언성 채점기 적용 → 핵심 RQ 측정.

입력: results/s2_*.jsonl (scenario_id, region, standard_dialogue, converted{c0,c_kb})
방법: 민원인 턴만 추출 → 표준↔방언 어절 위치정렬 → B(①코퍼스 손목록) 채점.
      +표지=타깃권역 방언 어미, −누수=타권역 어미. 조건별(C0 vs C_kb) 비교.
재현: python src/eval/score_generated.py results/s2_YYYYMMDD_HHMMSS.jsonl
"""
import sys, os, json, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_dialectness import load_markers, transform

def complainant_turns(dialogue):
    """대화 텍스트에서 '민원인:' 발화만 순서대로 추출."""
    turns=[]; cur=None
    for line in str(dialogue).splitlines():
        s=line.strip()
        if s.startswith("민원인:"): cur="민"; turns.append(s.split(":",1)[1].strip())
        elif s.startswith("상담원:"): cur="상"
        elif cur=="민" and s and turns: turns[-1]+=" "+s
    return turns

import difflib
def _norm(w):
    return w.strip(" .,?!~\"'()·…").strip()
def pairs_from(std_dlg, dia_dlg):
    """표준·방언 대화의 민원인 턴을 diff 정렬해 (표준어절, 방언어절) 쌍 생성.
    같은 어절은 앵커로 고정하고 '바뀐 블록'만 1:1로 짝지어 밀림을 방지."""
    st, di = complainant_turns(std_dlg), complainant_turns(dia_dlg)
    pairs=[]
    for s,d in zip(st,di):
        sw=[w for w in (_norm(x) for x in s.split()) if w]
        dw=[w for w in (_norm(x) for x in d.split()) if w]
        sm=difflib.SequenceMatcher(None, sw, dw, autojunk=False)
        for tag,i1,i2,j1,j2 in sm.get_opcodes():
            if tag=="replace":                     # 바뀐 구간만 짝지음(equal/insert/delete 제외)
                for a,b in zip(sw[i1:i2], dw[j1:j2]):
                    pairs.append((a,b))
    return pairs

def load_lex():
    """어휘 축: 방언 단어 → 소속 권역 집합 (vocab_clean.jsonl). 단형(오탐) 제외."""
    p=os.path.join(os.path.dirname(__file__),"..","..","data","dialect_kb","vocab_clean.jsonl")
    idx=collections.defaultdict(set)
    if os.path.exists(p):
        for line in open(p,encoding="utf-8"):
            d=json.loads(line); w=(d.get("dialect") or "").strip()
            if len(w)>=2: idx[w].add(d.get("region"))
    return idx
def lex_regions(dia, lex):
    """방언 어절에서 조사/어미 꼬리를 최대 2자 떼며 사전 방언단어 매칭."""
    for w in (dia, dia[:-1], dia[:-2]):
        if len(w)>=2 and w in lex: return lex[w]
    return set()

def score_pairs(pairs, region, tbl, lex):
    """문법(어미) 축 + 어휘(단어) 축을 분리 채점."""
    g_plus=g_minus=l_plus=l_minus=0; found=[]
    for std,dia in pairs:
        t=transform(std,dia)
        if t:                                   # 어간 보존 + 꼬리 변화 = 문법 축
            regs=tbl.get(t)
            if regs:
                if region in regs: g_plus+=1; found.append((f"{t[0]}→{t[1]}","문법+"))
                else: g_minus+=1
            continue
        r2=lex_regions(dia, lex)                 # 어간 바뀜 = 어휘 축
        if r2:
            if region in r2: l_plus+=1; found.append((dia,"어휘+"))
            else: l_minus+=1
    return dict(g_plus=g_plus,g_minus=g_minus,l_plus=l_plus,l_minus=l_minus), found

def main():
    tbl=load_markers(); lex=load_lex()
    print(f"손목록 {len(tbl)}쌍 · 어휘사전 {len(lex)}단어 로드.")
    files=[f for f in sys.argv[1:] if os.path.exists(f)]
    rows=[]
    for f in files: rows += [json.loads(l) for l in open(f,encoding="utf-8")]
    print(f"채점: {', '.join(os.path.basename(x) for x in files)} (n={len(rows)})\n")
    agg=collections.defaultdict(lambda: collections.Counter())
    print(f"{'sc':>2} {'권역':<4} {'조건':<5} {'문법+':>5} {'어휘+':>5} {'누수−':>5}  예")
    for r in rows:
        R=r.get("region"); conv=r.get("converted",{})
        for cond in ("c0","c_kb"):
            if cond not in conv: continue
            s,found=score_pairs(pairs_from(r.get("standard_dialogue",""), conv[cond]), R, tbl, lex)
            for k in s: agg[(R,cond)][k]+=s[k]
            agg[(R,cond)]["n"]+=1
            ex=", ".join(f"{a}({b})" for a,b in found[:3])
            print(f"{r.get('scenario_id'):>2} {R:<4} {cond:<5} {s['g_plus']:>5} {s['l_plus']:>5} {s['g_minus']+s['l_minus']:>5}  {ex}")
    print("\n=== 조건별 집계 (권역×조건, 대화당 평균) ===")
    print(f"{'권역':<4} {'조건':<5} {'문법+':>7} {'어휘+':>7} {'합계+':>7} {'누수−':>7}")
    for (R,cond),c in sorted(agg.items()):
        n=c["n"]; g=c['g_plus']/n; l=c['l_plus']/n; m=(c['g_minus']+c['l_minus'])/n
        print(f"{R:<4} {cond:<5} {g:>7.1f} {l:>7.1f} {g+l:>7.1f} {m:>7.1f}")
    print("\n핵심 비교: C_kb의 (문법+ / 어휘+)가 C0보다 높으면 RAG가 각 축 방언성을 올린다는 증거.")
    print("RQ2: 문법 축 vs 어휘 축 중 어디서 C_kb 이득이 큰가.")

if __name__=="__main__":
    main()
