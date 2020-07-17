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
from acts.controllers import bits
from acts.test_utils.instrumentation.power import power_metrics


class BitsTest(unittest.TestCase):

    def test_metric_name_transformation_for_legacy_support(self):
        avg_current = bits.transform_name('default_name.Monsoon.Monsoon:mA')
        avg_power = bits.transform_name('default_name.Monsoon.Monsoon:mW')

        self.assertEqual('avg_current', avg_current)
        self.assertEqual('avg_power', avg_power)

    def test_metric_name_transformation(self):
        avg_current = bits.transform_name('default_name.slider.XYZ:mA')
        avg_power = bits.transform_name('default_name.slider.ABCD:mW')
        unknown_unit = bits.transform_name('default_name.aaaaa.QWERTY:unknown')

        self.assertEqual('XYZ_avg_current', avg_current)
        self.assertEqual('ABCD_avg_power', avg_power)
        self.assertEqual('QWERTY', unknown_unit)

    def test_raw_data_to_metrics(self):
        raw_data = {'data': [
            {'name': 'default_device.Monsoon.Monsoon:mA',
             'avg': 21,
             'unit': 'mA'},
            {'name': 'default_device.Monsoon.Monsoon:mW',
             'avg': 91,
             'unit': 'mW'}]}

        metrics = bits.raw_data_to_metrics(raw_data)
        self.assertEqual(2, len(metrics))
        self.assertEqual(
            power_metrics.Metric(21, 'current', 'mA', 'avg_current'),
            metrics[0])
        self.assertEqual(
            power_metrics.Metric(91, 'power', 'mW', 'avg_power'),
            metrics[1])

    def test_raw_data_to_metrics_messages_are_ignored(self):
        raw_data = {'data': [
            {'name': 'default_device.Log.UserInputs',
             'avg': float('nan'),
             'unit': 'Msg'},
            {'name': 'default_device.Log.Warnings',
             'avg': float('nan'),
             'unit': 'Msg'}]}

        metrics = bits.raw_data_to_metrics(raw_data)
        self.assertEqual(0, len(metrics))


if __name__ == '__main__':
    unittest.main()
