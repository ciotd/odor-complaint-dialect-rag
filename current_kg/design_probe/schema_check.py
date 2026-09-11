"""Validate the explicitly supported JSON Schema subset without dependencies.

This is not a general JSON Schema implementation. Unknown validation keywords
are errors, so an expanded schema cannot silently skip new constraints.
"""
import json
from pathlib import Path

SUPPORTED = {'$schema', '$defs', '$ref', 'title', 'description', 'type', 'properties',
             'required', 'additionalProperties', 'items', 'minItems', 'minLength',
             'minimum', 'anyOf', 'enum', 'const'}


def check_schema(schema):
    unknown = set(schema) - SUPPORTED
    if unknown:
        raise ValueError('unsupported schema keywords: ' + str(unknown))
    for key in ('$defs', 'properties'):
        for child in schema.get(key, {}).values():
            check_schema(child)
    for child in schema.get('anyOf', []):
        check_schema(child)
    if 'items' in schema:
        check_schema(schema['items'])


def validate_schema(value, schema, root=None, path='$'):
    if root is None:
        root = schema
        check_schema(schema)
    if '$ref' in schema:
        name = schema['$ref']
        if not name.startswith('#/$defs/'):
            raise ValueError('only local $defs refs supported')
        validate_schema(value, root['$defs'][name.split('/')[-1]], root, path)
    if 'anyOf' in schema:
        failures = []
        for option in schema['anyOf']:
            try:
                validate_schema(value, option, root, path)
            except ValueError as error:
                failures.append(str(error))
            else:
                break
        else:
            raise ValueError(path + ': no anyOf option matched: ' + '; '.join(failures))
    types = {'object': lambda v: type(v) is dict, 'array': lambda v: type(v) is list,
             'string': lambda v: type(v) is str, 'integer': lambda v: type(v) is int,
             'number': lambda v: type(v) in (int, float), 'boolean': lambda v: type(v) is bool,
             'null': lambda v: v is None}
    if 'type' in schema and not types[schema['type']](value):
        raise ValueError(path + ': wrong type, expected ' + schema['type'])
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        raise ValueError(path + ': const mismatch')
    if 'enum' in schema and not any(type(value) is type(v) and value == v for v in schema['enum']):
        raise ValueError(path + ': enum mismatch')
    if type(value) is dict:
        if set(schema.get('required', [])) - value.keys():
            raise ValueError(path + ': missing fields')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False and value.keys() - props.keys():
            raise ValueError(path + ': unexpected fields')
        for key in value.keys() & props.keys():
            validate_schema(value[key], props[key], root, path + '.' + key)
    if type(value) is list:
        if len(value) < schema.get('minItems', 0):
            raise ValueError(path + ': too few items')
        if 'items' in schema:
            for i, item in enumerate(value):
                validate_schema(item, schema['items'], root, path + '[' + str(i) + ']')
    if type(value) is str and len(value) < schema.get('minLength', 0):
        raise ValueError(path + ': string too short')
    if type(value) in (int, float) and 'minimum' in schema and value < schema['minimum']:
        raise ValueError(path + ': below minimum')


def validate_bundle(data):
    schema = json.loads(Path(__file__).with_name('claim_bundle.schema.json').read_text())
    validate_schema(data, schema)
