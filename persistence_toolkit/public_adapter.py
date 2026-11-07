"""Strict conversion of a serialized schema-1.0 AuditResult (engine v0.1.2 or v0.1.3) to a comparison input.

All numeric quantities are extracted from the source result, never accepted as
separate user-supplied metrics. AuditResult itself is not recomputed.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from pathlib import Path

REQUIRED_RESULT_BLOCKS = ("population", "counts", "estimates", "reference", "provenance")
class AuditSchemaError(ValueError): pass

def from_v012_audit_result(result, *, model_instance, input_manifest, transaction_metrics=None):
    """Accept an AuditResult.to_dict() mapping or an object with to_dict().

    Strictly uses original schema-1.0 scientific result fields; metadata identities
    remain caller claims until independently fingerprinted against source data.
    """
    if not isinstance(result, dict):
        result=result.to_dict()
    if not isinstance(result, dict) or result.get('schema_version')!='1.0':
        raise AuditSchemaError('Expected public AuditResult v1.0 serialization')
    for k in REQUIRED_RESULT_BLOCKS:
        if not isinstance(result.get(k), dict):
            raise AuditSchemaError('Missing AuditResult block: '+k)
    p=result['population']; c=result['counts'];e=result['estimates'];ref=result['reference']
    prov=result['provenance'];status=result.get('status')
    if status not in ('ESTIMABLE','NOT_ESTIMABLE'):
        raise AuditSchemaError('Invalid AuditResult status')
    for k in ('eligible_entity_count','exposure_min','exposure_max','legitimate_event_count'):
        if k not in p:raise AuditSchemaError('Missing population field '+k)
    for k in ('false_positive_event_count','repeated_fp_entity_count'):
        if k not in c:raise AuditSchemaError('Missing count field '+k)
    if status=='ESTIMABLE':
        if ref.get('status')!='COMPLETED':raise AuditSchemaError('Reference not completed')
        for k in ('observed_repeat_fp_proportion','reference_expected_repeat_fp_proportion','excess_repeat_fp_percentage_points'):
            if e.get(k) is None:raise AuditSchemaError('Missing estimate '+k)
    else:
        if result.get('reason')!='zero_eligible_entities':raise AuditSchemaError('Unexpected NOT_ESTIMABLE reason')
    # Provenance field consistency guards. The source result is not editable here.
    if prov.get('result_schema_version')!='1.0':raise AuditSchemaError('Provenance/result schema mismatch')
    exp=input_manifest.get('exposure_bounds')
    if exp is not None and exp != {'min':p['exposure_min'],'max':p['exposure_max']}:
        raise AuditSchemaError('Manifest exposure differs from source result')
    if input_manifest.get('false_positive_budget') is not None and input_manifest['false_positive_budget'] != c['false_positive_event_count']:
        raise AuditSchemaError('Manifest flag count differs from source result')
    if status=='ESTIMABLE':
        metric={'status':status,'false_positive_count':c['false_positive_event_count'],
          'eligible_entity_count':p['eligible_entity_count'],
          'repeated_fp_entity_count':c['repeated_fp_entity_count'],
          'observed_repeat_fp_proportion':e['observed_repeat_fp_proportion'],
          'reference_expected_repeat_fp_proportion':e['reference_expected_repeat_fp_proportion'],
          'excess_repeat_fp_percentage_points':e['excess_repeat_fp_percentage_points']}
    else:
        metric={'status':status,'reason':result['reason'],
          'false_positive_count':c['false_positive_event_count'],
          'eligible_entity_count':p['eligible_entity_count'],
          'repeated_fp_entity_count':c['repeated_fp_entity_count']}
    if transaction_metrics:
        keys=('pr_auc','roc_auc','metric_population','metric_source')
        for k in keys:
            if k in transaction_metrics:metric[k]=transaction_metrics[k]
    report={'model_instance':copy.deepcopy(model_instance),
            'audit_input_manifest':copy.deepcopy(input_manifest),
            'audit_result':copy.deepcopy(result),'reported_metrics':metric}
    from .comparison import validate
    validate(report)
    return report

def fingerprint_public_frame(rows, *, event_key='event_id', entity_key='entity_id',
                             label_key='legitimate', context_key='final_stratum'):
    """Canonical row-order-invariant semantic audit-input fingerprint.

    Real event rows, not model scores or FP flags. Caller must use the SAME
    actual audit-input frame to establish comparable populations/context.
    All values must be JSON-compatible scalar identity fields.
    """
    if hasattr(rows,'to_dict'):rows=rows.to_dict(orient='records')
    cols=(event_key,entity_key,label_key,context_key)
    tuples=[]; ids=set()
    for row in rows:
        encoded=[row[k] for k in cols]
        for val in encoded:
            if val is None or not isinstance(val,(str,int,float,bool)) or (isinstance(val,float) and not math.isfinite(val)):
                raise AuditSchemaError('Invalid fingerprint field')
        key=json.dumps(encoded[0],ensure_ascii=False,sort_keys=True)
        if key in ids:raise AuditSchemaError('Duplicate event IDs')
        ids.add(key);tuples.append(encoded)
    tuples.sort(key=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True))
    raw=json.dumps(tuples,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')
    return hashlib.sha256(raw).hexdigest()
