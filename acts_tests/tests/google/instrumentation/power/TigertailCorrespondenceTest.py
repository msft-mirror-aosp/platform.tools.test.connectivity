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
from acts.controllers import tigertail as tigertail_controller

class TigertailCorrespondenceTest(base_test.BaseTestClass):
    """This class tests to see if the tigertail is connected to the device
    specified in the config
    """
    def __init__(self, configs):
        super().__init__(configs)

    def setup_class(self):
        self.tigertails = self.register_controller(tigertail_controller)
        for tigertail in self.tigertails:
            tigertail.setup(self.user_params)

    def test_tigertail(self):
        failures = 0
        for index, device in enumerate(self.android_devices):
            self.log.info('testing correspondence for %s', device.serial)

            # stop sl4a
            device.stop_services()
            tigertail = self.tigertails[index]

            for _ in range(3):
                # test turning of the tigertail
                tigertail.turn_off()
                if device.serial in device.adb.devices():
                    failures = failures + 1
                    self.log.error(
                        f'{device.serial} is still visible and it should not be. '
                        f'{tigertail.serial_number} is incorrectly mapped to {device.serial}'
                    )

                # test turning the tigert on
                tigertail.turn_on_mux_A()
                if device.serial not in device.adb.devices():
                    failures = failures + 1
                    self.log.error(
                        f'{device.serial} is not visible and it should. '
                        f'{tigertail.serial_number} is incorrectly mapped to {device.serial}'
                    )

            # start sl4a
            device.start_services()
        asserts.assert_equal(0, failures)
