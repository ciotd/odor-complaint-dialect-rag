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

# 5권역. 제주는 v2 사용(2026-08-11 편입): jeju_vocab_v2(단어형 91%)·jeju_grammar_v2.
# ⚠️ 제주 어휘 final은 지명유래 오염이라 제외, v2만 사용. 문법은 나무위키 파생 →
#    투고 전 학술 근거 보강 필요(data_audit §2). standard/dialect_form null 규칙은 자동 제외.
VOCAB = {
    "강원": "강원도/어휘/gangwon_vocab.json",
    "경상": "경상도/어휘/gyeongsang_vocab.json",
    "전라": "전라도/어휘/jeonla_vocab.json",
    "충청": "충청도/어휘/chungcheong_vocab.json",
    "제주": "제주도/어휘/jeju_vocab_v2.json",
}
GRAMMAR = {
    "강원": ["강원도/문법/gangwon_grammar.json",
             "강원도/문법/naver_gangwon_grammar_final2.json"],
    "경상": ["경상도/문법/gyeongsang_grammar.json"],
    "전라": ["전라도/문법/jeonla_grammar.json"],
    "충청": ["충청도/문법/chungcheong_grammar.json"],
    "제주": ["제주도/문법/jeju_grammar_v2.json"],
}

# 실사용 빈도가 낮아 제외하는 어미(현지인 확인, 2026-07-24): 전라 '-당께라우'
BANNED_FORMS = ["당께라우"]

# 규칙이 아니라 '문장 예문 쌍'인 category (LLM이 스스로 라벨링).
# standard_form/dialect_form이 통째로 문장이라 검색소스에 들어가면 사실상
# '미리 만든 few-shot 검색'이 되어 C1과 C_kb 구분이 무너진다(research_scope 5.1).
# 규칙셋에서 빼고 참조용 grammar_examples.jsonl로 보낸다. (2026-07-24, 경상 79건)
BANNED_CATEGORIES = {"예문대조규칙"}

# 규칙 검수 결정(2026-07-27) — malformed 항목 제거/필드교정. rule_overrides.json 참조.
_OVERRIDE_PATH = os.path.join(_HERE, "rule_overrides.json")


def _load_overrides():
    """rule_overrides.json → (drop_set, fix_map). 원본 standard_form으로 매칭."""
    if not os.path.isfile(_OVERRIDE_PATH):
        return set(), {}
    with open(_OVERRIDE_PATH, encoding="utf-8") as f:
        ov = json.load(f)
    drop = {(d["region"], d["standard_form"]) for d in ov.get("drop", [])}
    fix = {(x["region"], x["match"]):
           {"standard_form": x["standard_form"], "dialect_form": x["dialect_form"]}
           for x in ov.get("fix", [])}
    return drop, fix


# 주입 부적합 규칙 판별(2026-08-12 1차 자동 정제): 추상 음운·자모 리스트·문장형은
# 프롬프트에 넣어도 모델이 어절 단위로 적용 못 함. 어미/형태소 치환 규칙만 남긴다.
_JAMO = re.compile(r'[ㄱ-ㅎㅏ-ㅣ]')  # 자모 단독 = 음운 규칙 신호
_PHON_WORDS = ("음운", "모음", "자음", "움라우트", "된소리", "구개음화", "연음", "유기음",
               "경음", "후두", "전설", "후설", "단모음", "이중모음", "예사소리", "축약", "탈락")


def is_injectable_rule(sf, df, exp):
    """어절 단위 주입 가능한 어미/형태소 규칙인가. 음운·리스트·문장형이면 False."""
    if _JAMO.search(sf) or _JAMO.search(df):
        return False  # ㄱ→ㄲ, 외/의/류 같은 자모 규칙
    if "," in sf or "," in df or "、" in sf:
        return False  # 콤마 나열(음운/어휘 리스트)
    if any(w in exp for w in _PHON_WORDS):
        return False  # 설명이 음운 현상
    if len(sf.split()) >= 3 or len(sf) > 15:
        return False  # 문장형(예문 오염)
    return True

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
    drop_ov, fix_ov = _load_overrides()
    rules, examples, stats = [], [], {}
    for reg, paths in GRAMMAR.items():
        seen = set()
        n_in = kept = dup = n_ex = banned = drop_ex_cat = drop_review = fixed = 0
        drop_null = drop_phon = 0
        for p in paths:
            for r in _load_rules(base, p):
                n_in += 1
                df = str(r.get("dialect_form") or "").strip()
                if any(b in df for b in BANNED_FORMS):
                    banned += 1
                    continue  # 실사용 빈도 낮은 어미: 규칙·예문 모두 제외
                sf = str(r.get("standard_form") or "").strip()
                exp = str(r.get("explanation", "")).strip()
                # 구조화 폼 없는 규칙(설명문만) 제외: 검색·주입 불가 (제주 나무위키 파생 다수)
                if r.get("grammar_category") not in BANNED_CATEGORIES and (not sf or not df):
                    drop_null += 1
                    continue
                # 주입 부적합(추상 음운·자모 리스트·문장형) 제외: 어미/형태소 규칙만 유지
                if r.get("grammar_category") not in BANNED_CATEGORIES and not is_injectable_rule(sf, df, exp):
                    drop_phon += 1
                    continue
                # 문장 예문 쌍(예문대조규칙): 규칙 아님 → 참조용 예문으로 이관
                if r.get("grammar_category") in BANNED_CATEGORIES:
                    examples.append({"region": reg, "standard": sf,
                                     "dialect": df, "from": "예문대조규칙"})
                    drop_ex_cat += 1
                    continue
                # 검수 override: 서술형 제거 / 필드 교정(원본 sf로 매칭)
                if (reg, sf) in drop_ov:
                    drop_review += 1
                    continue
                if (reg, sf) in fix_ov:
                    fx = fix_ov[(reg, sf)]
                    sf, df = fx["standard_form"], fx["dialect_form"]
                    fixed += 1
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
                          drop_ex_cat=drop_ex_cat, drop_review=drop_review,
                          fixed=fixed, examples_split=n_ex, drop_null=drop_null,
                          drop_phon=drop_phon)
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
    print(f"{'권역':<4}{'입력규칙':>8}{'유지':>6}{'중복':>6}{'제외어미':>8}"
          f"{'예문대조':>8}{'검수제거':>8}{'검수수정':>8}{'폼null':>7}{'분리예문':>8}")
    for reg, s in gstats.items():
        print(f"{reg:<4}{s['input']:>8}{s['kept']:>6}{s['dup']:>6}"
              f"{s.get('banned', 0):>8}{s.get('drop_ex_cat', 0):>8}"
              f"{s.get('drop_review', 0):>8}{s.get('fixed', 0):>8}"
              f"{s.get('drop_null', 0):>7}{s.get('drop_phon', 0):>7}{s['examples_split']:>8}")
    print(f"  → 총 유지 규칙: {len(rules)} / 분리 예문(참조용): {len(examples)}")
    print(f"  제외 어미(BANNED_FORMS): {BANNED_FORMS}")


if __name__ == "__main__":
    main()
