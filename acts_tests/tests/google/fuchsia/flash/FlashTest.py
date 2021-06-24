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
Script for to flash Fuchsia devices using the built in flashing tool for
fuchsia_devices.
"""
from acts import signals
from acts.base_test import BaseTestClass


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

    def test_flash_devices(self):
        for fuchsia_device in self.fuchsia_devices:
            fuchsia_device.reboot(reboot_type='flash',
                                  use_ssh=True,
                                  unreachable_timeout=120,
                                  ping_timeout=120)
        self.log.info("All of your fuchsia_devices have been flashed.")
        return True

