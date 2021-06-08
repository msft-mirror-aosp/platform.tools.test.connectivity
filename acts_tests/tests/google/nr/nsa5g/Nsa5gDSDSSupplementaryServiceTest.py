#!/usr/bin/env python3
#
#   Copyright 2021 - Google
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

import re
import time

from acts import asserts
from acts import signals
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.tel.loggers.protos.telephony_metric_pb2 import TelephonyVoiceTestResult
from acts_contrib.test_utils.tel.loggers.telephony_metric_logger import TelephonyMetricLogger
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import CAPABILITY_CONFERENCE
from acts_contrib.test_utils.tel.tel_subscription_utils import get_outgoing_voice_sub_id
from acts_contrib.test_utils.tel.tel_test_utils import set_call_waiting
from acts_contrib.test_utils.tel.tel_test_utils import get_capability_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_dsds_utils import erase_call_forwarding
from acts_contrib.test_utils.tel.tel_dsds_utils import msim_call_forwarding
from acts_contrib.test_utils.tel.tel_dsds_utils import msim_call_voice_conf

CallResult = TelephonyVoiceTestResult.CallResult.Value

class Nsa5gDSDSSupplementaryServiceTest(TelephonyBaseTest):
    def setup_class(self):
        TelephonyBaseTest.setup_class(self)
        self.message_lengths = (50, 160, 180)
        self.tel_logger = TelephonyMetricLogger.for_test_case()
        erase_call_forwarding(self.log, self.android_devices[0])
        if not get_capability_for_subscription(
            self.android_devices[0],
            CAPABILITY_CONFERENCE,
            get_outgoing_voice_sub_id(self.android_devices[0])):
            self.android_devices[0].log.error(
                "Conference call is not supported, abort test.")
            raise signals.TestAbortClass(
                "Conference call is not supported, abort test.")

    def teardown_test(self):
        ensure_phones_idle(self.log, self.android_devices)
        erase_call_forwarding(self.log, self.android_devices[0])
        set_call_waiting(self.log, self.android_devices[0], enable=1)

    # psim 5g nsa volte & esim 4g volte
    @test_tracker_info(uuid="9fb2da2e-00f6-4d0f-a921-49786ffbb758")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_callee_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        """Call forwarding unconditional test on pSIM of the primary device.
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)

            Test steps:
                1. Enable CFU on pSIM of the primary device.
                2. Let the 2nd device call the pSIM of the primary device. The
                   call should be forwarded to the 3rd device. Answer and then
                   hang up the call.
                3. Disable CFU on pSIM of the primary device.
                4. Let the 2nd device call the pSIM of the primary device. The
                   call should NOT be forwarded to the primary device. Answer
                   and then hang up the call.
                5. Disable and erase CFU on the primary device.
        """
        return msim_call_forwarding(
            self.log,
            self.android_devices,
            None,
            0,
            None,
            0,
            callee_rat=["5g_volte", "volte"],
            call_forwarding_type="unconditional")

    @test_tracker_info(uuid="da42b577-30a6-417d-a545-629ccbfaebb2")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_callee_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        """Call forwarding unconditional test on eSIM of the primary device.
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)

            Test steps:
                1. Enable CFU on eSIM of the primary device.
                2. Let the 2nd device call the eSIM of the primary device. The
                   call should be forwarded to the 3rd device. Answer and then
                   hang up the call.
                3. Disable CFU on eSIM of the primary device.
                4. Let the 2nd device call the eSIM of the primary device. The
                   call should NOT be forwarded to the primary device. Answer
                   and then hang up the call.
                5. Disable and erase CFU on the primary device.
        """
        return msim_call_forwarding(
            self.log,
            self.android_devices,
            None,
            1,
            None,
            0,
            callee_rat=["5g_volte", "volte"],
            call_forwarding_type="unconditional")

    # psim 4g volte & esim 5g nsa volte
    @test_tracker_info(uuid="0e951ee2-4a38-4b97-8a79-f6b3c66bf4d5")
    def test_msim_cfu_callee_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        """Call forwarding unconditional test on pSIM of the primary device.
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at eSIM (slot 1)

            Test steps:
                1. Enable CFU on pSIM of the primary device.
                2. Let the 2nd device call the pSIM of the primary device. The
                   call should be forwarded to the 3rd device. Answer and then
                   hang up the call.
                3. Disable CFU on pSIM of the primary device.
                4. Let the 2nd device call the pSIM of the primary device. The
                   call should NOT be forwarded to the primary device. Answer
                   and then hang up the call.
                5. Disable and erase CFU on the primary device.
        """
        return msim_call_forwarding(
            self.log,
            self.android_devices,
            None,
            0,
            None,
            1,
            callee_rat=["volte", "5g_volte"],
            call_forwarding_type="unconditional")

    @test_tracker_info(uuid="0f15a135-aa30-46fb-956a-99b5b1109783")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_callee_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        """Call forwarding unconditional test on eSIM of the primary device.
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at eSIM (slot 1)

            Test steps:
                1. Enable CFU on eSIM of the primary device.
                2. Let the 2nd device call the eSIM of the primary device. The
                   call should be forwarded to the 3rd device. Answer and then
                   hang up the call.
                3. Disable CFU on eSIM of the primary device.
                4. Let the 2nd device call the eSIM of the primary device. The
                   call should NOT be forwarded to the primary device. Answer
                   and then hang up the call.
                5. Disable and erase CFU on the primary device.
        """
        return msim_call_forwarding(
            self.log,
            self.android_devices,
            None,
            1,
            None,
            1,
            callee_rat=["volte", "5g_volte"],
            call_forwarding_type="unconditional")

    # psim 5g nsa volte & esim 4g volte
    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="ff107828-0b09-47fb-ba85-b0e13b89970f")
    def test_msim_conf_call_host_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        """Conference call test on pSIM of the primary device
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)

            Test steps:
                1. Enable CW on pSIM of the primary device.
                2. Let the pSIM of primary device call the 2nd device. Keep the
                   call active.
                3. Let the 3rd device call the pSIM of the primary device. Keep
                   both calls active.
                4. Swap the call twice.
                5. Merge 2 active calls.
        """
        return msim_call_voice_conf(
            self.log,
            self.android_devices,
            0, None, None, 0, host_rat=["5g_volte", "volte"])

    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="4a3152e2-8cc6-477d-9dd6-55f3ac35681e")
    def test_msim_conf_call_host_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        """Conference call test on eSIM of the primary device
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)

            Test steps:
                1. Enable CW on eSIM of the primary device.
                2. Let the eSIM of primary device call the 2nd device. Keep the
                   call active.
                3. Let the 3rd device call the eSIM of the primary device. Keep
                   both calls active.
                4. Swap the call twice.
                5. Merge 2 active calls.
        """
        return msim_call_voice_conf(
            self.log,
            self.android_devices,
            1, None, None, 0, host_rat=["5g_volte", "volte"])

    # psim 4g volte & esim 5g nsa volte
    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="8f46e57c-c7a2-49e9-9e4c-1f83ab67cd5e")
    def test_msim_conf_call_host_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        """Conference call test on pSIM of the primary device
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at pSIM (slot 1)

            Test steps:
                1. Enable CW on pSIM of the primary device.
                2. Let the pSIM of primary device call the 2nd device. Keep the
                   call active.
                3. Let the 3rd device call the pSIM of the primary device. Keep
                   both calls active.
                4. Swap the call twice.
                5. Merge 2 active calls.
        """
        return msim_call_voice_conf(
            self.log,
            self.android_devices,
            0, None, None, 1, host_rat=["volte", "5g_volte"])

    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="7975fc5b-4146-4370-9f1b-1ad1987a14f3")
    def test_msim_conf_call_host_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        """Conference call test on eSIM of the primary device
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at pSIM (slot 1)

            Test steps:
                1. Enable CW on eSIM of the primary device.
                2. Let the eSIM of primary device call the 2nd device. Keep the
                   call active.
                3. Let the 3rd device call the eSIM of the primary device. Keep
                   both calls active.
                4. Swap the call twice.
                5. Merge 2 active calls.
        """
        return msim_call_voice_conf(
            self.log,
            self.android_devices,
            1, None, None, 1, host_rat=["volte", "5g_volte"])

    # psim 5g nsa volte & esim 4g volte
    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="753a8651-8230-4714-aa5c-32ed7e7d7c04")
    def test_msim_cw_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        """Call waiting test on pSIM of the primary device
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)

            Test steps:
                1. Enable CW on pSIM of the primary device.
                2. Let the pSIM of primary device call the 2nd device. Keep the
                   call active.
                3. Let the 3rd device call the pSIM of the primary device. Keep
                   both calls active.
                4. Swap the call twice.
                5. Hang up 2 calls from the 2nd and 3rd devices.
                6. Disable CW on pSIM of the primary device.
                7. Repeat step 2 & 3. In the step 3 the primary device should
                   not receive the incoming call.
        """
        result = True
        if not msim_call_voice_conf(
            self.log,
            self.android_devices,
            0,
            None,
            None,
            0,
            host_rat=["5g_volte", "volte"],
            merge=False, disable_cw=False):
        	result = False
        if not msim_call_voice_conf(
            self.log,
            self.android_devices,
            0,
            None,
            None,
            0,
            host_rat=["5g_volte", "volte"],
            merge=False,
            disable_cw=True):
        	result = False
        return result

    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="fc92c004-5862-4035-98b4-5ea3d3c2c5e9")
    def test_msim_cw_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        """Call waiting test on eSIM of the primary device
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)

            Test steps:
                1. Enable CW on eSIM of the primary device.
                2. Let the eSIM of primary device call the 2nd device. Keep the
                   call active.
                3. Let the 3rd device call the eSIM of the primary device. Keep
                   both calls active.
                4. Swap the call twice.
                5. Hang up 2 calls from the 2nd and 3rd devices.
                6. Disable CW on eSIM of the primary device.
                7. Repeat step 2 & 3. In the step 3 the primary device should
                   not receive the incoming call.
        """
        result = True
        if not msim_call_voice_conf(
            self.log,
            self.android_devices,
            1,
            None,
            None,
            0,
            host_rat=["5g_volte", "volte"],
            merge=False, disable_cw=False):
            result = False
        if not msim_call_voice_conf(
            self.log,
            self.android_devices,
            1,
            None,
            None,
            0,
            host_rat=["5g_volte", "volte"],
            merge=False,
            disable_cw=True):
            result = False
        return result

    # psim 4g volte & esim 5g nsa volte
    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="80c7e356-9419-484f-9b34-65ca5544bc39")
    def test_msim_cw_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        """Call waiting test on pSIM of the primary device
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at eSIM (slot 1)

            Test steps:
                1. Enable CW on pSIM of the primary device.
                2. Let the pSIM of primary device call the 2nd device. Keep the
                   call active.
                3. Let the 3rd device call the pSIM of the primary device. Keep
                   both calls active.
                4. Swap the call twice.
                5. Hang up 2 calls from the 2nd and 3rd devices.
                6. Disable CW on pSIM of the primary device.
                7. Repeat step 2 & 3. In the step 3 the primary device should
                   not receive the incoming call.
        """
        result = True
        if not msim_call_voice_conf(
            self.log,
            self.android_devices,
            0,
            None,
            None,
            1,
            host_rat=["volte", "5g_volte"],
            merge=False,
            disable_cw=False):
            result = False
        if not msim_call_voice_conf(
            self.log,
            self.android_devices,
            0,
            None,
            None,
            1,
            host_rat=["volte", "5g_volte"],
            merge=False,
            disable_cw=True):
            result = False
        return result

    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="6cd6b062-d68a-4b1b-b6ca-92af72ebe3b9")
    def test_msim_cw_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        """Call waiting test on eSIM of the primary device
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at eSIM (slot 1)

            Test steps:
                1. Enable CW on eSIM of the primary device.
                2. Let the eSIM of primary device call the 2nd device. Keep the
                   call active.
                3. Let the 3rd device call the eSIM of the primary device. Keep
                   both calls active.
                4. Swap the call twice.
                5. Hang up 2 calls from the 2nd and 3rd devices.
                6. Disable CW on eSIM of the primary device.
                7. Repeat step 2 & 3. In the step 3 the primary device should
                   not receive the incoming call.
        """
        result = True
        if not msim_call_voice_conf(
            self.log,
            self.android_devices,
            1,
            None,
            None,
            1,
            host_rat=["volte", "5g_volte"],
            merge=False,
            disable_cw=False):
            result = False
        if not msim_call_voice_conf(
            self.log,
            self.android_devices,
            1,
            None,
            None,
            1,
            host_rat=["volte", "5g_volte"],
            merge=False,
            disable_cw=True):
            result = False
        return result