# -*- coding: utf-8 -*-
"""AI-Hub 코퍼스에서 '독립' 방언 어휘 목록 추출 (어휘 방언율 편향 제거용).

어미 마커(extract_corpus_markers_v3)는 '꼬리만 바뀐' 쌍을 뽑는다. 여기선 반대로
'어간(내용어)이 통째로 바뀐' 쌍을 뽑아 방언 어휘 목록을 만든다. RAG 사전과 출처가
다르므로(웹사전 아님, AI-Hub), 어휘 방언율의 홈 어드밴티지 편향을 제거하는 참조가 된다.

규칙(어미 추출과 대칭):
  - 어절쌍 (표준 s, 방언 dd), s!=dd, 숫자 제외, 위치정렬(len 같을 때만).
  - g = 표준 s의 문법경계(E*/J* 시작 전). content=s[:g], tail=s[g:].
  - k = 공통접두. k < g 이면 '어간(내용) 자체가 다름' = 어휘 변이(어미 변화 아님).
  - 표준 content가 명사/용언(NNG/NNP/VV/VA)일 것.
  - 방언 content = dd에서 표준 tail을 떼어냄(같은 조사 유지 시). 한글 2자+.

출력: 권역별 방언 어휘 목록 CSV + 표본 육안검증 출력.
재현: python src/eval/extract_vocab_pairs_aihub.py
"""
import zipfile, io, json, glob, re, collections, csv, os
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ZDIR = os.path.abspath(os.path.join(ROOT, "..", "dialect_corpus", "aihub"))
HOME = os.path.expanduser("~")
OUT = os.path.join(ROOT, "docs", "dialect_vocab_aihub.csv")
REGIONS = ["경상", "강원", "충청", "전라", "제주"]
ONE_ZIPS = [os.path.join(HOME, "139-1.중·노년층 한국어 방언 데이터 (강원도, 경상도).zip"),
            os.path.join(HOME, "139-2.중·노년층 한국어 방언 데이터 (충청도, 전라도, 제주도).zip")]

kiwi = Kiwi()
_c = {}
_DIGIT = re.compile(r"[0-9]")
_NONHAN = re.compile(r"[^가-힣]")
# 명사만(NNG/NNP) — 용언 활용형은 어미 변화가 섞여 노이즈 → 어휘 참조에서 제외.
_NOUN = {"NNG", "NNP"}


def gts_info(std):
    """(문법경계 g, 첫 형태소가 명사인가) 반환."""
    if std in _c:
        return _c[std]
    try:
        toks = kiwi.tokenize(std)
    except Exception:
        _c[std] = (len(std), False)
        return _c[std]
    end = 0
    is_noun = bool(toks) and toks[0].tag in _NOUN
    for t in toks:
        if t.tag[0] not in ("E", "J"):
            end = max(end, t.start + t.len)
    _c[std] = (end, is_noun)
    return _c[std]


def lcp(a, b):
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return i


def region_of(name):
    for r in REGIONS:
        if r in name:
            return r
    return None


def add_vocab(vocab, ex, s, dd):
    """어절쌍 → 방언 내용어 추출(어간이 다른 경우)."""
    if s == dd or _DIGIT.search(s) or _DIGIT.search(dd):
        return
    if "#" in s or "#" in dd:        # 비식별화 마스킹(#이름# 등) 제외
        return
    g, is_noun = gts_info(s)
    if g <= 0 or not is_noun:
        return
    k = lcp(s, dd)
    if k >= g:                       # 꼬리만 변화 = 어미(제외)
        return
    tail = s[g:]
    dcont = dd[:-len(tail)] if (tail and dd.endswith(tail)) else dd
    scont = s[:g]
    dh = _NONHAN.sub("", dcont)
    if len(dh) < 2 or dh == _NONHAN.sub("", scont):
        return
    vocab[dh] += 1
    ex.setdefault(dh, (s, dd))


def extract_2in(zip_path, vocab, ex):
    zf = zipfile.ZipFile(zip_path)
    for n in zf.namelist():
        if not n.endswith(".json"):
            continue
        d = json.loads(zf.read(n).decode("utf-8"))
        for seg in d.get("transcription", {}).get("segments", []):
            sd = (seg.get("standard") or "").strip()
            di = (seg.get("dialect") or "").strip()
            if not sd or not di or sd == di:
                continue
            sw, dw = sd.split(), di.split()
            if len(sw) != len(dw):
                continue
            for s, dd in zip(sw, dw):
                add_vocab(vocab, ex, s, dd)


def extract_1in(outer_zip, region, vocab, ex):
    outer = zipfile.ZipFile(outer_zip)
    inners = [n for n in outer.namelist()
              if region in os.path.basename(n) and "1인발화" in n
              and "VL_" in n and n.endswith(".zip")]
    for tgt in inners:
        inner = zipfile.ZipFile(io.BytesIO(outer.read(tgt)))
        for jn in inner.namelist():
            if not jn.endswith(".json"):
                continue
            tr = json.loads(inner.read(jn)).get("transcription", {})
            sd = (tr.get("standard") or "").strip()
            di = (tr.get("dialect") or "").strip()
            if not sd or not di or sd == di:
                continue
            sw, dw = sd.split(), di.split()
            if len(sw) != len(dw):
                continue
            for s, dd in zip(sw, dw):
                add_vocab(vocab, ex, s, dd)


def main():
    per = {r: (collections.Counter(), {}) for r in REGIONS}
    for z in glob.glob(os.path.join(ZDIR, "*2인발화*.zip")):
        r = region_of(z)
        if not r:
            continue
        vocab, ex = per[r]
        extract_2in(z, vocab, ex)
        print(f"  [2인] {r}: 누적 어휘형 {len(vocab):,}")
    for oz in ONE_ZIPS:
        if not os.path.isfile(oz):
            continue
        for r in REGIONS:
            vocab, ex = per[r]
            before = len(vocab)
            extract_1in(oz, r, vocab, ex)
            if len(vocab) > before:
                print(f"  [1인] {r}: +{len(vocab)-before:,} (누적 {len(vocab):,})")

    # 저장
    rows = []
    for r in REGIONS:
        vocab, ex = per[r]
        for form, c in vocab.items():
            s, dd = ex[form]
            rows.append({"권역": r, "방언어휘": form, "빈도": c, "예시": f"{s}→{dd}"})
    rows.sort(key=lambda x: (x["권역"], -x["빈도"]))
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=["권역", "방언어휘", "빈도", "예시"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n저장: {os.path.relpath(OUT, ROOT)} (총 {len(rows)}개)")

    # 육안검증 표본
    print("\n" + "=" * 50 + "\n[육안검증] 권역별 상위 15개 (표준→방언)\n" + "=" * 50)
    for r in REGIONS:
        vocab, ex = per[r]
        top = sorted(vocab.items(), key=lambda x: -x[1])[:15]
        print(f"\n{r} (고유 {len(vocab)}개):")
        for form, c in top:
            s, dd = ex[form]
            print(f"  {form}({c})  [{s}→{dd}]")


if __name__ == "__main__":
    main()
