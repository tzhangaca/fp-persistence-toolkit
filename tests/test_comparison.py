import copy,json,math,unittest
from pathlib import Path
from persistence_toolkit import compare_reports,render_markdown,summarize_seed_runs,ComparisonInputError
root=Path(__file__).resolve().parents[1]
class TestComparison(unittest.TestCase):
 def setUp(self):
  self.a=json.loads((root/'examples/toy_model_A.json').read_text())
  self.b=json.loads((root/'examples/toy_model_B.json').read_text())
 def test_example_exact_expected(self):
  ref=1-math.comb(9,4)/math.comb(12,4)-3*math.comb(9,3)/math.comb(12,4)
  self.assertAlmostEqual(self.a['reported_metrics']['reference_expected_repeat_fp_proportion'],ref)
 def test_compatible(self):
  result=compare_reports(self.a,self.b)
  self.assertEqual(result['comparison_status'],'INDETERMINATE')
  self.assertEqual(result['source_validation_status'],'UNVERIFIED_SERIALIZED_INPUT')
  self.assertEqual(len(result['compatibility_checks']),15)
  self.assertIsNone(result['reported_metrics']['difference_in_excess_pp_left_minus_right'])
 def test_preserve_values(self):
  a=copy.deepcopy(self.a);b=copy.deepcopy(self.b)
  res=compare_reports(a,b)
  self.assertEqual(a,self.a);self.assertEqual(b,self.b)
  self.assertEqual(res['audit_results']['left'],a['audit_result'])
 def test_mismatch(self):
  b=copy.deepcopy(self.b);b['audit_input_manifest']['false_positive_budget']=5
  x=compare_reports(self.a,b)
  self.assertEqual(x['comparison_status'],'INCOMPATIBLE')
  self.assertIsNone(x['reported_metrics']['difference_in_excess_pp_left_minus_right'])
 def test_unknown(self):
  b=copy.deepcopy(self.b);b['audit_input_manifest'].pop('dataset_sha256')
  self.assertEqual(compare_reports(self.a,b)['comparison_status'],'INDETERMINATE')
 def test_wrong_excess(self):
  b=copy.deepcopy(self.b);b['reported_metrics']['excess_repeat_fp_percentage_points']=42.
  with self.assertRaises(ComparisonInputError):compare_reports(self.a,b)
 def test_missing_metric_source(self):
  b=copy.deepcopy(self.b);b['reported_metrics']['pr_auc']=.5
  with self.assertRaises(ComparisonInputError):compare_reports(self.a,b)
 def test_nonestimable(self):
  b=copy.deepcopy(self.b);b['reported_metrics']={'status':'NOT_ESTIMABLE','reason':'no eligible entities'}
  self.assertIsNone(compare_reports(self.a,b)['reported_metrics']['difference_in_excess_pp_left_minus_right'])
 def test_unknown_not_estimable_no_reason(self):
  b=copy.deepcopy(self.b);b['reported_metrics']={'status':'NOT_ESTIMABLE'}
  with self.assertRaises(ComparisonInputError):compare_reports(self.a,b)
 def test_units_markdown(self):
  res=render_markdown(compare_reports(self.a,self.b))
  self.assertIn('excess_repeat_fp_percentage_points',res)
  self.assertNotIn('winner',res)
 def test_context_allocation_note_does_not_break_markdown_table(self):
  sample=compare_reports(self.a,self.b)
  sample['context_flag_allocation']={'status':'MATCH','interpretation':'Same context budgets.'}
  md=render_markdown(sample)
  self.assertIn('Context-specific FP allocation: **MATCH**',md)
  self.assertIn('| Field | Left instance | Right instance |\n|---|---:|---:|\n| pr_auc |',md)
  self.assertLess(md.index('Context-specific FP allocation:'),md.index('| Field |'))
 def test_seeds(self):
  v=summarize_seed_runs([{'procedure':'x','excess_pp':1},{'procedure':'x','excess_pp':2}])
  self.assertEqual(v['x']['n'],2)
  self.assertAlmostEqual(v['x']['mean_pp'],1.5)
 def test_compared_output_stable(self):
  self.assertEqual(compare_reports(self.a,self.b),compare_reports(self.a,self.b))
if __name__=='__main__':unittest.main()
