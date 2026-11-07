"""Integration tests use the REAL installed public engine (v0.1.2 or v0.1.3).

Skipped only when that dependency is absent (e.g. isolated offline review).
The GitHub Actions matrix installs it and MUST run this file.
"""
import unittest
import importlib.util
import pandas as pd
from persistence_toolkit.direct_audit import audit_and_compare_shared_frame

@unittest.skipUnless(importlib.util.find_spec('fp_persistence'),
    'Published public engine must be installed for this integration test')
class RealEngineIntegration(unittest.TestCase):
    def source(self):
        from fp_persistence import ExposureSpec, PermutationSpec
        events=pd.DataFrame({
            'event_id':[f'e{i:02d}' for i in range(12)],
            'entity_id':['A']*3+['B']*3+['C']*3+['D']*3,
            'legitimate':[1]*12,
            'final_stratum':['d1']*6+['d2']*6,
            'flags_A':[1,0,0, 1,0,0, 1,0,0, 1,0,0],
            'flags_B':[1,1,0, 0,0,0, 1,1,0, 0,0,0],
        })
        return events, ExposureSpec, PermutationSpec
    def args(self, events, exposure, permutation):
        return dict(data=events,left_flag_col='flags_A',right_flag_col='flags_B',
                    event_id_col='event_id',entity_col='entity_id',
                    legitimate_col='legitimate',final_stratum_col='final_stratum',
                    exposure=exposure,permutation=permutation)
    def test_real_engine_matched_context(self):
        ev,E,P=self.source()
        output=audit_and_compare_shared_frame(**self.args(ev,E(3,3),P(50,17)))
        self.assertEqual(output['comparison_status'],'COMPARABLE')
        self.assertEqual(output['context_flag_allocation']['status'],'MATCH')
        self.assertEqual(output['reported_metrics']['left']['repeated_fp_entity_count'],0)
        self.assertEqual(output['reported_metrics']['right']['repeated_fp_entity_count'],2)
    def test_real_engine_context_allocation_change(self):
        ev,E,P=self.source()
        ev.loc[6,'flags_B']=0
        ev.loc[2,'flags_B']=1
        output=audit_and_compare_shared_frame(**self.args(ev,E(3,3),P(50,17)))
        self.assertEqual(output['comparison_status'],'COMPARABLE')
        self.assertEqual(output['context_flag_allocation']['status'],'DIFFERENT')
    def test_real_engine_not_estimable(self):
        ev,E,P=self.source()
        output=audit_and_compare_shared_frame(**self.args(ev,E(4,4),P(20,17)))
        self.assertEqual(output['comparison_status'],'COMPARABLE')
        self.assertEqual(output['reported_metrics']['left']['status'],'NOT_ESTIMABLE')
        self.assertIsNone(output['reported_metrics']['difference_in_excess_pp_left_minus_right'])
