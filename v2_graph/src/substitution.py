# -*- coding: utf-8 -*-
"""v2-graph 치환(flat substitution) 레이어 로더.

조건부 KG(종결어미·음운)와 달리, 치환은 '표준형→방언형 직접매핑'(조건 없음).
소스는 v1 자원(data/dialect_kb, 라이선스상 gitignore)을 **복사하지 않고 런타임 참조**.
- 어휘: vocab_clean.jsonl 경상 (head→dialect)  [11,304]
- 문법 flat: grammar_rules.jsonl 경상 category '문법론' (조사·선어말·부정·활용·인용)

get_substitutions(sentence): 문장에 등장하는 표준형 → 방언형 후보 반환(치환 주입용).
"""
import json, os
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
VOCAB = os.path.join(REPO, "data", "dialect_kb", "vocab_clean.jsonl")
GRAM = os.path.join(REPO, "data", "dialect_kb", "grammar_rules.jsonl")

kiwi = Kiwi()
_CONTENT = {"NNG", "NNP", "MAG"}          # 명사·부사: 표면형 매칭
_PRED = {"VV", "VA"}                       # 용언: 어간+다 lemma 매칭


def load_lexicon(region="경상"):
    idx = {}
    for l in open(VOCAB, encoding="utf-8"):
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("region") != region:
            continue
        h, d = r.get("head"), r.get("dialect")
        if h and d:
            idx.setdefault(h, [])
            if d not in idx[h]:
                idx[h].append(d)
    return idx


def load_grammar_flat(region="경상"):
    FLAT = {"문법론"}
    out = []
    for l in open(GRAM, encoding="utf-8"):
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("region") != region or r.get("category") not in FLAT:
            continue
        out.append({"표준": r.get("standard_form"), "방언": r.get("dialect_form"),
                    "유형": r.get("category")})
    return out


def get_substitutions(sentence, lex):
    """문장의 내용어 중 어휘사전에 있는 표준형 → 방언형 후보."""
    hits = []
    seen = set()
    for t in kiwi.tokenize(sentence):
        if t.tag in _CONTENT:
            key = t.form
        elif t.tag in _PRED:
            key = t.form + "다"           # 용언 어간 → 사전형
        else:
            continue
        if key in lex and key not in seen:
            hits.append({"유형": "어휘", "표준": key, "방언": lex[key]})
            seen.add(key)
    return hits


def _demo():
    lex = load_lexicon()
    gram = load_grammar_flat()
    print(f"어휘 사전: {len(lex)}표제어 | 문법flat: {len(gram)}개")
    print("문법flat 샘플:", [g["표준"][:20] + "→" + str(g["방언"])[:15] for g in gram[:4]])
    for s in ["오늘 며느리가 부엌에서 밥을 하더라", "할머니가 가랑이가 아프다고 하네",
              "그 사람이 액자를 가꾸고 있다"]:
        print(f"\n입력: {s}")
        for h in get_substitutions(s, lex):
            print(f"   치환 {h['표준']} → {h['방언']}")


if __name__ == "__main__":
    _demo()
