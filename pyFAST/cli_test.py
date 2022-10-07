import unittest

from .cli import filter_cases, parse_args, parse_test_config


class TestCLI(unittest.TestCase):
    def test_parse_args_1(self):
        args = parse_args("--verbose -j 10".split())
        self.assertTrue(args.verbose)
        self.assertFalse(args.show_only)
        self.assertEqual(args.jobs, 10)
        self.assertEqual(args.test_config, "test_config.yaml")

    def test_parse_args_2(self):
        args = parse_args(
            "-N -L hello|world -R foobar -c newconfig.yaml".split())
        self.assertTrue(args.show_only)
        self.assertEqual(args.label_regex, "hello|world")
        self.assertEqual(args.test_regex, "foobar")
        self.assertEqual(args.jobs, -1)
        self.assertEqual(args.test_config, "newconfig.yaml")

    def test_parse_test_config(self):
        cases = parse_test_config("", sample_config)
        cases_exp = [
            {
                "name": "AWT_YFix_WSt",
                "absolute_tolerance": 1.5,
                "relative_tolerance": 2,
                "plot": True,
                "type": "regression",
                "driver": "openfast",
                "labels": ["aerodyn14", "elastodyn", "servodyn"],
                "baseline_file": "AWT_YFix_WSt.outb",
                "turbine_directory": "AWT27",
                "test": 1,
                "input_path": "reg_tests/r-test/glue-codes/openfast",
                "run_path": "build/reg_tests/glue-codes/openfast",
                "executable_path": "build/glue_codes/openfast/openfast"
            },
            {
                "name": "AWT_WSt_StartUp_HighSpShutDown",
                "absolute_tolerance": 1.9,
                "relative_tolerance": 2,
                "plot": False,
                "type": "regression",
                "driver": "openfast",
                "labels": ["aerodyn", "elastodyn", "servodyn"],
                "baseline_file": "AWT_WSt_StartUp_HighSpShutDown.outb",
                "turbine_directory": "AWT27",
                "test": 1,
                "input_path": "reg_tests/r-test/glue-codes/openfast",
                "run_path": "build/reg_tests/glue-codes/openfast",
                "executable_path": "build/glue_codes/openfast/openfast"
            }
        ]
        for case, case_exp in zip(cases, cases_exp):
            self.assertDictEqual(case, case_exp)

    def test_filter_cases(self):

        # Include cases based on name
        cases = filter_cases(sample_cases, test_regex="WP_")
        self.assertListEqual([c["name"] for c in cases], [
            "WP_VSP_WTurb_PitchFail", "WP_VSP_ECD", "WP_VSP_WTurb",
            "WP_Stationary_Linear"])

        # Include cases based on label
        cases = filter_cases(sample_cases, label_regex="moor")
        self.assertListEqual([c["name"] for c in cases], [
                             "5MW_OC4Semi_WSt_WavesWN"])
        cases = filter_cases(sample_cases, label_regex="moor|map")
        self.assertListEqual([c["name"] for c in cases], [
            "5MW_ITIBarge_DLL_WTurb_WavesIrr",
            "5MW_TLP_DLL_WTurb_WavesIrr_WavesMulti",
            "5MW_OC3Spar_DLL_WTurb_WavesIrr",
            "5MW_OC4Semi_WSt_WavesWN"])

        # Exclude cases based on name
        cases = filter_cases(sample_cases,
                             test_exclude_regex="UAE|AOC|WP|AWT|5MW|\w+_YFree")
        self.assertListEqual([c["name"] for c in cases], [
            "Ideal_Beam_Fixed_Free_Linear", "Ideal_Beam_Free_Free_Linear"])

        # Exclude cases based on label
        cases = filter_cases(sample_cases,
                             label_exclude_regex="aerodyn|servodyn")
        self.assertListEqual([c["name"] for c in cases], [
            "Ideal_Beam_Fixed_Free_Linear", "Ideal_Beam_Free_Free_Linear",
            "WP_Stationary_Linear"])

        # Combined filters
        cases = filter_cases(sample_cases,
                             test_regex="5MW",
                             test_exclude_regex="\w+_BD_",
                             label_regex="offshore",
                             label_exclude_regex="moordyn|map")
        self.assertListEqual([c["name"] for c in cases], [
            "5MW_OC3Mnpl_DLL_WTurb_WavesIrr", "5MW_OC3Trpd_DLL_WSt_WavesReg",
            "5MW_OC4Jckt_DLL_WTurb_WavesIrr_MGrowth"])


sample_config = '''
driver_defaults:
    test: 1
drivers:
    openfast:
        input_path: reg_tests/r-test/glue-codes/openfast
        run_path: build/reg_tests/glue-codes/openfast
        executable_path: build/glue_codes/openfast/openfast
    aerodyn:
        input_path: reg_tests/r-test/modules/aerodyn
        run_path: build/reg_tests/modules/aerodyn
        executable_path: build/modules/aerodyn/aerodyn_driver
case_defaults:
    absolute_tolerance: 1.9
    relative_tolerance: 2
    plot: true
cases:
    AWT_YFix_WSt:
        type: regression
        driver: openfast
        labels: [ aerodyn14, elastodyn, servodyn]
        baseline_file: AWT_YFix_WSt.outb
        turbine_directory: AWT27
        absolute_tolerance: 1.5

    AWT_WSt_StartUp_HighSpShutDown:
        type: regression
        driver: openfast
        labels: [aerodyn, elastodyn, servodyn]
        baseline_file: AWT_WSt_StartUp_HighSpShutDown.outb
        turbine_directory: AWT27
        plot: false
'''

sample_cases = [
    {"name": "AWT_YFix_WSt",
     "labels": ["aerodyn14", "elastodyn", "servodyn"]},
    {"name": "AWT_WSt_StartUp_HighSpShutDown",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "AWT_YFree_WSt",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "AWT_YFree_WTurb",
     "labels": ["aerodyn14", "elastodyn", "servodyn"]},
    {"name": "AWT_WSt_StartUpShutDown",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "AOC_WSt",
     "labels": ["aerodyn14", "elastodyn", "servodyn"]},
    {"name": "AOC_YFree_WTurb",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "AOC_YFix_WSt",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "UAE_Dnwind_YRamp_WSt",
     "labels": ["aerodyn14", "elastodyn", "servodyn"]},
    {"name": "UAE_Upwind_Rigid_WRamp_PwrCurve",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "WP_VSP_WTurb_PitchFail",
     "labels": ["aerodyn14", "elastodyn", "servodyn"]},
    {"name": "WP_VSP_ECD",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "WP_VSP_WTurb",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "SWRT_YFree_VS_EDG01",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "SWRT_YFree_VS_EDC01",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "SWRT_YFree_VS_WTurb",
     "labels": ["aerodyn14", "elastodyn", "servodyn"]},
    {"name": "5MW_Land_DLL_WTurb",
     "labels": ["aerodyn", "elastodyn", "servodyn"]},
    {"name": "5MW_OC3Mnpl_DLL_WTurb_WavesIrr",
     "labels": ["aerodyn", "elastodyn", "servodyn",
                "hydrodyn", "subdyn", "offshore"]},
    {"name": "5MW_OC3Trpd_DLL_WSt_WavesReg",
     "labels": ["aerodyn", "elastodyn", "servodyn",
                "hydrodyn", "subdyn", "offshore"]},
    {"name": "5MW_OC4Jckt_DLL_WTurb_WavesIrr_MGrowth",
     "labels": ["aerodyn", "elastodyn", "servodyn",
                "hydrodyn", "subdyn", "offshore"]},
    {"name": "5MW_ITIBarge_DLL_WTurb_WavesIrr",
     "labels": ["aerodyn14", "elastodyn",
                "servodyn", "hydrodyn", "map", "offshore"]},
    {"name": "5MW_TLP_DLL_WTurb_WavesIrr_WavesMulti",
     "labels": ["aerodyn", "elastodyn", "servodyn",
                "hydrodyn", "map", "offshore"]},
    {"name": "5MW_OC3Spar_DLL_WTurb_WavesIrr",
     "labels": ["aerodyn", "elastodyn", "servodyn",
                "hydrodyn", "map", "offshore"]},
    {"name": "5MW_OC4Semi_WSt_WavesWN",
     "labels": ["aerodyn", "elastodyn", "servodyn",
                "hydrodyn", "moordyn", "offshore"]},
    {"name": "5MW_Land_BD_DLL_WTurb",
     "labels": ["aerodyn", "beamdyn", "servodyn"]},
    {"name": "5MW_Land_BD_Linear",
     "labels": ["aerodyn", "beamdyn", "servodyn", "linear"]},
    {"name": "Ideal_Beam_Fixed_Free_Linear", "labels": ["beamdyn", "linear"]},
    {"name": "Ideal_Beam_Free_Free_Linear", "labels": ["beamdyn", "linear"]},
    {"name": "WP_Stationary_Linear", "labels": ["elastodyn", "linear"]},
]

if __name__ == '__main__':
    unittest.main()
