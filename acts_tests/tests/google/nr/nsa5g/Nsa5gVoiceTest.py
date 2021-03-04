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
    Test Script for 5G Voice scenarios
"""

import time

from acts.test_decorators import test_tracker_info
from acts.utils import adb_shell_ping
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_IN_CALL_FOR_IMS
from acts_contrib.test_utils.tel.tel_defines import DIRECTION_MOBILE_ORIGINATED
from acts_contrib.test_utils.tel.tel_defines import DIRECTION_MOBILE_TERMINATED
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import GEN_5G
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import call_setup_teardown
from acts_contrib.test_utils.tel.tel_test_utils import hangup_call
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import is_phone_in_call_active
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_volte
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_call_hold_unhold_test
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_volte
from acts_contrib.test_utils.tel.tel_voice_utils import two_phone_call_short_seq
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_voice_3g
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_3g
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_iwlan
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_iwlan
from acts_contrib.test_utils.tel.tel_5g_utils import set_preferred_mode_for_5g
from acts_contrib.test_utils.tel.tel_5g_utils import provision_both_devices_for_5g
from acts_contrib.test_utils.tel.tel_5g_utils import provision_both_devices_for_volte
from acts_contrib.test_utils.tel.tel_5g_utils import verify_5g_attach_for_both_devices
from acts_contrib.test_utils.tel.tel_5g_utils import is_current_network_5g_nsa
from acts_contrib.test_utils.tel.tel_data_utils import wifi_cell_switching
from acts_contrib.test_utils.tel.tel_data_utils import test_call_setup_in_active_data_transfer
from acts_contrib.test_utils.tel.tel_data_utils import test_call_setup_in_active_youtube_video
from acts_contrib.test_utils.tel.tel_data_utils import call_epdg_to_epdg_wfc


class Nsa5gVoiceTest(TelephonyBaseTest):
    def setup_class(self):
        super().setup_class()
        self.number_of_devices = 2
        self.message_lengths = (50, 160, 180)

    def setup_test(self):
        TelephonyBaseTest.setup_test(self)

    def teardown_test(self):
        ensure_phones_idle(self.log, self.android_devices)

    """ Tests Begin """

    @test_tracker_info(uuid="1bef3da1-4608-4b0e-8b78-f3f7be0115d5")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_volte_to_volte(self):
        """ 5g nsa volte to volte call test

        1. Make sure PhoneA is in nsa5g mode (with volte).
        2. Make sure PhoneB is in nsa5g mode (with volte).
        3. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneA.
        4. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneB.
        5. Verify both PhoneA and PhoneB gets attached back to nsa5g

        Raises:
            TestFailure if not success.
        """
        ads = self.android_devices
        if not provision_both_devices_for_volte(self.log, ads):
            return False

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        # VoLTE calls
        result = two_phone_call_short_seq(
            self.log, ads[0], None, is_phone_in_call_volte, ads[1],
            None, is_phone_in_call_volte, None,
            WAIT_TIME_IN_CALL_FOR_IMS)
        if not result:
            self.log.error("Failure is volte call during 5g nsa")
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            return False

        self.log.info("PASS - volte test over 5g nsa validated")
        return True

    @test_tracker_info(uuid="3df252a4-308a-49c3-8e37-08e9c4e8efef")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_volte_to_3g(self):
        """ 5g nsa volte to 3g call test

        1. Make sure PhoneA is in nsa5g mode (with volte).
        2. Make sure PhoneB is in 3g mode.
        3. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneA.
        4. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneB.
        5. Verify both PhoneA and PhoneB gets attached back to nsa5g

        Raises:
            TestFailure if not success.
        """
        ads = self.android_devices

        # LTE attach
        tasks = [(phone_setup_volte, (self.log, ads[0])),
                 (phone_setup_voice_3g, (self.log, ads[1]))]
        if not multithread_func(self.log, tasks):
            self.log.error("Phone failed to set up in volte/3g")
            return False

        # Mode Pref
        set_preferred_mode_for_5g(ads[0])

        # Attach nsa5g
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5g nsa before call.")
            return False

        # VoLTE to 3G
        result = two_phone_call_short_seq(
            self.log, ads[0], None, is_phone_in_call_volte, ads[1],
            None, is_phone_in_call_3g, None,
            WAIT_TIME_IN_CALL_FOR_IMS)
        if not result:
            self.log.error("Failure is volte to 3g call during 5g nsa")
            return False

        # Attach nsa5g
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5g nsa after call end.")
            return False

        self.log.info("PASS - VoLTE to 3g over 5g nsa validated")
        return True


    @test_tracker_info(uuid="3a8147d6-c136-42cb-92ca-2023b8eed85e")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_volte_mo_hold_unhold(self):
        """ 5g nsa volte mo hold unhold test

        1. Make sure PhoneA is in nsa 5g (with volte)
        2. Make sure PhoneB is in nsa 5g (with volte)
        3. Call from PhoneA to PhoneB, accept on PhoneB
        4. Make sure PhoneA/B are in call
        5. Hold and unhold on PhoneA
        6. Verify both PhoneA and PhoneB gets attached back to nsa5g

        Raises:
            TestFailure if not success.
        """
        ads = self.android_devices
        if not provision_both_devices_for_volte(self.log, ads):
            return False

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        if not phone_setup_call_hold_unhold_test(self.log,
                                                 ads,
                                                 DIRECTION_MOBILE_ORIGINATED,
                                                 caller_func=is_phone_in_call_volte):
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            return False
        return True

    @test_tracker_info(uuid="1825f9d9-dcf1-4407-922d-3f218d5b8932")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_volte_mt_hold_unhold(self):
        """ 5g nsa volte mt hold unhold test

        1. Make sure PhoneA is in nsa 5g (with volte)
        2. Make sure PhoneB is in nsa 5g (with volte)
        3. Call from PhoneB to PhoneA, accept on PhoneA
        4. Make sure PhoneA/B are in call
        5. Hold and unhold on PhoneA
        6. Verify both PhoneA and PhoneB gets attached back to nsa5g

        Raises:
            TestFailure if not success.
        """
        ads = self.android_devices
        if not provision_both_devices_for_volte(self.log, ads):
            return False

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        if not phone_setup_call_hold_unhold_test(self.log,
                                                 ads,
                                                 DIRECTION_MOBILE_TERMINATED,
                                                 callee_func=is_phone_in_call_volte):
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            return False
        return True


    @test_tracker_info(uuid="c082a9b0-fb66-4d3a-9fdd-1ce5710624be")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mo_volte_in_active_data_transfer(self):
        """Test call can be established during active data connection in 5G NSA.

        Turn off airplane mode, disable WiFi, enable Cellular Data.
        Make sure phone in 5G NSA.
        Starting downloading file from Internet.
        Initiate a MO voice call. Verify call can be established.
        Hangup Voice Call, verify file is downloaded successfully.
        Note: file download will be suspended when call is initiated if voice
              is using voice channel and voice channel and data channel are
              on different RATs.

        Returns:
            True if success.
            False if failed.
        """
        ads = self.android_devices
        if not phone_setup_volte(self.log, ads[0]):
            ads[0].log.error("failed to setup volte")
            return False
        return test_call_setup_in_active_data_transfer(self.log,
                                                       ads,
                                                       GEN_5G,
                                                       DIRECTION_MOBILE_ORIGINATED)


    @test_tracker_info(uuid="aaa98e51-0bde-472a-abc3-5dc180f56a08")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mt_volte_in_active_data_transfer(self):
        """Test call can be established during active data connection in 5G NSA.

        Turn off airplane mode, disable WiFi, enable Cellular Data.
        Make sure phone in 5G NSA.
        Starting downloading file from Internet.
        Initiate a MT voice call. Verify call can be established.
        Hangup Voice Call, verify file is downloaded successfully.
        Note: file download will be suspended when call is initiated if voice
              is using voice channel and voice channel and data channel are
              on different RATs.

        Returns:
            True if success.
            False if failed.
        """
        ads = self.android_devices
        if not phone_setup_volte(self.log, ads[0]):
            ads[0].log.error("failed to setup volte")
            return False
        return test_call_setup_in_active_data_transfer(self.log,
                                                       ads,
                                                       GEN_5G,
                                                       DIRECTION_MOBILE_TERMINATED)


    @test_tracker_info(uuid="3a607dee-7e92-4567-8ca0-05099590b773")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_volte_in_call_wifi_toggling(self):
        """ Test data connection network switching during VoLTE call in 5G NSA.

        1. Make Sure PhoneA in VoLTE.
        2. Make Sure PhoneB in VoLTE.
        3. Make sure Phones are in 5G NSA
        4. Call from PhoneA to PhoneB.
        5. Toggling Wifi connection in call.
        6. Verify call is active.
        7. Hung up the call on PhoneA
        8. Make sure Phones are in 5G NSA

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        result = True
        if not provision_both_devices_for_volte(self.log, ads):
            return False

        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            self.log.error("Phone not attached on 5G NSA before call.")
            return False

        if not call_setup_teardown(self.log, ads[0], ads[1], None, None, None,
                                   5):
            self.log.error("Call setup failed")
            return False
        else:
            self.log.info("Call setup succeed")

        if not wifi_cell_switching(self.log, ads[0], None, self.wifi_network_ssid,
                                   self.wifi_network_pass):
            ads[0].log.error("Failed to do WIFI and Cell switch in call")
            result = False

        if not is_phone_in_call_active(ads[0]):
            return False
        else:
            if not ads[0].droid.telecomCallGetAudioState():
                ads[0].log.error("Audio is not on call")
                result = False
            else:
                ads[0].log.info("Audio is on call")
            hangup_call(self.log, ads[0])

            time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

            if not verify_5g_attach_for_both_devices(self.log, ads):
                self.log.error("Phone not attached on 5G NSA after call.")
                return False
            return result


    @test_tracker_info(uuid="96b7d8c9-d32a-4abf-8326-6b060d116ac2")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_epdg_to_epdg_wfc_wifi_preferred(self):
        """ WiFi Preferred, WiFi calling to WiFi Calling test on 5G NSA

        1. Setup PhoneA WFC mode: WIFI_PREFERRED, APM off.
        2. Setup PhoneB WFC mode: WIFI_PREFERRED, APM off .
        3. Set PhoneA/PhoneB on 5G NSA
        4. Make sure PhoneA/PhoneB on 5G NSA before testing
        5. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneA.
        6. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneB.
        7. Make sure PhoneA/PhoneB on 5G NSA after testing

        Returns:
            True if pass; False if fail.
        """
        return call_epdg_to_epdg_wfc(self.log,
                                     self.android_devices,
                                     False,
                                     WFC_MODE_WIFI_PREFERRED,
                                     self.wifi_network_ssid,
                                     self.wifi_network_pass,
                                     GEN_5G)


    @test_tracker_info(uuid="29fa7f44-8d6a-4948-8178-33c9a9aab334")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mo_volte_in_active_youtube(self):
        """Test call can be established during active youtube video on 5G NSA.

        1. Enable VoLTE on PhoneA.
        2. Set up PhoneA on 5G NSA.
        3. Make sure phoneA is on 5G NSA.
        4. Starting an youtube video.
        5. Initiate a MO voice call. Verify call can be established.
        6. Make sure phoneA is on 5G NSA.

        Returns:
            True if success.
            False if failed.
        """
        if not phone_setup_volte(self.log, self.android_devices[0]):
            self.android_devices[0].log.error("Failed to setup VoLTE")
            return False
        return test_call_setup_in_active_youtube_video(self.log,
                                                       self.android_devices,
                                                       GEN_5G,
                                                       DIRECTION_MOBILE_ORIGINATED)

    @test_tracker_info(uuid="4e138477-3536-48bd-ab8a-7fb7c228b3e6")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mt_volte_in_active_youtube(self):
        """Test call can be established during active youtube video on 5G NSA.

        1. Enable VoLTE on PhoneA.
        2. Set up PhoneA on 5G NSA.
        3. Make sure phoneA is on 5G NSA.
        4. Starting an youtube video.
        5. Initiate a MT voice call. Verify call can be established.
        6. Make sure phoneA is on 5G NSA.

        Returns:
            True if success.
            False if failed.
        """
        if not phone_setup_volte(self.log, self.android_devices[0]):
            self.android_devices[0].log.error("Failed to setup VoLTE")
            return False
        return test_call_setup_in_active_youtube_video(self.log,
                                                       self.android_devices,
                                                       GEN_5G,
                                                       DIRECTION_MOBILE_TERMINATED)


    @test_tracker_info(uuid="0d477f6f-3464-4b32-a5e5-0fd134f2753d")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mo_vowifi_in_active_data_transfer(self):
        """Test MO voice wifi call can be established during active data connection on 5G NSA.

        1. Turn off airplane mode, turn on wfc and wifi on phoneA.
        2. Set PhoneA on 5G NSA
        3. Make sure PhoneA on 5G NSA before testing
        4. Starting downloading file from Internet.
        5. Initiate a MO voice call. Verify call can be established.
        6. Hangup Voice Call, verify file is downloaded successfully.
        7. Make sure PhoneA on 5G NSA after testing

        Returns:
            True if success.
            False if failed.
        """
        if not phone_setup_iwlan(self.log, self.android_devices[0], False,
                                 WFC_MODE_WIFI_PREFERRED,
                                 self.wifi_network_ssid,
                                 self.wifi_network_pass):
            self.android_devices[0].log.error(
                "Failed to setup iwlan with APM off and WIFI and WFC on")
            return False

        return self._test_call_setup_in_active_data_transfer_5g_nsa(
            call_direction=DIRECTION_MOBILE_ORIGINATED)


    @test_tracker_info(uuid="4d1d7dd9-b373-4361-8301-8517ef77b57b")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mt_vowifi_in_active_data_transfer(self):
        """Test MT voice wifi call can be established during active data connection on 5G NSA.

        1. Turn off airplane mode, turn on wfc and wifi on phoneA.
        2. Set PhoneA on 5G NSA
        3. Make sure PhoneA on 5G NSA before testing
        4. Starting downloading file from Internet.
        5. Initiate a MT voice call. Verify call can be established.
        6. Hangup Voice Call, verify file is downloaded successfully.
        7. Make sure PhoneA on 5G NSA after testing

        Returns:
            True if success.
            False if failed.
        """
        if not phone_setup_iwlan(self.log, self.android_devices[0], False,
                                 WFC_MODE_WIFI_PREFERRED,
                                 self.wifi_network_ssid,
                                 self.wifi_network_pass):
            self.android_devices[0].log.error(
                "Failed to setup iwlan with APM off and WIFI and WFC on")
            return False

        return self._test_call_setup_in_active_data_transfer_5g_nsa(
            call_direction=DIRECTION_MOBILE_TERMINATED)


    @test_tracker_info(uuid="e360bc3a-96b3-4fdf-9bf3-fe3aa08b1af5")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_epdg_mo_hold_unhold_wfc_wifi_preferred(self):
        """ WiFi Preferred, WiFi calling MO call hold/unhold test on 5G NSA

        1. Setup PhoneA WFC mode: WIFI_PREFERRED.
        2. Set preferred network of phoneA on 5G NSA
        3. Verify phoneA is on 5G NSA.
        4. Call from PhoneA to PhoneB, accept on PhoneB.
        5. Hold and unhold on PhoneA.
        6. Verify phoneA is on 5G NSA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        if not phone_setup_iwlan(self.log, self.android_devices[0], False,
                                 WFC_MODE_WIFI_PREFERRED,
                                 self.wifi_network_ssid,
                                 self.wifi_network_pass):
            self.android_devices[0].log.error(
                "Failed to setup iwlan with APM off and WIFI and WFC on")
            return False
        # Mode Pref
        set_preferred_mode_for_5g(ads[0])

        # Attach nsa5g
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5G NSA before call.")
            return False

        if not phone_setup_call_hold_unhold_test(self.log,
                                                 ads,
                                                 DIRECTION_MOBILE_ORIGINATED,
                                                 caller_func=is_phone_in_call_iwlan):
            return False

        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5G NSA after call.")
            return False
        return True


    @test_tracker_info(uuid="d2335c83-87ec-4a0e-97a8-b53f769b0d21")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_epdg_mt_hold_unhold_wfc_wifi_preferred(self):
        """ WiFi Preferred, WiFi calling MT call hold/unhold test on 5G NSA

        1. Setup PhoneA WFC mode: WIFI_PREFERRED.
        2. Set preferred network of phoneA on 5G NSA
        3. Verify if phoneA is on 5G NSA.
        4. Call from PhoneB to PhoneA, accept on PhoneA.
        5. Hold and unhold on PhoneA.
        6. Verify if phoneA is on 5G NSA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        if not phone_setup_iwlan(self.log, self.android_devices[0], False,
                                 WFC_MODE_WIFI_PREFERRED,
                                 self.wifi_network_ssid,
                                 self.wifi_network_pass):
            self.android_devices[0].log.error(
                "Failed to setup iwlan with APM off and WIFI and WFC on")
            return False
        # Mode Pref
        set_preferred_mode_for_5g(ads[0])

        # Attach nsa5g
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5G NSA before call.")
            return False

        if not phone_setup_call_hold_unhold_test(self.log,
                                                 ads,
                                                 DIRECTION_MOBILE_TERMINATED,
                                                 callee_func=is_phone_in_call_iwlan):
            return False

        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5G NSA after call.")
            return False
        return True

    """ Tests End """
