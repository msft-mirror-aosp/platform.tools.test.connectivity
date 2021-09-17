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
Tests STA handling of channel switch announcements.
"""

import time

from acts import asserts
from acts.controllers.access_point import setup_ap
from acts.controllers.ap_lib import hostapd_constants

from acts_contrib.test_utils.abstract_devices.wlan_device import create_wlan_device
from acts_contrib.test_utils.abstract_devices.wlan_device_lib.AbstractDeviceWlanDeviceBaseTest import AbstractDeviceWlanDeviceBaseTest
from acts.utils import rand_ascii_str


class ChannelSwitchTest(AbstractDeviceWlanDeviceBaseTest):
    # Time to wait between issuing channel switches
    WAIT_BETWEEN_CHANNEL_SWITCHES_S = 15

    def setup_class(self):
        super().setup_class()
        self.ssid = rand_ascii_str(10)
        if 'dut' in self.user_params:
            if self.user_params['dut'] == 'fuchsia_devices':
                self.dut = create_wlan_device(self.fuchsia_devices[0])
            elif self.user_params['dut'] == 'android_devices':
                self.dut = create_wlan_device(self.android_devices[0])
            else:
                raise ValueError('Invalid DUT specified in config. (%s)' %
                                 self.user_params['dut'])
        else:
            # Default is an android device, just like the other tests
            self.dut = create_wlan_device(self.android_devices[0])
        self.ap = self.access_points[0]
        self.in_use_interface = None

    def teardown_test(self):
        self.dut.disconnect()
        self.dut.reset_wifi()
        self.ap.stop_all_aps()

    def channel_switch(self, band):
        """Setup and run a channel switch test with the given parameters.

        Creates an AP, associates to it, and then issues channel switches
        for multiple channels (currently trying all known valid US channels
        for the given band). After each channel switch, the test checks
        that the DUT is connected for a period of time before considering
        the channel switch successful.

        Args:
            band: str, band that AP will use, must be a valid band (e.g.
                hostapd_constants.BAND_2G)
        """
        self.current_channel_num = None
        asserts.assert_true(
            band in [hostapd_constants.BAND_2G, hostapd_constants.BAND_5G],
            'Failed to setup AP, invalid band {}'.format(band))

        if band == hostapd_constants.BAND_5G:
            self.in_use_interface = self.ap.wlan_5g
            self.current_channel_num = hostapd_constants.AP_DEFAULT_CHANNEL_5G
        elif band == hostapd_constants.BAND_2G:
            self.in_use_interface = self.ap.wlan_2g
            self.current_channel_num = hostapd_constants.AP_DEFAULT_CHANNEL_2G

        setup_ap(access_point=self.ap,
                 profile_name='whirlwind',
                 channel=self.current_channel_num,
                 ssid=self.ssid)
        self.log.info('sending associate command for ssid %s', self.ssid)
        self.dut.associate(target_ssid=self.ssid)
        asserts.assert_true(self.dut.is_connected(), 'Failed to connect.')

        if band == hostapd_constants.BAND_2G:
            channels = hostapd_constants.US_CHANNELS_2G
        elif band == hostapd_constants.BAND_5G:
            channels = hostapd_constants.US_CHANNELS_5G
        else:
            asserts.fail('Cannot run test, need valid band')

        for channel_num in channels:
            if channel_num == self.current_channel_num:
                continue
            self.log.info('channel switch: {} -> {}'.format(
                self.current_channel_num, channel_num))
            self.ap.channel_switch(self.in_use_interface, channel_num)
            channel_num_after_switch = self.ap.get_current_channel(
                self.in_use_interface)
            asserts.assert_true(channel_num_after_switch == channel_num,
                                'AP failed to channel switch')
            self.current_channel_num = channel_num

            # Check periodically to see if DUT stays connected. Sometimes
            # CSA-induced disconnects occur seconds after last channel switch.
            for i in range(self.WAIT_BETWEEN_CHANNEL_SWITCHES_S):
                asserts.assert_true(
                    self.dut.is_connected(),
                    'Failed to stay connected after channel switch.')
                # TODO(fxbug.dev/84701): Verify that DUT is on expected channel.
                time.sleep(1)

        return True

    def test_channel_switch_2g(self):
        self.channel_switch(band=hostapd_constants.BAND_2G)

    # TODO(fxbug.dev/64280): This test fails on 5 GHz channel switches.
    def test_channel_switch_5g(self):
        self.channel_switch(band=hostapd_constants.BAND_5G)
