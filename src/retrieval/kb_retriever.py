# -*- coding: utf-8 -*-
"""방언 지식 베이스(C_kb) 검색기.

표준어 텍스트를 질의로 받아, 해당 권역의 방언 '지식'을 검색해 반환한다.
z/ 프로젝트(제주어 RAG)의 순수 파이썬 BM25·형태소 토크나이저를 이 리포로
복사(vendoring)했다. z는 동결 보존 대상이라 cross-import 하지 않는다.

z와의 차이 — 검색 대상이 '병렬 문장'이 아니라 '지식 항목'이다:
  - 어휘(lexicon): head(표준어 표제어) → dialect(방언형) 후보
  - 규칙(rules)  : standard_form(표준형) → dialect_form(방언형) + explanation

설계 원칙 (research_scope RQ2):
  어휘와 규칙은 자원 성격이 달라 검색 방식도 다르다:
    - 어휘: head(표제어) 정확매칭 = 사전 조회. 질의의 내용어(명사·용언)만 표제어형
      으로 복원해 dict에서 정확 일치시킨다. 조사·어미(기능어)는 배제 → 잡음 없음.
    - 규칙: 형태소 BM25(fuzzy). 어미·조사는 유연 매칭이 필요하므로.
  (초기엔 어휘도 BM25였으나 '너무→너물' 등 잡음이 커서 정확매칭으로 교체. 2026-07-27.)
  RQ2(어휘 vs 규칙) 해석 시 '두 자원의 검색 메커니즘도 다르다'는 점을 함께 명시한다.

검색 범위는 항상 '한 권역 내부'다(idf도 권역 내 계산). use_lex/use_rule 스위치가
C_kb-lex / C_kb-rule / C_kb-both 실험 조건에 그대로 대응한다.

쿼리는 S2(변환) 전략의 표준어 텍스트다. S1(직접 생성)은 쿼리가 없어 대조군이다.
"""
import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
KB_DIR = _REPO / "data" / "dialect_kb"

# ── 형태소 토크나이저 (z/ bm25_retriever.py에서 복사) ──────────────────────
_kiwi = None
# 문장부호·기호류 품사는 매칭에서 제외
_SYMBOL_TAGS = {"SF", "SP", "SS", "SSO", "SSC", "SE", "SO",
                "SW", "SB", "SH", "SL", "SN"}


def tokenize_morph(text):
    """형태소 단위 토큰화 (kiwipiepy). 기호류 품사 제외, 형태(form) 문자열 반환.
    규칙(문법) 검색용 — 어미·조사까지 포함해 BM25로 매칭한다."""
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    return [t.form for t in _kiwi.tokenize(str(text))
            if t.tag not in _SYMBOL_TAGS]


# 어휘 표제어 매칭용: 내용어(명사·동사·형용사)만. 조사·어미·부사는 배제
# (그건 규칙 DB가 담당). 용언은 어간을 표제어형(+다)으로 복원해 정확매칭.
_CONTENT_TAGS = {"NNG", "NNP", "VV", "VA"}


def content_keys(text):
    """질의에서 내용어를 뽑아 (표층형, [표제어 후보키]) 목록 반환.
    명사: [form], 용언: [form+'다', form]. → head 정확매칭에 사용."""
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    out = []
    for t in _kiwi.tokenize(str(text)):
        if t.tag in ("NNG", "NNP"):
            out.append((t.form, [t.form]))
        elif t.tag in ("VV", "VA"):
            out.append((t.form, [t.form + "다", t.form]))
    return out


# ── BM25 (z/에서 복사 + 역색인 최적화) ─────────────────────────────────────
class BM25:
    """순수 파이썬 BM25. 어휘 2만+ 규모를 위해 역색인(postings)으로 최적화.

    z 버전은 질의어마다 전체 문서를 순회(O(N))했으나, 여기선 term→[(doc,freq)]
    역색인을 미리 만들어 실제로 그 term을 가진 문서만 채점한다.
    """

    def __init__(self, corpus_tokens, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.N = len(corpus_tokens)
        self.doc_len = [len(d) for d in corpus_tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        # 역색인: term -> [(doc_i, freq), ...]
        self.postings = defaultdict(list)
        df = Counter()
        for i, d in enumerate(corpus_tokens):
            for term, f in Counter(d).items():
                self.postings[term].append((i, f))
                df[term] += 1
        self.idf = {
            term: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
            for term, n in df.items()
        }

    def top_k(self, query_tokens, k=5):
        scores = defaultdict(float)
        for term in set(query_tokens):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, f in self.postings[term]:
                denom = f + self.k1 * (
                    1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                scores[i] += idf * (f * (self.k1 + 1)) / denom
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(i, s) for i, s in ranked[:k] if s > 0]


# ── 색인 텍스트 정의 (무엇을 검색 대상으로 삼는가) ─────────────────────────
def _rule_text(r):
    """규칙 색인 텍스트: 표준형 + keywords(검색 훅). explanation은 길어서
    색인하면 매칭이 희석되므로 주입 페이로드로만 쓰고 색인엔 넣지 않는다."""
    return f"{r.get('standard_form', '')} {' '.join(r.get('keywords') or [])}"


class _Index:
    def __init__(self, records, text_fn):
        self.records = records
        self.bm25 = BM25([tokenize_morph(text_fn(r)) for r in records])

    def search(self, query_tokens, k):
        return [(self.records[i], s) for i, s in self.bm25.top_k(query_tokens, k)]


class KBRetriever:
    def __init__(self, kb_dir=KB_DIR):
        kb_dir = Path(kb_dir)
        vocab = _read_jsonl(kb_dir / "vocab_clean.jsonl")
        rules = _read_jsonl(kb_dir / "grammar_rules.jsonl")
        self.regions = sorted({r["region"] for r in vocab} |
                              {r["region"] for r in rules})
        # 권역별 분리 색인.
        #  어휘: head(표제어) → 항목들 정확매칭 인덱스 (BM25 아님, 사전 조회).
        #        head=None(뜻풀이만) 항목은 정확매칭 불가라 제외.
        #  규칙: 형태소 BM25 (어미·조사를 fuzzy 매칭해야 하므로).
        self.head_index, self.rule_idx = {}, {}
        for reg in self.regions:
            hidx = {}
            for r in vocab:
                if r["region"] != reg:
                    continue
                h = r.get("head")
                if h:
                    hidx.setdefault(h, []).append(r)
            self.head_index[reg] = hidx
            self.rule_idx[reg] = _Index(
                [r for r in rules if r["region"] == reg], _rule_text)

    def retrieve(self, query, region, use_lex=True, use_rule=True,
                 k_lex=5, k_rule=5):
        """표준어 query에 대해 region의 방언 지식을 검색.

        반환: {"lexicon": [...], "rules": [...]}  (스위치로 섹션 on/off)
        """
        if region not in self.regions:
            raise ValueError(f"미등록 권역: {region} (가능: {self.regions})")
        out = {"lexicon": [], "rules": []}
        if use_lex:
            out["lexicon"] = self._search_vocab(query, region, k_lex)
        if use_rule:
            out["rules"] = self._search_rules(tokenize_morph(query), region, k_rule)
        return out

    def _search_vocab(self, query, region, k):
        """어휘 검색 = 표제어 정확매칭(사전 조회). 질의의 내용어(명사·용언)를
        표제어형으로 복원해 head와 정확히 일치하는 것만 반환. 기능어(조사·어미·
        부사)는 매칭 대상이 아님(그건 규칙 DB 담당) → BM25식 잡음 없음."""
        idx = self.head_index[region]
        seen, out = set(), []
        for _surface, keys in content_keys(query):
            hit = next((kk for kk in keys if kk in idx), None)
            if not hit or hit in seen:
                continue
            seen.add(hit)
            entries = idx[hit]
            dialects = []
            for e in entries:
                if e["dialect"] not in dialects:
                    dialects.append(e["dialect"])
            out.append({"head": hit, "gloss": entries[0].get("gloss"),
                        "pos": entries[0].get("pos"),
                        "dialects": dialects[:5], "score": 1.0})
            if len(out) >= k:
                break
        return out

    def _search_rules(self, qtok, region, k):
        out = []
        for r, s in self.rule_idx[region].search(qtok, k):
            out.append({
                "category": r.get("category"),
                "standard_form": r.get("standard_form"),
                "dialect_form": r.get("dialect_form"),
                "explanation": r.get("explanation"),
                "score": round(s, 3),
            })
        return out


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ── 주입용 포맷 (프롬프트에 넣을 문자열) ───────────────────────────────────
def format_for_prompt(hits):
    """retrieve() 결과를 프롬프트 주입용 텍스트로."""
    lines = []
    if hits.get("lexicon"):
        lines.append("[방언 어휘]")
        for g in hits["lexicon"]:
            head = g["head"] or g["gloss"]
            lines.append(f"- '{head}' → {' / '.join(g['dialects'])}")
    if hits.get("rules"):
        lines.append("[방언 문법 규칙]")
        for r in hits["rules"]:
            lines.append(
                f"- {r['standard_form']} → {r['dialect_form']} "
                f"({r['explanation']})")
    return "\n".join(lines)


def _demo():
    ap = argparse.ArgumentParser(description="C_kb 검색기 데모(눈으로 확인)")
    ap.add_argument("--kb", default=str(KB_DIR))
    ap.add_argument("--region", default="경상")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("query", nargs="*",
                    help="표준어 질의(생략 시 기본 예시)")
    args = ap.parse_args()

    print("색인 중...")
    retr = KBRetriever(args.kb)
    print(f"권역: {retr.regions}\n")

    queries = args.query or [
        "쓰레기 냄새가 너무 심해서 창문을 못 열겠어요.",
        "그 공장에서 나는 악취 때문에 머리가 아파요.",
        "언제쯤 해결이 될까요?",
    ]
    for q in queries:
        print(f"■ [{args.region}] 질의: {q}")
        hits = retr.retrieve(q, args.region, k_lex=args.k, k_rule=args.k)
        print(format_for_prompt(hits) or "  (매칭 없음)")
        print()


if __name__ == "__main__":
    _demo()
