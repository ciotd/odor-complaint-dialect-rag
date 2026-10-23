"""Validate analysis instances against KG vocabulary, then derive target hypotheses.

This is an input boundary, not a Korean parser. Version 1.0 is read through
an explicit compatibility migration; new producers must emit version 1.1.
"""
from copy import deepcopy
import json
from pathlib import Path

CONTRACT_PATH = Path(__file__).resolve().parents[1] / 'grammar/analysis_contract.json'
POLICY_ID = 'development_politeness_preservation_v1'
STYLE_TARGETS = {
    'polite': [{'speech_level': 'HAEYO_LEVEL'}, {'speech_level': 'HAISOCHE'},
               {'addressee_treatment': 'informal_high'}],
    'non_polite': [{'speech_level': 'HAECHE'}, {'speech_level': 'HAERACHE'},
                   {'addressee_treatment': 'informal_low'}],
    'unknown': [],
}
TARGET_FIELDS = {'speech_level', 'addressee_treatment', 'register', 'region', 'interaction_tone'}
CANDIDATE_FIELDS = {'preceding_form', 'following_form', 'prefinal_profile',
                    'attachment_coda', 'attachment_coda_class'}
FUNCTIONS = {'declarative': 'DECLARATIVE', 'interrogative': 'INTERROGATIVE',
             'imperative': 'IMPERATIVE', 'hortative': 'HORTATIVE', 'exclamative': 'EXCLAMATIVE'}
CONNECTIVES = {'condition': 'CONDITION', 'cause': 'CAUSE',
               'purpose_intention': 'PURPOSE', 'movement_purpose': 'PURPOSE',
               'concession': 'CONCESSION', 'contrast': 'CONCESSION',
               'retrospective_sequence': 'CONNECTIVE_ENDING',
               'retrospective_contrast': 'CONNECTIVE_ENDING',
               'interruption_transition': 'CONNECTIVE_ENDING', 'addition': 'COORDINATION'}
CLAUSE_FIELDS = {'clause_id', 'predicate_complex_id', 'text', 'span', 'role', 'features',
                 'preserved_candidate_features', 'observed_politeness',
                 'observed_subject_honorific', 'tense_or_modality', 'scope_note',
                 'candidate_analysis_limit', 'annotations'}
LEGACY_NOTES = {'subject_honorific': {'lexical_honorific'},
                'modality': {'tentative_schedule_question'}}


def fail(path, message):
    raise ValueError(f'{path}: {message}')


def obj(value, path, allowed=None):
    if not isinstance(value, dict):
        fail(path, 'expected object')
    if allowed is not None and set(value) - allowed:
        fail(path, f'unrecognized fields: {sorted(set(value) - allowed)}')


def string(value, path):
    if not isinstance(value, str) or not value.strip():
        fail(path, 'expected non-empty string')


def normalize_analysis(analysis):
    """Return validated 1.1 input. Never mutate or silently repair source values.

    Missing optional features / explicit null mean unknown. Candidate assumptions
    stay separate from input observations; notes never become KG conditions.
    """
    obj(analysis, 'analysis', {'version', 'origin', 'status', 'policy', 'items'})
    version = analysis.get('version')
    if version not in {'1.0', '1.1', '1.2'}:
        fail('analysis.version', 'supported versions: 1.0 (legacy), 1.1, 1.2')
    result = deepcopy(analysis)
    for key in ('origin', 'status'):
        string(result.get(key), 'analysis.' + key)
    policy = result.get('policy')
    obj(policy, 'analysis.policy', {'no_seed_assertions_or_target_dialect_forms',
        'target_region', 'style_policy', 'candidate_features', 'selection', 'style_policy_id'})
    if policy.get('target_region') is not None:
        fail('analysis.policy.target_region', 'regional filtering is not implemented')
    if version in {'1.1', '1.2'} and policy.get('style_policy_id') != POLICY_ID:
        fail('analysis.policy.style_policy_id', 'unsupported or missing target policy')
    if version == '1.0' and policy.get('style_policy_id', POLICY_ID) != POLICY_ID:
        fail('analysis.policy.style_policy_id', 'unsupported target policy')
    for key in ('style_policy', 'candidate_features', 'selection'):
        string(policy.get(key), 'analysis.policy.' + key)
    policy['style_policy_id'] = POLICY_ID
    items = result.get('items')
    if not isinstance(items, list) or not items:
        fail('analysis.items', 'expected non-empty list')
    features = json.loads(CONTRACT_PATH.read_text())['features']
    item_ids, clause_ids, predicate_ids = set(), set(), set()
    for item in items:
        obj(item, 'item', {'id', 'input', 'preservation_note', 'unqueried_structure_note', 'clauses', 'source_units'})
        for key in ('id', 'input', 'preservation_note', 'unqueried_structure_note'):
            string(item.get(key), 'item.' + key)
        if item['id'] in item_ids:
            fail(item['id'], 'duplicate item ID')
        item_ids.add(item['id'])
        if 'source_units' in item:
            validate_source_units(item['input'], item['source_units'])
        clauses = item.get('clauses')
        if not isinstance(clauses, list) or not clauses:
            fail(item['id'], 'expected non-empty clauses')
        for clause in clauses:
            path = f"{item['id']}/{clause.get('clause_id', '?')}" if isinstance(clause, dict) else item['id']
            obj(clause, path, CLAUSE_FIELDS | ({'target_scenarios'} if version == '1.0' else set()))
            for key, used in [('clause_id', clause_ids), ('predicate_complex_id', predicate_ids)]:
                string(clause.get(key), path + '.' + key)
                if clause[key] in used:
                    fail(path, f'duplicate {key}')
                used.add(clause[key])
            string(clause.get('text'), path + '.text')
            span = clause.get('span')
            if (not isinstance(span, list) or len(span) != 2 or
                    any(type(x) is not int for x in span) or
                    not 0 <= span[0] < span[1] <= len(item['input']) or
                    item['input'][span[0]:span[1]] != clause['text']):
                fail(path + '.span', 'must bind exactly to input using Python character offsets')
            if clause.get('role') not in {'main', 'connective'}:
                fail(path + '.role', 'expected main or connective')
            polite = clause.get('observed_politeness')
            if polite not in STYLE_TARGETS:
                fail(path + '.observed_politeness', 'expected polite, non_polite or unknown')
            if version == '1.0':
                if clause.get('target_scenarios') != STYLE_TARGETS[polite]:
                    fail(path + '.target_scenarios', 'legacy targets conflict with observed politeness / policy')
                del clause['target_scenarios']
            notes = clause.setdefault('annotations', {})
            obj(notes, path + '.annotations', set(LEGACY_NOTES))
            for key, value in notes.items():
                string(value, path + '.annotations.' + key)
            for container, allowed in [('features', set(features) - TARGET_FIELDS - CANDIDATE_FIELDS),
                                        ('preserved_candidate_features', CANDIDATE_FIELDS)]:
                values = clause.get(container)
                obj(values, path + '.' + container)
                if version == '1.0' and container == 'features':
                    for key, known_values in LEGACY_NOTES.items():
                        if key in values:
                            if values[key] not in known_values or key in notes:
                                fail(path + '.' + key, 'unsupported or conflicting legacy annotation')
                            notes[key] = values.pop(key)
                for key, value in values.items():
                    if key not in allowed:
                        fail(path + '.' + container, f'unregistered or wrong-source feature: {key}')
                    if value is None:
                        continue
                    string(value, path + '.' + key)
                    if 'values' in features[key] and value not in features[key]['values']:
                        fail(path + '.' + key, f'unknown vocabulary value: {value}')
            for key, allowed in {
                'observed_subject_honorific': {'not_observed', 'si_in_benefactive_auxiliary', 'lexical', 'si', 'unknown'},
                'tense_or_modality': {'present', 'past', 'modal', 'retrospective', 'unknown'},
            }.items():
                if key in clause and clause[key] not in allowed:
                    fail(path + '.' + key, 'unrecognized observation')
            # A known question interpretation cannot accompany a known non-question type.
            observed = clause['features']
            if (observed.get('question_type') is not None and
                    observed.get('sentence_type') not in {None, 'interrogative'}):
                fail(path, 'question_type conflicts with sentence_type')
    result['version'] = '1.2' if any('source_units' in i for i in result['items']) else '1.1'
    return result


def targets_for(clause):
    return deepcopy(STYLE_TARGETS[clause['observed_politeness']])


def route_functions(clause):
    known = clause['features']
    functions = set()
    key, routes = ('clause_relation', CONNECTIVES) if clause['role'] == 'connective' else ('sentence_type', FUNCTIONS)
    primary = routes.get(known.get(key))
    if primary is None:
        return functions, ['missing_or_unsupported_function_route:' + key]
    functions.add(primary)
    if known.get('question_type') in {'polar', 'content'}:
        functions.add('POLAR_QUESTION' if known['question_type'] == 'polar' else 'CONTENT_QUESTION')
    if known.get('speech_act') == 'request':
        functions.add('REQUEST')
    if known.get('speech_act') == 'state_intention':
        functions.add('INTENTION')
    return functions, []


def validate_source_units(sentence, units):
    """Open construction descriptions are retrieval hints, never KG condition values."""
    if not isinstance(units,list) or len(units)>24:
        fail('source_units','expected up to 24 source-bound units')
    ids=set()
    for i,u in enumerate(units):
        obj(u,'source_unit',{'unit_id','text','span','kind','parent_index','meaning','form_queries','semantic_queries','features'})
        features=u.get('features',{})
        obj(features,'source_unit.features',{'clause_relation','quotation_type'})
        vocabulary=json.loads(CONTRACT_PATH.read_text())['features']
        for key,value in features.items():
            if value is not None and value not in vocabulary[key]['values']:
                fail('source_unit.features.'+key,'unknown vocabulary value')
        for k in ['unit_id','text','kind','meaning']:string(u.get(k),'source_unit.'+k)
        if u['unit_id'] in ids:fail('source_unit','duplicate ID')
        ids.add(u['unit_id'])
        span=u.get('span')
        if (not isinstance(span,list) or len(span)!=2 or any(type(x) is not int for x in span)
            or not 0<=span[0]<span[1]<=len(sentence) or sentence[span[0]:span[1]]!=u['text']):
            fail('source_unit.span','must bind exactly to source')
        parent=u.get('parent_index')
        if parent is not None:
            if type(parent) is not int or not 0<=parent<i:fail('source_unit.parent_index','parent must precede child')
            ps=units[parent]['span']
            if not ps[0]<=span[0]<span[1]<=ps[1]:fail('source_unit.parent_index','parent must contain child')
        for key in ['form_queries','semantic_queries']:
            qs=u.get(key)
            if not isinstance(qs,list) or not 1<=len(qs)<=4:fail(key,'expected one to four search hints')
            for q in qs:
                string(q,key)
                if len(q)>240:fail(key,'query too long')
