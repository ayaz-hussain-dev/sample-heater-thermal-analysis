"""Numerical checks for the physical limits and exported-data interpretation."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyse import first_crossing, geometry, lumped_temperature, read_history


class CalculationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "data/cases.json").read_text())

    def test_adiabatic_limit_and_initial_condition(self):
        # 10 W for 100 s into 100 J/K raises the temperature by exactly 10 K.
        out = lumped_temperature(np.array([0,100]),100,.01,0,10,22,22)
        np.testing.assert_allclose(out,[22,32],rtol=0,atol=1e-12)

    def test_zero_power_cooling_and_time_constant(self):
        # At one time constant, a 10 K excess must fall to 10/e K.
        out = lumped_temperature(100,100,.1,10,0,32,22)
        self.assertAlmostEqual(float(out),22+10/np.e,places=12)

    def test_removed_mass_matches_solid_slice(self):
        a,b=geometry(self.config,"A"),geometry(self.config,"B")
        # Identical cavities cancel: removed material is exactly 60 x 40 x 5 mm.
        self.assertAlmostEqual(a["mass_kg"]-b["mass_kg"],.03324,places=12)
        self.assertAlmostEqual(a["convection_area_m2"]-b["convection_area_m2"],.001,places=12)

    def test_threshold_interpolation_and_unreached_target(self):
        self.assertEqual(first_crossing([0,10,20],[20,40,60],50),15)
        self.assertIsNone(first_crossing([0,10,20],[20,40,60],65))

    def test_all_exported_histories_match_their_fixed_clocks(self):
        count=0
        for c in self.config["cases"]:
            for key in ["temperature_file","heatflux_file","wellwalls_file"]:
                if key in c:
                    h=read_history(ROOT/"data/raw"/c[key],c["dt_s"])
                    self.assertEqual(h.time[-1],600)
                    self.assertTrue(np.all(h.minimum<=h.maximum))
                    count+=1
        self.assertEqual(count,18)


if __name__=="__main__":
    unittest.main()
