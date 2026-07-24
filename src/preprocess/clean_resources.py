# -*- coding: utf-8 -*-
"""방언 지식 리소스(RAG_resource) 정제 스크립트.

research_scope.md 5.3 기준. 입력은 리포 밖 RAG_resource/(네이버 사전·문법서 원자료),
출력은 리포 안 data/dialect_kb/(.gitignore — 라이선스상 커밋 금지).

어휘(vocab): standard를 head(표제어)+gloss(뜻풀이)로 파싱. 무변환/속담/중복 제거.
문법(grammar): examples 분리(검색소스 제외), 규칙만 추출. 강원 2파일 병합.

주의: 예문(examples)은 LLM 생성 인공물이라 검색소스에서 제외한다(research_scope 5.1).
      필요 시 평가 참조용으로 grammar_examples.jsonl에 따로 남긴다.
"""
import argparse
import json
import os
import re
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
DEFAULT_IN = os.path.abspath(os.path.join(_REPO, "..", "RAG_resource"))
DEFAULT_OUT = os.path.join(_REPO, "data", "dialect_kb")

# 4권역만 (제주 보류 — research_scope 4장)
VOCAB = {
    "강원": "강원도/어휘/gangwon_vocab.json",
    "경상": "경상도/어휘/gyeongsang_vocab.json",
    "전라": "전라도/어휘/jeonla_vocab.json",
    "충청": "충청도/어휘/chungcheong_vocab.json",
}
GRAMMAR = {
    "강원": ["강원도/문법/gangwon_grammar.json",
             "강원도/문법/naver_gangwon_grammar_final2.json"],
    "경상": ["경상도/문법/gyeongsang_grammar.json"],
    "전라": ["전라도/문법/jeonla_grammar.json"],
    "충청": ["충청도/문법/chungcheong_grammar.json"],
}

# 실사용 빈도가 낮아 제외하는 어미(현지인 확인, 2026-07-24): 전라 '-당께라우'
BANNED_FORMS = ["당께라우"]

# 규칙이 아니라 '문장 예문 쌍'인 category (LLM이 스스로 라벨링).
# standard_form/dialect_form이 통째로 문장이라 검색소스에 들어가면 사실상
# '미리 만든 few-shot 검색'이 되어 C1과 C_kb 구분이 무너진다(research_scope 5.1).
# 규칙셋에서 빼고 참조용 grammar_examples.jsonl로 보낸다. (2026-07-24, 경상 79건)
BANNED_CATEGORIES = {"예문대조규칙"}

# 문장/속담 판단: 종결어미
_SENT_TAIL = re.compile(r"(다|까|라|네|군|지|요|음|함)$")


def parse_standard(s):
    """standard 문자열 → (head, gloss). head가 None이면 표제어 불명(뜻풀이만)."""
    s = str(s).strip()
    m = re.match(r"^([^(]+?)\s*\((.+)\)\s*$", s)  # '표제어(뜻풀이)'
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # 괄호 없음: 여러 어절의 서술이거나 매우 길면 뜻풀이만으로 간주
    if s.count(" ") >= 2 or len(s) > 12:
        return None, s
    return s, None


def is_proverb(dialect):
    """방언형이 단어가 아니라 속담/문장인가."""
    d = str(dialect).strip()
    return d.count(" ") >= 2 and bool(_SENT_TAIL.search(d))


def clean_vocab(base):
    rows, stats = [], {}
    for reg, path in VOCAB.items():
        with open(os.path.join(base, path), encoding="utf-8") as f:
            data = json.load(f)
        seen = set()
        kept, drop_novar, drop_prov, drop_dup, drop_empty, no_head = 0, 0, 0, 0, 0, 0
        for x in data:
            std, dia = str(x.get("standard", "")).strip(), str(x.get("dialect", "")).strip()
            if not std or not dia:
                drop_empty += 1
                continue
            head, gloss = parse_standard(std)
            if is_proverb(dia):
                drop_prov += 1
                continue
            # 무변환: 표제어==방언형이고 뜻풀이도 없음 → 방언 정보 없음
            if head is not None and head == dia and not gloss:
                drop_novar += 1
                continue
            key = (head or gloss, dia)
            if key in seen:
                drop_dup += 1
                continue
            seen.add(key)
            if head is None:
                no_head += 1
            rows.append({
                "region": reg, "head": head, "gloss": gloss,
                "dialect": dia, "pos": x.get("pos"),
            })
            kept += 1
        stats[reg] = dict(input=len(data), kept=kept, drop_novar=drop_novar,
                          drop_proverb=drop_prov, drop_dup=drop_dup,
                          drop_empty=drop_empty, no_head=no_head)
    return rows, stats


def _load_rules(base, path):
    with open(os.path.join(base, path), encoding="utf-8") as f:
        g = json.load(f)
    return g.get("grammar_rules", g) if isinstance(g, dict) else g


def clean_grammar(base):
    rules, examples, stats = [], [], {}
    for reg, paths in GRAMMAR.items():
        seen = set()
        n_in = kept = dup = n_ex = banned = drop_ex_cat = 0
        for p in paths:
            for r in _load_rules(base, p):
                n_in += 1
                df = str(r.get("dialect_form", "")).strip()
                if any(b in df for b in BANNED_FORMS):
                    banned += 1
                    continue  # 실사용 빈도 낮은 어미: 규칙·예문 모두 제외
                sf = str(r.get("standard_form", "")).strip()
                exp = str(r.get("explanation", "")).strip()
                # 문장 예문 쌍(예문대조규칙): 규칙 아님 → 참조용 예문으로 이관
                if r.get("grammar_category") in BANNED_CATEGORIES:
                    examples.append({"region": reg, "standard": sf,
                                     "dialect": df, "from": "예문대조규칙"})
                    drop_ex_cat += 1
                    continue
                # 예문 분리 (검색소스 제외, 참조용 별도 보관)
                for ex in (r.get("examples") or []):
                    examples.append({"region": reg,
                                     "standard": ex.get("standard"),
                                     "dialect": ex.get("dialect")})
                    n_ex += 1
                key = (df, exp[:40])  # 강원 2파일 병합 시 중복 제거
                if key in seen:
                    dup += 1
                    continue
                seen.add(key)
                rules.append({
                    "region": reg,
                    "category": r.get("grammar_category"),
                    "standard_form": sf, "dialect_form": df,
                    "explanation": exp,
                    "keywords": r.get("keywords") or [],
                })
                kept += 1
        stats[reg] = dict(input=n_in, kept=kept, dup=dup, banned=banned,
                          drop_ex_cat=drop_ex_cat, examples_split=n_ex)
    return rules, examples, stats


def write_jsonl(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=DEFAULT_IN)
    ap.add_argument("--output", default=DEFAULT_OUT)
    args = ap.parse_args()

    print(f"입력: {args.input}\n출력: {args.output}\n")

    vocab, vstats = clean_vocab(args.input)
    write_jsonl(vocab, os.path.join(args.output, "vocab_clean.jsonl"))
    print("=== 어휘 정제 ===")
    print(f"{'권역':<4}{'입력':>7}{'유지':>7}{'무변환':>7}{'속담':>6}{'중복':>7}{'빈값':>5}{'표제어없음':>9}")
    for reg, s in vstats.items():
        print(f"{reg:<4}{s['input']:>7}{s['kept']:>7}{s['drop_novar']:>7}"
              f"{s['drop_proverb']:>6}{s['drop_dup']:>7}{s['drop_empty']:>5}{s['no_head']:>9}")
    print(f"  → 총 유지 어휘: {len(vocab)}")

    rules, examples, gstats = clean_grammar(args.input)
    write_jsonl(rules, os.path.join(args.output, "grammar_rules.jsonl"))
    write_jsonl(examples, os.path.join(args.output, "grammar_examples.jsonl"))
    print("\n=== 문법 정제 (규칙만, 예문 분리) ===")
    print(f"{'권역':<4}{'입력규칙':>8}{'유지':>6}{'중복':>6}{'제외어미':>8}{'예문대조':>8}{'분리예문':>8}")
    for reg, s in gstats.items():
        print(f"{reg:<4}{s['input']:>8}{s['kept']:>6}{s['dup']:>6}"
              f"{s.get('banned', 0):>8}{s.get('drop_ex_cat', 0):>8}{s['examples_split']:>8}")
    print(f"  → 총 유지 규칙: {len(rules)} / 분리 예문(참조용): {len(examples)}")
    print(f"  제외 어미(BANNED_FORMS): {BANNED_FORMS}")


if __name__ == "__main__":
    main()
