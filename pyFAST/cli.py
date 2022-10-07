"""CLI functionality for pyFAST"""

import sys
import argparse
from typing import List
import re
import yaml
import os

from pyFAST.executor import Executor
from pyFAST.regression_tester import RegressionTester
from pyFAST.postprocessor import SummaryHandler


def run_cli():
    """
    Runs the pyFAST suite.
    """

    # Parse command line arguments
    args = parse_args(sys.argv[1:])

    # Get root path as an absolute path
    root_path = os.path.abspath(args.repo_root)

    # Parse test configuration file from path in cli args
    cases = parse_test_config(root_path, open(args.test_config).read())

    # Filter cases based on cli argument regular expressions
    cases = filter_cases(cases, args.test_regex, args.label_regex,
                         args.test_exclude_regex, args.label_exclude_regex)

    # If no cases after filtering
    if len(cases) == 0:
        print("No cases selected after filtering")
        return

    # Create executor to run cases
    executor = Executor(
        cases,
        show_only=args.show_only,
        verbose=args.verbose,
        jobs=args.jobs,
    )

    # Run cases
    executor.run()

    # Print summary of case results
    all_ok = True
    print("\nCase Summary:")
    print("%8s  %-16s  %-42s  %-6s  %-6s  %-8s" %
          ("Number", "Driver", "Case Name", "Run", "Check", "Status"))
    for case in executor.cases:
        print(f"{case['index']:>8}  {case['driver']:<16}  "
              f"{case['name']:<42}  {case['run_ok']!s:<6}  "
              f"{case['check_ok']!s:<6}  {case['status']:<8}")
        all_ok &= case['check_ok']

    # If all cases not passed, exit with error
    if not all_ok:
        sys.exit("FAILED")

    # # Gather the outputs
    # baseline, test = executor.read_output_files()

    # # Run the regression test
    # reg_test = RegressionTester(args.tolerance)
    # ix = [f"{i}/{len(executor.cases)}" for i in range(1,
    #                                                   len(executor.cases) + 1)]
    # norm_res, pass_fail_list, norm_list = reg_test.test_norm(
    #     ix,
    #     cases,
    #     baseline,
    #     test
    # )

    # # Extract the attributes metadata and the data
    # attributes = [
    #     list(zip(info["attribute_names"], info["attribute_units"]))
    #     for _, info in baseline
    # ]
    # baseline_data = [data for data, _ in baseline]
    # test_data = [data for data, _ in test]

    # # Create the regression test summaries
    # summary = SummaryHandler(args.plot, executor.local_test_location)
    # plots = summary.retrieve_plot_html(
    #     baseline_data, test_data, attributes, pass_fail_list)
    # summary.create_results_summary(
    #     cases, attributes, norm_res, norm_list, plots, args.tolerance)


def filter_cases(cases: List[dict],
                 test_regex: str = "",
                 label_regex: str = "",
                 test_exclude_regex: str = "",
                 label_exclude_regex: str = "") -> List[dict]:
    if test_regex:
        _re = re.compile(test_regex, re.IGNORECASE)
        cases = [case for case in cases if _re.search(case["name"])]
    if label_regex:
        _re = re.compile(label_regex, re.IGNORECASE)
        cases = [case for case in cases if _re.search(case["labels"])]
    if test_exclude_regex:
        _re = re.compile(test_exclude_regex, re.IGNORECASE)
        cases = [case for case in cases if not _re.search(case["name"])]
    if label_exclude_regex:
        _re = re.compile(label_exclude_regex, re.IGNORECASE)
        cases = [case for case in cases if not _re.search(case["labels"])]
    return cases


def parse_test_config(root_path: str, text: str) -> List[dict]:
    """"""

    # Parse configuration from text
    config = yaml.load(text, yaml.Loader)

    # Get default case
    default_case = config.pop('default_case', {})

    # Create list to hold cases
    cases = []

    # Loop through drivers
    for driver_name, driver in config.items():

        # Add driver name to driver dict
        driver['driver'] = driver_name

        # Loop through cases in driver
        for case_name, case in driver.get('cases', {}).items():

            # Combine default case, driver, and case fields
            case = {**default_case, **driver, **case, "name": case_name}

            # Calculate case specific paths
            if 'input_directory' in case:
                case['input_path'] = os.path.join(case['input_path'],
                                                  case['input_directory'])
            else:
                case['input_path'] = os.path.join(
                    case['input_path'], case['name'])
            case['run_path'] = os.path.join(case['run_path'], case['name'])

            # Calculate input file path
            if 'input_file' not in case:
                if 'input_file_ext' in case:
                    case['input_file'] = case['name'] + case['input_file_ext']
                else:
                    raise Exception(
                        f"{case_name} missing 'input_file' or 'input_file_ext'")
            case['input_file_path'] = os.path.join(
                case['run_path'], case['input_file'])

            # Create log file path
            case['log_path'] = os.path.join(
                case['run_path'], case['name'] + '.log')

            # Expand turbine directory if specified
            if 'turbine_directory' in case:
                case['turbine_input_path'] = \
                    os.path.join(driver['input_path'],
                                 case['turbine_directory'])
                case['turbine_run_path'] = \
                    os.path.join(driver['run_path'], case['turbine_directory'])

            # Expand paths in case with root_path
            for path in filter(lambda k: k.endswith('_path'), case.keys()):
                case[path] = os.path.join(root_path, case[path])

            # Add case to cases
            cases.append(case)

    return cases


def parse_args(args: List[str]) -> argparse.Namespace:
    """
    Parse arguments from command line with 'argparse'.

    Parameters
    ----------
    args : List[str]
        Command line arguments (sys.argv[1:])

    Returns
    -------
    argparse.Namespace
        Namespace containing parsed argument values.
    """

    parser = argparse.ArgumentParser(
        description=("Executes the requested cases and quantifies " +
                     "the difference in local and baseline results."),
        prog="pyFAST"
    )
    parser.add_argument(
        "-V",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="Enable verbose output from tests.",
    )
    parser.add_argument(
        "-VV",
        "--extra-verbose",
        dest="extra_verbose",
        action="store_true",
        help="Enable more verbose output from tests.",
    )
    parser.add_argument(
        "--output-on-failure",
        dest="output_on_failure",
        action="store_true",
        help="Output anything from test program if it should fail.",
    )
    parser.add_argument(
        "--stop-on-failure",
        dest="stop_on_failure",
        action="store_true",
        help="Stop running tests on the first failure.",
    )
    parser.add_argument(
        "-j",
        "--parallel",
        dest="jobs",
        type=int,
        default=-1,
        help="Number of cases to run in parallel. Use -1 for 80 percent of available cores",
    )
    parser.add_argument(
        "-N",
        "--show-only",
        dest="show_only",
        action="store_true",
        help="Disable execution of tests. Shows which tests would be run but doesn't run them.",
    )
    parser.add_argument(
        "-L",
        "--label-regex",
        dest="label_regex",
        type=str,
        default="",
        help='Run tests with labels matching the regular expression.',
    )
    parser.add_argument(
        "-R",
        "--test-regex",
        dest="test_regex",
        type=str,
        default="",
        help='Run tests with names matching the regular expression.',
    )
    parser.add_argument(
        "-E",
        "--exclude-regex",
        dest="test_exclude_regex",
        type=str,
        default="",
        help='Exclude tests with names matching the regular expression.',
    )
    parser.add_argument(
        "-LE",
        "--label-exclude",
        dest="label_exclude_regex",
        type=str,
        default="",
        help='Exclude tests with labels matching the regular expression.',
    )
    parser.add_argument(
        "-c",
        "--test-config",
        dest="test_config",
        type=str,
        default="test_config.yaml",
        help="YAML file containing test configurations.",
    )
    parser.add_argument(
        "--repo-root",
        dest="repo_root",
        type=str,
        default=".",
        help="Path to the OpenFAST repository",
    )

    return parser.parse_args(args)


if __name__ == '__main__':
    run_cli()
