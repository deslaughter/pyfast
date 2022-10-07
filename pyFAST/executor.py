
import os
import shutil
from typing import List, Tuple
from multiprocessing import cpu_count
from multiprocessing.pool import Pool
from time import perf_counter
import subprocess
import glob

import numpy as np

from .utilities import (
    validate_file,
    validate_directory,
    validate_executable
)
from .fast_io import load_output
from .regression_tester import passing_channels, calculateNorms
from .error_plotting import export_case_summary, plot_channel_data


class Executor:
    """
    Base execution class for OpenFAST regression tests.

    This class first constructs the internal directories containing the test case input files.
    Then, the test cases are executed using multiple processors, if requested.
    The locally generated outputs are tested against their corresponding baselines.

    Attributes
    ----------
    """

    def __init__(
            self,
            cases: List[dict],
            show_only: bool = False,
            verbose: bool = False,
            jobs: bool = -1,
    ):
        """
        Initialize the required inputs

        TODO:
        - There should exist a test pipeline that executes the full regression test process for each case
        - Thats what should be parallelized, not just the case execution
        - As is, the regression test results must wait for all tests to finish executing
        - We want to be able to bail if one test case fails the regression test but others haven't finished

        - Choose to use str or Path for all paths

        Parameters
        ----------
        cases : List[str]
            Test cases as a list of dictionaries.
        show_only : bool, default: False
            Flag to avoid executing the simulations, but proceed with the regression test.
        verbose : bool, default: False
            Flag to include system ouptut.
        jobs : int, default: -1
            Maximum number of parallel jobs to run:
             - -1: Number of nodes available minus 1
             - >0: Minimum of the number passed and the number of nodes available
        """

        self.cases = cases
        self.verbose = verbose
        self.show_only = show_only
        self.jobs = jobs if jobs != 0 else -1

        # Set case index
        for i, case in enumerate(self.cases, 1):
            case['num'] = i
            case['index'] = f"{i}/{len(self.cases)}"

        self._validate_inputs()

        # Set the appropriate number of parallel jobs to run
        if self.jobs == -1:
            self.jobs = max(1, cpu_count() - 1)
        if self.jobs > 0:
            self.jobs = min(self.jobs, cpu_count())
        if self.jobs > len(self.cases):
            self.jobs = len(self.cases)

    def _validate_inputs(self):

        # Loop through cases
        for case in self.cases:

            # Validate path to case executable or script
            if 'executable_path' in case:
                validate_executable(case['executable_path'])
            elif 'script_path' in case:
                validate_file(case['script_path'])

            # Validate path to case input directory
            validate_directory(case['input_path'])

        #  Is the jobs flag within the supported range?
        if self.jobs < -1:
            raise ValueError("Invalid value given for 'jobs'")

    def _build_local_case_directories(self):
        """
        Copies the input data to the local directories where the tests will be run
        """

        # Create list to hold paths to which turbine directories have been copied
        turbine_copies = []

        # Loop through cases
        for case in self.cases:

            # Copy files from driver's input directory to output directory.
            # Overwrite existing files
            shutil.copytree(case['input_path'], case['run_path'],
                            dirs_exist_ok=True)

            # Get list of baseline files
            case['baseline_files'] = \
                [os.path.basename(f) for f in
                 glob.glob(os.path.join(case['input_path'],
                                        '*' + case['baseline_file_ext']))]

            # If no baseline files found, raise exception
            if len(case['baseline_files']) == 0:
                raise Exception(
                    f"no baseline files found for case '{case['name']}'")

            # Remove baseline files from run path
            for baseline_file in case['baseline_files']:
                os.remove(os.path.join(case['run_path'], baseline_file))

            # If case has a turbine directory and it hasn't been copied
            # by a previous case, copy directory and overwrite existing files
            if 'turbine_run_path' in case:
                if case['turbine_run_path'] not in turbine_copies:
                    shutil.copytree(case['turbine_input_path'],
                                    case['turbine_run_path'],
                                    dirs_exist_ok=True)
                    turbine_copies.append(case['turbine_run_path'])

    def _execute_case(
        self,
        case: dict,
        verbose: bool = False,
    ):
        """
        Runs an OpenFAST regression test case.

        Parameters
        ----------
        case : dict
            Dictionary describing case to run
        verbose : bool, optional
            Flag to include verbose output, by default False.
        """

        # Validate that input file exists
        validate_file(case['input_file_path'])

        # Create command to run case
        if 'executable_path' in case:
            command = [case['executable_path'], case['input_file']]
        elif 'script_path' in case:
            command = ['python', case['script_path'], case['input_file']]
        else:
            raise Exception("no executable specified for case")

        # Print info for logging
        msg = (f"{case['index']:>8}  Start: {case['name']}\n" +
               f"{case['index']:>8}    Cmd: {' '.join(command)}\n" +
               f"{case['index']:>8}    CWD: {case['run_path']}\n" +
               f"{case['index']:>8}    Log: {case['log_path']}")
        print(msg, flush=True)

        # Get environment to be passed to command, modify if required by case
        env = os.environ.copy()
        if 'lib_path' in case:
            env["PATH"] = case['lib_path'] + os.pathsep + env["PATH"]

        # Run command
        start_time = perf_counter()
        with open(case['log_path'], 'w') as w:
            case['ret_code'] = subprocess.call(command, stdout=w, stderr=w,
                                               cwd=case['run_path'], env=env)
        end_time = perf_counter()

        # Calculate elapsed time
        case['run_time'] = end_time - start_time

        # Set flag for run completed successfully
        case['run_ok'] = case['ret_code'] == 0

        # Set case status based on return code
        case['status'] = 'COMPLETE' if case['run_ok'] else 'FAILED'

    def _run_case(self, case: dict):
        """
        Runs a single OpenFAST test case

        Parameters
        ----------
        case : str
            Case name.
        """

        case['status'] = 'None'
        case['run_ok'] = False
        case['check_ok'] = False

        # Run test case
        self._execute_case(case, verbose=self.verbose)

        status = ""
        if self.verbose:
            for line in open(case['log_path']):
                status += f"\n{case['index']:>8}    Log: {line}"
        status = (f"{case['index']:>8}    Run: {case['name'].ljust(42, '.')} {case['status']:<8} with code "
                  f"{case['ret_code']} {case['run_time']:>8.3f} seconds")
        if not case['run_ok']:
            return case, status

        # Compare test case output to baseline
        self._compare_results_to_baseline(case)

        # Add to status
        for baseline_file, file_ok in zip(case['baseline_files'], case['check_files_ok']):
            file_status = "PASSED" if file_ok else 'FAILED'
            status += f"\n{case['index']:>8}  Check: {baseline_file.ljust(42)} {file_status:<8}"
        status += f"\n{case['index']:>8}    End: {case['name'].ljust(42, '.')} {case['status']:<8}"

        # Return message to display
        return case, status

    def _run_cases(self) -> List[dict]:
        """
        Runs all of the OpenFAST cases in parallel, if defined.
        """
        cases = []
        if self.jobs == 1:
            for case, status in map(self._run_case, self.cases):
                print(status, flush=True)
                cases.append(case)
        else:
            with Pool(self.jobs) as pool:
                for case, status in pool.imap_unordered(self._run_case, self.cases):
                    print(status, flush=True)
                    cases.append(case)

        self.cases = sorted(cases, key=lambda c: c['num'])

    def run(self):
        """
        Function to build the references to ouput directories. If executing
        OpenFAST, then the directories are created if they don't already exist.
        """

        if self.show_only:
            for case in self.cases:
                print(f"  Test {case['num']:>3}: {case['name']}")
            print(f"\nTotal Tests: {len(self.cases)}")
        else:
            self._build_local_case_directories()
            self._run_cases()

    def _compare_results_to_baseline(self, case: dict):

        case['check_ok'] = True

        case['check_files_ok'] = []

        # Loop through baseline files
        for baseline_file in case['baseline_files']:

            # Create path to baseline and output files
            baseline_file_path = os.path.join(
                case['input_path'], baseline_file)
            out_file_path = os.path.join(case['run_path'], baseline_file)

            # Validate files
            try:
                validate_file(out_file_path)
                validate_file(baseline_file_path)
            except FileNotFoundError as error:
                return f"\x1b[1;31m{case['name']}\x1b[0m: {error}\n"

            # Check output files
            if case['baseline_file_ext'] in ['.outb', '.out']:

                # Load output and baseline files
                out_data, out_info, _ = load_output(out_file_path)
                baseline_data, _, _ = load_output(baseline_file_path)

                # Get channel names
                channel_names = out_info["attribute_names"]
                channel_units = out_info["attribute_units"]

                # Determine which channels are passing relative to baseline
                channels_ok = passing_channels(out_data.T, baseline_data.T,
                                               case['relative_tolerance'],
                                               case['absolute_tolerance'])

                # Calculate norms
                norms = calculateNorms(out_data, baseline_data)

                # Plot channel data
                plots = []
                if case['plot']:
                    plots = plot_channel_data(channel_names, channel_units, out_data,
                                              baseline_data, case['relative_tolerance'],
                                              case['absolute_tolerance'])

                # Export all case summaries
                export_case_summary(case['run_path'], case['name'],
                                    channel_names, channels_ok, norms, plots)

                case['check_ok'] &= np.all(channels_ok)
                case['check_files_ok'].append(np.all(channels_ok))
                case['status'] = 'PASSED' if case['check_ok'] else 'FAILED'

            # Check linearization files
            elif case['baseline_file_ext'] == '.lin':
                case['check_ok'] &= False
                case['check_files_ok'].append(False)
                case['status'] = 'NOT_IMPL'
