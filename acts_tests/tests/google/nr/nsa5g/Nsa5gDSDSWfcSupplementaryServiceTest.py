#!/usr/bin/env python3
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

import time
from acts import signals
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.tel.loggers.protos.telephony_metric_pb2 import TelephonyVoiceTestResult
from acts_contrib.test_utils.tel.loggers.telephony_metric_logger import TelephonyMetricLogger
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import CAPABILITY_CONFERENCE
from acts_contrib.test_utils.tel.tel_defines import GEN_5G
from acts_contrib.test_utils.tel.tel_defines import INVALID_SUB_ID
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_CELLULAR_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_PREFERRED
from acts_contrib.test_utils.tel.tel_subscription_utils import get_incoming_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_outgoing_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_from_slot_index
from acts_contrib.test_utils.tel.tel_subscription_utils import set_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_0
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_1
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_on_same_network_of_host_ad
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import toggle_volte_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import toggle_wfc_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import set_wfc_mode_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import verify_http_connection
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import erase_call_forwarding_by_mmi
from acts_contrib.test_utils.tel.tel_test_utils import get_capability_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import set_wifi_to_default
from acts_contrib.test_utils.tel.tel_test_utils import set_call_forwarding_by_mmi
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_test_utils import get_operator_name
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_voice_general
from acts_contrib.test_utils.tel.tel_voice_utils import three_phone_call_forwarding_short_seq
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_on_rat

CallResult = TelephonyVoiceTestResult.CallResult.Value

class Nsa5gDSDSWfcSupplementaryServiceTest(TelephonyBaseTest):
    def setup_class(self):
        TelephonyBaseTest.setup_class(self)
        self.tel_logger = TelephonyMetricLogger.for_test_case()
        toggle_airplane_mode(self.log, self.android_devices[0], False)
        self.erase_call_forwarding(self.log, self.android_devices[0])
        if not get_capability_for_subscription(
            self.android_devices[0],
            CAPABILITY_CONFERENCE,
            get_outgoing_voice_sub_id(self.android_devices[0])):
            self.android_devices[0].log.error(
                "Conference call is not supported, abort test.")
            raise signals.TestAbortClass(
                "Conference call is not supported, abort test.")

    def teardown_test(self):
        toggle_airplane_mode(self.log, self.android_devices[0], False)
        ensure_phones_idle(self.log, self.android_devices)
        self.erase_call_forwarding(self.log, self.android_devices[0])
        set_wifi_to_default(self.log, self.android_devices[0])

    def erase_call_forwarding(self, log, ad):
        slot0_sub_id = get_subid_from_slot_index(log, ad, 0)
        slot1_sub_id = get_subid_from_slot_index(log, ad, 1)
        current_voice_sub_id = get_incoming_voice_sub_id(ad)
        for sub_id in (slot0_sub_id, slot1_sub_id):
            set_voice_sub_id(ad, sub_id)
            get_operator_name(log, ad, sub_id)
            erase_call_forwarding_by_mmi(log, ad)
        set_voice_sub_id(ad, current_voice_sub_id)

    def _test_msim_volte_wfc_call_forwarding(
            self,
            callee_slot,
            dds_slot,
            callee_rat=["5g_wfc", "5g_wfc"],
            call_forwarding_type="unconditional",
            enable_volte=[True, True],
            enable_wfc=[True, True],
            is_airplane_mode=False,
            is_wifi_connected=False,
            wfc_mode=[
                WFC_MODE_CELLULAR_PREFERRED,
                WFC_MODE_CELLULAR_PREFERRED]):
        """Make VoLTE/WFC call to the primary device at specific slot with DDS
        at specific slot, and then forwarded to 3rd device with specific call
        forwarding type.

        Test step:
        1. Get sub IDs of specific slots of both MO and MT devices.
        2. Set up phones in desired RAT.
        3. Enable VoLTE/WFC.
        4. Switch DDS to specific slot.
        5. Check HTTP connection after DDS switch.
        6. Register and enable call forwarding with specifc type.
        7. Make VoLTE/WFC call to the primary device and wait for being
           forwarded to 3rd device.

        Args:
            callee_slot: Slot of primary device receiving and forwarding MT call
                         (0 or 1)
            dds_slot: Preferred data slot
            callee_rat: RAT for both slots of the primary device
            call_forwarding_type:
                "unconditional"
                "busy"
                "not_answered"
                "not_reachable"
            enable_volte: True for enabling and False for disabling VoLTE for
                          each slot on the primary device
            enable_wfc: True for enabling and False for disabling WFC for
                        each slot on the primary device
            is_airplane_mode: True of False for WFC setup
            wfc_mode: Cellular preferred or Wi-Fi preferred.

        Returns:
            True or False
        """
        ads = self.android_devices
        ad_caller = ads[1]
        ad_callee = ads[0]
        ad_forwarded_callee = ads[2]
        slot_0_subid = get_subid_from_slot_index(self.log, ad_callee, 0)
        slot_1_subid = get_subid_from_slot_index(self.log, ad_callee, 1)

        if not toggle_airplane_mode(self.log, ad_callee, False):
            ad_callee.log.error("Failed to disable airplane mode.")
            return False

        # Set up callee (primary device)
        callee_sub_id = get_subid_from_slot_index(
            self.log, ad_callee, callee_slot)
        if callee_sub_id == INVALID_SUB_ID:
            self.log.warning(
                "Failed to get sub ID at slot %s.", callee_slot)
            return
        callee_other_sub_id = get_subid_from_slot_index(
            self.log, ad_callee, 1-callee_slot)
        set_voice_sub_id(ad_callee, callee_sub_id)
        ad_callee.log.info(
            "Sub ID for incoming call at slot %s: %s",
            callee_slot, get_incoming_voice_sub_id(ad_callee))

        # Set up caller
        _, caller_sub_id, _ = get_subid_on_same_network_of_host_ad(ads)
        if caller_sub_id == INVALID_SUB_ID:
            ad_caller.log.warning("Failed to get proper sub ID of the caller")
            return
        set_voice_sub_id(ad_caller, caller_sub_id)
        ad_caller.log.info(
            "Sub ID for outgoing call of the caller: %s",
            get_outgoing_voice_sub_id(ad_caller))

        # Set up forwarded callee
        _, _, forwarded_callee_sub_id = get_subid_on_same_network_of_host_ad(
            ads)
        if forwarded_callee_sub_id == INVALID_SUB_ID:
            ad_forwarded_callee.log.warning(
                "Failed to get proper sub ID of the forwarded callee.")
            return
        set_voice_sub_id(ad_forwarded_callee, forwarded_callee_sub_id)
        ad_forwarded_callee.log.info(
            "Sub ID for incoming call of the forwarded callee: %s",
            get_incoming_voice_sub_id(ad_forwarded_callee))

        set_call_forwarding_by_mmi(self.log, ad_callee, ad_forwarded_callee)

        ad_callee.log.info("Step 0: Set up phones in desired RAT.")

        if callee_slot == 1:
            phone_setup_on_rat(
                self.log,
                ad_callee,
                callee_rat[0],
                callee_other_sub_id,
                is_airplane_mode,
                wfc_mode[0],
                self.wifi_network_ssid,
                self.wifi_network_pass)

        elif callee_slot == 0:
            phone_setup_on_rat(
                self.log,
                ad_callee,
                callee_rat[1],
                callee_other_sub_id,
                is_airplane_mode,
                wfc_mode[1],
                self.wifi_network_ssid,
                self.wifi_network_pass)

        callee_phone_setup_func = phone_setup_on_rat(
            self.log, ad_callee, callee_rat[callee_slot], only_return_fn=True)

        if callee_rat[callee_slot] == '5g_wfc':
            argv = (
                self.log,
                ad_callee,
                callee_sub_id,
                is_airplane_mode,
                wfc_mode[callee_slot],
                self.wifi_network_ssid,
                self.wifi_network_pass,
                GEN_5G)
        else:
            argv = (self.log, ad_callee, callee_sub_id)

        if callee_slot:
            if not set_dds_on_slot_1(ad_callee):
                ad_callee.log.warning(
                    "Failed to set DDS at host slot: eSIM to check NW type on %s"
                    , ad_callee.serial)
        else:
            if not set_dds_on_slot_0(ad_callee):
                ad_callee.log.warning(
                    "Failed to set DDS at host slot: pSIM to check NW type on %s",
                     ad_callee.serial)

        tasks = [(phone_setup_voice_general, (self.log, ad_caller)),
                (callee_phone_setup_func, argv),
                (phone_setup_voice_general, (self.log, ad_forwarded_callee))]

        if not multithread_func(self.log, tasks):
            self.log.error("Phone Failed to Set Up Properly.")
            self.tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
            raise signals.TestFailure("Failed",
                extras={"fail_reason": "Phone Failed to Set Up Properly."})

        if is_wifi_connected:
            if not ensure_wifi_connected(
                self.log,
                ad_callee,
                self.wifi_network_ssid,
                self.wifi_network_pass,
                apm=is_airplane_mode):
                return False
            time.sleep(5)

        ad_callee.log.info("Step 1: Enable/disable VoLTE and WFC.")
        for sub_id, volte in zip([slot_0_subid, slot_1_subid], enable_volte):
            if not toggle_volte_for_subscription(
                self.log,
                ad_callee,
                new_state=volte,
                sub_id=sub_id):
                return False

        for sub_id, wfc, mode in zip(
            [slot_0_subid, slot_1_subid], enable_wfc, wfc_mode):
            if not toggle_wfc_for_subscription(
                self.log,
                ad_callee,
                new_state=wfc,
                sub_id=sub_id):
                return False
            if not set_wfc_mode_for_subscription(ad_callee, mode, sub_id=sub_id):
                return False

        ad_callee.log.info("Step 2: Switch DDS.")
        if dds_slot:
            if not set_dds_on_slot_1(ad_callee):
                ad_callee.log.warning(
                    "Failed to set DDS at eSIM on %s", ad_callee.serial)
                return
        else:
            if not set_dds_on_slot_0(ad_callee):
                ad_callee.log.warning(
                    "Failed to set DDS at pSIM on %s", ad_callee.serial)
                return

        ad_callee.log.info("Step 3: Check HTTP connection after DDS switch.")
        if not verify_http_connection(self.log, ad_callee):
            ad_callee.log.error("Failed to verify http connection.")
            return False
        else:
            ad_callee.log.info("Verify http connection successfully.")

        is_callee_in_call = is_phone_in_call_on_rat(
            self.log, ad_callee, callee_rat[callee_slot], only_return_fn=True)

        self.log.info(
            "Step 4: Make voice call with call forwarding %s.",
            call_forwarding_type)
        result = three_phone_call_forwarding_short_seq(
            self.log,
            ad_callee,
            None,
            is_callee_in_call,
            ad_caller,
            ad_forwarded_callee,
            call_forwarding_type=call_forwarding_type)

        if not result:
            self.log.error(
                "Failed to make MO call from %s to %s slot %s and forward"
                " to %s.",
                ad_caller.serial,
                ad_callee.serial,
                callee_slot,
                ad_forwarded_callee.serial)
        return result

    @test_tracker_info(uuid="53169ee2-eb70-423e-bbe0-3112f34d2d73")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_psim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_0(self):
        return self._test_msim_volte_wfc_call_forwarding(
            0,
            0,
            callee_rat=['5g_wfc', 'general'],
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED])