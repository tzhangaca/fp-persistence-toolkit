import copy
import unittest
from persistence_toolkit.public_adapter import from_v012_audit_result,fingerprint_public_frame,AuditSchemaError
from persistence_toolkit.comparison import compare_reports

class SchemaAdapterTests(unittest.TestCase):
    def setUp(self):
        self.result={'schema_version':'1.0','status':'ESTIMABLE','reason':None,
         'population':{'eligible_entity_count':4,'exposure_min':3,'exposure_max':3,'legitimate_event_count':12},
         'counts':{'false_positive_event_count':4,'repeated_fp_entity_count':2,'excess_repeated_fp_entity_count':1.054545454545454},
         'estimates':{'observed_repeat_fp_proportion':0.5,'reference_expected_repeat_fp_proportion':0.23636363636363644,
                      'excess_repeat_fp_percentage_points':26.363636363636356},
         'reference':{'status':'COMPLETED','replicates':500,'seed':123},
         'provenance':{'result_schema_version':'1.0','package_version':'0.1.2'}}
        self.m={'exposure_bounds':{'min':3,'max':3},'false_positive_budget':4}
    def wrapped(self,r=None,m=None):
        return from_v012_audit_result(self.result if r is None else r,model_instance={'instance_id':'x'},input_manifest=self.m if m is None else m)
    def test_extracts_source_metrics(self):
        a=self.wrapped();self.assertAlmostEqual(a['reported_metrics']['excess_repeat_fp_percentage_points'],26.363636363636356)
    def test_rejects_wrong_exposure(self):
        m=copy.deepcopy(self.m);m['exposure_bounds']['min']=4
        with self.assertRaises(AuditSchemaError):self.wrapped(m=m)
    def test_rejects_wrong_fp(self):
        m=copy.deepcopy(self.m);m['false_positive_budget']=5
        with self.assertRaises(AuditSchemaError):self.wrapped(m=m)
    def test_rejects_unknown_schema(self):
        r=copy.deepcopy(self.result);r['schema_version']='2.0'
        with self.assertRaises(AuditSchemaError):self.wrapped(r)
    def test_rejects_missing_ref(self):
        r=copy.deepcopy(self.result);r['reference']['status']='NOT_RUN_NOT_ESTIMABLE'
        with self.assertRaises(AuditSchemaError):self.wrapped(r)
    def test_indeterminate_compatibility(self):
        r=self.wrapped(); self.assertEqual(compare_reports(r,r)['comparison_status'],'INDETERMINATE')
    def test_not_estimable(self):
        r=copy.deepcopy(self.result);r['status']='NOT_ESTIMABLE';r['reason']='zero_eligible_entities';r['population']['eligible_entity_count']=0
        for k in ('observed_repeat_fp_proportion','reference_expected_repeat_fp_proportion','excess_repeat_fp_percentage_points'):r['estimates'][k]=None
        r['counts']['repeated_fp_entity_count']=0
        a=self.wrapped(r);self.assertEqual(a['reported_metrics']['status'],'NOT_ESTIMABLE')
    def test_hash_order_invariance(self):
        rows=[{'event_id':'1','entity_id':'A','legitimate':1,'final_stratum':'x'}, {'event_id':'2','entity_id':'B','legitimate':1,'final_stratum':'x'}]
        self.assertEqual(fingerprint_public_frame(rows),fingerprint_public_frame(rows[::-1]))
    def test_hash_changes_context(self):
        rows=[{'event_id':'1','entity_id':'A','legitimate':1,'final_stratum':'x'}]
        rows2=copy.deepcopy(rows);rows2[0]['final_stratum']='z'
        self.assertNotEqual(fingerprint_public_frame(rows),fingerprint_public_frame(rows2))
    def test_rejects_duplicate_event(self):
        rows=[{'event_id':'1','entity_id':'A','legitimate':1,'final_stratum':'x'}]*2
        with self.assertRaises(AuditSchemaError):fingerprint_public_frame(rows)

if __name__=='__main__':unittest.main()
