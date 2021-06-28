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

    @test_tracker_info(uuid="38f01127-54bf-4c55-b7d8-d8f41352b399")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_5g_nsa_volte_esim_4g_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 1, mo_rat=["5g_volte", "volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="4e0c9692-a758-4169-85fe-c33bd2651525")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_5g_nsa_volte_esim_4g_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 1, mt_rat=["5g_volte", "volte"], msg="SMS", direction="mt")

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

    @test_tracker_info(uuid="527e8629-6e0d-4742-98c0-5cbc868c430e")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_4g_volte_psim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 1, mo_rat=["5g_volte", "volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="66277aa0-0a9a-4a25-828f-b0315ae7fd0e")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_4g_volte_psim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 1, mt_rat=["5g_volte", "volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="a4d797b6-2699-48de-b36b-b10a1901305b")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_4g_volte_esim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 0, mo_rat=["volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="371286ba-f1da-4459-a7e8-0368d0fae147")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_4g_volte_esim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 0, mt_rat=["volte", "5g_volte"], msg="SMS", direction="mt")

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

    @test_tracker_info(uuid="dfe54cea-8396-4af4-8aee-9dadad602e5b")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_5g_nsa_volte_psim_4g_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 0, mo_rat=["volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="fd4ae44c-3527-4b90-8d33-face10e160a6")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_5g_nsa_volte_psim_4g_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 0, mt_rat=["volte", "5g_volte"], msg="SMS", direction="mt")

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

    @test_tracker_info(uuid="dde1e900-abcd-4a5f-8872-02456ea248ee")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 0, mo_rat=["5g_volte", "5g_volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="5a8ad6dc-687a-498e-8b99-119f3cbb781c")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 0, mt_rat=["5g_volte", "5g_volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="765443f4-d4a0-45fe-8c97-763feb4b588b")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 1, mo_rat=["5g_volte", "5g_volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="026b9e8f-400e-4b59-b40d-d4e741838be0")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 1, mt_rat=["5g_volte", "5g_volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="468536c1-de6e-48e7-b59e-11f17389ac12")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 0, mo_rat=["5g_volte", "5g_volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="c4ae7f6b-bc20-4cb2-8e41-8a02171aec6f")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 0, mt_rat=["5g_volte", "5g_volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="2d70443e-b442-48e0-9c1f-ce1409184ff8")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 1, mo_rat=["5g_volte", "5g_volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="47fbc6c0-ca76-44c0-a166-d8c99d16b6ac")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 1, mt_rat=["5g_volte", "5g_volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="39684fbc-73d1-48cb-af3f-07a366a6b190")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 0, mo_rat=["5g_volte", "volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="6adf4163-4969-4129-bbac-4ebdac4c4cf5")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 0, mt_rat=["5g_volte", "volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="7b636038-5b0c-4844-ba2a-2e76ed787f72")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_psim_5g_nsa_volte_esim_4g_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 1, mo_rat=["5g_volte", "volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="b5008ad4-372d-4849-b47b-583be6aa080a")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_psim_5g_nsa_volte_esim_4g_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 1, mt_rat=["5g_volte", "volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="fd6b33b6-c654-4ec0-becc-2fd7ec10c291")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 0, mo_rat=["5g_volte", "volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="0267c4e8-e5b8-4001-912f-76c387a15f79")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 0, mt_rat=["5g_volte", "volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="a54caa16-dfc6-46e1-a376-b4b585e2e840")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_esim_4g_volte_psim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 1, mo_rat=["5g_volte", "volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="f6af184a-933b-467e-81a7-44ef48b56540")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_esim_4g_volte_psim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 1, mt_rat=["5g_volte", "volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="2e89f125-aacc-4c36-a1c2-308cd83b0e22")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_psim_4g_volte_esim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 0, mo_rat=["volte", "5g_volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="03c23c94-3cc5-4ecf-9b87-273c815b9f53")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_psim_4g_volte_esim_5g_nsa_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 0, mt_rat=["volte", "5g_volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="d2af382a-0f87-46c0-b2de-84f5a549e32c")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            0, None, 1, mo_rat=["volte", "5g_volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="bf788d99-954b-47e2-b465-8565bb30e907")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 0, 1, mt_rat=["volte", "5g_volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="f0b1d46b-6ddc-4625-b653-38e323e542ad")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_esim_5g_nsa_volte_psim_4g_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 0, mo_rat=["volte", "5g_volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="b17a4943-1f69-428a-bd63-13144b2bc592")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_esim_5g_nsa_volte_psim_4g_volte_dds_0(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 0, mt_rat=["volte", "5g_volte"], msg="MMS", direction="mt")

    @test_tracker_info(uuid="98d7b7b8-0bd3-4362-957b-56c8b19ac3d4")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mo_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            1, None, 1, mo_rat=["volte", "5g_volte"], msg="MMS", direction="mo")

    @test_tracker_info(uuid="5f0f4174-548d-43ab-b520-5e2211fdaacc")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_mms_mt_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        return dsds_message_test(
            self.log,
            self.android_devices,
            None, 1, 1, mt_rat=["volte", "5g_volte"], msg="MMS", direction="mt")