# -*- coding: utf-8 -*-
"""A단계(주) — LLM 기반 합성 교란으로 B 지표의 민감도·특이도 검증.

기존 사전기반 교란(perturb_sensitivity.py)은 채점기와 오염기가 같은 어미 사전이라
순환성이 있다. 여기서는 오염을 '독립 참조 모델(Claude)'에게 시켜 순환성을 완화한다.
(생성은 로컬 Qwen 전용이라는 논문 요지와 별개로, Claude는 '평가용 독립 오염기'로만 사용.)

두 교란 (정상 방언 대화의 '민원인' 발화에만 적용):
  (A) 표준어화     : 방언 → 표준어      → 방언율 하락 기대  (민감도)
  (B) 타권역화     : 소스권역 → 타권역   → 소스 방언율 하락 + 누수율 상승 기대 (특이도)

지표:
  민감도 = (D(정상) - D(표준어화)) / D(정상)          [D = 방언율]
  특이도(누수 상승) = 누수(타권역화) - 누수(정상)
  변환 확인 = D_타깃권역(타권역화)  (Claude가 실제로 변환했는지 방증)

사용:
  python src/eval/llm_perturb_sensitivity.py results/s1_*.jsonl [조건] [--model claude-opus-4-8]
"""
import sys, os, json, collections
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from eval_conditions import (  # noqa: E402
    load_markers, complainant_turns, words_of, score_surface,
)
import run  # noqa: E402  (call_anthropic, load_env 재사용)

# 소스권역 → 타권역 교체 대상(변별력 강한 권역 선택)
OTHER_REGION = {
    "경상": "충청", "전라": "충청", "충청": "경상",
    "강원": "경상", "제주": "충청",
}


def prompt_standardize(dialogue: str) -> str:
    return (
        "아래는 악취 민원 상담 대화입니다. '민원인:' 발화를 모두 자연스러운 표준어로 바꿔 주세요.\n"
        "- 방언 종결어미와 방언 어휘를 제거하고 표준어로 씁니다.\n"
        "- 내용·의미·대화 순서·턴 수는 그대로 유지합니다.\n"
        "- '상담원:' 발화는 원문 그대로 둡니다.\n"
        "- 출력은 원문과 동일한 '상담원: ...' / '민원인: ...' 형식의 대화만. 설명·머리말 금지.\n\n"
        f"[대화]\n{dialogue}"
    )


def prompt_crossregion(dialogue: str, src: str, tgt: str) -> str:
    return (
        f"아래는 {src}도 방언 악취 민원 대화입니다. '민원인:' 발화를 모두 자연스러운 "
        f"{tgt}도 방언으로 바꿔 주세요.\n"
        f"- {src}도 방언 요소를 {tgt}도 방언 종결어미·어휘로 교체합니다.\n"
        "- 내용·의미·대화 순서·턴 수는 그대로 유지합니다.\n"
        "- '상담원:' 발화는 원문 그대로 둡니다.\n"
        "- 출력은 '상담원: ...' / '민원인: ...' 형식의 대화만. 설명·머리말 금지.\n\n"
        f"[대화]\n{dialogue}"
    )


def rate(sc: dict) -> tuple:
    tot = max(sc["total_words"], 1)
    return sc["plus"] / tot, sc["minus"] / tot


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    model = "claude-opus-4-8"
    for o in opts:
        if o.startswith("--model="):
            model = o.split("=", 1)[1]
    if not args:
        print("사용: python llm_perturb_sensitivity.py results/s1_*.jsonl [조건] [--model=...]")
        sys.exit(1)
    path = args[0]
    cond = args[1] if len(args) > 1 else "c_kb_c1"

    run.load_env()
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("[중단] ANTHROPIC_API_KEY 없음 (.env 확인)")
        sys.exit(1)

    tbl = load_markers()
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]

    # 방언이 실현된 대화만 대상(D정상>0)
    targets = []
    for r in rows:
        region = r.get("region", "?")
        text = (r.get("generated") or {}).get(cond, "")
        if not text:
            continue
        sc0 = score_surface(words_of(complainant_turns(text)), region, tbl)
        if sc0["plus"] > 0:
            targets.append((r.get("scenario_id", "?"), region, text))
    print(f"[LLM A단계] 소스={os.path.basename(path)} 조건={cond} 모델={model} "
          f"대상={len(targets)}개 (D정상>0)\n")

    # Claude 호출 (표준어화 + 타권역화)
    def corrupt(item):
        sid, region, text = item
        tgt = OTHER_REGION.get(region, "충청")
        rA = run.call_anthropic(model, prompt_standardize(text), 1500, 120.0)
        rB = run.call_anthropic(model, prompt_crossregion(text, region, tgt), 1500, 120.0)
        return {
            "scenario_id": sid, "region": region, "target_region": tgt,
            "original": text,
            "standardized": rA.get("text", "") if rA.get("ok") else f"[ERR]{rA.get('error')}",
            "crossregion": rB.get("text", "") if rB.get("ok") else f"[ERR]{rB.get('error')}",
        }

    out = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(corrupt, it): it for it in targets}
        for i, f in enumerate(as_completed(futs), 1):
            out.append(f.result())
            print(f"  진행 {i}/{len(targets)}", end="\r")
    print()

    # 채점·집계
    sens, leak_rise, src_drop_B, conv_tgt = [], [], [], []
    per = collections.defaultdict(lambda: collections.Counter())
    for o in out:
        region, tgt = o["region"], o["target_region"]
        if o["standardized"].startswith("[ERR") or o["crossregion"].startswith("[ERR"):
            continue
        w0 = words_of(complainant_turns(o["original"]))
        wA = words_of(complainant_turns(o["standardized"]))
        wB = words_of(complainant_turns(o["crossregion"]))
        d0, l0 = rate(score_surface(w0, region, tbl))
        dA, _ = rate(score_surface(wA, region, tbl))
        dB, lB = rate(score_surface(wB, region, tbl))      # 소스권역 기준
        dB_tgt, _ = rate(score_surface(wB, tgt, tbl))       # 타깃권역 기준(변환 확인)
        if d0 <= 0:
            continue
        sens.append((d0 - dA) / d0)
        src_drop_B.append((d0 - dB) / d0)
        leak_rise.append(lB - l0)
        conv_tgt.append(dB_tgt)
        p = per[region]
        p["d0"] += d0; p["dA"] += dA; p["dB"] += dB; p["lB"] += lB; p["l0"] += l0
        p["dBt"] += dB_tgt; p["n"] += 1

    print(f"{'권역':<5}{'D정상':>8}{'D표준화':>9}{'D타권역':>9}{'누수정상':>9}{'누수타권역':>10}{'변환D타깃':>10}{'n':>4}")
    print("-" * 64)
    for region, p in sorted(per.items()):
        n = max(p["n"], 1)
        print(f"{region:<5}{p['d0']/n:>8.3f}{p['dA']/n:>9.3f}{p['dB']/n:>9.3f}"
              f"{p['l0']/n:>9.3f}{p['lB']/n:>10.3f}{p['dBt']/n:>10.3f}{p['n']:>4}")

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    print(f"\n=== 요약 (유효 {len(sens)}개) ===")
    print(f"  민감도(표준어화 시 방언율 하락)   : {mean(sens):.3f}")
    print(f"  특이도-A(타권역화 시 소스방언율↓) : {mean(src_drop_B):.3f}")
    print(f"  특이도-B(타권역화 시 누수율 상승)  : +{mean(leak_rise):.4f}")
    print(f"  변환 확인(타권역화의 타깃 방언율)  : {mean(conv_tgt):.3f}  (높을수록 Claude가 실제 변환)")

    # 교란 산출물 저장(수동 검수·재현용)
    ts = os.path.basename(path).replace(".jsonl", "")
    out_path = os.path.join(ROOT, "results", f"llm_perturb_{ts}.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"\n[저장] {out_path}  (수동 검수용)")


if __name__ == "__main__":
    main()
