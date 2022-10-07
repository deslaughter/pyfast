
from typing import List, Tuple
import numpy as np
from functools import partial
from multiprocessing.pool import Pool
from .norm import calculate_norms, pass_regression_test


class RegressionTester:

    def __init__(self, tolerance):
        self.jobs = 1
        self.tolerance = tolerance

    def test_norm(
        self,
        ix_list: List[str],
        case_list: List[str],
        baseline_list: List[Tuple[np.ndarray, list]],
        test_list: List[Tuple[np.ndarray, list]],
        norm_list: List[str] = ["max_norm",
                                "max_norm_over_range", "l2_norm", "relative_l2_norm"],
        test_norm_condition: List[str] = [
            "relative_l2_norm"],  # flag in __main__.py
    ) -> Tuple[List[np.ndarray], List[bool], List[str]]:
        """
        Computes the norms for each of the valid test cases.

        Parameters
        ----------
        ix_list : List[str]
            List of indices for cases to be run in the form of "i/N".
        case_list : List[str]
            List of valid cases where a norm can be computed.
        baseline_list : List[Tuple[np.ndarray, list]]
            Tuples of baseline data and info corresponding to `case_list.
        test_list : List[Tuple[np.ndarray, list]]
            Tuples of test data and info correpsonding to `case_list`.
        norm_list : List[str], optional
            List of norms to be computed, by default:
            ["max_norm","max_norm_over_range","l2_norm","relative_l2_norm"]
        test_norm_condition : List[str]
            Defines which norm(s) to use for the pass/fail condition, by
            default ["relative_l2_norm"].
        jobs : int
            Number of parallel jobs to compute the norms and test them.

        Returns
        -------
        norm_results : List[np.ndarray]
            List of norm results corresponding to `case_list`. Each array will
            have shape [len(attributes), len(norm_list)]
        pass_fail_list : List[bool]
            A list of indicators for if the case passed the regression test.
        norm_list : List[str]
            `norm_list`.
        """

        # Test to make sure that the test norm is included in the computed norms
        if not set(test_norm_condition).issubset(norm_list):
            message = (
                f"test_norm_condition: {test_norm_condition} should be contained in "
                f"norm_list: {norm_list}."
            )
            raise ValueError(message)

        norm_results = []
        arguments = [[b[0], t[0]] for b, t in zip(baseline_list, test_list)]
        partial_norms = partial(calculate_norms, norms=norm_list)
        with Pool(self.jobs) as pool:
            norm_results = list(pool.starmap(partial_norms, arguments))

        norm_ix = [norm_list.index(norm) for norm in test_norm_condition]
        arguments = [(norm[:, norm_ix], self.tolerance)
                     for norm in norm_results]
        with Pool(self.jobs) as pool:
            pass_fail_list = list(pool.starmap(
                pass_regression_test, arguments))

        n_fail = len(pass_fail_list) - sum(pass_fail_list)
        fail = []
        for ix, case, _pass in zip(ix_list, case_list, pass_fail_list):
            ix = ix.split("/")[0]
            if not _pass:
                fail.append((ix, case))
            pf = "pass" if _pass else "\x1b[1;31mFAIL\x1b[0m"
            print(f"{ix.rjust(6)}  TEST: {case.ljust(40, '.')} {pf}")

        print(f"\n{str(n_fail).rjust(6)} cases \x1b[1;31mFAILED\x1b[0m")
        for ix, case in fail:
            ix = ix.split("/")[0]
            message = f"\x1b[1;31m{ix.rjust(8)} {case}\x1b[0m"
            print(message)

        return norm_results, pass_fail_list, norm_list


def passing_channels(test, baseline, rtol, atol) -> np.ndarray:
    """
    test, baseline: arrays containing the results from OpenFAST in the following format
        [
            channels,
            data
        ]
    So that test[0,:] are the data for the 0th channel and test[:,0] are the 0th entry in each channel.
    """

    NUM_EPS = 1e-12
    ATOL_MIN = 1e-6

    n_channels = np.shape(test)[0]
    where_close = np.zeros_like(test, dtype=bool)

    rtol = 10**(-1 * rtol)
    baseline_offset = baseline - np.amin(baseline, axis=1, keepdims=True)
    b_order_of_magnitude = np.floor(np.log10(baseline_offset + NUM_EPS))
    # atol = 10**(-1 * atol)
    # atol = max( atol, 1e-6 )
    # atol[atol < ATOL_MIN] = ATOL_MIN
    atol = 10**(np.amax(b_order_of_magnitude) - atol)
    atol = max(atol, ATOL_MIN)
    where_close = np.isclose(test, baseline, atol=atol, rtol=rtol)

    where_not_nan = ~np.isnan(test)
    where_not_inf = ~np.isinf(test)

    # Return array of booleans indicating which channels are passing
    return np.all(where_close * where_not_nan * where_not_inf, axis=1)


def maxnorm(data, axis=0):
    return np.linalg.norm(data, np.inf, axis=axis)


def l2norm(data, axis=0):
    return np.linalg.norm(data, 2, axis=axis)


def calculate_relative_norm(testData, baselineData):
    norm_diff = l2norm(testData - baselineData)
    norm_baseline = l2norm(baselineData)

    # replace any 0s with small number before for division
    norm_baseline[norm_baseline == 0] = 1e-16

    norm = norm_diff.copy()
    ix_non_diff = (norm_baseline >= 1)
    norm[ix_non_diff] = norm_diff[ix_non_diff] / norm_baseline[ix_non_diff]
    return norm


def calculate_max_norm_over_range(test_data, baseline_data):
    channel_ranges = np.abs(baseline_data.max(
        axis=0) - baseline_data.min(axis=0))
    diff = abs(test_data - baseline_data)

    ix_non_diff = (channel_ranges >= 1)
    norm = maxnorm(diff, axis=0)
    norm[ix_non_diff] = maxnorm(
        diff[:, ix_non_diff] / channel_ranges[ix_non_diff])

    return norm


def calculate_max_norm(testData, baselineData):
    return maxnorm(abs(testData - baselineData))


def calculateNorms(test_data, baseline_data):
    if test_data.size != baseline_data.size:
        # print("Calculate Norms size(testdata)={}".format(test_data.size))
        # print("Calculate Norms size(baseline)={}".format(baseline_data.size))
        relative_norm = np.nan * \
            calculate_max_norm_over_range(test_data, test_data)
        max_norm = relative_norm
        relative_l2_norm = relative_norm
    else:
        relative_norm = calculate_max_norm_over_range(test_data, baseline_data)
        max_norm = calculate_max_norm(test_data, baseline_data)
        relative_l2_norm = calculate_relative_norm(test_data, baseline_data)

    results = np.stack(
        (
            relative_norm,
            relative_l2_norm,
            max_norm
        ),
        axis=1
    )
    return results
