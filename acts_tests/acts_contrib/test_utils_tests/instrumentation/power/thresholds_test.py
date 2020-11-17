#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
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

from acts.controllers.power_metrics import Metric
from acts_contrib.test_utils.instrumentation import config_wrapper
from acts_contrib.test_utils.instrumentation.power.thresholds import AbsoluteThresholds


class AbsoluteThresholdsTest(unittest.TestCase):
    def test_build_from_absolutes(self):
        thresholds = AbsoluteThresholds(lower=1, upper=2,
                                        unit_type='power',
                                        unit='mW')
        self.assertEqual(thresholds.lower, Metric(1, 'power', 'mW'))
        self.assertEqual(thresholds.upper, Metric(2, 'power', 'mW'))

    def test_build_from_percentual_deviation(self):
        """Test construction of thresholds defined by percentual deviation."""
        thresholds = (AbsoluteThresholds
                      .from_percentual_deviation(expected=100,
                                                 percentage=2,
                                                 unit_type='power',
                                                 unit='mW'))
        self.assertEqual(thresholds.lower, Metric(98, 'power', 'mW'))
        self.assertEqual(thresholds.upper, Metric(102, 'power', 'mW'))

    def test_build_from_absolutes_config(self):
        """Test that thresholds by absolute values can be built through configs.
        """
        config = config_wrapper.ConfigWrapper(
            {'lower_limit': 1, 'upper_limit': 2,
             'unit_type': 'power', 'unit': 'mW'})
        thresholds = AbsoluteThresholds.from_threshold_conf(config)
        self.assertEqual(thresholds.lower, Metric(1, 'power', 'mW'))
        self.assertEqual(thresholds.upper, Metric(2, 'power', 'mW'))

    def test_build_from_deviation_config(self):
        """Test that thresholds for percentual deviations can be built."""
        config = config_wrapper.ConfigWrapper(
            {'expected_value': 100, 'percent_deviation': 2,
             'unit_type': 'power', 'unit': 'mW'})
        thresholds = AbsoluteThresholds.from_threshold_conf(config)
        self.assertEqual(thresholds.lower, Metric(98, 'power', 'mW'))
        self.assertEqual(thresholds.upper, Metric(102, 'power', 'mW'))

    def test_build_from_config_without_unit_type(self):
        """Test that from_threshold_conf raises an error if not given a unit
        type."""
        config = config_wrapper.ConfigWrapper(
            {'expected_value': 100, 'percent_deviation': 2,
             'unit_type': 'power'})
        expected_msg = 'A threshold config must contain a unit'
        with self.assertRaisesRegex(ValueError, expected_msg):
            AbsoluteThresholds.from_threshold_conf(config)

    def test_build_from_config_without_unit(self):
        """Test that from_threshold_conf raises an error if not given a unit."""
        config = config_wrapper.ConfigWrapper(
            {'expected_value': 100, 'percent_deviation': 2,
             'unit': 'mW'})
        expected_msg = 'A threshold config must contain a unit_type'
        with self.assertRaisesRegex(ValueError, expected_msg):
            AbsoluteThresholds.from_threshold_conf(config)

    def test_build_from_config_without_limits_nor_deviation(self):
        """Test that from_threshold_conf raises an error if not given a limits
        nor percentual deviation arguments."""
        config = config_wrapper.ConfigWrapper(
            {'unit_type': 'power',
             'unit': 'mW'})
        expected_msg = ('Thresholds must be either absolute .* or defined by '
                        'percentual deviation')
        with self.assertRaisesRegex(ValueError, expected_msg):
            AbsoluteThresholds.from_threshold_conf(config)

    def test_build_from_deviation_config_without_expected_value(self):
        """Test that from_threshold_conf raises an error if percentual deviation
        definition is missing a expected value."""
        config = config_wrapper.ConfigWrapper(
            {'percent_deviation': 2,
             'unit_type': 'power', 'unit': 'mW'})
        expected_msg = ('Incomplete definition of a threshold by percentual '
                        'deviation. percent_deviation given, but missing '
                        'expected_value')
        with self.assertRaisesRegex(ValueError, expected_msg):
            AbsoluteThresholds.from_threshold_conf(config)

    def test_build_from_deviation_config_without_percent_deviation(self):
        """Test that from_threshold_conf raises an error if percentual deviation
        definition is missing a percent deviation value."""
        config = config_wrapper.ConfigWrapper(
            {'expected_value': 100,
             'unit_type': 'power', 'unit': 'mW'})
        expected_msg = ('Incomplete definition of a threshold by percentual '
                        'deviation. expected_value given, but missing '
                        'percent_deviation')
        with self.assertRaisesRegex(ValueError, expected_msg):
            AbsoluteThresholds.from_threshold_conf(config)
