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

import time

from acts import asserts
from acts import base_test
from acts.metrics.loggers.blackbox import BlackboxMappedMetricLogger
from acts.metrics.loggers.bounded_metrics import BoundedMetricsLogger

DEFAULT_WAIT_FOR_DEVICE_TIMEOUT = 180


class MonsoonCorrespondenceTest(base_test.BaseTestClass):

    def __init__(self, configs):
        super().__init__(configs)
        self.blackbox_logger = BlackboxMappedMetricLogger.for_test_case()
        self.bounded_metric_logger = BoundedMetricsLogger.for_test_case()

    def test_monsoon_correspondence(self):
        failures = 0
        for index, device in enumerate(self.android_devices):
            self.log.info('testing correspondence for %s' % device.serial)
            # stop sl4a
            device.stop_services()
            monsoon = self.monsoons[index]

            failures = 0

            for _ in range(3):
                # test it goes away
                monsoon.usb('off')
                if device.serial in device.adb.devices():
                    failures = failures + 1
                    self.log.error(
                        '%s is still visible and it should not be. Monsoon %s '
                        'is incorrectly mapped to %s.' % (
                            device.serial, monsoon.serial, device.serial))

                # test it returns
                monsoon.usb('on')
                self.log.info('waiting for device to come back online')
                for i in range(30):
                    self.log.info('waiting %s/30' % i)
                    time.sleep(1)
                if device.serial not in device.adb.devices():
                    failures = failures + 1
                    self.log.error(
                        '%s is still not visible and it should be. Monsoon %s '
                        'is incorrectly mapped to %s.' % (
                            device.serial, monsoon.serial, device.serial))

            device.start_services()

        self.blackbox_logger.add_metric('monsoon_correspondence_failures',
                                        failures)
        self.bounded_metric_logger.add(
            'monsoon_correspondence_failures',
            failures,
            upper_limit=0,
            lower_limit=0,
            unit='count')
        asserts.assert_equal(0, failures)
