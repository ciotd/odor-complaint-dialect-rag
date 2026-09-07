# -*- coding: utf-8 -*-
"""AI-Hub 경상 2인발화 → (표준, 방언) 완성형 문장쌍 추출 (v2 평가 입력).

세그먼트(어절)를 orderInFile로 잇고, 종결어미(EF)로 끝나는 어절에서 문장 분리.
표준측 = standard(있으면) else dialect(=표준과 동일). 방언측 = dialect. 토큰 1:1 정렬 유지.
필터: 길이 14~42자, 표준≠방언(방언 차이 있음), 중복 제거.

출력: archive/v2_failed/data/eval_pairs.jsonl  {id, 표준, 방언_ref}
      ※ AI-Hub 저작권 → gitignore. 스크립트로 재현.
사용: python build_eval_set.py [N목표]
"""
import zipfile, json, os, sys, re
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ZIP = os.path.join(PROJECT_ROOT, "..", "dialect_corpus", "aihub", "VL_02. 경상도_03. 2인발화.zip")
OUT = os.path.join(HERE, "..", "data", "eval_pairs.jsonl")

kiwi = Kiwi()
_HAN = re.compile(r"[가-힣]")


Q_END = {"나", "노", "냐", "느냐", "으냐", "는가", "ㄴ가", "은가", "는고", "ㄴ고", "니"}


def extract(n_gen=35, n_q=25, maxfiles=800):
    """일반셋(n_gen) + 의문셋(n_q). 둘 다 실제 AI-Hub. 유형 태그 포함."""
    z = zipfile.ZipFile(ZIP)
    names = [n for n in z.namelist() if n.lower().endswith(".json")]
    gen, q, seen = [], [], set()
    for n in names[:maxfiles]:
        d = json.loads(z.read(n).decode("utf-8"))
        segs = sorted(d.get("transcription", {}).get("segments", []),
                      key=lambda s: s.get("orderInFile") or 0)
        std = [(s.get("standard") or s.get("dialect") or "").strip() for s in segs]
        dia = [(s.get("dialect") or "").strip() for s in segs]
        start = 0
        for i, tok in enumerate(std):
            if not tok:
                continue
            tk = kiwi.tokenize(tok)
            if tk and tk[-1].tag == "EF":
                ss = " ".join(t for t in std[start:i + 1] if t)
                dd = " ".join(t for t in dia[start:i + 1] if t)
                last = tk[-1].form
                start = i + 1
                if not (12 <= len(ss) <= 42) or ss == dd or not _HAN.search(ss) or ss in seen:
                    continue
                seen.add(ss)
                if last in Q_END and len(q) < n_q:
                    q.append((ss, dd, "의문"))
                elif len(gen) < n_gen:
                    gen.append((ss, dd, "일반"))
        if len(gen) >= n_gen and len(q) >= n_q:
            break
    return gen + q


def main():
    pairs = extract()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for i, (ss, dd, typ) in enumerate(pairs, 1):
            f.write(json.dumps({"id": f"A{i:03d}", "표준": ss, "방언_ref": dd, "유형": typ},
                               ensure_ascii=False) + "\n")
    import collections
    c = collections.Counter(t for _, _, t in pairs)
    print(f"저장: {OUT} ({len(pairs)}쌍, {dict(c)})")
    print("의문 샘플:")
    for ss, dd, t in [p for p in pairs if p[2] == "의문"][:6]:
        print(f"  {ss}  →  {dd}")


if __name__ == "__main__":
    main()
