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

from acts.controllers.power_metrics import Metric


class AbsoluteThresholds(object):
    """Class to represent thresholds in absolute (non-relative) values.

    Attributes:
        lower: Lower limit of the threshold represented by a measurement.
        upper: Upper limit of the threshold represented by a measurement.
        unit_type: Type of the unit (current, power, etc).
        unit: The  unit for this threshold (W, mW, uW).
    """

    def __init__(self, lower, upper, unit_type, unit):
        self.unit_type = unit_type
        self.unit = unit
        self.lower = Metric(lower, unit_type, unit)
        self.upper = Metric(upper, unit_type, unit)

    @staticmethod
    def from_percentual_deviation(expected, percentage, unit_type, unit):
        """Creates an AbsoluteThresholds object from an expected value and its
        allowed percentual deviation (also in terms of the expected value).

        For example, if the expected value is 20 and the deviation 25%, this
        would imply that the absolute deviation is 20 * 0.25 = 5 and therefore
        the absolute threshold would be from (20-5, 20+5) or (15, 25).

        Args:
            expected: Central value from which the deviation will be estimated.
            percentage: Percentage of allowed deviation, the percentage itself
            is in terms of the expected value.
            unit_type: Type of the unit (current, power, etc).
            unit: Unit for this threshold (W, mW, uW).
        """
        return AbsoluteThresholds(expected * (1 - percentage / 100),
                                  expected * (1 + percentage / 100),
                                  unit_type,
                                  unit)

    @staticmethod
    def from_threshold_conf(thresholds_conf):
        """Creates a AbsoluteThresholds object from a ConfigWrapper describing
        a threshold (either absolute or percentual).

        Args:
            thresholds_conf: ConfigWrapper object that describes a threshold.
        Returns:
            AbsolutesThresholds object.
        Raises:
            ValueError if configuration is incorrect or incomplete.
        """
        if 'unit_type' not in thresholds_conf:
            raise ValueError(
                'A threshold config must contain a unit_type. %s is incorrect'
                % str(thresholds_conf))

        if 'unit' not in thresholds_conf:
            raise ValueError(
                'A threshold config must contain a unit. %s is incorrect'
                % str(thresholds_conf))

        unit_type = thresholds_conf['unit_type']
        unit = thresholds_conf['unit']

        is_relative = (
            'expected_value' in thresholds_conf and
            'percent_deviation' in thresholds_conf)

        is_almost_relative = (
            'expected_value' in thresholds_conf or
            'percent_deviation' in thresholds_conf)

        is_absolute = ('lower_limit' in thresholds_conf or
                       'upper_limit' in thresholds_conf)

        if is_absolute and is_almost_relative:
            raise ValueError(
                'Thresholds can either be absolute (with lower_limit and'
                'upper_limit defined) or by percentual deviation (with'
                'expected_value and percent_deviation defined), but never'
                'a mixture of both. %s is incorrect'
                % str(thresholds_conf))

        if is_almost_relative and not is_relative:
            if 'expected_value' not in thresholds_conf:
                raise ValueError(
                    'Incomplete definition of a threshold by percentual '
                    'deviation. percent_deviation given, but missing '
                    'expected_value. %s is incorrect'
                    % str(thresholds_conf))

            if 'percent_deviation' not in thresholds_conf:
                raise ValueError(
                    'Incomplete definition of a threshold by percentual '
                    'deviation. expected_value given, but missing '
                    'percent_deviation. %s is incorrect'
                    % str(thresholds_conf))

        if not is_absolute and not is_relative:
            raise ValueError(
                'Thresholds must be either absolute (with lower_limit and'
                'upper_limit defined) or defined by percentual deviation (with'
                'expected_value and percent_deviation defined). %s is incorrect'
                % str(thresholds_conf))

        if is_relative:
            expected = thresholds_conf.get_numeric('expected_value')
            percent = thresholds_conf.get_numeric('percent_deviation')

            thresholds = (
                AbsoluteThresholds.from_percentual_deviation(
                    expected,
                    percent,
                    unit_type, unit))

        else:
            lower_value = thresholds_conf.get_numeric('lower_limit',
                                                      float('-inf'))
            upper_value = thresholds_conf.get_numeric('upper_limit',
                                                      float('inf'))
            thresholds = AbsoluteThresholds(lower_value, upper_value, unit_type,
                                            unit)
        return thresholds
