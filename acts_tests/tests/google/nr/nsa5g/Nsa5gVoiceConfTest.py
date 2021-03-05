#!/usr/bin/env python3.4
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

"""
    Test Script for 5G Voice Conference scenarios
"""


import time
from acts import signals
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import CALL_STATE_ACTIVE
from acts_contrib.test_utils.tel.tel_defines import CAPABILITY_CONFERENCE
from acts_contrib.test_utils.tel.tel_subscription_utils import get_outgoing_voice_sub_id
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import get_capability_for_subscription
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_volte
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_wcdma
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_voice_3g
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_volte
from acts_contrib.test_utils.tel.tel_voice_conf_utils import _get_expected_call_state
from acts_contrib.test_utils.tel.tel_voice_conf_utils import \
    _test_ims_conference_merge_drop_first_call_from_host
from acts_contrib.test_utils.tel.tel_voice_conf_utils import \
    _test_ims_conference_merge_drop_first_call_from_participant
from acts_contrib.test_utils.tel.tel_voice_conf_utils import \
    _test_ims_conference_merge_drop_second_call_from_host
from acts_contrib.test_utils.tel.tel_voice_conf_utils import \
    _test_ims_conference_merge_drop_second_call_from_participant
from acts_contrib.test_utils.tel.tel_voice_conf_utils import _test_call_mo_mo_add_swap_x
from acts_contrib.test_utils.tel.tel_voice_conf_utils import _test_call_mo_mt_add_swap_x
from acts_contrib.test_utils.tel.tel_voice_conf_utils import _test_call_mt_mt_add_swap_x
from acts_contrib.test_utils.tel.tel_voice_conf_utils import \
    _three_phone_hangup_call_verify_call_state
from acts_contrib.test_utils.tel.tel_5g_utils import is_current_network_5g_nsa
from acts_contrib.test_utils.tel.tel_5g_utils import provision_device_for_5g


class Nsa5gVoiceConfTest(TelephonyBaseTest):
    def setup_class(self):
        TelephonyBaseTest.setup_class(self)
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


    """ Tests Begin """


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_5g_nsa_volte_merge_drop_second_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneA (nsa 5G VoLTE) to PhoneC (nsa 5G VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_5g_nsa_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneA (nsa 5G VoLTE) to PhoneC (nsa 5G VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                       ads=ads,
                                       num_swaps=0,
                                       phone_setup_a=provision_device_for_5g,
                                       phone_setup_b=provision_device_for_5g,
                                       phone_setup_c=provision_device_for_5g,
                                       verify_phone_a_network_subscription=is_phone_in_call_volte,
                                       verify_phone_b_network_subscription=is_phone_in_call_volte,
                                       verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_5g_nsa_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneA (nsa 5G VoLTE) to PhoneC (nsa 5G VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_5g_nsa_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneA (nsa 5G VoLTE) to PhoneC (nsa 5G VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_5g_nsa_volte_merge_drop_second_call_from_participant(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_5g_nsa_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="86faf200-be78-452d-8662-85e7f42a2d3b")
    def test_5g_nsa_volte_mo_mt_add_5g_nsa_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_5g_nsa_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_5g_nsa_volte_merge_drop_second_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_5g_nsa_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_5g_nsa_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_5g_nsa_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_4g_volte_merge_drop_second_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (VoLTE), accept on PhoneB.
        2. Call from PhoneA (nsa 5G VoLTE) to PhoneC (VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_4g_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (VoLTE), accept on PhoneB.
        2. Call from PhoneA (nsa 5G VoLTE) to PhoneC (VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_4g_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (VoLTE), accept on PhoneB.
        2. Call from PhoneA (nsa 5G VoLTE) to PhoneC (VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_4g_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (VoLTE), accept on PhoneB.
        2. Call from PhoneA (nsa 5G VoLTE) to PhoneC (VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_4g_volte_merge_drop_second_call_from_participant(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (VoLTE), accept on PhoneB.
        2. Call from PhoneC (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_4g_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (VoLTE), accept on PhoneB.
        2. Call from PhoneC (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="86faf200-be78-452d-8662-85e7f42a2d3b")
    def test_5g_nsa_volte_mo_mt_add_4g_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (VoLTE), accept on PhoneB.
        2. Call from PhoneC (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_4g_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5G VoLTE) to PhoneB (VoLTE), accept on PhoneB.
        2. Call from PhoneC (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_4g_volte_merge_drop_second_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        2. Call from PhoneC (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_4g_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        2. Call from PhoneC (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_4g_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        2. Call from PhoneC (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_4g_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        2. Call from PhoneC (VoLTE) to PhoneA (nsa 5G VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mo_add_5g_nsa_volte_merge_drop_second_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneA (VoLTE) to PhoneC (nsa 5G VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mo_add_5g_nsa_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneA (VoLTE) to PhoneC (nsa 5G VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mo_add_5g_nsa_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneA (VoLTE) to PhoneC (nsa 5G VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mo_add_5g_nsa_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneA (VoLTE) to PhoneC (nsa 5G VoLTE), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mt_add_5g_nsa_volte_merge_drop_second_call_from_participant(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mt_add_5g_nsa_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="86faf200-be78-452d-8662-85e7f42a2d3b")
    def test_4g_volte_mo_mt_add_5g_nsa_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mt_add_5g_nsa_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (VoLTE) to PhoneB (nsa 5G VoLTE), accept on PhoneB.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mt_mt_add_5g_nsa_volte_merge_drop_second_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mt_mt_add_5g_nsa_volte_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mt_mt_add_5g_nsa_volte_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mt_mt_add_5g_nsa_volte_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        2. Call from PhoneC (nsa 5G VoLTE) to PhoneA (VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)

    """" New Test """

    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_wcdma_merge_drop_second_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5g VoLTE) to PhoneB (WCDMA), accept on PhoneB.
        2. Call from PhoneA (nsa 5g VoLTE) to PhoneC (WCDMA), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_wcdma_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5g VoLTE) to PhoneB (WCDMA), accept on PhoneB.
        2. Call from PhoneA (nsa 5g VoLTE) to PhoneC (WCDMA), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_wcdma_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5g VoLTE) to PhoneB (WCDMA), accept on PhoneB.
        2. Call from PhoneA (nsa 5g VoLTE) to PhoneC (WCDMA), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_wcdma_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5g VoLTE) to PhoneB (WCDMA), accept on PhoneB.
        2. Call from PhoneA (nsa 5g VoLTE) to PhoneC (WCDMA), accept on PhoneC.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_wcdma_merge_drop_second_call_from_participant_cep(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5g VoLTE) to PhoneB (WCDMA), accept on PhoneB.
        2. Call from PhoneC (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)



    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_wcdma_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5g VoLTE) to PhoneB (WCDMA), accept on PhoneB.
        2. Call from PhoneC (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_wcdma_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5g VoLTE) to PhoneB (WCDMA), accept on PhoneB.
        2. Call from PhoneC (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_wcdma_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneA (nsa 5g VoLTE) to PhoneB (WCDMA), accept on PhoneB.
        2. Call from PhoneC (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_wcdma_merge_drop_second_call_from_participant_cep(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        2. Call from PhoneC (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneC, verify call continues.
        5. End call on PhoneB, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_wcdma_merge_drop_second_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        2. Call from PhoneC (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-C, verify call continues.
        5. On PhoneA disconnect call between A-B, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_second_call_from_host(self.log, self.android_devices,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_wcdma_merge_drop_first_call_from_participant(
            self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        2. Call from PhoneC (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. End call on PhoneB, verify call continues.
        5. End call on PhoneC, verify call end on PhoneA.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_participant(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mt_mt_add_wcdma_merge_drop_first_call_from_host(self):
        """ Test VoLTE Conference Call among three phones.

        1. Call from PhoneB (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        2. Call from PhoneC (WCDMA) to PhoneA (nsa 5g VoLTE), accept on PhoneA.
        3. On PhoneA, merge to conference call.
        4. On PhoneA disconnect call between A-B, verify call continues.
        5. On PhoneA disconnect call between A-C, verify call continues.

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        call_ab_id, call_ac_id = _test_call_mt_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=0,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_voice_3g,
                                        phone_setup_c=phone_setup_voice_3g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_wcdma,
                                        verify_phone_c_network_subscription=is_phone_in_call_wcdma)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _test_ims_conference_merge_drop_first_call_from_host(self.log, ads,
            call_ab_id, call_ac_id)


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_5g_nsa_volte_swap_twice_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneA (nsa 5g VoLTE) call PhoneC (nsa 5g VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_5g_nsa_volte_swap_twice_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneA (nsa 5g VoLTE) call PhoneC (nsa 5g VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_5g_nsa_volte_swap_twice_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneC (nsa 5g VoLTE) call PhoneA (nsa 5g VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_5g_nsa_volte_swap_twice_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneC (nsa 5g VoLTE) call PhoneA (nsa 5g VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_5g_nsa_volte_swap_once_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneA (nsa 5g VoLTE) call PhoneC (nsa 5g VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_5g_nsa_volte_swap_once_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneA (nsa 5g VoLTE) call PhoneC (nsa 5g VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_5g_nsa_volte_swap_once_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneC (nsa 5g VoLTE) call PhoneA (nsa 5g VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False
        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_5g_nsa_volte_swap_once_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneC (nsa 5g VoLTE) call PhoneA (nsa 5g VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_4g_volte_swap_twice_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (VoLTE), accept on PhoneB.
        PhoneA (nsa 5g VoLTE) call PhoneC (VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_4g_volte_swap_twice_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (VoLTE), accept on PhoneB.
        PhoneA (nsa 5g VoLTE) call PhoneC (VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_4g_volte_swap_twice_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (VoLTE), accept on PhoneB.
        PhoneC (VoLTE) call PhoneA (nsa 5g VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_4g_volte_swap_twice_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (VoLTE), accept on PhoneB.
        PhoneC (VoLTE) call PhoneA (nsa 5g VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_4g_volte_swap_once_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (VoLTE), accept on PhoneB.
        PhoneA (nsa 5g VoLTE) call PhoneC (VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mo_add_4g_volte_swap_once_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (VoLTE), accept on PhoneB.
        PhoneA (nsa 5g VoLTE) call PhoneC (VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_4g_volte_swap_once_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (VoLTE), accept on PhoneB.
        PhoneC (VoLTE) call PhoneA (nsa 5g VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False
        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_5g_nsa_volte_mo_mt_add_4g_volte_swap_once_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (nsa 5g VoLTE) call PhoneB (VoLTE), accept on PhoneB.
        PhoneC (VoLTE) call PhoneA (nsa 5g VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=provision_device_for_5g,
                                        phone_setup_b=phone_setup_volte,
                                        phone_setup_c=phone_setup_volte,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mo_add_5g_nsa_volte_swap_twice_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneA (VoLTE) call PhoneC (nsa 5g VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mo_add_5g_nsa_volte_swap_twice_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneA (VoLTE) call PhoneC (nsa 5g VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mt_add_5g_nsa_volte_swap_twice_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneC (nsa 5g VoLTE) call PhoneA (VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mt_add_5g_nsa_volte_swap_twice_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneC (nsa 5g VoLTE) call PhoneA (VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=2,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mo_add_5g_nsa_volte_swap_once_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneA (VoLTE) call PhoneC (nsa 5g VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mo_add_5g_nsa_volte_swap_once_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneA (VoLTE) call PhoneC (nsa 5g VoLTE), accept on PhoneC.
        Swap active call on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mo_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[2]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mt_add_5g_nsa_volte_swap_once_drop_held(self):
        """Test swap feature in VoLTE call.

        PhoneA (VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneC (nsa 5g VoLTE) call PhoneA (VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneC, check if call continues between AB.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False
        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[2],
            ad_verify=ads[0],
            call_id=call_ab_id,
            call_state=CALL_STATE_ACTIVE,
            ads_active=[ads[0], ads[1]])


    @TelephonyBaseTest.tel_test_wrap
    @test_tracker_info(uuid="")
    def test_4g_volte_mo_mt_add_5g_nsa_volte_swap_once_drop_active(self):
        """Test swap feature in VoLTE call.

        PhoneA (VoLTE) call PhoneB (nsa 5g VoLTE), accept on PhoneB.
        PhoneC (nsa 5g VoLTE) call PhoneA (VoLTE), accept on PhoneA.
        Swap active call on PhoneA.
        Hangup call from PhoneB, check if call continues between AC.

        """
        ads = self.android_devices

        call_ab_id, call_ac_id = _test_call_mo_mt_add_swap_x(log=self.log,
                                        ads=ads,
                                        num_swaps=1,
                                        phone_setup_a=phone_setup_volte,
                                        phone_setup_b=provision_device_for_5g,
                                        phone_setup_c=provision_device_for_5g,
                                        verify_phone_a_network_subscription=is_phone_in_call_volte,
                                        verify_phone_b_network_subscription=is_phone_in_call_volte,
                                        verify_phone_c_network_subscription=is_phone_in_call_volte)
        if call_ab_id is None or call_ac_id is None:
            return False

        return _three_phone_hangup_call_verify_call_state(log=self.log,
            ad_hangup=ads[1],
            ad_verify=ads[0],
            call_id=call_ac_id,
            call_state=_get_expected_call_state(ads[0]),
            ads_active=[ads[0], ads[2]])

