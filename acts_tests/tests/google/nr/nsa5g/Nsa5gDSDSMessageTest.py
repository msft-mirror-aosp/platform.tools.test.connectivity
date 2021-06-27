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
from acts_contrib.test_utils.tel.loggers.protos.telephony_metric_pb2 import TelephonyVoiceTestResult
from acts_contrib.test_utils.tel.loggers.telephony_metric_logger import TelephonyMetricLogger
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_dsds_utils import dsds_message_test

CallResult = TelephonyVoiceTestResult.CallResult.Value

class Nsa5gDSDSMessageTest(TelephonyBaseTest):
    def setup_class(self):
        TelephonyBaseTest.setup_class(self)
        self.tel_logger = TelephonyMetricLogger.for_test_case()

    def teardown_test(self):
        ensure_phones_idle(self.log, self.android_devices)

    @test_tracker_info(uuid="123a50bc-f0a0-4129-9377-cc63c76d5727")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 0, mo_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="5dcf76bc-369f-4d47-b3ec-318559a95843")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 0, mt_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="dd4a9fb5-b0fe-492b-ad24-61e022d13a22")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 0, mo_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="09100a8f-b7ed-41a0-9f04-e716115cabb8")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 0, mt_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="245a6148-cd45-4b82-bf4c-5679ebe15e29")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 1, mo_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="5a93d377-d9bc-477c-bfab-2496064e3522")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 1, mt_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="b5971c57-bbe9-4e87-a6f2-9953fa770a15")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 1, mo_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="142b11d4-b593-4a09-8fc6-35e310739244")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 1, mt_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="87759475-0208-4d9b-b5b9-814fdb97f09c")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 0, mo_rat=["5g_volte", "volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="2f14e81d-330f-4cdd-837c-1168185ffec4")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 0, mt_rat=["5g_volte", "volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="9cc45474-1fca-4008-8499-87829d6516ea")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 0, mo_rat=["5g_volte", "volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="341786de-5b23-438a-a91b-97cf420ef5fd")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 0, mt_rat=["5g_volte", "volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="51d5e05d-66e7-4369-91e0-6cdc573d9a59")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 1, mo_rat=["volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="38271a0f-2efb-4991-9f24-6da9f003ddd4")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 1, mt_rat=["volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="183cda35-45aa-485d-b3d4-975d78f7d361")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 1, mo_rat=["volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="d9cb69ce-c462-4fd4-b716-bfb1fd2ed86a")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 1, mt_rat=["volte", "5g_volte"], msg="SMS", direction="mt")
