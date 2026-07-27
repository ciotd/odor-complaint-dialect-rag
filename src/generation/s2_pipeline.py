# -*- coding: utf-8 -*-
"""S2(변환) 전략 생성 하네스 — 표준어 생성 → (검색·주입) → 방언 변환.

C0 vs C_kb 비교를 '변환 단계'에서만 다르게 하여 RAG 효과를 분리한다:
  - S2×C0  : 표준어 대화 생성 → (지식 없이) 방언 변환
  - S2×C_kb: 표준어 대화 생성 → 민원인 표준어 발화를 쿼리로 검색 → 지식 주입 변환
변환 프롬프트는 knowledge_block 유무만 다르고 나머지는 동일(공정 비교).

쿼리 = ①단계에서 만든 '민원인 표준어 발화'. 어휘=표제어 정확매칭, 규칙=형태소 BM25.
미매칭 부분은 프롬프트에 없으므로 LLM 자체 지식으로 출력됨 → coverage를 로그로 남긴다.

사용:
  python src/generation/s2_pipeline.py --n 8 --regions 경상,전라 --model Qwen --conditions c0,c_kb
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
import run  # noqa: E402  (call_local/anthropic/openai, load_env, sample_scenario)
from src.retrieval.kb_retriever import (  # noqa: E402
    KBRetriever, content_keys, format_for_prompt,
)

PROMPTS = _REPO / "prompts"


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


def parse_turns(text: str):
    """대화 텍스트 → [(speaker, utterance)]. '상담원:/민원인:' 라벨 기준."""
    turns = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for sp in ("상담원", "민원인"):
            if line.startswith(sp):
                rest = line[len(sp):].lstrip(": ：").strip()
                turns.append((sp, rest))
                break
    return turns


def retrieve_knowledge(retr, complainant_lines, region, k_lex, k_rule,
                       cap_lex=20, cap_rule=10):
    """민원인 표준어 발화들 → 통합 검색. (knowledge_block, coverage)."""
    lex, rules = {}, {}
    n_content = n_hit = 0
    for line in complainant_lines:
        # coverage: 이 발화의 내용어 중 몇 개가 어휘 DB에 걸리나
        keys = content_keys(line)
        n_content += len(keys)
        hits = retr.retrieve(line, region, k_lex=k_lex, k_rule=k_rule)
        matched_heads = {g["head"] for g in hits["lexicon"]}
        for surface, cand in keys:
            if any(c in matched_heads for c in cand):
                n_hit += 1
        for g in hits["lexicon"]:
            lex.setdefault(g["head"], g)
        for r in hits["rules"]:
            rules.setdefault((r["standard_form"], r["dialect_form"]), r)
    agg = {"lexicon": list(lex.values())[:cap_lex],
           "rules": list(rules.values())[:cap_rule]}
    block = format_for_prompt(agg)
    cov = {"content_words": n_content, "lex_hits": n_hit,
           "lex_rate": round(n_hit / n_content, 3) if n_content else 0.0,
           "n_lex": len(agg["lexicon"]), "n_rules": len(agg["rules"])}
    return block, cov


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--regions", type=str, default="경상,전라")
    ap.add_argument("--model", type=str, default="Qwen/Qwen3.6-27B")
    ap.add_argument("--conditions", type=str, default="c0,c_kb")
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
        print("[중단] 로컬 vLLM 서버 미기동(localhost:8000).")
        sys.exit(1)
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    print(f"[설정] model={args.model}({provider}) · 조건={conditions} · 권역={regions}")

    std_tmpl = (PROMPTS / "prompt_standard.txt").read_text(encoding="utf-8")
    conv_tmpl = (PROMPTS / "convert_template.txt").read_text(encoding="utf-8")
    retr = KBRetriever() if "c_kb" in conditions else None

    # 시나리오 샘플 (run.py와 동일 방식·시드 → 재현/공정)
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

        # ① 표준어 대화 생성
        std_prompt = fill(std_tmpl, sc)
        r1 = call(provider, args.model, std_prompt, args.max_tokens, args.timeout)
        if not r1["ok"]:
            print(f"  표준어 생성 실패: {r1['error'][:60]}")
            results.append({"scenario_id": sid, "region": region,
                            "error": r1["error"]})
            continue
        std_dialogue = r1["text"]
        turns = parse_turns(std_dialogue)
        complainant = [u for sp, u in turns if sp == "민원인"]
        print(f"  ① 표준어 {len(turns)}턴(민원인 {len(complainant)}) 생성")

        # ②-a 검색(조건 c_kb만)
        block, cov = "", None
        if "c_kb" in conditions and complainant:
            raw, cov = retrieve_knowledge(retr, complainant, region,
                                          args.k_lex, args.k_rule)
            block = ("\n[활용할 방언 지식 — 우선 참고하되, 없는 표현은 자연스러운 방언으로]\n"
                     + raw + "\n") if raw else ""
            print(f"  ②검색 어휘{cov['n_lex']}·규칙{cov['n_rules']} "
                  f"(어휘 coverage {cov['lex_rate']})")

        # ②-b 변환 (조건별)
        conv = {}
        for cond in conditions:
            kb = block if cond == "c_kb" else ""
            cp = fill(conv_tmpl, {"region_name": rname,
                                  "knowledge_block": kb,
                                  "standard_dialogue": std_dialogue})
            r2 = call(provider, args.model, cp, args.max_tokens, args.timeout)
            conv[cond] = r2["text"] if r2["ok"] else f"[ERROR] {r2['error']}"
            print(f"  ②변환[{cond}] {'OK' if r2['ok'] else 'ERR'}")

        results.append({
            "scenario_id": sid, "region": region, "region_name": rname,
            "input": {k: sc[k] for k in (
                "complainant_location_text", "smell_type",
                "smell_intensity", "smell_duration", "suspected_location_text")},
            "standard_dialogue": std_dialogue,
            "coverage": cov,
            "converted": conv,
        })

    # 저장
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl = outdir / f"s2_{stamp}.jsonl"
    with open(jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 눈으로 볼 txt (표준어 + 조건별 변환 나란히)
    txt = outdir / f"s2_{stamp}.txt"
    with open(txt, "w", encoding="utf-8") as f:
        for r in results:
            if "error" in r:
                continue
            f.write("=" * 72 + "\n")
            f.write(f"[s{r['scenario_id']}] {r['region_name']} · "
                    f"{r['input']['smell_type']}\n")
            if r.get("coverage"):
                f.write(f"coverage: {r['coverage']}\n")
            f.write("\n--- 표준어(①) ---\n" + r["standard_dialogue"] + "\n")
            for cond, text in r["converted"].items():
                f.write(f"\n--- 변환[{cond}] ---\n" + text + "\n")
            f.write("\n")

    ok = sum(1 for r in results if "error" not in r)
    print(f"\n[요약] {ok}/{len(results)} 시나리오 완료")
    if any(r.get("coverage") for r in results):
        rates = [r["coverage"]["lex_rate"] for r in results if r.get("coverage")]
        print(f"  어휘 coverage 평균: {round(sum(rates)/len(rates), 3)}")
    print(f"[저장] {jsonl}\n[저장] {txt}")


if __name__ == "__main__":
    main()
