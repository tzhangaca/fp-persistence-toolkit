"""Actual v0.1.2 public audit engine -> two model-instance audit reports.

This script requires the REAL pip-installed fp-persistence-audit==0.1.2.
A synthetic 12-event fixture illustrates semantics; it is not empirical
validation on real fraud data, and makes no performance/harm claim.
"""
from pathlib import Path
import json
import pandas as pd
from fp_persistence import ExposureSpec, PermutationSpec
from persistence_toolkit.direct_audit import audit_and_compare_shared_frame
from persistence_toolkit.comparison import render_markdown

root=Path(__file__).resolve().parents[1]
events=pd.DataFrame({
    'event_id':[f'e{i:02d}' for i in range(12)],
    'entity_id':['A']*3+['B']*3+['C']*3+['D']*3,
    'legitimate':[1]*12,
    'final_stratum':['day1']*6+['day2']*6,
    'flags_dispersed':[1,0,0, 1,0,0, 1,0,0, 1,0,0],
    'flags_concentrated':[1,1,0, 0,0,0, 1,1,0, 0,0,0],
})
comparison=audit_and_compare_shared_frame(
    events,left_flag_col='flags_dispersed',right_flag_col='flags_concentrated',
    entity_col='entity_id',event_id_col='event_id',
    final_stratum_col='final_stratum',legitimate_col='legitimate',
    exposure=ExposureSpec(3,3),permutation=PermutationSpec(500,2026091601),
    audit_window='twelve constructed events, not chronological',
    left_instance_id='constructed-dispersed',right_instance_id='constructed-concentrated',
)
assert comparison['comparison_status']=='COMPARABLE', comparison['comparison_status']
assert comparison['source_validation_status']=='IN_PROCESS_SAME_FRAME'
assert comparison['context_flag_allocation']['status']=='MATCH'
assert comparison['reported_metrics']['left']['repeated_fp_entity_count']==0
assert comparison['reported_metrics']['right']['repeated_fp_entity_count']==2
assert comparison['reported_metrics']['left']['false_positive_count']==4
assert comparison['reported_metrics']['right']['false_positive_count']==4
output_dir=root/'demo_output';output_dir.mkdir(exist_ok=True)
(output_dir/'comparison_report.json').write_text(json.dumps(comparison,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
(output_dir/'comparison_report.md').write_text(render_markdown(comparison))
print('PASS — real published engine v0.1.2 -> verified-in-process descriptive comparison')
print('Results:',output_dir)
print(render_markdown(comparison))
