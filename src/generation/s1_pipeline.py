# -*- coding: utf-8 -*-
"""S1(직접 생성) 전략 생성 하네스 — 방언 대화를 한 번에 직접 생성.

2단계 변환(표준어→방언) 없이 prompt_template.txt 기반으로 조건별 지식을 주입해
방언 대화를 바로 생성한다. hallucination 비교 실험용.

  - S1×C0      : 지식 없이 방언 대화 직접 생성
  - S1×C1      : 고정 few-shot 예시 주입 후 직접 생성
  - S1×C_kb    : 어휘+규칙 검색·주입 후 직접 생성
  - S1×C_kb_c1 : KB + few-shot 동시 주입 후 직접 생성

RAG 쿼리 = 시나리오 입력값(smell_type + complainant_location_text).
S2와 동일한 시드·시나리오를 사용해 공정 비교 가능.

사용:
  python src/generation/s1_pipeline.py --n 10 --regions 경상,전라,충청,강원,제주 \\
      --model Qwen/Qwen3.6-27B --conditions c0,c1,c_kb,c_kb_c1
"""
import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO))

import config  # noqa: E402
import run  # noqa: E402
from src.retrieval.kb_retriever import (  # noqa: E402
    KBRetriever, content_keys, format_for_prompt,
)

PROMPTS = _REPO / "prompts"
_C1_EXAMPLES_PATH = _REPO / "data" / "c1_examples.json"
_REGIONAL_EX_PATH = _REPO / "data" / "regional_dialogue_examples.json"


def load_c1_examples() -> dict:
    with open(_C1_EXAMPLES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_regional_examples() -> dict:
    with open(_REGIONAL_EX_PATH, encoding="utf-8") as f:
        return json.load(f)


def format_regional_example_block(dialogue: str) -> str:
    return ("\n[방언 대화 예시 — 아래 대화를 참고해 해당 권역의 자연스러운 방언을 사용한다]\n\n"
            + dialogue + "\n")


def format_c1_block(examples: list) -> str:
    lines = ["\n[방언 표현 참고 — 아래 표준어/방언 쌍을 참고한다]\n"]
    for ex in examples:
        lines.append(f"표준어: {ex['standard']}")
        lines.append(f"방언:   {ex['dialect']}\n")
    return "\n".join(lines)


def provider_of(model: str) -> str:
    m = model.lower()
    if "claude" in m:
        return "anthropic"
    if m.startswith("gpt") or m.startswith("o"):
        return "openai"
    return "local"


def call(provider, model, prompt, max_tokens, timeout):
    fn = {"openai": run.call_openai, "anthropic": run.call_anthropic,
          "local": run.call_local}[provider]
    return fn(model, prompt, max_tokens, timeout)


def fill(template: str, mapping: dict) -> str:
    out = template
    for k, v in mapping.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def retrieve_knowledge(retr, query_text, region, k_lex, k_rule,
                       use_lex=True, use_rule=True, cap_lex=20, cap_rule=10):
    """시나리오 쿼리 텍스트 → 지식 블록 + coverage."""
    if region not in retr.regions:
        empty_cov = {"content_words": 0, "lex_hits": 0, "lex_rate": 0.0,
                     "n_lex": 0, "n_rules": 0}
        return "", empty_cov
    keys = content_keys(query_text)
    n_content = len(keys)
    hits = retr.retrieve(query_text, region, use_lex=use_lex, use_rule=use_rule,
                         k_lex=k_lex, k_rule=k_rule)
    matched_heads = {g["head"] for g in hits["lexicon"]}
    n_hit = sum(1 for _, cand in keys if any(c in matched_heads for c in cand))
    agg = {"lexicon": hits["lexicon"][:cap_lex], "rules": hits["rules"][:cap_rule]}
    block = format_for_prompt(agg)
    cov = {"content_words": n_content, "lex_hits": n_hit,
           "lex_rate": round(n_hit / n_content, 3) if n_content else 0.0,
           "n_lex": len(agg["lexicon"]), "n_rules": len(agg["rules"])}
    return block, cov


# 조건명 → (use_lex, use_rule) 매핑
_COND_SWITCHES = {
    "c_kb":    (True, True),
    "c_kb_c1": (True, True),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--regions", type=str, default="경상,전라")
    ap.add_argument("--model", type=str, default="Qwen/Qwen3.6-27B")
    ap.add_argument("--conditions", type=str, default="c0,c1,c_kb,c_kb_c1")
    ap.add_argument("--k-lex", type=int, default=5)
    ap.add_argument("--k-rule", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=2500)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--seed", type=int, default=20260612)
    ap.add_argument("--out", type=str, default=str(_REPO / "results"))
    args = ap.parse_args()

    run.load_env()
    provider = provider_of(args.model)
    if provider == "local" and not run.local_up():
        print("[중단] 로컬 vLLM 서버 미기동.")
        sys.exit(1)
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    print(f"[설정] model={args.model}({provider}) · 조건={conditions} · 권역={regions}")

    gen_tmpl = (PROMPTS / "prompt_template.txt").read_text(encoding="utf-8")
    needs_retr = any(c in _COND_SWITCHES for c in conditions)
    retr = KBRetriever() if needs_retr else None
    needs_c1 = any(c in ("c1", "c_kb_c1") for c in conditions)
    c1_examples = load_c1_examples() if needs_c1 else {}
    regional_examples = load_regional_examples() if needs_c1 else {}

    run._ensure_orig_sampler()
    rng = random.Random(args.seed)
    scenarios = []
    for i in range(args.n):
        region = regions[i % len(regions)]
        sc = run.sample_scenario(rng, region)
        sc["scenario_id"] = i + 1
        sc["region_key"] = region
        scenarios.append(sc)

    results = []
    for sc in scenarios:
        sid, region = sc["scenario_id"], sc["region_key"]
        rname = sc["region_name"]
        print(f"\n[s{sid}] {rname} · {sc['smell_type']}")

        # RAG 쿼리 = 냄새 종류 + 위치 텍스트
        query = f"{sc.get('smell_type', '')} {sc.get('complainant_location_text', '')}"

        # 조건별 KB 블록 검색
        kb_blocks, cov = {}, None
        for cond, (ul, ur) in _COND_SWITCHES.items():
            if cond not in conditions:
                continue
            raw, _cov = retrieve_knowledge(retr, query, region,
                                           args.k_lex, args.k_rule,
                                           use_lex=ul, use_rule=ur)
            kb_blocks[cond] = (
                "\n[활용할 방언 지식 — 우선 참고하되, 없는 표현은 자연스러운 방언으로]\n"
                + raw + "\n") if raw else ""
            if cond == "c_kb":
                cov = _cov
        if cov:
            print(f"  검색(c_kb) 어휘{cov['n_lex']}·규칙{cov['n_rules']} "
                  f"(coverage {cov['lex_rate']})")

        # 조건별 직접 생성
        generated = {}
        for cond in conditions:
            if cond == "c_kb_c1":
                kb_part = kb_blocks.get(cond, "")
                reg_ex = regional_examples.get(region, "")
                exs = c1_examples.get(region, [])
                kb = (kb_part
                      + (format_regional_example_block(reg_ex) if reg_ex else "")
                      + (format_c1_block(exs) if exs else ""))
            elif cond in _COND_SWITCHES:
                kb = kb_blocks.get(cond, "")
            elif cond == "c1":
                reg_ex = regional_examples.get(region, "")
                exs = c1_examples.get(region, [])
                kb = ((format_regional_example_block(reg_ex) if reg_ex else "")
                      + (format_c1_block(exs) if exs else ""))
            else:  # c0
                kb = ""

            prompt = fill(gen_tmpl, {**sc, "knowledge_block": kb})
            r = call(provider, args.model, prompt, args.max_tokens, args.timeout)
            generated[cond] = r["text"] if r["ok"] else f"[ERROR] {r['error']}"
            print(f"  생성[{cond}] {'OK' if r['ok'] else 'ERR'}")

        results.append({
            "scenario_id": sid, "region": region, "region_name": rname,
            "input": {k: sc[k] for k in (
                "complainant_location_text", "smell_type",
                "smell_intensity", "smell_duration", "suspected_location_text")},
            "coverage": cov,
            "generated": generated,
        })

    # 저장
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl = outdir / f"s1_{stamp}.jsonl"
    with open(jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    txt = outdir / f"s1_{stamp}.txt"
    with open(txt, "w", encoding="utf-8") as f:
        for r in results:
            if "error" in r:
                continue
            f.write("=" * 72 + "\n")
            f.write(f"[s{r['scenario_id']}] {r['region_name']} · "
                    f"{r['input']['smell_type']}\n")
            if r.get("coverage"):
                f.write(f"coverage: {r['coverage']}\n")
            for cond, text in r["generated"].items():
                f.write(f"\n--- 생성[{cond}] ---\n" + text + "\n")
            f.write("\n")

    ok = sum(1 for r in results if "error" not in r)
    print(f"\n[요약] {ok}/{len(results)} 시나리오 완료")
    if any(r.get("coverage") for r in results):
        rates = [r["coverage"]["lex_rate"] for r in results if r.get("coverage")]
        print(f"  어휘 coverage 평균: {round(sum(rates)/len(rates), 3)}")
    print(f"[저장] {jsonl}\n[저장] {txt}")


if __name__ == "__main__":
    main()
