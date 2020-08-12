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

import math

from acts.test_utils.instrumentation import instrumentation_proto_parser as parser
from acts.test_utils.instrumentation.instrumentation_base_test import InstrumentationTestError

# Unit type constants
CURRENT = 'current'
POWER = 'power'
TIME = 'time'
VOLTAGE = 'voltage'

# Unit constants
MILLIVOLT = 'mV'
VOLT = 'V'
MILLIAMP = 'mA'
AMP = 'A'
AMPERE = AMP
MILLIWATT = 'mW'
WATT = 'W'
MILLISECOND = 'ms'
SECOND = 's'
MINUTE = 'm'
HOUR = 'h'

CONVERSION_TABLES = {
    CURRENT: {
        MILLIAMP: 0.001,
        AMP: 1
    },
    POWER: {
        MILLIWATT: 0.001,
        WATT: 1
    },
    TIME: {
        MILLISECOND: 0.001,
        SECOND: 1,
        MINUTE: 60,
        HOUR: 3600
    },
    VOLTAGE: {
        MILLIVOLT: 0.001,
        VOLT : 1
    }
}


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


class Metric(object):
    """Base class for describing power measurement values. Each object contains
    an value and a unit. Enables some basic arithmetic operations with other
    measurements of the same unit type.

    Attributes:
        value: Numeric value of the measurement
        _unit_type: Unit type of the measurement (e.g. current, power)
        unit: Unit of the measurement (e.g. W, mA)
    """

    def __init__(self, value, unit_type, unit, name=None):
        if unit_type not in CONVERSION_TABLES:
            raise TypeError(
                '%s is not a valid unit type, valid unit types are %s' % (
                    unit_type, str(CONVERSION_TABLES.keys)))
        self.value = value
        self.unit = unit
        self.name = name
        self._unit_type = unit_type

    # Convenience constructor methods
    @staticmethod
    def amps(amps, name=None):
        """Create a new current measurement, in amps."""
        return Metric(amps, CURRENT, AMP, name=name)

    @staticmethod
    def watts(watts, name=None):
        """Create a new power measurement, in watts."""
        return Metric(watts, POWER, WATT, name=name)

    @staticmethod
    def seconds(seconds, name=None):
        """Create a new time measurement, in seconds."""
        return Metric(seconds, TIME, SECOND, name=name)

    # Comparison methods

    def __eq__(self, other):
        return self.value == other.to_unit(self.unit).value

    def __lt__(self, other):
        return self.value < other.to_unit(self.unit).value

    def __le__(self, other):
        return self == other or self < other

    # Addition and subtraction with other measurements

    def __add__(self, other):
        """Adds measurements of compatible unit types. The result will be in the
        same units as self.
        """
        return Metric(self.value + other.to_unit(self.unit).value,
                      self._unit_type, self.unit, name=self.name)

    def __sub__(self, other):
        """Subtracts measurements of compatible unit types. The result will be
        in the same units as self.
        """
        return Metric(self.value - other.to_unit(self.unit).value,
                      self._unit_type, self.unit, name=self.name)

    # String representation

    def __str__(self):
        return '%g%s' % (self.value, self.unit)

    def __repr__(self):
        return str(self)

    def to_unit(self, new_unit):
        """Create an equivalent measurement under a different unit.
        e.g. 0.5W -> 500mW

        Args:
            new_unit: Target unit. Must be compatible with current unit.

        Returns: A new measurement with the converted value and unit.
        """
        try:
            new_value = self.value * (
                CONVERSION_TABLES[self._unit_type][self.unit] /
                CONVERSION_TABLES[self._unit_type][new_unit])
        except KeyError:
            raise TypeError('Incompatible units: %s, %s' %
                            (self.unit, new_unit))
        return Metric(new_value, self._unit_type, new_unit, self.name)


def import_raw_data(path):
    """Create a generator from a Monsoon data file.

    Args:
        path: path to raw data file

    Returns: generator that yields (timestamp, sample) per line
    """
    with open(path, 'r') as f:
        for line in f:
            time, sample = line.split()
            yield float(time[:-1]), float(sample)


def generate_test_metrics(raw_data, timestamps=None,
                          voltage=None):
    """Split the data into individual test metrics, based on the timestamps
    given as a dict.

    Args:
        raw_data: raw data as list or generator of (timestamp, sample)
        timestamps: dict following the output format of
            instrumentation_proto_parser.get_test_timestamps()
        voltage: voltage used during measurements
    """

    # Initialize metrics for each test
    if timestamps is None:
        timestamps = {}
    test_starts = {}
    test_ends = {}
    test_metrics = {}
    for seg_name, times in timestamps.items():
        test_metrics[seg_name] = PowerMetrics(voltage)
        try:
            test_starts[seg_name] = Metric(
                times[parser.START_TIMESTAMP], TIME, MILLISECOND).to_unit(
                SECOND).value
        except KeyError:
            raise InstrumentationTestError(
                'Missing start timestamp for test scenario "%s". Refer to '
                'instrumentation_proto.txt for details.' % seg_name)
        try:
            test_ends[seg_name] = Metric(
                times[parser.END_TIMESTAMP], TIME, MILLISECOND).to_unit(
                SECOND).value
        except KeyError:
            raise InstrumentationTestError(
                'Missing end timestamp for test scenario "%s". Test '
                'scenario may have terminated with errors. Refer to '
                'instrumentation_proto.txt for details.' % seg_name)

    # Assign data to tests based on timestamps
    for timestamp, amps in raw_data:
        for seg_name in timestamps:
            if test_starts[seg_name] <= timestamp <= test_ends[seg_name]:
                test_metrics[seg_name].update_metrics(amps)

    result = {}
    for seg_name, power_metrics in test_metrics.items():
        result[seg_name] = [
            power_metrics.avg_current,
            power_metrics.max_current,
            power_metrics.min_current,
            power_metrics.stdev_current,
            power_metrics.avg_power]
    return result


class PowerMetrics(object):
    """Class for processing raw power metrics generated by Monsoon measurements.
    Provides useful metrics such as average current, max current, and average
    power. Can generate individual test metrics.

    See section "Numeric metrics" below for available metrics.
    """

    def __init__(self, voltage):
        """Create a PowerMetrics.

        Args:
            voltage: Voltage of the measurement
        """
        self._voltage = voltage
        self._num_samples = 0
        self._sum_currents = 0
        self._sum_squares = 0
        self._max_current = None
        self._min_current = None
        self.test_metrics = {}

    def update_metrics(self, sample):
        """Update the running metrics with the current sample.

        Args:
            sample: A current sample in Amps.
        """
        self._num_samples += 1
        self._sum_currents += sample
        self._sum_squares += sample ** 2
        if self._max_current is None or sample > self._max_current:
            self._max_current = sample
        if self._min_current is None or sample < self._min_current:
            self._min_current = sample

    # Numeric metrics
    @property
    def avg_current(self):
        """Average current, in milliamps."""
        if not self._num_samples:
            return Metric.amps(0).to_unit(MILLIAMP)
        return (Metric.amps(self._sum_currents / self._num_samples,
                            'avg_current')
                .to_unit(MILLIAMP))

    @property
    def max_current(self):
        """Max current, in milliamps."""
        return Metric.amps(self._max_current or 0, 'max_current').to_unit(
            MILLIAMP)

    @property
    def min_current(self):
        """Min current, in milliamps."""
        return Metric.amps(self._min_current or 0, 'min_current').to_unit(
            MILLIAMP)

    @property
    def stdev_current(self):
        """Standard deviation of current values, in milliamps."""
        if self._num_samples < 2:
            return Metric.amps(0, 'stdev_current').to_unit(MILLIAMP)
        stdev = math.sqrt(
            (self._sum_squares - (
                self._num_samples * self.avg_current.to_unit(AMP).value ** 2))
            / (self._num_samples - 1))
        return Metric.amps(stdev, 'stdev_current').to_unit(MILLIAMP)

    @property
    def avg_power(self):
        """Average power, in milliwatts."""
        return Metric.watts(self.avg_current.to_unit(AMP).value * self._voltage,
                            'avg_power').to_unit(MILLIWATT)
