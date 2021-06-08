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

from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_dsds_utils import dsds_voice_call_test

class Nsa5gDSDSVoiceTest(TelephonyBaseTest):
    def setup_class(self):
        TelephonyBaseTest.setup_class(self)

    def teardown_test(self):
        ensure_phones_idle(self.log, self.android_devices)

    # psim 5g nsa volte & esim 4g volte
    @test_tracker_info(uuid="2890827d-deb2-42ea-921d-3b45f7645d61")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_voice_psim_mo_5g_nsa_volte_esim_4g_volte_dds_0(self):
        """A MO VoLTE call dialed at pSIM, where
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)
        """
        return dsds_voice_call_test(
            self.log,
            self.android_devices,
            0,
            None,
            0,
            mo_rat=["5g_volte", "volte"],
            call_direction="mo")

    @test_tracker_info(uuid="83d9b127-25da-4c19-a3a0-470a5ced020b")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_voice_psim_mt_5g_nsa_volte_esim_4g_volte_dds_0(self):
        """A MT VoLTE call received at pSIM, where
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)
        """
        return dsds_voice_call_test(
            self.log,
            self.android_devices,
            None,
            0,
            0,
            mt_rat=["5g_volte", "volte"],
            call_direction="mt")

    @test_tracker_info(uuid="14c29c79-d100-4f03-b3df-f2ae4a172cc5")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_voice_esim_mo_4g_volte_psim_5g_nsa_volte_dds_0(self):
        """A MO VoLTE call dialed at eSIM, where
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)
        """
        return dsds_voice_call_test(
            self.log,
            self.android_devices,
            1,
            None,
            0,
            mo_rat=["5g_volte", "volte"],
            call_direction="mo")

    @test_tracker_info(uuid="12a59cc1-8c1e-44a0-836b-0d842c0746a3")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_voice_esim_mt_4g_volte_psim_5g_nsa_volte_dds_0(self):
        """A MT VoLTE call received at eSIM, where
            - pSIM 5G NSA VoLTE
            - eSIM 4G VoLTE
            - DDS at pSIM (slot 0)
        """
        return dsds_voice_call_test(
            self.log,
            self.android_devices,
            None,
            1,
            0,
            mt_rat=["5g_volte", "volte"],
            call_direction="mt")

    # psim 4g volte & esim 5g nsa volte
    @test_tracker_info(uuid="8ee47ad7-24b6-4cd3-9443-6ab677695eb7")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_voice_psim_mo_4g_volte_esim_5g_nsa_volte_dds_1(self):
        """A MO VoLTE call dialed at pSIM, where
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at eSIM (slot 1)
        """
        return dsds_voice_call_test(
            self.log,
            self.android_devices,
            0,
            None,
            1,
            mo_rat=["volte", "5g_volte"],
            call_direction="mo")

    @test_tracker_info(uuid="8795b95d-a138-45cd-b45c-41ad4021589a")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_voice_psim_mt_4g_volte_esim_5g_nsa_volte_dds_1(self):
        """A MT VoLTE call received at pSIM, where
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at eSIM (slot 1)
        """
        return dsds_voice_call_test(
            self.log,
            self.android_devices,
            None,
            0,
            1,
            mt_rat=["volte", "5g_volte"],
            call_direction="mt")

    @test_tracker_info(uuid="33f2fa73-de7b-4b68-b9b8-aa08f6511e1a")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_voice_esim_mo_5g_nsa_volte_psim_4g_volte_dds_1(self):
        """A MO VoLTE call dialed at eSIM, where
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at eSIM (slot 1)
        """
        return dsds_voice_call_test(
            self.log,
            self.android_devices,
            1,
            None,
            1,
            mo_rat=["volte", "5g_volte"],
            call_direction="mo")

    @test_tracker_info(uuid="b1ae55f1-dfd4-4e50-a0e3-df3b3ae29c68")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_voice_esim_mt_5g_nsa_volte_psim_4g_volte_dds_1(self):
        """A MT VoLTE call received at eSIM, where
            - pSIM 4G VoLTE
            - eSIM 5G NSA VoLTE
            - DDS at eSIM (slot 1)
        """
        return dsds_voice_call_test(
            self.log,
            self.android_devices,
            None,
            1,
            1,
            mt_rat=["volte", "5g_volte"],
            call_direction="mt")