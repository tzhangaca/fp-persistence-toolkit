"""Injected fake engine checks ONLY comparator wiring, not public-engine integration."""
import copy
import sys
import types
import unittest
from unittest.mock import patch
import pandas as pd
from persistence_toolkit.comparison import compare_reports, ComparisonInputError
from persistence_toolkit.direct_audit import audit_and_compare_shared_frame
from persistence_toolkit.public_adapter import from_v012_audit_result

ROWS = pd.DataFrame({
 'event_id':[f'e{i:02d}' for i in range(12)],
 'entity_id':['A']*3+['B']*3+['C']*3+['D']*3,
 'legitimate':[1]*12,
 'final_stratum':['d1']*6+['d2']*6,
 'flags_A':[1,0,0,1,0,0,1,0,0,1,0,0],
 'flags_B':[1,1,0,0,0,0,1,1,0,0,0,0],
})

class StubAuditResult:
 def __init__(self, value): self.value=value
 def to_dict(self):return copy.deepcopy(self.value)

def fake_audit(rows, *, flag_col, **kwargs):
 counts=(rows.loc[rows['legitimate']==1].groupby('entity_id')[flag_col].sum())
 repeated=int((counts>=2).sum())
 obs=repeated/4
 ref=0.2
 return StubAuditResult({'schema_version':'1.0','status':'ESTIMABLE','reason':None,
    'population':{'input_event_count':12,'legitimate_event_count':12,'exposure_min':3,'exposure_max':3,
      'entity_count_before_exposure_filter':4,'eligible_entity_count':4},
    'counts':{'false_positive_event_count':4,'repeated_fp_entity_count':repeated,'excess_repeated_fp_entity_count':None},
    'estimates':{'observed_repeat_fp_proportion':obs,'reference_expected_repeat_fp_proportion':ref,
                 'excess_repeat_fp_percentage_points':100*(obs-ref)},
    'reference':{'status':'COMPLETED','replicates':500,'seed':123,'rng':'numpy.random.default_rng',
                 'interval_quantiles':[0.025,0.975],'quantile_method':'linear'},
    'provenance':{'package_name':'fp-persistence-audit','package_version':'0.1.2','result_schema_version':'1.0',
         'statistical_contract_sha256':'frozen-contract','context_source':'caller_supplied'}})

class TestDirectAudit(unittest.TestCase):
 def run_validated(self,data=ROWS):
  with patch.dict(sys.modules,{'fp_persistence':types.SimpleNamespace(audit=fake_audit)}):
   return audit_and_compare_shared_frame(data,left_flag_col='flags_A',right_flag_col='flags_B',
    entity_col='entity_id',event_id_col='event_id',final_stratum_col='final_stratum',
    legitimate_col='legitimate',exposure=object(),permutation=object())
 def test_context_mismatch_disclosed(self):
  data=ROWS.copy()
  # Same total K=4, but move one selected flag from d2 to d1.
  data.loc[6,'flags_B']=0
  data.loc[2,'flags_B']=1
  r=self.run_validated(data)
  self.assertEqual(r['comparison_status'],'COMPARABLE')
  self.assertEqual(r['context_flag_allocation']['status'],'DIFFERENT')
  self.assertIn('may differ', r['context_flag_allocation']['interpretation'])
 def test_context_match_disclosed(self):
  r=self.run_validated()
  self.assertEqual(r['context_flag_allocation']['status'],'MATCH')
 def test_duplicate_dataframe_columns_rejected(self):
  data=ROWS.copy()
  data.columns=list(data.columns[:-1])+['flags_A']
  with self.assertRaises(ComparisonInputError):self.run_validated(data)
 def test_source_exposure_mismatch_rejected(self):
  def bad_audit(*args,**kwargs):
   x=fake_audit(*args,**kwargs).to_dict()
   x['population']['eligible_entity_count']=3
   return StubAuditResult(x)
  with patch.dict(sys.modules,{'fp_persistence':types.SimpleNamespace(audit=bad_audit)}):
   with self.assertRaises(ComparisonInputError):
    audit_and_compare_shared_frame(ROWS,left_flag_col='flags_A',right_flag_col='flags_B',
     entity_col='entity_id',event_id_col='event_id',final_stratum_col='final_stratum',
     legitimate_col='legitimate',exposure=object(),permutation=object())
 def _run_with_engine_version(self,version):
  def versioned_audit(*args,**kwargs):
   x=fake_audit(*args,**kwargs).to_dict()
   x['provenance']['package_version']=version
   return StubAuditResult(x)
  with patch.dict(sys.modules,{'fp_persistence':types.SimpleNamespace(audit=versioned_audit)}):
   return audit_and_compare_shared_frame(ROWS,left_flag_col='flags_A',right_flag_col='flags_B',
    entity_col='entity_id',event_id_col='event_id',final_stratum_col='final_stratum',
    legitimate_col='legitimate',exposure=object(),permutation=object())
 def test_engine_v013_accepted(self):
  self.assertEqual(self._run_with_engine_version('0.1.3')['comparison_status'],'COMPARABLE')
 def test_unverified_engine_version_rejected(self):
  for version in ('0.1.1','0.1.4','0.2.0'):
   with self.subTest(version=version):
    with self.assertRaises(ComparisonInputError):self._run_with_engine_version(version)
 def test_in_process_comparable(self):
  r=self.run_validated()
  self.assertEqual(r['comparison_status'],'COMPARABLE')
  self.assertEqual(r['source_validation_status'],'IN_PROCESS_SAME_FRAME')
  self.assertAlmostEqual(r['reported_metrics']['difference_in_excess_pp_left_minus_right'],-50.)
 def test_source_hash_order_invariant(self):
  a=self.run_validated();b=self.run_validated(ROWS.sample(frac=1,random_state=42).reset_index(drop=True))
  self.assertEqual(a['source_frame_sha256'],b['source_frame_sha256'])
 def test_budget_mismatch_rejected(self):
  data=ROWS.copy();data.loc[0,'flags_B']=0
  with self.assertRaises(ComparisonInputError):self.run_validated(data)
 def test_modified_common_frame_changes_hash(self):
  data=ROWS.copy();data.loc[0,'final_stratum']='d3'
  self.assertNotEqual(self.run_validated(data)['source_frame_sha256'],self.run_validated()['source_frame_sha256'])
 def test_duplicate_event_rejected(self):
  data=ROWS.copy();data.loc[0,'event_id']=data.loc[1,'event_id']
  with self.assertRaises(ComparisonInputError):self.run_validated(data)
 def test_serialized_reports_no_automatic_proof(self):
  r=self.run_validated()
  left={'model_instance':r['models']['left'],'audit_input_manifest':{},'audit_result':r['audit_results']['left'],'reported_metrics':r['reported_metrics']['left']}
  right={'model_instance':r['models']['right'],'audit_input_manifest':{},'audit_result':r['audit_results']['right'],'reported_metrics':r['reported_metrics']['right']}
  self.assertEqual(compare_reports(left,right)['comparison_status'],'INDETERMINATE')
 def test_mismatched_metric_caught(self):
  r=self.run_validated();result=copy.deepcopy(r['audit_results']['left'])
  report=from_v012_audit_result(result,model_instance={'instance_id':'A'},input_manifest={})
  report['reported_metrics']['excess_repeat_fp_percentage_points'] += .5
  with self.assertRaises(ComparisonInputError):compare_reports(report,report)
 def test_tampered_source_budget_caught(self):
  r=self.run_validated();report=from_v012_audit_result(r['audit_results']['left'],model_instance={'instance_id':'A'},input_manifest={})
  report['audit_input_manifest']['false_positive_budget']=5
  with self.assertRaises(ComparisonInputError):compare_reports(report,report)

if __name__=='__main__':unittest.main()
