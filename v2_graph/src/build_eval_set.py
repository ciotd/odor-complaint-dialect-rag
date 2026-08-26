# -*- coding: utf-8 -*-
"""AI-Hub 경상 2인발화 → (표준, 방언) 완성형 문장쌍 추출 (v2 평가 입력).

세그먼트(어절)를 orderInFile로 잇고, 종결어미(EF)로 끝나는 어절에서 문장 분리.
표준측 = standard(있으면) else dialect(=표준과 동일). 방언측 = dialect. 토큰 1:1 정렬 유지.
필터: 길이 14~42자, 표준≠방언(방언 차이 있음), 중복 제거.

출력: v2_graph/data/eval_pairs.jsonl  {id, 표준, 방언_ref}
      ※ AI-Hub 저작권 → gitignore. 스크립트로 재현.
사용: python build_eval_set.py [N목표]
"""
import zipfile, json, os, sys, re
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
ZIP = os.path.join(REPO, "..", "dialect_corpus", "aihub", "VL_02. 경상도_03. 2인발화.zip")
OUT = os.path.join(HERE, "..", "data", "eval_pairs.jsonl")

kiwi = Kiwi()
_HAN = re.compile(r"[가-힣]")


def extract(target=60, maxfiles=600):
    z = zipfile.ZipFile(ZIP)
    names = [n for n in z.namelist() if n.lower().endswith(".json")]
    pairs, seen = [], set()
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
            if tk and tk[-1].tag == "EF":            # 종결어미 = 문장 끝
                ss = " ".join(t for t in std[start:i + 1] if t)
                dd = " ".join(t for t in dia[start:i + 1] if t)
                start = i + 1
                if not (14 <= len(ss) <= 42) or ss == dd:
                    continue
                if not _HAN.search(ss):
                    continue
                if ss in seen:
                    continue
                seen.add(ss)
                pairs.append((ss, dd))
        if len(pairs) >= target:
            break
    return pairs[:target]


def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    pairs = extract(target)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for i, (ss, dd) in enumerate(pairs, 1):
            f.write(json.dumps({"id": f"A{i:03d}", "표준": ss, "방언_ref": dd},
                               ensure_ascii=False) + "\n")
    print(f"저장: {OUT} ({len(pairs)}쌍)")
    print("샘플:")
    for ss, dd in pairs[:8]:
        print(f"  {ss}  →  {dd}")


if __name__ == "__main__":
    main()
