#!/usr/bin/env python3
#
#   Copyright 2021 - The Android Open Source Project
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
import datetime
import logging

from acts import asserts
from acts.test_decorators import test_tracker_info

from acts.base_test import BaseTestClass
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.GFTInOutBaseTest import GFTInOutBaseTest

from acts_contrib.test_utils.tel.tel_test_utils import get_service_state_by_adb
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import run_multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import get_screen_shot_log
from acts_contrib.test_utils.tel.tel_test_utils import get_screen_shot_logs
from acts_contrib.test_utils.tel.tel_test_utils import log_screen_shot
from acts_contrib.test_utils.tel.tel_test_utils import hangup_call

from acts_contrib.test_utils.tel.tel_defines import DATA_STATE_CONNECTED
from acts_contrib.test_utils.tel.tel_defines import DATA_STATE_DISCONNECTED
from acts_contrib.test_utils.tel.tel_defines import SERVICE_STATE_EMERGENCY_ONLY
from acts_contrib.test_utils.tel.tel_defines import SERVICE_STATE_IN_SERVICE
from acts_contrib.test_utils.tel.tel_defines import SERVICE_STATE_UNKNOWN
from acts_contrib.test_utils.tel.tel_defines import SERVICE_STATE_OUT_OF_SERVICE
from acts_contrib.test_utils.tel.tel_defines import SERVICE_STATE_POWER_OFF

from acts_contrib.test_utils.tel.gft_inout_utils import check_no_service_time
from acts_contrib.test_utils.tel.gft_inout_utils import check_back_to_service_time
from acts_contrib.test_utils.tel.gft_inout_utils import mo_voice_call
from acts_contrib.test_utils.tel.gft_inout_utils import get_voice_call_type

from acts_contrib.test_utils.tel.gft_inout_defines import VOICE_CALL
from acts_contrib.test_utils.tel.gft_inout_defines import VOLTE_CALL
from acts_contrib.test_utils.tel.gft_inout_defines import CSFB_CALL
from acts_contrib.test_utils.tel.gft_inout_defines import WFC_CALL
from acts_contrib.test_utils.tel.gft_inout_defines import NO_SERVICE_POWER_LEVEL
from acts_contrib.test_utils.tel.gft_inout_defines import IN_SERVICE_POWER_LEVEL
from acts_contrib.test_utils.tel.gft_inout_defines import NO_SERVICE_AREA
from acts_contrib.test_utils.tel.gft_inout_defines import IN_SERVICE_AREA
from acts_contrib.test_utils.tel.gft_inout_defines import WIFI_AREA
from acts_contrib.test_utils.tel.gft_inout_defines import NO_WIFI_AREA
from acts_contrib.test_utils.tel.gft_inout_defines import NO_SERVICE_TIME
from acts_contrib.test_utils.tel.gft_inout_defines import WAIT_FOR_SERVICE_TIME


class TelLabGFTInOutServiceTest(GFTInOutBaseTest):
    def __init__(self, controllers):
        GFTInOutBaseTest.__init__(self, controllers)

    def setup_test(self):
        self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)
        self.adjust_wifi_signal(IN_SERVICE_POWER_LEVEL)
        GFTInOutBaseTest.setup_test(self)
        self.check_network()

    @test_tracker_info(uuid="c602e556-8273-4c75-b8fa-4d51ba514654")
    @TelephonyBaseTest.tel_test_wrap
    def test_in_out_no_service_idle_1min(self, idle_time=60):
        """ UE is in idle
            Move UE from coverage area to no service area and UE shows no service
            Wait for 1 min, then re-enter coverage area

            Args:
                idle_time: idle time in service area

            Returns:
                True if pass; False if fail.
        """
        return self._test_in_out_service_idle(idle_time)

    @test_tracker_info(uuid="c602e556-8273-4c75-b8fa-4d51ba514654")
    @TelephonyBaseTest.tel_test_wrap
    def test_in_out_no_service_idle_2min(self, idle_time=120):
        """ UE is in idle
            Move UE from coverage area to no service area and UE shows no service
            Wait for 2 min, then re-enter coverage area

            Args:
                idle_time: idle time in service area

            Returns:
                True if pass; False if fail.
        """
        return self._test_in_out_service_idle(idle_time)


    @test_tracker_info(uuid="1d437482-caff-4695-9f3f-f3daf6793540")
    @TelephonyBaseTest.tel_test_wrap
    def test_in_out_no_service_idle_5min(self, idle_time=300):
        """ UE is in idle
            Move UE from coverage area to no service area and UE shows no service
            Wait for 5 min, then re-enter coverage area

            Args:
                loop: cycle
                idle_time: idle time in service area

            Returns:
                True if pass; False if fail.
        """
        return self._test_in_out_service_idle(idle_time)

    @test_tracker_info(uuid="339b4bf5-57a1-48f0-b26a-83a7db21b08b")
    @TelephonyBaseTest.tel_test_wrap
    def test_in_out_no_service_idle_10min(self, idle_time=600):
        """ UE is in idle
            Move UE from coverage area to no service area and UE shows no service
            Wait for 10 min, then re-enter coverage area

            Args:
                loop: cycle
                idle_time: idle time in service area

            Returns:
                True if pass; False if fail.
        """
        return self._test_in_out_service_idle(idle_time)

    def _test_in_out_service_idle(self, idle_time, loop=1):
        """ UE is in idle
            Move UE from coverage area to no service area and UE shows no service
            Args:
                loop: cycle
                idle_time: idle time in service area

            Returns:
                True if pass; False if fail.
        """
        test_result = True
        if 'autoio_cycle' in self.user_params:
            loop = self.user_params.get('autoio_cycle')

        for x in range (loop):
            self.log.info("%s loop: %s/%s" %(self.current_test_name,x+1, loop))
            if not self._in_out_service_idle(idle_time):
                test_result = False
        return test_result


    def _in_out_service_idle(self, no_service_time=60, check_back_to_service=True,
                             check_no_service=True):
        """ Move UE from coverage area to no service area and UE shows no service
            Wait for no_service_time sec , then re-enter coverage area

            Args:
                no_service_time: stay at no service area time in sec
                check_back_to_service: check device is back to service flag
                check_no_service: check device is no service flag

            Returns:
                True if pass; False if fail.
        """
        test_result = True
        for ad in self.android_devices:
            network_type = ad.droid.telephonyGetNetworkType()
            service_state = get_service_state_by_adb(self.log,ad)
            ad.log.info("service_state=%s. network_type=%s"
                %(service_state ,network_type))
            if service_state != SERVICE_STATE_IN_SERVICE:
                ad.log.info("Device is not ready for AutoIO test. service_state=%s."
                            %(service_state))
                return False

        self.log.info("Move UE from coverage area to no service area")
        self.adjust_cellular_signal(NO_SERVICE_POWER_LEVEL)

        if check_no_service:
            tasks = [(check_no_service_time, (ad, )) for ad in self.android_devices]
            if not multithread_func(self.log, tasks):
                self.log.info("Device does not become no service")
                return False
            else:
                self.log.info("wait for %s sec in no/limited service area" %(no_service_time))
                time.sleep(no_service_time)
        self.log.info("Move UE back to service area")
        self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)

        if test_result:
            if check_back_to_service:
                tasks = [(check_back_to_service_time, (ad,)) for ad in self.android_devices]
                test_result = multithread_func(self.log, tasks)
                self.log.info("Device is not back to the service")
        return test_result