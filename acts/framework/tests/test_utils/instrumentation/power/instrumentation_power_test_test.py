#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest

from acts import signals
from acts.controllers import power_metrics
from acts.test_utils.instrumentation import instrumentation_proto_parser as parser
from acts.test_utils.instrumentation.config_wrapper import ConfigWrapper
from acts.test_utils.instrumentation.power.instrumentation_power_test import ACCEPTANCE_THRESHOLD
from acts.test_utils.instrumentation.power.instrumentation_power_test import InstrumentationPowerTest
import mock

# avg: 2.214, stdev: 1.358, max: 4.78, min: 0.61
AMPS = [1.64, 2.98, 1.72, 3.45, 1.31, 4.78, 3.43, 0.61, 1.19, 1.03]
RAW_DATA = list(zip(range(10), AMPS))
# timestamps that cover all samples
TIMESTAMP_LIMITS = {parser.START_TIMESTAMP: 0,
                    parser.END_TIMESTAMP: 10_000}

TIMESTAMPS = {'instrTest1': TIMESTAMP_LIMITS,
              'instrTest2': TIMESTAMP_LIMITS}

METRICS = power_metrics.generate_test_metrics(
    raw_data=RAW_DATA, voltage=4.2, timestamps=TIMESTAMPS)


class MockInstrumentationPowerTest(InstrumentationPowerTest):
    """Mock test class to initialize required attributes."""

    def __init__(self):
        self.log = mock.Mock()
        self.metric_logger = mock.Mock()
        self.current_test_name = 'test_case'
        self._instrumentation_config = ConfigWrapper({ACCEPTANCE_THRESHOLD: {}})

    def set_criteria(self, criteria):
        """Set the acceptance criteria for metrics validation."""
        self._instrumentation_config = ConfigWrapper(
            {ACCEPTANCE_THRESHOLD: criteria})


class InstrumentationPowerTestTest(unittest.TestCase):
    """Unit tests for InstrumentationPowerTest."""

    def setUp(self):
        self.instrumentation_power_test = MockInstrumentationPowerTest()

    def test_validate_power_results_lower_and_upper_limit_accept(self):
        """Test that validate_power_results accept passing measurements
        given a lower and upper limit.
        """
        criteria_accept = {
            'instrTest1': {
                'avg_current': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'lower_limit': 1.5,
                    'upper_limit': 2.5
                },
                'max_current': {
                    'unit_type': 'current',
                    'unit': 'mA',
                    'upper_limit': 5000
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_accept)
        with self.assertRaises(signals.TestPass):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1')

    def test_validate_power_results_lower_and_upper_limit_reject(self):
        """Test that validate_power_results reject failing measurements
        given a lower and upper limit.
        """
        criteria_reject = {
            'instrTest1': {
                'avg_current': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'lower_limit': 1.5,
                    'upper_limit': 2
                },
                'max_current': {
                    'unit_type': 'current',
                    'unit': 'mA',
                    'upper_limit': 4000
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_reject)
        with self.assertRaises(signals.TestFailure):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1')

    def test_validate_power_results_expected_value_and_deviation_accept(self):
        """Test that validate_power_results accept passing measurements
        given an expected value and percent deviation.
        """
        criteria_accept = {
            'instrTest1': {
                'stdev_current': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'expected_value': 1.5,
                    'percent_deviation': 20
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_accept)
        with self.assertRaises(signals.TestPass):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1')

    def test_validate_power_results_expected_value_and_deviation_reject(self):
        """Test that validate_power_results reject failing measurements
        given an expected value and percent deviation.
        """
        criteria_reject = {
            'instrTest1': {
                'min_current': {
                    'unit_type': 'current',
                    'unit': 'mA',
                    'expected_value': 500,
                    'percent_deviation': 10
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_reject)
        with self.assertRaises(signals.TestFailure):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1')

    def test_validate_power_results_no_such_test(self):
        """Test that validate_power_results skip validation if there are no
        criteria matching the specified instrumentation test name.
        """
        criteria_wrong_test = {
            'instrTest2': {
                'min_current': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'expected_value': 2,
                    'percent_deviation': 20
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_wrong_test)
        with self.assertRaises(signals.TestPass):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1')

    def test_validate_power_results_no_such_metric(self):
        """Test that validate_power_results skip validation if the specified
        metric is invalid.
        """
        criteria_invalid_metric = {
            'instrTest1': {
                'no_such_metric': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'lower_limit': 5,
                    'upper_limit': 7
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_invalid_metric)
        with self.assertRaises(signals.TestPass):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1')

    def test_validate_power_results_criteria_missing_params(self):
        """Test that validate_power_results skip validation if the specified
        metric has missing parameters.
        """
        criteria_missing_params = {
            'instrTest1': {
                'avg_current': {
                    'unit': 'A',
                    'lower_limit': 1,
                    'upper_limit': 2
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_missing_params)
        with self.assertRaises(signals.TestPass):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1')

    def test_validate_power_results_pass_if_all_tests_accept(self):
        """Test that validate_power_results succeeds if it accepts the results
        of all instrumentation tests.
        """
        criteria_multi_test_accept = {
            'instrTest1': {
                'avg_current': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'lower_limit': 2
                },
                'stdev_current': {
                    'unit_type': 'current',
                    'unit': 'mA',
                    'expected_value': 1250,
                    'percent_deviation': 30
                }
            },
            'instrTest2': {
                'max_current': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'upper_limit': 5
                },
                'avg_power': {
                    'unit_type': 'power',
                    'unit': 'W',
                    'upper_limit': 10
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_multi_test_accept)
        with self.assertRaises(signals.TestPass):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1',
                                                             'instrTest2')

    def test_validate_power_results_fail_if_at_least_one_test_rejects(self):
        """Test that validate_power_results fails if it rejects the results
        of at least one instrumentation test.
        """
        criteria_multi_test_reject = {
            'instrTest1': {
                'avg_current': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'lower_limit': 2
                },
                'stdev_current': {
                    'unit_type': 'current',
                    'unit': 'mA',
                    'expected_value': 1250,
                    'percent_deviation': 30
                }
            },
            'instrTest2': {
                'max_current': {
                    'unit_type': 'current',
                    'unit': 'A',
                    'upper_limit': 5
                },
                'avg_power': {
                    'unit_type': 'power',
                    'unit': 'W',
                    'upper_limit': 8
                }
            }
        }
        self.instrumentation_power_test.set_criteria(criteria_multi_test_reject)
        with self.assertRaises(signals.TestFailure):
            self.instrumentation_power_test.validate_metrics(METRICS,
                                                             'instrTest1',
                                                             'instrTest2')


if __name__ == '__main__':
    unittest.main()
