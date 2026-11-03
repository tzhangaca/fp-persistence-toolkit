"""Standalone descriptive comparison adapter; no recomputation of the audit estimand."""
from __future__ import annotations
import copy
import hashlib
import json
import math
import statistics
from dataclasses import dataclass

class ComparisonInputError(ValueError):
    pass

# These are audit *comparability* metadata, not learned model parameters.
COMPATIBILITY_FIELDS = (
    "dataset_sha256", "audit_window", "entity_definition", "label_semantics",
    "event_id_semantics", "event_population_sha256", "legitimate_population_definition",
    "eligible_entity_set_sha256", "exposure_bounds", "operating_point",
    "false_positive_budget", "context_specification", "context_assignment_sha256",
    "context_fallback", "reference_method",
)
NUMERIC_FIELDS = ("eligible_entity_count", "repeated_fp_entity_count", "false_positive_count",
                  "observed_repeat_fp_proportion", "reference_expected_repeat_fp_proportion",
                  "excess_repeat_fp_percentage_points")

def _exactly_equal(a,b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)

def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def validate(report):
    if not isinstance(report,dict):
        raise ComparisonInputError("Report must be an object")
    for field in ("model_instance", "audit_input_manifest", "audit_result", "reported_metrics"):
        if field not in report or not isinstance(report[field],dict):
            raise ComparisonInputError(f"Missing object {field}")
    if not report["model_instance"].get("instance_id"):
        raise ComparisonInputError("model_instance.instance_id is required")
    audit=report["audit_result"]
    if not audit:
        raise ComparisonInputError("audit_result must be nonempty")
    m=report["reported_metrics"]
    # For known v0.1.2 public results, never trust duplicate reported metrics.
    if audit.get("schema_version") == "1.0":
        try:
            ap= audit["population"]
            ac= audit["counts"]
            ae= audit["estimates"]
            prov= audit["provenance"]
            if prov["result_schema_version"] != "1.0":
                raise ComparisonInputError("Source/provenance schema disagreement")
            expected={
                "status":audit["status"],
                "eligible_entity_count":ap["eligible_entity_count"],
                "false_positive_count":ac["false_positive_event_count"],
                "repeated_fp_entity_count":ac["repeated_fp_entity_count"],
            }
            if audit["status"] == "ESTIMABLE":
                expected.update({
                    "observed_repeat_fp_proportion":ae["observed_repeat_fp_proportion"],
                    "reference_expected_repeat_fp_proportion":ae["reference_expected_repeat_fp_proportion"],
                    "excess_repeat_fp_percentage_points":ae["excess_repeat_fp_percentage_points"],
                })
            for field,value in expected.items():
                if field not in m or not _exactly_equal(m[field],value):
                    raise ComparisonInputError(f"Reported metric {field} conflicts with source AuditResult")
            manifest=report["audit_input_manifest"]
            if manifest.get("exposure_bounds") is not None and not _exactly_equal(
                manifest["exposure_bounds"], {"min":ap["exposure_min"],"max":ap["exposure_max"]}):
                raise ComparisonInputError("Manifest exposure conflicts with source AuditResult")
            if manifest.get("false_positive_budget") is not None and manifest["false_positive_budget"] != ac["false_positive_event_count"]:
                raise ComparisonInputError("Manifest FP budget conflicts with source AuditResult")
        except (KeyError,TypeError) as exc:
            raise ComparisonInputError("Incomplete public AuditResult serialization") from exc
    status=m.get("status")
    if status not in ("ESTIMABLE", "NOT_ESTIMABLE"):
        raise ComparisonInputError("reported_metrics.status must be ESTIMABLE or NOT_ESTIMABLE")
    if status=="ESTIMABLE":
        for k in NUMERIC_FIELDS:
            if k not in m or not isinstance(m[k],(int,float)) or isinstance(m[k],bool) or not math.isfinite(float(m[k])):
                raise ComparisonInputError(f"Missing or nonfinite numeric field: {k}")
        if not (0 <= m["observed_repeat_fp_proportion"] <= 1 and 0 <= m["reference_expected_repeat_fp_proportion"] <= 1):
            raise ComparisonInputError("Proportions must be in [0,1]")
        if m["eligible_entity_count"] <= 0 or m["false_positive_count"] < 0 or m["repeated_fp_entity_count"] < 0:
            raise ComparisonInputError("Invalid counts")
        if m["repeated_fp_entity_count"] > m["eligible_entity_count"]:
            raise ComparisonInputError("Repeated-flag entities exceed eligible entities")
        if abs(m["observed_repeat_fp_proportion"]-m["repeated_fp_entity_count"]/m["eligible_entity_count"])>1e-8:
            raise ComparisonInputError("Reported observed recurrence inconsistent with reported counts")
        if abs(m["excess_repeat_fp_percentage_points"] - 100*(m["observed_repeat_fp_proportion"]-m["reference_expected_repeat_fp_proportion"]))>1e-7:
            raise ComparisonInputError("Reported excess is not consistent with reported observed/reference values")
    else:
        if not m.get("reason"):
            raise ComparisonInputError("NOT_ESTIMABLE needs a reason")
        if any(k in m and m[k] is not None for k in ("excess_repeat_fp_percentage_points", "observed_repeat_fp_proportion")):
            raise ComparisonInputError("Do not supply estimates for NOT_ESTIMABLE")
    for k in ("pr_auc","roc_auc"):
        if k in m and m[k] is not None:
            if (not isinstance(m[k], (int,float))) or not math.isfinite(m[k]) or not (0 <= m[k] <= 1):
                raise ComparisonInputError(f"Invalid optional metric: {k}")
            if not m.get("metric_population") or not m.get("metric_source"):
                raise ComparisonInputError(f"{k} requires metric_population and metric_source")
    return report

@dataclass(frozen=True)
class _InProcessSourceVerification:
    """Non-serialized, short-lived evidence of two actual audit calls on one frame.

    Not a digital signature; exported JSON must never be treated as tamper-proof.
    """
    left_sha256: str
    right_sha256: str
    frame_sha256: str
    audit_engine: str


def compare_reports(left,right, *, _verified=None):
    validate(left);validate(right)
    lm=left["audit_input_manifest"];rm=right["audit_input_manifest"]
    fields=[]
    for name in COMPATIBILITY_FIELDS:
        a=lm.get(name);b=rm.get(name)
        if a is None or b is None or a=="" or b=="":
            state="UNKNOWN"
        elif _exactly_equal(a,b):
            state="MATCH"
        else:
            state="MISMATCH"
        fields.append({"field":name,"left":copy.deepcopy(a),"right":copy.deepcopy(b),"status":state})
    outcomes={row["status"] for row in fields}
    # Equal caller-supplied manifests are assertions, NOT provenance proof.
    # Only the in-process audit_from_shared_frame workflow can mark a pair comparable.
    live_verified = (
        isinstance(_verified, _InProcessSourceVerification)
        and _verified.left_sha256 == _sha(left)
        and _verified.right_sha256 == _sha(right)
    )
    overall=("INCOMPATIBLE" if "MISMATCH" in outcomes else
             "INDETERMINATE" if "UNKNOWN" in outcomes or not live_verified
             else "COMPARABLE")
    L=left["reported_metrics"];R=right["reported_metrics"]
    descriptive={"left":copy.deepcopy(L),"right":copy.deepcopy(R),"difference_in_excess_pp_left_minus_right":None}
    if overall=="COMPARABLE" and L["status"]==R["status"]=="ESTIMABLE":
        descriptive["difference_in_excess_pp_left_minus_right"]=L["excess_repeat_fp_percentage_points"]-R["excess_repeat_fp_percentage_points"]
    return {"schema_version":"0.2.0", "report_type":"DESCRIPTIVE_MODEL_INSTANCE_COMPARISON",
            "comparison_status":overall,
            "source_validation_status": "IN_PROCESS_SAME_FRAME" if live_verified else "UNVERIFIED_SERIALIZED_INPUT",
            "source_frame_sha256": _verified.frame_sha256 if live_verified else None,
            "compatibility_checks":fields,
            "models":{"left":copy.deepcopy(left["model_instance"]),"right":copy.deepcopy(right["model_instance"])},
            "audit_results":{"left":copy.deepcopy(left["audit_result"]),"right":copy.deepcopy(right["audit_result"])},
            "source_sha256":{"left":_sha(left),"right":_sha(right)},"reported_metrics":descriptive,
            "limits":["Model-instance comparison only; no model-family generalization, significance test, or equivalence claim.",
                      "Only compare reported fields; underlying audit estimates and reference expectations are not recalculated.",
                      "False-positive model flags do not establish verification, declined transactions, consumer harm, or financial loss.",
                      "External conventional metrics are user supplied and their provenance requires independent review.",
                      "A saved result is not an authenticated source record. Equal metadata in JSON cannot prove the original input was shared.",
                      "A direct shared-frame comparison checks input identity but does not establish historical labels, real-world decision outcomes, or model-family equivalence."]}

def render_markdown(result):
    x=result; lines=["# Descriptive AI/ML fraud-screening audit comparison", "",f"Compatibility: **{x['comparison_status']}**", "",
        f"Source validation: **{x.get('source_validation_status','UNKNOWN')}**", ""]
    alloc=x.get('context_flag_allocation')
    if alloc:
        lines.extend(["Context-specific FP allocation: **"+alloc['status']+"**", "", alloc['interpretation'], ""])
    lines.extend(["| Field | Left instance | Right instance |", "|---|---:|---:|"])
    m=x["reported_metrics"]
    for field in ("pr_auc","roc_auc","false_positive_count","eligible_entity_count","repeated_fp_entity_count","observed_repeat_fp_proportion","reference_expected_repeat_fp_proportion","excess_repeat_fp_percentage_points"):
        def display(v):
            if v is None: return "N/A"
            return f"{v:.6f}" if isinstance(v,float) else str(v)
        lines.append(f"| {field} | {display(m['left'].get(field))} | {display(m['right'].get(field))} |")
    lines += ["", "## Compatibility details", ""]
    for c in x["compatibility_checks"]:
        lines.append(f"- `{c['field']}`: **{c['status']}**")
    lines += ["", "## Interpretation limits", ""]+["- "+i for i in x["limits"]]
    return "\n".join(lines)+"\n"

def summarize_seed_runs(entries):
    """Descriptive stats only; each row represents a fitted instance on a fixed evaluation population."""
    groups={}
    for e in entries:
        fam=e.get("procedure")
        val=e.get("excess_pp")
        if not fam or not isinstance(val,(int,float)) or not math.isfinite(val):
            raise ComparisonInputError("Every seed record must have procedure and finite excess_pp")
        groups.setdefault(fam,[]).append(float(val))
    return {fam:{"n":len(v),"mean_pp":statistics.mean(v),"sd_pp":statistics.stdev(v) if len(v)>1 else None,
                 "min_pp":min(v),"max_pp":max(v),"median_pp":statistics.median(v)} for fam,v in sorted(groups.items())}
