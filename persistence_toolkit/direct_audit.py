"""Trusted-in-process descriptive comparison using the actual public audit engine.

This function never accepts provenance assertions as proof of source comparability.
Instead it runs both audits on the same user-supplied event frame.  It verifies
shared event/entity/legitimate/context data against the resulting AuditResults.
It cannot establish the truth of ground-truth labels or downstream harm.
"""
from __future__ import annotations
import hashlib
import json
import math
import pandas as pd
from .comparison import compare_reports, _InProcessSourceVerification, _sha, ComparisonInputError
from .public_adapter import from_v012_audit_result, fingerprint_public_frame


def _fingerprint_pairs(rows, columns):
    """Order-invariant digest for restricted public-demo primitive identifiers."""
    records = rows[list(columns)].to_dict(orient='records')
    canonical = []
    for r in records:
        entry=[]
        for name in columns:
            v = r[name]
            if v is None or not isinstance(v, (str,int,float,bool)) or (isinstance(v,float) and not math.isfinite(v)):
                raise ComparisonInputError(f"Unsupported identity/label value in {name}; normalize inputs first")
            entry.append([type(v).__name__,v])
        canonical.append(entry)
    canonical.sort(key=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False))
    return hashlib.sha256(json.dumps(canonical,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def audit_and_compare_shared_frame(
    data: pd.DataFrame,
    *,
    left_flag_col: str,
    right_flag_col: str,
    entity_col: str,
    event_id_col: str,
    final_stratum_col: str,
    legitimate_col: str,
    exposure,
    permutation,
    audit_window: str="not_specified",
    left_instance_id: str="model-A",
    right_instance_id: str="model-B",
):
    """Two REAL public-engine audits on one shared frame followed by comparison.

    Only binary external-flag mode supported in v0.2rc1. No ROC/PR-AUC
    estimation, no threshold tuning, no fraud recall claim.  Flag columns
    are allowed to differ; all common audit columns are identical by design.
    """
    if not isinstance(data,pd.DataFrame) or data.empty:
        raise ComparisonInputError("Nonempty pandas DataFrame required")
    if not data.columns.is_unique:
        raise ComparisonInputError("Duplicate dataframe column labels are not allowed")
    # Snapshot prevents either engine call from changing the source observed by the other.
    data = data.copy(deep=True)
    required=(left_flag_col,right_flag_col,entity_col,event_id_col,final_stratum_col,legitimate_col)
    if any(x not in data.columns for x in required):
        raise ComparisonInputError("Missing required audit input column")
    if len(set((entity_col,event_id_col,final_stratum_col,legitimate_col))) != 4:
        raise ComparisonInputError("Shared audit columns must be distinct")
    if left_flag_col == right_flag_col or left_flag_col in (entity_col,event_id_col,final_stratum_col,legitimate_col) or right_flag_col in (entity_col,event_id_col,final_stratum_col,legitimate_col):
        raise ComparisonInputError("Two distinct model flag columns are required")
    if not data[event_id_col].is_unique or data[event_id_col].isna().any():
        raise ComparisonInputError("Event IDs must be unique and non-null")
    if not set(data[legitimate_col].dropna().tolist()).issubset({0,1}) or data[legitimate_col].isna().any():
        raise ComparisonInputError("legitimate_col must contain nonmissing binary values")
    if data[list((left_flag_col,right_flag_col))].isna().any().any():
        raise ComparisonInputError("Flag columns cannot contain missing values")
    for flag in (left_flag_col,right_flag_col):
        if not set(data[flag].tolist()).issubset({0,1}):
            raise ComparisonInputError("Flag columns must contain binary values")
    if not isinstance(audit_window,str) or not audit_window.strip():
        raise ComparisonInputError("audit_window must be a nonempty descriptive label")

    # Pull the installed v0.1.2 public engine at runtime, not a private copy.
    from fp_persistence import audit

    shared=data[[event_id_col,entity_col,legitimate_col,final_stratum_col]].copy()
    source_hash = fingerprint_public_frame(shared,event_key=event_id_col,
                      entity_key=entity_col,label_key=legitimate_col,context_key=final_stratum_col)
    legit = data[legitimate_col] == 1
    legit_shared=shared.loc[legit]
    legitimate_hash = fingerprint_public_frame(legit_shared,event_key=event_id_col,
                      entity_key=entity_col,label_key=legitimate_col,context_key=final_stratum_col)
    n_eligible = legit_shared.groupby(entity_col,dropna=False).size()
    # Derive exposure from actual AuditResult (authoritative), not guessing API attribute names.
    raw_results=[]
    for flag in (left_flag_col,right_flag_col):
        out=audit(data,entity_col=entity_col,event_id_col=event_id_col,
                  final_stratum_col=final_stratum_col,legitimate_col=legitimate_col,
                  flag_col=flag,exposure=exposure,permutation=permutation)
        result=out.to_dict()
        raw_results.append(result)
        p=result['population'];c=result['counts'];pr=result['provenance'];ref=result['reference']
        if p['input_event_count']!=len(data) or p['legitimate_event_count']!=int(legit.sum()):
            raise ComparisonInputError("Public audit result does not match input event counts")
        if c['false_positive_event_count']!=int((data.loc[legit,flag]==1).sum()):
            raise ComparisonInputError("Public audit false-positive count does not match input flags")
        if pr['package_version']!='0.1.2' or result['schema_version']!='1.0':
            raise ComparisonInputError("Requires public audit engine v0.1.2 and result schema 1.0")

    p0=raw_results[0]['population']; p1=raw_results[1]['population'];
    if p0['eligible_entity_count']!=p1['eligible_entity_count']:
        raise ComparisonInputError("Eligible entity coverage differs between audits")
    e_min=p0['exposure_min'];e_max=p0['exposure_max']
    eligible_ids=set(n_eligible[n_eligible>=e_min].index.tolist()) if e_max is None else set(n_eligible[(n_eligible>=e_min)&(n_eligible<=e_max)].index.tolist())
    eligible_df=legit_shared[legit_shared[entity_col].isin(eligible_ids)][[entity_col]].drop_duplicates()
    if len(eligible_ids) != p0['eligible_entity_count']:
        raise ComparisonInputError("Public engine eligible entity count does not match source exposure")
    eligible_sha=_fingerprint_pairs(eligible_df, [entity_col])
    fp_counts=[x['counts']['false_positive_event_count'] for x in raw_results]
    # Same FP budget is mandatory for an apples-to-apples descriptive comparison.
    if fp_counts[0]!=fp_counts[1]:
        raise ComparisonInputError("Compared models require the same legitimate false-positive budget")
    # The conditional null holds each model's false-positive count fixed in each
    # resolved context. Equal global FP budgets need not imply equal allocations.
    # Record this distinction explicitly; differences in adjusted excess may
    # include changes in the per-context placement of flags.
    context_budgets = []
    for flag in (left_flag_col,right_flag_col):
        b = (data.loc[legit].groupby(final_stratum_col,dropna=False)[flag]
             .sum().to_dict())
        context_budgets.append(b)
    same_context_budgets = context_budgets[0] == context_budgets[1]
    # Reference-spec metadata must come from engine results, not caller strings.
    def ref_identity(r):
        pr=r['provenance'];ref=r['reference']
        return {'replicates':ref['replicates'],'seed':ref['seed'],'rng':ref['rng'],
                'quantiles':ref['interval_quantiles'],
                'quantile_method':ref['quantile_method'],
                'context_source':pr['context_source'],
                'statistical_contract_sha256':pr['statistical_contract_sha256']}
    if ref_identity(raw_results[0])!=ref_identity(raw_results[1]):
        raise ComparisonInputError("Public audit reference specifications differ")
    common={
      'dataset_sha256':source_hash,
      'audit_window':audit_window,
      'entity_definition':'column:'+entity_col,
      'label_semantics':'user-provided legitimate indicator:'+legitimate_col,
      'event_id_semantics':'unique column:'+event_id_col,
      'event_population_sha256':_fingerprint_pairs(shared, [event_id_col]),
      'legitimate_population_definition':'legitimate_col == 1; hashed legitimate inputs '+legitimate_hash,
      'eligible_entity_set_sha256':eligible_sha,
      'exposure_bounds':{'min':e_min,'max':e_max},
      'operating_point':'external binary flags; no threshold inferred',
      'false_positive_budget':fp_counts[0],
      'context_specification':'pre-resolved final_stratum_col:'+final_stratum_col,
      'context_assignment_sha256':_fingerprint_pairs(shared, [event_id_col,final_stratum_col]),
      'context_fallback':'already resolved upstream; not reconstructed by comparator',
      'reference_method':ref_identity(raw_results[0]),
    }
    reports=[]
    for instance_id, r in zip((left_instance_id,right_instance_id),raw_results):
        reports.append(from_v012_audit_result(r, model_instance={'instance_id':instance_id,'procedure':'user-supplied trained model or flags'},input_manifest=common))
    verified=_InProcessSourceVerification(left_sha256=_sha(reports[0]),right_sha256=_sha(reports[1]),
                frame_sha256=source_hash,audit_engine='fp-persistence-audit==0.1.2')
    output=compare_reports(*reports,_verified=verified)
    output['context_flag_allocation']={
        'status':'MATCH' if same_context_budgets else 'DIFFERENT',
        'interpretation':(
            'Each model has the same false-positive count within every resolved context.'
            if same_context_budgets else
            'Total FP budgets match, but their distributions across resolved contexts differ. '
            'Their conditional reference expectations may differ; do not attribute '
            'the excess gap solely to entity-level concentration.'),
    }
    output['data_origin_disclosure']=( 
        'A single shared event/entity/label/context frame was audited twice in this process. '
        'User-supplied ground-truth and business semantics are not independently validated; '
        'serialized output alone cannot cryptographically prove source authenticity.')
    return output
