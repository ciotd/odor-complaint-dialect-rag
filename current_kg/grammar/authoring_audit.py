"""Read-only audit of saved knowledge, with optional derived report export.

Counts are implementation diagnostics, not linguistic correctness or completeness scores.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def audit_ending_connections(records, graph):
    """Inventory all records, then audit a reproducibly selected ending-related scope.

    Absence of a particular edge is a review lead, not a linguistic error.
    Provenance and shared spellings do not count as semantic use connections.
    """
    core_concepts = {'ENDING', 'FINAL_ENDING', 'CONNECTIVE_ENDING', 'PREFINAL_ENDING'}
    function_concepts = {'DECLARATIVE', 'INTERROGATIVE', 'POLAR_QUESTION', 'CONTENT_QUESTION',
                         'IMPERATIVE', 'HORTATIVE', 'EXCLAMATIVE'}
    support_concepts = {'INFLECTION', 'STEM', 'ALLOMORPH', 'SPEECH_LEVEL',
                        'ADDRESSEE_HONORIFIC', 'SUBJECT_HONORIFIC', 'OBJECT_HONORIFIC',
                        'TENSE', 'PAST', 'FUTURE', 'MODALITY', 'INTENTION', 'GUESS',
                        'AUXILIARY_PREDICATE', 'QUOTATION', 'NEGATION', 'PROHIBITION',
                        'OBLIGATION', 'RESULTATIVE', 'ABILITY_NEGATION', 'ASPECT', 'PASSIVE', 'CAUSATIVE'}
    core_targets = {'clause.final_ending', 'clause.connective', 'clause.question_interpretation'}
    nodes = {n['id']: n for n in graph['nodes']}
    edges = graph['edges']
    by_id = {r['id']: r for r in records}
    outgoing = {}
    for e in edges:
        outgoing.setdefault(e['source'], []).append(e)
    semantic = [e for e in edges if 'assertion_id' in e['properties']]
    integration = [e for e in edges if 'integration_id' in e['properties']]
    used_forms = {n for e in semantic + integration for n in (e['source'], e['target'])}
    by_record = {}
    for e in semantic:
        by_record.setdefault(e['properties']['record_id'], []).append(e)

    # All-graph reference checks, not restricted to the selected ending scope.
    integrity = {
        'duplicate_node_ids': [k for k, v in Counter(n['id'] for n in graph['nodes']).items() if v > 1],
        'duplicate_edge_ids': [k for k, v in Counter(e['id'] for e in edges).items() if v > 1],
        'dangling_edges': [e['id'] for e in edges if e['source'] not in nodes or e['target'] not in nodes],
        'isolated_node_ids': sorted(set(nodes) - {x for e in edges for x in (e['source'], e['target'])}),
        'condition_edge_mismatches': [], 'assertion_link_errors': [],
    }
    def canon(cs):
        return sorted(json.dumps({k: c.get(k) for k in ('field','operator','values','evidence_keys')},
                                 sort_keys=True) for c in cs)
    for n in graph['nodes']:
        if n['type'] != 'Assertion':
            continue
        aid = n['id']; props = n['properties']; links = outgoing.get(aid, [])
        for mode in ('all', 'any'):
            actual = [nodes[e['target']]['properties'] for e in links
                      if e['type'] == 'requires_' + mode and e['target'] in nodes]
            if canon(actual) != canon(props['conditions'][mode]):
                integrity['condition_edge_mismatches'].append({'assertion_id': aid, 'mode': mode})
        for relation in ('subject', 'object', 'applies_at'):
            if len([e for e in links if e['type'] == relation]) != 1:
                integrity['assertion_link_errors'].append({'assertion_id': aid, 'relation': relation})
        # Assertions carry evidence_ids as properties; records/conditions have supported_at edges.
        evidence_ids = props.get('evidence_ids', [])
        if not evidence_ids or any(nodes.get(eid, {}).get('type') != 'SourceLocation' for eid in evidence_ids):
            integrity['assertion_link_errors'].append({'assertion_id': aid, 'relation': 'evidence_ids'})

    inventories = []
    for r in records:
        k = r['knowledge']; rid = r['id']; rels = k['relations']
        concepts = set(k['concepts'])
        targets = {a['application']['target'] for a in rels}
        reasons = []
        if k['kind'] == 'ending': reasons.append('kind=ending')
        if concepts & core_concepts: reasons.append('ending_concepts:' + ','.join(sorted(concepts & core_concepts)))
        if targets & core_targets: reasons.append('clause_targets:' + ','.join(sorted(targets & core_targets)))
        if k['kind'] != 'lexical' and concepts & function_concepts:
            reasons.append('sentence_function_concepts:' + ','.join(sorted(concepts & function_concepts)))
        if reasons:
            tier = 'core'
        else:
            if k['kind'] in ('inflection', 'phonology'):
                reasons.append('inflection_or_phonology_support')
            if concepts & support_concepts:
                reasons.append('support_concepts:' + ','.join(sorted(concepts & support_concepts)))
            if 'predicate.inflection' in targets: reasons.append('inflection_target')
            # Explicit wording supplements tags; candidate selection is auditable, not a full linguistic ontology.
            if k['kind'] != 'lexical' and any(w in k['label'] for w in ('어미','종결','높임','인용','요청','부탁','의문','명령')):
                reasons.append('explicit_ending_context_in_label')
            tier = 'support' if reasons else 'outside_selected_scope'
        rs = by_record.get(rid, [])
        all_conditions = [(rid + ':A' + str(i), c) for i, a in enumerate(rels, 1)
                          for mode in ('all','any') for c in a['conditions'][mode]]
        fields = sorted({c['field'] for _, c in all_conditions})
        realizes = [e for e in rs if e['type'] == 'realizes']
        interpretations = [e for e in rs if e['type'] == 'has_interpretation']
        links = [e for e in integration if any(x.split(':')[0] == rid for x in (e['source'], e['target']))]
        record_links = [e for e in edges if e['type'] == 'qualifies' and rid in (e['source'], e['target'])]
        meaning_only = []
        empty_conditions = []
        pending_semantics = []
        pending_bindings = []
        for i, a in enumerate(rels, 1):
            fs = {c['field'] for m in ('all','any') for c in a['conditions'][m]}
            if fs == {'meaning'}: meaning_only.append(rid + ':A' + str(i))
            if not fs: empty_conditions.append(rid + ':A' + str(i))
            aid = rid + ':A' + str(i)
            if fs & {'meaning', 'other'}:
                pending_semantics.append({'assertion_id': aid, 'conditions': a['conditions']})
            if not fs <= set(a['application'].get('feature_sources', {})):
                pending_bindings.append({'assertion_id': aid, 'unbound_fields': sorted(
                    fs - set(a['application'].get('feature_sources', {})))})
        # Field/link presence is not proof of exhaustive source coverage.
        tasks = []
        if pending_semantics: tasks.append('설명형 조건 분해')
        if pending_bindings: tasks.append('값 공급원 확인')
        if not links and not record_links: tasks.append('예외·활용 연결 필요성 판정')
        if r['review']['source_fidelity'] != 'author_checked': tasks.append('원문 해석 재검토')
        if k['gaps']: tasks.append('기록별 공백 대조')
        tasks.append('조건·예외 누락 여부 미확정')
        inventories.append({
            'record_id': rid, 'label': k['label'], 'kind': k['kind'], 'tier': tier,
            'selection_reasons': reasons or ['현재 어미/활용/높임 선택 기준에 해당하지 않음; 간접 관련성을 부정하는 것은 아님'], 'source_id': r['source_id'], 'authored_file': r['authored_file'],
            'evidence': k['evidence'], 'concepts': k['concepts'], 'application_targets': sorted(targets),
            'assertion_count': len(rels), 'relation_counts': dict(Counter(a['predicate'] for a in rels)),
            'condition_fields': fields, 'meaning_only_assertions': meaning_only,
            'empty_condition_assertions': empty_conditions,
            'realizes_assertions': [e['properties']['assertion_id'] for e in realizes],
            'realized_concept_ids': sorted({e['target'] for e in realizes}),
            'interpretation_assertions': [e['properties']['assertion_id'] for e in interpretations],
            'unconnected_forms': [{'id': rid + ':' + f['key'], 'text': f['text'], 'role': f['role']}
                                  for f in k['forms'] if rid + ':' + f['key'] not in used_forms],
            'integration_ids': [e['properties']['integration_id'] for e in links],
            'record_qualification_edge_ids': [e['id'] for e in record_links],
            'unknown_scope_dimensions': [name for name, value in k['scope'].items() if value['basis'] == 'unknown'],
            'source_review': r['review']['source_fidelity'], 'gaps': k['gaps'],
            'condition_work': {
                'status': 'tracked_not_certified_complete',
                'pending_semantic_conditions': pending_semantics,
                'pending_feature_bindings': pending_bindings,
                'next_actions': tasks,
                'exception_coverage': 'not_exhaustively_reviewed',
                'no_known_restriction_asserted': False,
            },
        })

    selected = [r for r in inventories if r['tier'] != 'outside_selected_scope']
    core = [r for r in selected if r['tier'] == 'core']
    selected_ids = {r['record_id'] for r in selected}
    core_ids = {r['record_id'] for r in core}
    summary = {
        'all_records_screened': len(records), 'selected_records': len(selected),
        'tiers': dict(Counter(r['tier'] for r in inventories)),
        'selected_kinds': dict(Counter(r['kind'] for r in selected)),
        'integrity_issue_counts': {k: len(v) for k, v in integrity.items()},
        'selected_unconnected_forms': sum(len(r['unconnected_forms']) for r in selected),
        'selected_records_with_unconnected_forms': sum(bool(r['unconnected_forms']) for r in selected),
        'core_records_without_any_realizes': sum(not r['realizes_assertions'] for r in core),
        'core_records_without_realizes_but_with_interpretation': sum(not r['realizes_assertions'] and bool(r['interpretation_assertions']) for r in core),
        'selected_meaning_only_assertions': sum(len(r['meaning_only_assertions']) for r in selected),
        'selected_assertions': sum(r['assertion_count'] for r in selected),
        'selected_records_with_meaning_only_assertions': sum(bool(r['meaning_only_assertions']) for r in selected),
        'core_condition_field_record_counts': dict(Counter(f for r in core for f in r['condition_fields'])),
        'core_records_with_surface_relation': sum('has_surface_form' in r['relation_counts'] for r in core),
        'core_records_without_interrecord_links': sum(not r['integration_ids'] and not r['record_qualification_edge_ids'] for r in core),
        'selected_source_review_pending': sum(r['source_review'] != 'author_checked' for r in selected),
        'selected_pending_binding_assertions': sum(len(r['condition_work']['pending_feature_bindings']) for r in selected),
        'selected_pending_semantic_assertions': sum(len(r['condition_work']['pending_semantic_conditions']) for r in selected),
        'ending_kind_application_target_counts': dict(Counter(a['application']['target'] for r in records
                if r['knowledge']['kind'] == 'ending' for a in r['knowledge']['relations'])),
    }
    # Exact concept-family paths, deliberately avoiding classification/provenance as use relations.
    families = {'평서': {'DECLARATIVE'}, '질문': {'INTERROGATIVE','POLAR_QUESTION','CONTENT_QUESTION'},
                '명령': {'IMPERATIVE'}, '청유': {'HORTATIVE'}, '감탄': {'EXCLAMATIVE'}}
    routes = {}
    for label, family in families.items():
        family_nodes = {'concept:' + x for x in family}
        annotated = {r['record_id'] for r in core if set(r['concepts']) & family}
        realized = {e['properties']['record_id'] for e in semantic
                    if e['type'] == 'realizes' and e['target'] in family_nodes and e['properties']['record_id'] in core_ids}
        direct_final = {e['properties']['record_id'] for e in semantic if e['type'] == 'realizes'
                        and e['target'] in family_nodes and e['properties']['record_id'] in core_ids
                        and nodes[e['properties']['assertion_id']]['properties']['application']['target'] == 'clause.final_ending'}
        routes[label] = {'classified_or_realized_record_ids': sorted(annotated | realized),
                         'direct_realizes_record_ids': sorted(realized),
                         'direct_final_ending_record_ids': sorted(direct_final),
                         'classified_without_direct_function_route': sorted(annotated - realized)}
    request_ids = [r['record_id'] for r in selected if any(t in r['label'] for t in ('요청','부탁'))]
    return {
        'status': 'structural_inventory_not_linguistic_validation',
        'scope_policy': {'core': 'ending 종류, 어미 개념, 절 종결/연결/질문 적용 위치, 비어휘 기록의 문장기능 분류의 합집합',
                         'support': '활용·음운 종류 및 높임/시제/양태/보조용언/인용/부정 개념, 활용 위치, 어미 관련 명시 제목',
                         'limitation': '331건 모두 선별했으나 선택 기준 밖에도 간접 관련 지식이 있을 수 있음. 모든 원문의 미작성 지식을 탐지한 결과가 아님.'},
        'summary': summary, 'whole_graph_integrity': integrity, 'function_routes': routes,
        'request_function': {'dedicated_request_concept_present': any(x in nodes for x in ('concept:REQUEST','concept:REQUESTIVE')),
                             'request_labeled_record_ids': request_ids,
                             'note': '요청 제목이 없다고 요청 의미가 없다는 뜻은 아님. 문장 형식과 발화 의도를 분리한 분류가 필요.'},
        'records': inventories,
        'limitations': ['관계의 부재를 오류로 단정하지 않음. 기본형·배경 설명에는 일부 관계가 불필요할 수 있음.',
                       'realizes 직접 경로 부재는 다른 구성/해석/변이 경로까지 없다는 뜻이 아님.',
                       '조건 필드 출현은 원문 조건 전체의 구조화나 조건 결합의 정확성을 보증하지 않음.',
                       '문헌 연결·출처·같은 철자 공유를 자유 치환/조건 상속으로 해석하지 않음.'],
    }


def audit():
    records = [json.loads(line) for line in (BASE / "records.jsonl").read_text().splitlines() if line.strip()]
    raw_graph = (BASE / "grammar.graph.json").read_bytes()
    graph = json.loads(raw_graph)
    integration = json.loads((BASE / "integration.json").read_text())
    progress = json.loads((BASE / "progress.json").read_text())
    by_id = {r["id"]: r for r in records}
    used_forms = {endpoint for e in graph["edges"]
                  if "assertion_id" in e["properties"] or "integration_id" in e["properties"]
                  for endpoint in (e["source"], e["target"])}
    disconnected_forms = []
    meaning_only = []
    for r in records:
        k = r["knowledge"]
        for f in k["forms"]:
            if r["id"] + ":" + f["key"] not in used_forms:
                disconnected_forms.append({"record_id": r["id"], "form_key": f["key"], "text": f["text"]})
        for i, relation in enumerate(k["relations"], 1):
            fields = {c["field"] for side in ("all", "any") for c in relation["conditions"][side]}
            if fields == {"meaning"}:
                meaning_only.append(r["id"] + ":A" + str(i))
    sections = []
    for source in integration["processing_inventory"]["sources"]:
        for section in source["sections"]:
            lo, hi = section["pages"]
            rows = [r for r in records if r["source_id"] == source["source_id"] and
                    any(lo <= e["page"] <= hi for e in r["knowledge"]["evidence"])]
            sections.append({"source_id": source["source_id"], **section,
                             "record_ids": [r["id"] for r in rows],
                             "exhaustive_statement_adjudication": False,
                             "note": "구간에 근거를 둔 기록 목록이며 모든 설명의 전수 판정 완료가 아님"})
    links = []
    for link in integration["links"]:
        left = by_id[link["from"].split(":")[0]]
        right = by_id[link["to"].split(":")[0]]
        links.append({**link, "cross_source": left["source_id"] != right["source_id"],
                      "endpoint_needs_review": any(r["review"]["source_fidelity"] == "needs_review" for r in (left, right))})
    return {"status": "partial_authoring_not_full_completion", "graph_sha256": hashlib.sha256(raw_graph).hexdigest(),
            "records": len(records), "by_source": dict(Counter(r["source_id"] for r in records)),
            "nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
            "semantic_edges": sum("assertion_id" in e["properties"] for e in graph["edges"]),
            "integration_edges": len(links), "cross_source_links": sum(l["cross_source"] for l in links),
            "held_links": sum(l["status"] == "held_scope_tension" or l["endpoint_needs_review"] for l in links),
            "records_needing_review": [r["id"] for r in records if r["review"]["source_fidelity"] == "needs_review"],
            "forms_without_semantic_or_integration_edge": disconnected_forms,
            "meaning_only_condition_assertions": meaning_only,
            "null_example_records": [r["id"] for r in records if not r["knowledge"]["illustrative_examples"]],
            "section_inventory": sections, "integration_links": links, "issues": integration["issues"],
            "rejected_links": integration.get("review_rejected_links", []),
            "page_status_counts": progress["page_status_counts"],
            "ending_connections": audit_ending_connections(records, graph),
            "function_route_review": integration.get("function_route_review"),
            "condition_exception_review": integration.get("condition_exception_review"),
            "ending_expansion_review": integration.get("ending_expansion_review")}


def render_ending_connections(result):
    a = result['ending_connections']; s = a['summary']; tiers = s['tiers']
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['## 어미 관련 전체 기록의 연결 현황 — 2026-09-23', '',
             f"전체 {s['all_records_screened']}건을 선별했다. 직접 관련 {tiers['core']}건과 활용·높임·음운 등 보조 {tiers['support']}건, 합계 {s['selected_records']}건을 구조 점검했다. 나머지 {tiers['outside_selected_scope']}건도 제외 목록과 이유를 JSON에 남겼다. 특정 개발 문장이나 정답 어미 목록으로 대상을 고르지 않았다.", '',
             '직접 관련은 ending 종류뿐 아니라 어미 개념·절 종결/연결/질문 위치·문장 기능 분류를 포함한다. 활용표처럼 ENDING 개념을 포함한 기록도 여기에 들어간다. 보조 범위는 넓게 잡아 음운 기록 전체 등을 포함한다. 이 분류는 진단을 위한 선택 기준이며 원문의 미작성 지식까지 모두 찾았다는 뜻이 아니다.', '',
             '### 끊어진 참조와 용법 조회의 공백을 구별', '',
             '| 점검 항목 | 결과 |', '|---|---:|']
    labels = {'duplicate_node_ids':'중복 노드 ID', 'duplicate_edge_ids':'중복 관계 ID',
              'dangling_edges':'존재하지 않는 노드를 가리키는 관계', 'isolated_node_ids':'어떤 관계에도 참여하지 않는 노드',
              'condition_edge_mismatches':'저장된 조건과 조건 노드 연결의 불일치',
              'assertion_link_errors':'진술의 주체·대상·적용 위치·근거 참조 이상'}
    lines += [f"| {labels[k]} | {v} |" for k,v in s['integrity_issue_counts'].items()]
    lines += [f"| 어미 관련 표현 중 의미·통합 관계에 전혀 참여하지 않는 표현 | {s['selected_unconnected_forms']} |", '',
              '**참조 구조가 정상이어도 입력에서 필요한 용법으로 이동하는 경로는 부족할 수 있다.** 아래는 직접 realizes 경로 집계다. 원문의 의미적 정확성이나 후보 적용 가능성 점수가 아니다.', '',
              '| 기능 | 해당 분류 또는 기능 관계가 있는 기록 | 기능 → 용법 직접 연결 | 종결 위치까지 명시된 직접 연결 | 분류는 있으나 해당 기능 직접 연결 없음 |',
              '|---|---:|---:|---:|---:|']
    for label, v in a['function_routes'].items():
        lines.append(f"| {label} | {len(v['classified_or_realized_record_ids'])} | {len(v['direct_realizes_record_ids'])} | {len(v['direct_final_ending_record_ids'])} | {len(v['classified_without_direct_function_route'])} |")
    lines += ['', '종결 위치를 명시하지 않았다고 모두 오류는 아니다. 활용·배경·질문 해석 기록에는 다른 적용 위치가 적합할 수 있다. 직접 연결이 없어도 결합→실현형→해석 경로가 있는 기록은 해당 경로를 따라가도록 조회기를 보완할 대상이다.', '',
              '부탁·요청: 전용 REQUEST/REQUESTIVE 개념 노드 ' + ('있음' if a['request_function']['dedicated_request_concept_present'] else '없음') + '. 요청이라는 제목이 있는 기록은 ' + ', '.join(a['request_function']['request_labeled_record_ids']) + '이다. 요청 의도와 의문/명령 형식은 구별한다. 모든 요청 표현의 경로가 완성됐다는 뜻은 아니다.', '',
              '### 조건·실현형·기록 간 연결', '',
              f"- 선택 범위의 관계 진술 {s['selected_assertions']}개 중 {s['selected_meaning_only_assertions']}개는 조건이 자유 서술형 meaning 하나에만 있다({s['selected_records_with_meaning_only_assertions']}개 기록). 이는 설명이 없다는 뜻이 아니라 입력 분석값과 비교할 구조화가 부족하다는 진단이다.",
              f"- 직접 관련 {tiers['core']}건 중 realizes가 전혀 없는 기록은 {s['core_records_without_any_realizes']}건이며 그중 {s['core_records_without_realizes_but_with_interpretation']}건에는 has_interpretation이 있다. 활용표와 배경 설명도 포함되므로 전부 기능 관계를 추가할 대상으로 세지 않는다.",
              f"- 직접 관련 기록 중 명시적 speech_level 조건은 {s['core_condition_field_record_counts'].get('speech_level',0)}건, prefinal_profile 조건은 {s['core_condition_field_record_counts'].get('prefinal_profile',0)}건이다. 다른 필드·구성 관계·본문 설명에 있는 정보를 포함한 완전한 높임/선어말 기술 수가 아니다.",
              f"- 직접 관련 기록 중 has_surface_form 관계가 있는 기록은 {s['core_records_with_surface_relation']}건이다. 기본형 하나로 충분한 기록에도 실현형 관계를 억지로 만들지는 않는다.",
              f"- 직접 관련 {tiers['core']}건 중 통합 또는 qualifies 기록 간 연결이 없는 기록은 {s['core_records_without_interrecord_links']}건이다. 연결 수를 늘리는 것 자체가 목표가 아니며 기본 규칙–예외–활용표 등 필요한 연결을 골라야 한다.",
              f"- 선택 범위에서 원문 해석 재검토 상태인 기록은 {s['selected_source_review_pending']}건이다. 그래프 연결 개선만으로 해소되지 않는다.", '',
              '### 최초 점검에서 확인한 사례와 이번 기능 연결 수정 후 상태', '',
              '| 기록 | 확인 내용 | 필요한 대응 |', '|---|---|---|',
              '| H005~H012: 의문형+요/예 | 결합·실현형·높임 해석에 더해 결합 후 F3 용법의 질문 기능 연결을 추가했다. | 첨사 결합과 목표 높임의 조건 평가를 연결 |',
              '| H022 / H023: 니더·이더 기본 조건 / 어휘별 예외 | 기본 분포와 예외·병존형 및 니더 배제를 연결했다. | 어휘·품사 조건을 독립 평가하고 현대 적합성은 별도 검토 |',
              '| Q011: -(으)ㄹ까 계열 | 변이 관계와 질문 유형 조건은 있지만 기능 realizes 경로는 없다. 원문 검토 보류도 있다. | 변이 관계를 함수처럼 적용하지 말고 기능·조건을 근거와 함께 보완 |',
              '| Y010: 상대 의도 질문 -거로 | INTENTION 관계를 유지하고 질문 기능 관계도 추가했다. | 의도를 묻는 경우에 한정하는 meaning 조건을 평가 |',
              '| J031: 도가·도고·다고 요청 | 요청 해석은 has_interpretation의 텍스트 값으로 저장되어 있다. | 부탁/요청 의도와 어휘 제한을 구조화 |',
              '| H005의 gaps | 다른 일곱 구성이 이미 작성돼 있어 “하나만 작성”이라는 과거 공백 문구를 제거했다. | 전체 문장 결합·현대 자연스러움 미검증은 유지 |', '',
              '최초 점검 후 네 문장 기능의 경로를 원문과 대조해 보완했다. 아래 기능 연결 수정 내역을 함께 본다. 기본 조건–예외 연결과 조건 실행의 완성은 별도 남은 작업이다.', '',
              '<details>', '<summary>어미 관련 기록 전체 목록 펼치기</summary>', '',
              '표의 “기능”은 직접 realizes 관계 수, “해석”은 has_interpretation 관계 수다. 0은 무조건 지식 누락을 뜻하지 않는다. 조건·예외·근거·선택 사유의 상세는 JSON의 ending_connections.records에 있다.', '',
              '| ID | 구분 | 기록 | 기능 / 해석 관계 | 조건 필드 | 통합 / 기록 연결 수 | 원문 검토 | 남은 작업 |',
              '|---|---|---|---:|---|---:|---|---|']
    for r in a['records']:
        if r['tier'] == 'outside_selected_scope': continue
        lines.append('| ' + ' | '.join(map(cell, [r['record_id'], '직접' if r['tier']=='core' else '보조',
            r['label'], f"{len(r['realizes_assertions'])} / {len(r['interpretation_assertions'])}",
            ', '.join(r['condition_fields']) or '명시 없음',
            f"{len(r['integration_ids'])} / {len(r['record_qualification_edge_ids'])}", r['source_review'],
            ', '.join(r['condition_work']['next_actions'])])) + ' |')
    lines += ['', '</details>', '']
    return lines


def render(result):
    def cell(v):
        return str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["# 전체 작성·연결 점검 결과", "", "기준: 저장된 현행 그래프(해시는 JSON 결과에 기록). 이 파일은 `authoring_audit.py --save`로 재생성한다.", "",
             "## 완료와 미완료", "",
             "원문 전 범위의 검토·처리방침과 개별 문법 설명의 전수 작성은 다르다. **현재 전수 작성·판정 완료를 입증하지 못했으며, 전체 완성본이 아니다.**", "",
             f"이번 요청 전 147건에서 {result['records']}건으로 증가했다. 독립 검토·생성 승인은 여전히 0건이다.", "",
             f"그래프 {result['nodes']:,}노드·{result['edges']:,}엣지 중 문법 진술 {result['semantic_edges']}개, 통합·대조 {result['integration_edges']}개다. 후자의 교차 문헌 연결은 {result['cross_source_links']}개다.", "",
             "## 작성본에서 발견한 공백", "",
             f"- 근거 해석 재검토 기록: {len(result['records_needing_review'])}건.",
             f"- 기능·결합·통합 엣지에 아직 참여하지 않는 표현 노드: {len(result['forms_without_semantic_or_integration_edge'])}개. 목록에 적었다고 용법 연결까지 끝난 것은 아니다.",
             f"- 조건이 자유 서술형 meaning에만 있는 관계: {len(result['meaning_only_condition_assertions'])}개. 모두 오류라는 뜻은 아니지만 자동 입력과 조건 판정의 연결을 완료한 것으로 볼 수 없다.",
             f"- 설명용 예문이 null인 기록: {len(result['null_example_records'])}건. 불확실한 예문을 만들어 채우지 않았다.",
             f"- 충돌 또는 끝점 기록의 재검토 상태 때문에 경로 반환을 보류하는 통합 관계: {result['held_links']}개.", "",
             "구체적인 ID와 쪽 구간별 작성 기록은 [authoring_audit.results.json](authoring_audit.results.json)에 있다. 이 수치를 자연스러움·정확성·원문 포괄률로 해석하지 않는다.", "",
             "## 자료별 작성", "", "| 자료 ID | 기록 수 |", "|---|---:|"]
    lines += [f"| {sid} | {n} |" for sid, n in result["by_source"].items()]
    lines += [""] + render_ending_connections(result)
    review = result.get("function_route_review")
    if review:
        lines += ["## 평서·질문·명령·청유 기능 연결 수정", "",
                  "수정 원본과 보류 판단은 integration.json의 function_route_review에 기록했다. 아래 전후 수치는 해당 기능의 직접 realizes 관계가 있는 기록 수다. 같은 기록이 여러 기능에 포함될 수 있다.", "",
                  "| 기능 | 수정 전 | 수정 후 |", "|---|---:|---:|"]
        for name, before in review["before_function_routes"].items():
            after = result["ending_connections"]["function_routes"][name]
            lines.append(f"| {name} | {len(before['direct_realizes_record_ids'])} | {len(after['direct_realizes_record_ids'])} |")
        lines += ["", "기능에서 접근 가능해졌다는 뜻이며 높임·지역·시제·현대 자연스러움이 모두 검증됐다는 뜻은 아니다. 원문 가설과 예문 한정을 보존했고, 입력 분석이나 생성 결과를 새로 만들지 않았다.", "",
                  "| 기록 | 처리 | 새 관계 / 표현 노드 | 이유 |", "|---|---|---|---|"]
        for row in review["decisions"]:
            lines.append("| " + " | ".join(map(cell, [row["record_id"],row["decision"],
                f"{len(row['assertions'])} / {len(row['forms'])}",row["reason"]])) + " |")
        lines.append("")
    condition_review = result.get("condition_exception_review")
    if condition_review:
        lines += ["## 조건 구조화·예외 연결 1차 — 2026-09-28", "",
                  "범위: 니더/이더 H022/H023, 의문형+요/예 H005~H012, 나/노·가/고 Q001~Q007. 총 17개 기록에 조건 공급원을 구분하고 33개 근거 있는 통합 관계를 추가했다. 모든 어미 조건을 완성한 작업은 아니다.", "",
                  "| 묶음 | 수정한 내용 | 남은 제한 |", "|---|---|---|",
                  "| 니더/이더 | 품사와 실제 결합 지점의 말음을 구분. 맑다/궁금하다의 니더 배제 및 좋다/낫다 등의 관찰형을 기본 용법에서 조회 | 사전형 받침을 활용 후보의 말음으로 복사하면 안 됨. 예외 목록 전체 작성·현대 적합성은 미완료 |",
                  "| 의문형+요/예 | 후보 내부 첨사, 질문 유형, 목표 해요체 수준 높임을 구분. 기저형 연결에서 하게체 조건을 상속하지 않음 | 기저형 분류와 결합 설명의 연결은 작성자 해석. 자동 분석·현대 사용 적합성은 미검증 |",
                  "| 나/노·가/고 | 이미 구조화된 질문/서술부/선어말 조건의 값 공급원을 명시. 기본형에서 변경형 및 충돌 기록으로 이동 | 시 단독 원문 충돌은 needs_review 및 보류 연결 유지 |", "",
                  "입력 관찰(input), 후보 내부(candidate), 목표 정책(target)은 application.feature_sources에 명시하며 requires_analysis_of 관계에도 value_source로 남긴다. 값을 모르면 unknown이다. 지정된 조건의 요구값을 역으로 후보값에 채워 넣지 않는다.", "",
                  "진단 재실행: `/usr/bin/python3 current_kg/grammar/query_review.py --condition-cases --save`. 저장 결과는 [query_review.results.json](query_review.results.json). 연구자가 지정한 특징 조합 9건이며 번역 결과나 자연스러움 평가가 아니다.", "",
                  "맑다에서는 기본 분포 match와 예외 배제를 함께 확인한다. 좋다의 이더형은 기본 분포 mismatch라도 예외 관찰을 남긴다. 계사 과거의 기본형 mismatch 뒤 변경형 match를 조회하며, 시 관련 충돌은 보류로 남는다. 이는 진단 확인이며 일반 생성 후보 순위화·최종 선택은 아직 구현하지 않았다.", ""]
    expansion = result.get('ending_expansion_review')
    if expansion:
        s = result['ending_connections']['summary']
        lines += ['## 전체 어미 범위 조건·예외 보완 확대 — 2026-09-28', '',
                  f"기존 어미 관련 {s['selected_records']}건 모두에 설명형 조건, 값 공급원, 기록 간 연결, 원문 해석, 공백별 작업 상태를 남겼다. 위 전체 목록의 ‘남은 작업’ 열과 JSON의 condition_work가 같은 장부다. 일괄 완료 판정은 하지 않는다.", '',
                  f"이번 원문 재대조로 {len(expansion['manual_source_rechecked_records'])}건의 조건을 보완했다: " + ', '.join(expansion['manual_source_rechecked_records']) + '.', '',
                  f"기존 계약에서 공급원이 명확한 관계 {len(expansion['provider_migrated_assertions'])}개에 input/candidate/target를 명시했다. 어휘·어간의 해석이 필요한 필드는 자동 이관하지 않았다. 남은 공급원 확인 대상은 {s['selected_pending_binding_assertions']}개 관계다. 이것을 원문 재검토 건수로 세지 않는다.", '',
                  f"의미 설명의 분해가 남은 관계는 {s['selected_pending_semantic_assertions']}개다. meaning만 있는 관계 수와 달리 다른 조건과 함께 남은 설명도 포함한다.", '',
                  '| 보완한 묶음 | 실제 변경 |', '|---|---|',
                  '| 니더·니껴/니꺼·디껴/디꺼 | 평서/의문·목표 높임·선행 형태를 분리. 회상 의미와 희소 결합의 한계는 보존 |',
                  '| 이더·리더·시더·ㄹ시더 | 품사·계사·화자 의도·약속을 구별. 문헌 간 말음/매개모음 설명 차이는 보류 연결 |',
                  '| 이소·소·세·이시더/시더 | 명령/청유, 청자 단독/공동 행동, 동사 직접 결합을 구분. 존재사 허용 각주도 별도 조회 |',
                  '| 도가/도고/다고·온나·래 | 요청 기능 노드와 어휘·후보 구성 조건, 활용표 참조. 다른 동사로 일반화하지 않음 |',
                  '| 거로 | 상대 의도 질문·화자 의도 진술·알아맞히기 질문 금지를 분리하고 금지를 함께 조회 |',
                  '| 함양 명령·청유·평서·감탄 | 문헌의 상대대우 정도를 목표 조건으로 분리. 사용 감소·세대 관찰을 현대의 절대 금지로 바꾸지 않음 |',
                  '| 먼·걸랑·ㅁ서·도·다·아서/어서·니·러·ㄹ수록·듯이 | 조건·원인·양보·동시·전환·이동 목적·정도·방식의 절 관계를 분리 |',
                  '| 서부 하소체 요/소 | 실제 결합 지점의 모음/ㄹ/기타 자음을 구별. 목표 지역·어체·문장 유형을 함께 확인 |',
                  '| 자문 고/꼬 및 느는고 | 상대 응답 요구와 자기 질문을 구별하고 머꼬 중의성 설명은 보존 |',
                  '| 는교 | 기본 기능에서 부산 하이소체 격식 장면의 자제 제약을 함께 조회 |', '',
                  '원문을 재확인한 쪽과 추가 관계 ID는 integration.json의 ending_expansion_review에 기록했다. query_review --condition-cases는 두 차수의 수동 특징 조합을 함께 저장한다. 자동 입력 분석·번역 재생성·자연스러움 검증은 아니다.', '']
    lines += ["", "## 모든 통합·대조 관계의 이유와 한계", "",
              "same_usage_candidate는 동일성 확정이 아니며, shares_function_with는 상호 치환 가능성을 뜻하지 않는다. 위키 네 문서를 독립 근거 네 개로 세지 않는다.", "",
              "| ID | 출발 → 관계 → 도착 | 연결 이유 | 제한·보류 |", "|---|---|---|---|"]
    for l in result["integration_links"]:
        state = " / 경로 보류" if l["status"] == "held_scope_tension" or l["endpoint_needs_review"] else " / 작성자 제안"
        lines.append("| " + " | ".join(map(cell, [l["id"], f"{l['from']} → {l['relation']} → {l['to']}", l["reason"], l["limits"] + state])) + " |")
    lines += ["", "### 검토 후 채택하지 않은 연결", ""]
    lines += [f"- {l['id']}: {l['reason']}" for l in result["rejected_links"]]
    lines += ["", "## 알려진 문제의 처리 상태", "", "| 문제 | 대응 | 상태 |", "|---|---|---|"]
    lines += ["| " + " | ".join(map(cell, [i["problem"], i["action"], i["status"]])) + " |" for i in result["issues"]]
    lines += ["", "## 남은 작업 — 이 보고로 대체하지 않음", "",
              "1. 각 원문의 개별 설명·표 항목과 작성 기록을 대조해 누락을 작성하거나 근거 있는 배경/보류/제외 판정을 남긴다. 구간 단위 장부만으로 전수 판정을 선언하지 않는다.",
              "2. 설명문에만 남은 용법별 결합 조건을 관계로 연결하고, 같은 기록 안에 나열만 된 표현을 필요한 경우 분리한다. 모델 지식으로 보완하는 가설은 원문 근거와 구별하여 기록한다.",
              "3. 보류된 원문 충돌·희소 예·재인용·글자 및 음성 문제를 해결 가능한 범위에서 검토한다. 독립 화자 판단이 필요한 항목은 계속 미승인으로 둔다.",
              "4. 전체 지식의 독립 검토는 미실시다. 수동 분석에 따른 개발용 생성 비교와 일부 조회 진단을 수행했으나 자동 입력 분석·본 실험은 미완료다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.save:
        (BASE / "authoring_audit.results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        (BASE / "작성검토.md").write_text(render(result))
    print(json.dumps({k: v for k, v in result.items() if k in {"status", "records", "nodes", "edges", "semantic_edges", "integration_edges", "cross_source_links", "held_links", "by_source", "page_status_counts"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
