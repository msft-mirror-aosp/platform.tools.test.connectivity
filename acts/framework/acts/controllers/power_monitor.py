#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import os
import logging
from acts.controllers.monsoon_lib.api.common import MonsoonError
from acts.test_utils.instrumentation.power.power_metrics import Measurement
from acts.test_utils.instrumentation.power.power_metrics import MILLIAMP
from acts.test_utils.instrumentation.power.power_metrics import PowerMetrics


class ResourcesRegistryError(Exception):
    pass


_REGISTRY = {}


def update_registry(registry):
    """Updates the registry with the one passed.

    Overriding a previous value is not allowed.

    Args:
        registry: A dictionary.
    Raises:
        ResourceRegistryError if a property is updated with a different value.
    """
    for k, v in registry.items():
        if k in _REGISTRY:
            if v == _REGISTRY[k]:
                continue
            raise ResourcesRegistryError(
                'Overwriting resources_registry fields is not allowed. %s was '
                'already defined as %s and was attempted to be overwritten '
                'with %s.' % (k, _REGISTRY[k], v))
        _REGISTRY[k] = v


def get_registry():
    return _REGISTRY


def _write_raw_data_in_improved_format(raw_data, path, start_time):
    """Writes the raw data to a file in (seconds since epoch, milliamps).

    TODO(b/155294049): Deprecate this once Monsoon controller output
        format is updated.

    Args:
        start_time: Measurement start time in seconds since epoch
        raw_data: raw data as list or generator of (timestamp, sample)
        path: path to write output
    """
    with open(path, 'w') as f:
        for timestamp, sample in raw_data:
            f.write('%s %s\n' %
                    (timestamp + start_time,
                     Measurement.amps(sample).to_unit(MILLIAMP).value))


class PowerMonitorFacade(object):

    def __init__(self, monsoon):
        """Constructs a PowerMonitorFacade.

        Args:
            monsoon: delegate monsoon object, either
                acts.controllers.monsoon_lib.api.hvpm.monsoon.Monsoon or
                acts.controllers.monsoon_lib.api.lvpm_stock.monsoon.Monsoon.
        """
        self.monsoon = monsoon
        self._log = logging.getLogger()

    def setup(self, monsoon_config=None, **__):
        """Set up the Monsoon controller for this testclass/testcase."""

        if monsoon_config is None:
            raise MonsoonError('monsoon_config can not be None')

        self._log.info('Setting up Monsoon %s' % self.monsoon.serial)
        voltage = monsoon_config.get_numeric('voltage', 4.2)
        self.monsoon.set_voltage_safe(voltage)
        if 'max_current' in monsoon_config:
            self.monsoon.set_max_current(
                monsoon_config.get_numeric('max_current'))

    def connect_usb(self, **__):
        self.monsoon.usb('on')

    def start_measurement(self, measurement_args=None, start_time=None,
                          output_path=None, **__):
        if measurement_args is None:
            raise MonsoonError('measurement_args can not be None')

        self.monsoon.measure_power(**measurement_args,
                                   output_path=output_path)

        if output_path and start_time is not None:
            _write_raw_data_in_improved_format(
                PowerMetrics.import_raw_data(output_path),
                os.path.join(os.path.dirname(output_path), 'monsoon.txt'),
                start_time
            )

    def stop_measurement(self, **__):
        # nothing to do
        pass

    def disconnect_usb(self, **__):
        self.monsoon.usb('off')

    def get_metrics(self, start_time=None, voltage=None, monsoon_file_path=None,
                    timestamps=None, **__):
        if start_time is None:
            raise MonsoonError('start_time can not be None')
        if voltage is None:
            raise MonsoonError('voltage can not be None')
        if monsoon_file_path is None:
            raise MonsoonError('monsoon_file_path can not be None')

        power_metrics = PowerMetrics(
            voltage=voltage,
            start_time=start_time)
        power_metrics.generate_test_metrics(
            PowerMetrics.import_raw_data(monsoon_file_path),
            timestamps)
        return power_metrics

    def teardown(self, **__):
        # nothing to do
        pass
