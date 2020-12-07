#!/usr/bin/env python3.4
#
#   Copyright 2020 - Google
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
"""
    Test Script for 5G MMS scenarios
"""

import time

from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_CELLULAR_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_PREFERRED
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import call_setup_teardown
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_test_utils import mms_send_receive_verify
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_volte
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_volte
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_iwlan
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_iwlan
from acts_contrib.test_utils.tel.tel_5g_utils import is_current_network_5g_nsa
from acts_contrib.test_utils.tel.tel_5g_utils import set_preferred_mode_for_5g
from acts.utils import rand_ascii_str

class Nsa5gMmsTest(TelephonyBaseTest):
    def setup_class(self):
        super().setup_class()
        self.number_of_devices = 2
        self.message_lengths = (50, 160, 180)

    def setup_test(self):
        TelephonyBaseTest.setup_test(self)

    def teardown_test(self):
        ensure_phones_idle(self.log, self.android_devices)

    def _provision_both_devices_for_5g(self, ads):
        # Mode Pref
        tasks = [(set_preferred_mode_for_5g, [ad]) for ad in ads]
        if not multithread_func(self.log, tasks):
            self.log.error("Failed to set preferred network mode.")
            return False
        # Attach
        tasks = [(is_current_network_5g_nsa, [ad]) for ad in ads]
        if not multithread_func(self.log, tasks):
            self.log.error("Phone not on 5G NSA before sending SMS.")
            return False

    def _provision_both_devices_for_volte(self, ads):
        # LTE attach and enable VoLTE on both phones
        tasks = [(phone_setup_volte, (self.log, ads[0])),
                 (phone_setup_volte, (self.log, ads[1]))]
        if not multithread_func(self.log, tasks):
            self.log.error("Phone Failed to Set Up in VoLTE.")
            return False

    def _provision_both_devices_for_wfc_cell_pref(self, ads, apm_mode=True):
        tasks = [(phone_setup_iwlan,
                  (self.log, ads[0], apm_mode, WFC_MODE_CELLULAR_PREFERRED,
                   self.wifi_network_ssid, self.wifi_network_pass)),
                 (phone_setup_iwlan,
                  (self.log, ads[1], apm_mode, WFC_MODE_CELLULAR_PREFERRED,
                   self.wifi_network_ssid, self.wifi_network_pass))]
        if not multithread_func(self.log, tasks):
            self.log.error("Failed to setup in wfc_cell_pref mode")
            return False

    def _provision_both_devices_for_wfc_wifi_pref(self, ads, apm_mode=False):
        tasks = [(phone_setup_iwlan,
                  (self.log, ads[0], apm_mode, WFC_MODE_WIFI_PREFERRED,
                   self.wifi_network_ssid, self.wifi_network_pass)),
                 (phone_setup_iwlan,
                  (self.log, ads[1], apm_mode, WFC_MODE_WIFI_PREFERRED,
                   self.wifi_network_ssid, self.wifi_network_pass))]
        if not multithread_func(self.log, tasks):
            self.log.error("Failed to setup in wfc_wifi_pref mode")
            return False

    def _verify_5g_attach_for_both_devices(self, ads):
        # Attach
        tasks = [(is_current_network_5g_nsa, [ad]) for ad in ads]
        if not multithread_func(self.log, tasks):
            self.log.error("Phone not on 5G NSA after sending SMS.")
            return False

    def _disable_apm_mode_both_devices(self, ads):
        # Turn off airplane mode
        self.log.info("Turn off APM mode before starting testing.")
        tasks = [(toggle_airplane_mode, (self.log, ads[0], False)),
                 (toggle_airplane_mode, (self.log, ads[1], False))]
        if not multithread_func(self.log, tasks):
            self.log.error("Failed to turn off airplane mode")
            return False

    def _connect_both_devices_to_wifi(self, ads):
        tasks = [(ensure_wifi_connected, (self.log, ad,
                                          self.wifi_network_ssid,
                                          self.wifi_network_pass))
                 for ad in ads]
        if not multithread_func(self.log, tasks):
            self.log.error("Phone Failed to connect to wifi.")
            return False

    def _mms_test_mo(self, ads, expected_result=True):
        return self._mms_test(
            [ads[0], ads[1]], expected_result=expected_result)

    def _mms_test_mt(self, ads, expected_result=True):
        return self._mms_test(
            [ads[1], ads[0]], expected_result=expected_result)

    def _mms_test(self, ads, expected_result=True):
        """Test MMS between two phones.

        Returns:
            True if success.
            False if failed.
        """
        for length in self.message_lengths:
            message_array = [("Test Message", rand_ascii_str(length), None)]
            if not mms_send_receive_verify(
                    self.log,
                    ads[0],
                    ads[1],
                    message_array,
                    expected_result=expected_result):
                self.log.warning("MMS of body length %s test failed", length)
                return False
            else:
                self.log.info("MMS of body length %s test succeeded", length)
        self.log.info("MMS test of body lengths %s succeeded",
                      self.message_lengths)
        return True


    """ Tests Begin """

    @test_tracker_info(uuid="bc484c2c-8086-42db-94cd-a1e4a35f35cf")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_mms_mo_mt(self):
        """Test MMS between two phones in 5g NSA

        Provision devices in 5g NSA
        Send and Verify MMS from PhoneA to PhoneB
        Verify both devices are still on 5g NSA

        Returns:
            True if success.
            False if failed.
        """
        ads = self.android_devices
        if not self._provision_both_devices_for_5g(ads):
            return False

        if not self._mms_test_mo(ads):
            return False

        if not self._verify_5g_attach_for_both_devices(ads):
            return False

        self.log.info("PASS - mms test over 5g nsa validated")
        return True

    @test_tracker_info(uuid="51d42104-cb87-4c9b-9a16-302e246a21dc")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_mms_mo_mt_volte(self):
        """Test MMS between two phones with VoLTE on 5G NSA

        Provision devices on VoLTE
        Provision devices in 5g NSA
        Send and Verify MMS from PhoneA to PhoneB
        Verify both devices are still on 5g NSA

        Returns:
            True if success.
            False if failed.
        """

        ads = self.android_devices
        if not self._provision_both_devices_for_volte(ads):
            return False

        if not self._provision_both_devices_for_5g(ads):
            return False

        if not self._mms_test_mo(ads):
            return False

        if not self._verify_5g_attach_for_both_devices(ads):
            return False

        self.log.info("PASS - volte mms test over 5g nsa validated")
        return True

    @test_tracker_info(uuid="97d6b071-aef2-40c1-8245-7be6c31870a6")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_mms_mo_mt_in_call_volte(self):
        """ Test MO MMS during a VoLTE call over 5G NSA.

        Provision devices on VoLTE
        Provision devices in 5g NSA
        Make a Voice call from PhoneA to PhoneB
        Send and Verify MMS from PhoneA to PhoneB
        Verify both devices are still on 5g NSA

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        if not self._provision_both_devices_for_volte(ads):
            return False

        if not self._provision_both_devices_for_5g(ads):
            return False

        self.log.info("Begin Incall mms test.")
        if not call_setup_teardown(
                self.log,
                ads[0],
                ads[1],
                ad_hangup=None,
                verify_caller_func=is_phone_in_call_volte,
                verify_callee_func=None):
            return False

        if not self._mms_test_mo(ads):
            return False

        if not self._verify_5g_attach_for_both_devices(ads):
            return False
        self.log.info("PASS - Incall volte mms test over 5g nsa validated")
        return True


    @test_tracker_info(uuid="bbb4b80c-fc1b-4377-b3c7-eeed642c5980")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_mms_mo_mt_iwlan(self):
        """ Test MMS text function between two phones,
        Phones in APM, WiFi connected, WFC Cell Preferred mode.

        Disable APM on both devices
        Provision devices in 5g NSA
        Provision devices for WFC Cell Pref with APM ON
        Send and Verify MMS from PhoneA to PhoneB

        Returns:
            True if pass; False if fail.
        """

        ads = self.android_devices
        if not self._disable_apm_mode_both_devices(ads):
            return False

        if not self._provision_both_devices_for_5g(ads):
            return False

        if not self._provision_both_devices_for_wfc_cell_pref(ads):
            return False
        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

        if not self._mms_test_mo(ads):
            return False

        self.log.info("PASS - iwlan mms test over 5g nsa validated")
        return True


    @test_tracker_info(uuid="d36d95dc-0973-4711-bb08-c29ce23495e4")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_mms_mo_mt_iwlan_apm_off(self):
        """ Test MO MMS, Phone in APM off, WiFi connected, WFC WiFi Pref Mode

        Disable APM on both devices
        Provision devices in 5g NSA
        Provision devices for WFC Wifi Pref with APM OFF
        Send and Verify MMS from PhoneA to PhoneB
        Verify 5g NSA attach for both devices

        Returns:
            True if pass; False if fail.
        """

        ads = self.android_devices
        if not self._disable_apm_mode_both_devices(ads):
            return False

        if not self._provision_both_devices_for_5g(ads):
            return False

        if not self._provision_both_devices_for_wfc_wifi_pref(ads):
            return False
        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

        if not self._mms_test_mo(ads):
            self.log.error("Failed to send receive sms over 5g nsa")
            return False
        self.log.info("PASS - iwlan mms test over 5g nsa validated")

        if not self._verify_5g_attach_for_both_devices(ads):
            return False
        return True


    @test_tracker_info(uuid="74ffb79e-f1e9-4087-a9d2-e07878e47869")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_mms_mo_mt_in_call_iwlan(self):
        """ Test MO MMS, Phone in APM, WiFi connected, WFC WiFi Pref mode

        Disable APM on both devices
        Provision devices in 5g NSA
        Provision devices for WFC Wifi Pref with APM ON
        Make a Voice call from PhoneA to PhoneB
        Send and Verify MMS from PhoneA to PhoneB

        Returns:
            True if pass; False if fail.
        """

        ads = self.android_devices

        if not self._disable_apm_mode_both_devices(ads):
            return False

        if not self._provision_both_devices_for_5g(ads):
            return False

        if not self._provision_both_devices_for_wfc_wifi_pref(ads,
                                                              apm_mode=True):
            return False
        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

        self.log.info("Begin Incall mms test")
        if not call_setup_teardown(
                self.log,
                ads[0],
                ads[1],
                ad_hangup=None,
                verify_caller_func=is_phone_in_call_iwlan,
                verify_callee_func=None):
            return False

        return self._mms_test_mo(ads)

    @test_tracker_info(uuid="68c8e0ca-bea4-45e4-92cf-19424ee47ca4")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_mms_mo_mt_in_call_volte_wifi(self):
        """ Test MMS during VoLTE call and WiFi connected

        Make sure PhoneA/B are in 5G NSA (with VoLTE).
        Make sure PhoneA/B are able to make/receive call.
        Connect PhoneA/B to Wifi.
        Call from PhoneA to PhoneB, accept on PhoneB, send MMS on PhoneA.
        Make sure PhoneA/B are in 5G NSA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        if not self._provision_both_devices_for_volte(ads):
            return False

        if not self._provision_both_devices_for_5g(ads):
            return False

        if not self._connect_both_devices_to_wifi(ads):
            return False

        self.log.info("Begin In Call MMS Test.")
        if not call_setup_teardown(
                self.log,
                ads[0],
                ads[1],
                ad_hangup=None,
                verify_caller_func=is_phone_in_call_volte,
                verify_callee_func=None):
            return False

        if not self._mms_test_mo(ads):
            return False

        if not self._verify_5g_attach_for_both_devices(ads):
            return False
        return True

    """ Tests End """