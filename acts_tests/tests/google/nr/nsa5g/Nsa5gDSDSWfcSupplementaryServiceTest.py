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
from acts_contrib.test_utils.tel.tel_defines import CALL_CAPABILITY_MANAGE_CONFERENCE
from acts_contrib.test_utils.tel.tel_defines import CALL_PROPERTY_CONFERENCE
from acts_contrib.test_utils.tel.tel_defines import CALL_STATE_ACTIVE
from acts_contrib.test_utils.tel.tel_defines import CAPABILITY_CONFERENCE
from acts_contrib.test_utils.tel.tel_defines import GEN_5G
from acts_contrib.test_utils.tel.tel_defines import GEN_4G
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_IN_CALL
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
from acts_contrib.test_utils.tel.tel_test_utils import call_setup_teardown
from acts_contrib.test_utils.tel.tel_test_utils import hangup_call
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import num_active_calls
from acts_contrib.test_utils.tel.tel_test_utils import verify_incall_state
from acts_contrib.test_utils.tel.tel_test_utils import toggle_volte_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import toggle_wfc_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import set_wfc_mode_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import verify_http_connection
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import erase_call_forwarding_by_mmi
from acts_contrib.test_utils.tel.tel_test_utils import get_capability_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import wait_and_reject_call_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import set_wifi_to_default
from acts_contrib.test_utils.tel.tel_test_utils import set_call_forwarding_by_mmi
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_test_utils import set_call_waiting
from acts_contrib.test_utils.tel.tel_test_utils import initiate_call
from acts_contrib.test_utils.tel.tel_test_utils import get_operator_name
from acts_contrib.test_utils.tel.tel_voice_utils import get_cep_conference_call_id
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_voice_general
from acts_contrib.test_utils.tel.tel_voice_utils import three_phone_call_forwarding_short_seq
from acts_contrib.test_utils.tel.tel_voice_utils import swap_calls
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

    def _hangup_call(self, ad, device_description='Device'):
        if not hangup_call(self.log, ad):
            ad.log.error("Failed to hang up on %s", device_description)
            return False
        return True

    def erase_call_forwarding(self, log, ad):
        slot0_sub_id = get_subid_from_slot_index(log, ad, 0)
        slot1_sub_id = get_subid_from_slot_index(log, ad, 1)
        current_voice_sub_id = get_incoming_voice_sub_id(ad)
        for sub_id in (slot0_sub_id, slot1_sub_id):
            set_voice_sub_id(ad, sub_id)
            get_operator_name(log, ad, sub_id)
            erase_call_forwarding_by_mmi(log, ad)
        set_voice_sub_id(ad, current_voice_sub_id)

    def _three_phone_call_mo_add_mt(
        self,
        ads,
        phone_setups,
        verify_funcs,
        reject_once=False):
        """Use 3 phones to make MO call and MT call.

        Call from PhoneA to PhoneB, accept on PhoneB.
        Call from PhoneC to PhoneA, accept on PhoneA.

        Args:
            ads: list of ad object.
                The list should have three objects.
            phone_setups: list of phone setup functions.
                The list should have three objects.
            verify_funcs: list of phone call verify functions.
                The list should have three objects.

        Returns:
            If success, return 'call_AB' id in PhoneA.
            if fail, return None.
        """

        class _CallException(Exception):
            pass

        try:
            verify_func_a, verify_func_b, verify_func_c = verify_funcs
            tasks = []
            for ad, setup_func in zip(ads, phone_setups):
                if setup_func is not None:
                    tasks.append((setup_func, (self.log, ad)))
            if tasks != [] and not multithread_func(self.log, tasks):
                self.log.error("Phone Failed to Set Up Properly.")
                raise _CallException("Setup failed.")
            for ad in ads:
                ad.droid.telecomCallClearCallList()
                if num_active_calls(self.log, ad) != 0:
                    ad.log.error("Phone Call List is not empty.")
                    raise _CallException("Clear call list failed.")

            self.log.info("Step1: Call From PhoneA to PhoneB.")
            if not call_setup_teardown(
                    self.log,
                    ads[0],
                    ads[1],
                    ad_hangup=None,
                    verify_caller_func=verify_func_a,
                    verify_callee_func=verify_func_b):
                raise _CallException("PhoneA call PhoneB failed.")

            calls = ads[0].droid.telecomCallGetCallIds()
            ads[0].log.info("Calls in PhoneA %s", calls)
            if num_active_calls(self.log, ads[0]) != 1:
                raise _CallException("Call list verify failed.")
            call_ab_id = calls[0]

            self.log.info("Step2: Call From PhoneC to PhoneA.")
            if reject_once:
                self.log.info("Step2-1: Reject incoming call once.")
                if not initiate_call(
                    self.log,
                    ads[2],
                    ads[0].telephony['subscription'][get_incoming_voice_sub_id(
                        ads[0])]['phone_num']):
                    ads[2].log.error("Initiate call failed.")
                    raise _CallException("Failed to initiate call.")

                if not wait_and_reject_call_for_subscription(
                        self.log,
                        ads[0],
                        get_incoming_voice_sub_id(ads[0]),
                        incoming_number= \
                            ads[2].telephony['subscription'][
                                get_incoming_voice_sub_id(
                                    ads[2])]['phone_num']):
                    ads[0].log.error("Reject call fail.")
                    raise _CallException("Failed to reject call.")

                self._hangup_call(ads[2], "PhoneC")
                time.sleep(15)

            if not call_setup_teardown(
                    self.log,
                    ads[2],
                    ads[0],
                    ad_hangup=None,
                    verify_caller_func=verify_func_c,
                    verify_callee_func=verify_func_a):
                raise _CallException("PhoneA call PhoneC failed.")
            if not verify_incall_state(self.log, [ads[0], ads[1], ads[2]],
                                       True):
                raise _CallException("Not All phones are in-call.")

        except Exception as e:
            self.log.error(e)
            setattr(ads[0], "exception", e)
            return None

        return call_ab_id

    def _test_ims_conference_merge_drop_second_call_from_participant(
            self, call_ab_id, call_ac_id):
        """Test conference merge and drop in IMS (VoLTE or WiFi Calling) call.
        (supporting both cases of CEP enabled and disabled).

        PhoneA in IMS (VoLTE or WiFi Calling) call with PhoneB.
        PhoneA in IMS (VoLTE or WiFi Calling) call with PhoneC.
        Merge calls to conference on PhoneA.
        Hangup on PhoneC, check call continues between AB.
        Hangup on PhoneB, check A ends.

        Args:
            call_ab_id: call id for call_AB on PhoneA.
            call_ac_id: call id for call_AC on PhoneA.

        Returns:
            True if succeed;
            False if failed.
        """
        ads = self.android_devices

        call_conf_id = self._merge_ims_conference_call(call_ab_id, call_ac_id)
        if call_conf_id is None:
            return False

        self.log.info("Step5: End call on PhoneC and verify call continues.")
        if not self._hangup_call(ads[2], "PhoneC"):
            return False
        time.sleep(WAIT_TIME_IN_CALL)
        calls = ads[0].droid.telecomCallGetCallIds()
        ads[0].log.info("Calls in PhoneA %s", calls)
        if not verify_incall_state(self.log, [ads[0], ads[1]], True):
            return False
        if not verify_incall_state(self.log, [ads[2]], False):
            return False

        self.log.info("Step6: End call on PhoneB and verify PhoneA end.")
        if not self._hangup_call(ads[1], "PhoneB"):
            return False
        time.sleep(WAIT_TIME_IN_CALL)
        if not verify_incall_state(self.log, [ads[0], ads[1], ads[2]], False):
            return False
        return True


    def _merge_ims_conference_call(self, call_ab_id, call_ac_id):
        """Merge IMS conference call for both cases of CEP enabled and disabled.

        PhoneA in IMS (VoLTE or WiFi Calling) call with PhoneB.
        PhoneA in IMS (VoLTE or WiFi Calling) call with PhoneC.
        Merge calls to conference on PhoneA.

        Args:
            call_ab_id: call id for call_AB on PhoneA.
            call_ac_id: call id for call_AC on PhoneA.

        Returns:
            call_id for conference
        """
        ads = self.android_devices
        self.log.info("Step4: Merge to Conf Call and verify Conf Call.")
        ads[0].droid.telecomCallJoinCallsInConf(call_ab_id, call_ac_id)
        time.sleep(WAIT_TIME_IN_CALL)
        calls = ads[0].droid.telecomCallGetCallIds()
        ads[0].log.info("Calls in PhoneA %s", calls)

        call_conf_id = None
        if num_active_calls(self.log, ads[0]) != 1:
            ads[0].log.info("Total number of call ids is not 1.")
            call_conf_id = get_cep_conference_call_id(ads[0])
            if call_conf_id is not None:
                self.log.info("New conference call id is found. CEP enabled.")
                calls.remove(call_conf_id)
                if (set(ads[0].droid.telecomCallGetCallChildren(
                    call_conf_id)) != set(calls)):
                    ads[0].log.error(
                        "Children list %s for conference call is not correct.",
                        ads[0].droid.telecomCallGetCallChildren(call_conf_id))
                    return None

                if (CALL_PROPERTY_CONFERENCE not in ads[0]
                        .droid.telecomCallGetProperties(call_conf_id)):
                    ads[0].log.error(
                        "Conf call id % properties wrong: %s", call_conf_id,
                        ads[0].droid.telecomCallGetProperties(call_conf_id))
                    return None

                if (CALL_CAPABILITY_MANAGE_CONFERENCE not in ads[0]
                        .droid.telecomCallGetCapabilities(call_conf_id)):
                    ads[0].log.error(
                        "Conf call id %s capabilities wrong: %s", call_conf_id,
                        ads[0].droid.telecomCallGetCapabilities(call_conf_id))
                    return None

                if (call_ab_id in calls) or (call_ac_id in calls):
                    self.log.error("Previous call ids should not in new call"
                    " list after merge.")
                    return None
        else:
            for call_id in calls:
                if call_id != call_ab_id and call_id != call_ac_id:
                    call_conf_id = call_id
                    self.log.info("CEP not enabled.")

        if not call_conf_id:
            self.log.error("Merge call fail, no new conference call id.")
            raise signals.TestFailure(
                "Calls were not merged. Failed to merge calls.",
                extras={"fail_reason": "Calls were not merged."
                    " Failed to merge calls."})
        if not verify_incall_state(self.log, [ads[0], ads[1], ads[2]], True):
            return False

        # Check if Conf Call is currently active
        if ads[0].droid.telecomCallGetCallState(
                call_conf_id) != CALL_STATE_ACTIVE:
            ads[0].log.error(
                "Call_ID: %s, state: %s, expected: STATE_ACTIVE", call_conf_id,
                ads[0].droid.telecomCallGetCallState(call_conf_id))
            return None

        return call_conf_id


    def _test_wcdma_conference_merge_drop(self, call_ab_id, call_ac_id):
        """Test conference merge and drop in WCDMA/CSFB_WCDMA call.

        PhoneA in WCDMA (or CSFB_WCDMA) call with PhoneB.
        PhoneA in WCDMA (or CSFB_WCDMA) call with PhoneC.
        Merge calls to conference on PhoneA.
        Hangup on PhoneC, check call continues between AB.
        Hangup on PhoneB, check A ends.

        Args:
            call_ab_id: call id for call_AB on PhoneA.
            call_ac_id: call id for call_AC on PhoneA.

        Returns:
            True if succeed;
            False if failed.
        """
        ads = self.android_devices

        self.log.info("Step4: Merge to Conf Call and verify Conf Call.")
        ads[0].droid.telecomCallJoinCallsInConf(call_ab_id, call_ac_id)
        time.sleep(WAIT_TIME_IN_CALL)
        calls = ads[0].droid.telecomCallGetCallIds()
        ads[0].log.info("Calls in PhoneA %s", calls)
        num_calls = num_active_calls(self.log, ads[0])
        if num_calls != 3:
            ads[0].log.error("Total number of call ids is not 3.")
            if num_calls == 2:
                if call_ab_id in calls and call_ac_id in calls:
                    ads[0].log.error("Calls were not merged."
                        " Failed to merge calls.")
                    raise signals.TestFailure(
                        "Calls were not merged. Failed to merge calls.",
                        extras={"fail_reason": "Calls were not merged."
                            " Failed to merge calls."})
            return False
        call_conf_id = None
        for call_id in calls:
            if call_id != call_ab_id and call_id != call_ac_id:
                call_conf_id = call_id
        if not call_conf_id:
            self.log.error("Merge call fail, no new conference call id.")
            return False
        if not verify_incall_state(self.log, [ads[0], ads[1], ads[2]], True):
            return False

        # Check if Conf Call is currently active
        if ads[0].droid.telecomCallGetCallState(
                call_conf_id) != CALL_STATE_ACTIVE:
            ads[0].log.error(
                "Call_id: %s, state: %s, expected: STATE_ACTIVE", call_conf_id,
                ads[0].droid.telecomCallGetCallState(call_conf_id))
            return False

        self.log.info("Step5: End call on PhoneC and verify call continues.")
        if not self._hangup_call(ads[2], "PhoneC"):
            return False
        time.sleep(WAIT_TIME_IN_CALL)
        calls = ads[0].droid.telecomCallGetCallIds()
        ads[0].log.info("Calls in PhoneA %s", calls)
        if num_active_calls(self.log, ads[0]) != 1:
            return False
        if not verify_incall_state(self.log, [ads[0], ads[1]], True):
            return False
        if not verify_incall_state(self.log, [ads[2]], False):
            return False

        self.log.info("Step6: End call on PhoneB and verify PhoneA end.")
        if not self._hangup_call(ads[1], "PhoneB"):
            return False
        time.sleep(WAIT_TIME_IN_CALL)
        if not verify_incall_state(self.log, [ads[0], ads[1], ads[2]], False):
            return False
        return True


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

    def _test_msim_volte_wfc_call_voice_conf(
            self,
            host_slot,
            dds_slot,
            host_rat=["5g_wfc", "5g_wfc"],
            merge=True,
            disable_cw=False,
            enable_volte=[True, True],
            enable_wfc=[True, True],
            is_airplane_mode=False,
            is_wifi_connected=False,
            wfc_mode=[WFC_MODE_CELLULAR_PREFERRED, WFC_MODE_CELLULAR_PREFERRED],
            reject_once=False):
        """Make a VoLTE/WFC conference call at specific slot with DDS at
           specific slot.

        Test step:
        1. Get sub IDs of specific slots of both MO and MT devices.
        2. Set up phones in desired RAT
        3. Enable VoLTE/WFC.
        4. Switch DDS to specific slot.
        5. Check HTTP connection after DDS switch.
        6. Make 3-way VoLTE/WFC call.
        7. Swap calls.
        8. Merge calls.

        Args:
            host_slot: Slot on the primary device to host the comference call.
                       0 or 1 (0 for pSIM or 1 for eSIM)call
            dds_slot: Preferred data slot
            host_rat: RAT for both slots of the primary devicevice
            merge: True for merging 2 calls into the conference call. False for
                   not merging 2 separated call.
            disable_cw: True for disabling call waiting and False on the
                        contrary.
            enable_volte: True for enabling and False for disabling VoLTE for
                          each slot on the primary device
            enable_wfc: True for enabling and False for disabling WFC for
                        each slot on the primary device
            is_airplane_mode: True of False for WFC setup
            wfc_mode: Cellular preferred or Wi-Fi preferred.
            reject_once: True for rejecting the 2nd call once from the 3rd
                         device (Phone C) to the primary device (Phone A).

        Returns:
            True of False
        """

        ads = self.android_devices
        ad_host = ads[0]
        ad_p1 = ads[1]
        ad_p2 = ads[2]
        slot_0_subid = get_subid_from_slot_index(ad_host.log, ad_host, 0)
        slot_1_subid = get_subid_from_slot_index(ad_host.log, ad_host, 1)

        host_sub_id = get_subid_from_slot_index(self.log, ad_host, host_slot)
        if host_sub_id == INVALID_SUB_ID:
            ad_host.log.warning("Failed to get sub ID at slot.", host_slot)
            return
        host_other_sub_id = get_subid_from_slot_index(
            self.log, ad_host, 1-host_slot)
        set_voice_sub_id(ad_host, host_sub_id)
        ad_host.log.info(
            "Sub ID for outgoing call at slot %s: %s",
            host_slot, get_outgoing_voice_sub_id(ad_host))

        _, p1_sub_id, p2_sub_id = get_subid_on_same_network_of_host_ad(ads)

        if p1_sub_id == INVALID_SUB_ID:
            ad_p1.log.warning("Failed to get proper sub ID.")
            return
        set_voice_sub_id(ad_p1, p1_sub_id)
        ad_p1.log.info(
            "Sub ID for incoming call: %s",
            get_incoming_voice_sub_id(ad_p1))

        if p2_sub_id == INVALID_SUB_ID:
            ad_p2.log.warning("Failed to get proper sub ID.")
            return
        set_voice_sub_id(ad_p2, p2_sub_id)
        ad_p2.log.info(
            "Sub ID for incoming call: %s", get_incoming_voice_sub_id(ad_p2))

        ad_host.log.info("Step 0: Set up phones in desired RAT.")

        if disable_cw:
            if not set_call_waiting(self.log, ad_host, enable=0):
                return False

        if host_slot == 1:
            phone_setup_on_rat(
                self.log,
                ad_host,
                host_rat[0],
                host_other_sub_id,
                is_airplane_mode,
                wfc_mode[0],
                self.wifi_network_ssid,
                self.wifi_network_pass
                )

        elif host_slot == 0:
            phone_setup_on_rat(
                self.log,
                ad_host,
                host_rat[1],
                host_other_sub_id,
                is_airplane_mode,
                wfc_mode[1],
                self.wifi_network_ssid,
                self.wifi_network_pass
                )

        host_phone_setup_func = phone_setup_on_rat(
            self.log, ad_host, host_rat[host_slot], only_return_fn=True)

        if host_rat[host_slot].lower() in ['5g_wfc', 'wfc']:
            argv = (
                self.log,
                ad_host,
                host_sub_id,
                is_airplane_mode,
                wfc_mode[host_slot],
                self.wifi_network_ssid,
                self.wifi_network_pass,
                GEN_5G if host_rat[host_slot].lower() == '5g_wfc' else GEN_4G)
        else:
            argv = (self.log, ad_host, host_sub_id)

        if host_slot:
            if not set_dds_on_slot_1(ad_host):
                ad_host.log.warning(
                    "Failed to set DDS at host slot: eSIM to check NW type on %s"
                    , ad_host.serial)
        else:
            if not set_dds_on_slot_0(ad_host):
                ad_host.log.warning(
                    "Failed to set DDS at host slot: pSIM to check NW type on %s",
                     ad_host.serial)

        tasks = [(phone_setup_voice_general, (self.log, ad_p1)),
                (host_phone_setup_func, argv),
                (phone_setup_voice_general, (self.log, ad_p2))]

        if not multithread_func(self.log, tasks):
            self.log.error("Phone Failed to Set Up Properly.")
            self.tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
            raise signals.TestFailure("Failed",
                extras={"fail_reason": "Phone Failed to Set Up Properly."})

        if is_wifi_connected:
            if not ensure_wifi_connected(
                self.log,
                ad_host,
                self.wifi_network_ssid,
                self.wifi_network_pass,
                apm=is_airplane_mode):
                return False
            time.sleep(5)

        ad_host.log.info("Step 1: Enable/disable VoLTE and WFC.")
        for sub_id, volte in zip([slot_0_subid, slot_1_subid], enable_volte):
            if not toggle_volte_for_subscription(
                self.log,
                ad_host,
                new_state=volte,
                sub_id=sub_id):
                return False

        for sub_id, wfc, mode in zip(
            [slot_0_subid, slot_1_subid], enable_wfc, wfc_mode):
            if not toggle_wfc_for_subscription(
                self.log,
                ad_host,
                new_state=wfc,
                sub_id=sub_id):
                return False
            if not set_wfc_mode_for_subscription(ad_host, mode, sub_id=sub_id):
                return False

        ad_host.log.info("Step 2: Switch DDS.")
        if dds_slot:
            if not set_dds_on_slot_1(ad_host):
                ad_host.log.warning(
                    "Failed to set DDS at eSIM on %s", ad_host.serial)
                return
        else:
            if not set_dds_on_slot_0(ad_host):
                ad_host.log.warning(
                    "Failed to set DDS at pSIM on %s", ad_host.serial)
                return

        ad_host.log.info("Step 3: Check HTTP connection after DDS switch.")
        if not verify_http_connection(self.log, ads[0]):
            ad_host.log.error("Failed to verify http connection.")
            return False
        else:
            ad_host.log.info("Verify http connection successfully.")

        self.log.info("Step 4: Make 3-way voice call.")
        is_host_in_call = is_phone_in_call_on_rat(
            self.log, ad_host, host_rat[host_slot], only_return_fn=True)
        call_ab_id = self._three_phone_call_mo_add_mt(
            [ad_host, ad_p1, ad_p2],
            [None, None, None],
            [is_host_in_call, None, None],
            reject_once=reject_once)

        if call_ab_id is None:
            if disable_cw:
                set_call_waiting(self.log, ad_host, enable=1)
                if str(getattr(ad_host, "exception", None)) == \
                    "PhoneA call PhoneC failed.":
                    ads[0].log.info("PhoneA failed to call PhoneC due to call"
                    " waiting being disabled.")
                    delattr(ad_host, "exception")
                    return True
            self.log.error("Failed to get call_ab_id")
            return False
        else:
            if disable_cw:
                set_call_waiting(self.log, ad_host, enable=0)
                return False

        calls = ads[0].droid.telecomCallGetCallIds()
        ads[0].log.info("Calls in PhoneA %s", calls)
        if num_active_calls(self.log, ads[0]) != 2:
            return False
        if calls[0] == call_ab_id:
            call_ac_id = calls[1]
        else:
            call_ac_id = calls[0]

        if call_ac_id is None:
            self.log.error("Failed to get call_ac_id")
            return False

        num_swaps = 2
        ad_host.log.info("Step 5: Begin Swap x%s test.", num_swaps)
        if not swap_calls(self.log, ads, call_ab_id, call_ac_id,
                          num_swaps):
            ad_host.log.error("Swap test failed.")
            return False

        if not merge:
            result = True
            if not self._hangup_call(ads[1], "PhoneB"):
                result =  False
            if not self._hangup_call(ads[2], "PhoneC"):
                result =  False
            return result
        else:
            ad_host.log.info("Step 6: Merge calls.")
            if host_rat[host_slot].lower in ["5g_volte", "5g_wfc", "volte", "wfc"]:
                return self._test_ims_conference_merge_drop_second_call_from_participant(
                    call_ab_id, call_ac_id)
            else:
                return self._test_wcdma_conference_merge_drop(
                    call_ab_id, call_ac_id)

    @test_tracker_info(uuid="53169ee2-eb70-423e-bbe0-3112f34d2d73")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_psim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_0(self):
        return self._test_msim_volte_wfc_call_forwarding(
            0,
            0,
            callee_rat=['5g_wfc', 'general'],
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED])

    @test_tracker_info(uuid="f0b1c9ce-a386-4b25-8a44-8ca4897fc650")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_psim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_1(self):
        return self._test_msim_volte_wfc_call_forwarding(
            0,
            1,
            callee_rat=['5g_wfc', 'general'],
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED])

    @test_tracker_info(uuid="c952fe28-823d-412d-a3ac-797bd6e2dc09")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_psim_nsa_5g_volte_wfc_cellular_preferred_wifi_on_dds_0(self):
        return self._test_msim_volte_wfc_call_forwarding(
            0,
            0,
            callee_rat=["5g_volte", "general"],
            is_wifi_connected=True)

    @test_tracker_info(uuid="d9e58366-46ea-454a-a1b1-466ec91112ef")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_esim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_0(self):
        return self._test_msim_volte_wfc_call_forwarding(
            1,
            0,
            callee_rat=['general', '5g_wfc'],
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED])

    @test_tracker_info(uuid="18ce70a6-972c-4723-8e65-0c9814d14e76")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_esim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_1(self):
        return self._test_msim_volte_wfc_call_forwarding(
            1,
            1,
            callee_rat=['general', '5g_wfc'],
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED])

    @test_tracker_info(uuid="d843d4cd-c562-47f1-b35b-57a84896314e")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cfu_esim_nsa_5g_volte_wfc_cellular_preferred_wifi_on_dds_0(self):
        return self._test_msim_volte_wfc_call_forwarding(
            1,
            0,
            callee_rat=["general", "5g_volte"],
            is_wifi_connected=True)

    @test_tracker_info(uuid="556a0737-f2c2-44c4-acfd-4eeb57e4c15e")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cw_hold_swap_psim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_0(self):
        return self._test_msim_volte_wfc_call_voice_conf(
            0,
            0,
            host_rat=['5g_wfc', 'general'],
            merge=False,
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED],
            reject_once=True)

    @test_tracker_info(uuid="d86de799-73ed-432e-b9b8-e762df459ad0")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cw_hold_swap_psim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_1(self):
        return self._test_msim_volte_wfc_call_voice_conf(
            0,
            1,
            host_rat=['5g_wfc', 'general'],
            merge=False,
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED],
            reject_once=True)

    @test_tracker_info(uuid="9b9a9cd0-218f-4694-b5b7-ec2818abad48")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cw_hold_swap_psim_nsa_5g_volte_wfc_cellular_preferred_wifi_on_dds_0(self):
        return self._test_msim_volte_wfc_call_voice_conf(
            0,
            0,
            host_rat=["5g_volte", "general"],
            merge=False,
            is_airplane_mode=False,
            is_wifi_connected=True,
            reject_once=True)

    @test_tracker_info(uuid="02dd5686-0a55-497f-8b0c-9f624b6d7af5")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cw_hold_swap_esim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_0(self):
        return self._test_msim_volte_wfc_call_voice_conf(
            1,
            0,
            host_rat=['general', '5g_wfc'],
            merge=False,
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED],
            reject_once=True)

    @test_tracker_info(uuid="1527f060-8226-4507-a502-09e55096da0a")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cw_hold_swap_esim_nsa_5g_volte_wfc_wifi_preferred_apm_off_dds_1(self):
        return self._test_msim_volte_wfc_call_voice_conf(
            1,
            1,
            host_rat=['general', '5g_wfc'],
            merge=False,
            wfc_mode=[WFC_MODE_WIFI_PREFERRED, WFC_MODE_WIFI_PREFERRED],
            reject_once=True)

    @test_tracker_info(uuid="e6db2878-8d64-4566-95f9-e8cbf28723e8")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_cw_hold_swap_esim_nsa_5g_volte_wfc_cellular_preferred_wifi_on_dds_0(self):
        return self._test_msim_volte_wfc_call_voice_conf(
            1,
            0,
            host_rat=["general", "5g_volte"],
            merge=False,
            is_airplane_mode=False,
            is_wifi_connected=True,
            reject_once=True)
