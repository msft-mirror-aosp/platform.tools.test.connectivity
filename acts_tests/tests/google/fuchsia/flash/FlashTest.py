#!/usr/bin/env python3
#
# Copyright (C) 2021 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""
Script for to flash Fuchsia devices and reports the DUT's version of Fuchsia in
the Sponge test result properties. Uses the built in flashing tool for
fuchsia_devices.
"""
import time

import acts.libs.proc.job as job

from acts import signals
from acts.base_test import BaseTestClass
from acts.utils import get_device


class FlashTest(BaseTestClass):
    def setup_class(self):
        super().setup_class()
        success_str = ("Congratulations! Fuchsia controllers have been "
                       "initialized successfully!")
        err_str = ("Sorry, please try verifying FuchsiaDevice is in your "
                   "config file and try again.")
        if len(self.fuchsia_devices) > 0:
            self.log.info(success_str)
        else:
            raise signals.TestAbortClass("err_str")

    def teardown_class(self):
        dut = get_device(self.fuchsia_devices, 'DUT')
        self.record_data({
            'sponge_properties': {
                'DUT_VERSION': dut.version()
            }
        })

        return super().teardown_class()

    def test_flash_devices(self):
        flash_retry_max = 3
        flash_counter = 0
        for fuchsia_device in self.fuchsia_devices:
            while flash_counter < flash_retry_max:
                try:
                    fuchsia_device.reboot(reboot_type='flash',
                                          use_ssh=True,
                                          unreachable_timeout=120,
                                          ping_timeout=120)
                    flash_counter = flash_retry_max
                except Exception as err:
                    if fuchsia_device.device_pdu_config:
                        self.log.info('Flashing failed.'
                                      '  Hard rebooting fuchsia_device(%s)'
                                      ' and retrying.'
                                      % fuchsia_device.orig_ip)
                        fuchsia_device.reboot(reboot_type='hard',
                                              testbed_pdus=self.pdu_devices)
                        flash_counter = flash_counter + 1
                        if flash_counter == flash_retry_max:
                            raise err
                        time.sleep(1)
                    else:
                        raise err
                self.log.info("fuchsia_device(%s) has been flashed."
                              % fuchsia_device.orig_ip)
            flash_counter = 0

        return True

    def test_report_dut_version(self):
        """Empty test to ensure the version of the DUT is reported in the Sponge
        results in the case when flashing the device is not necessary.

        Useful for when flashing the device is not necessary; specify ACTS to
        only run this test from the test class.
        """
        pass
