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
import sys
import collections
import random
import time
import datetime
import os
import logging
import json
import subprocess
import math
import re

from acts import asserts
from acts.test_decorators import test_tracker_info

from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.GFTInOutBaseTest import GFTInOutBaseTest
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_test_utils import set_wfc_mode
from acts_contrib.test_utils.tel.tel_test_utils import toggle_wfc
from acts_contrib.test_utils.tel.tel_test_utils import toggle_volte
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import run_multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import get_screen_shot_log
from acts_contrib.test_utils.tel.tel_test_utils import get_screen_shot_logs
from acts_contrib.test_utils.tel.tel_test_utils import log_screen_shot
from acts_contrib.test_utils.tel.tel_test_utils import hangup_call
from acts_contrib.test_utils.tel.tel_test_utils import is_ims_registered
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_iwlan
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_volte
from acts_contrib.test_utils.tel.tel_voice_utils import \
    phone_setup_volte_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import wait_for_ims_registered
from acts_contrib.test_utils.tel.gft_inout_utils import check_no_service_time
from acts_contrib.test_utils.tel.gft_inout_utils import check_back_to_service_time
from acts_contrib.test_utils.tel.gft_inout_utils import mo_voice_call
from acts_contrib.test_utils.tel.gft_inout_utils import get_voice_call_type
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_ONLY
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_CELLULAR_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_DISABLED
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


WAIT_TIME_AT_NO_SERVICE_AREA = 300


class TelLabGFTVoWifiTest(GFTInOutBaseTest):

    def __init__(self, controllers):
        GFTInOutBaseTest.__init__(self, controllers)
        self.wifi_ssid = self.user_params.get('wifi_network_ssid')
        self.wifi_pw = self.user_params.get('wifi_network_pw')
        self.my_error_msg = ""
        logging.info("wifi_ssid = %s" %self.wifi_ssid)
        logging.info("wifi_pw = %s" %self.wifi_pw )

    def setup_test(self):
        self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)
        self.adjust_wifi_signal(IN_SERVICE_POWER_LEVEL)
        GFTInOutBaseTest.setup_test(self)
        for ad in self.android_devices:
            ad.droid.wifiToggleState(True)
        # Ensure IMS on
        self.log.info("Turn on ims")
        tasks = [(phone_setup_volte, (self.log, ad, )) for ad in self.android_devices]
        if not multithread_func(self.log, tasks):
            error_msg = "fail to setup volte"
            self.log.info(error_msg)
            asserts.skip(error_msg)
        # ensure WFC is enabled
        tasks = [(toggle_wfc, (self.log, ad,True)) for ad in self.android_devices]
        if not multithread_func(self.log, tasks):
            error_msg = "device does not support WFC! Skip test"
            self.log.info(error_msg)
            asserts.skip(error_msg)
        for ad in self.android_devices:
            log_screen_shot(ad, self.test_name)

    def teardown_test(self):
        super().teardown_test()
        tasks = [(toggle_airplane_mode, (self.log, ad, False))
            for ad in self.android_devices]
        multithread_func(self.log, tasks)

    @test_tracker_info(uuid="21ec1aff-a161-4dc9-9682-91e0dd8a13a7")
    @TelephonyBaseTest.tel_test_wrap
    def test_wfc_in_out_wifi(self, loop=1, wfc_mode=WFC_MODE_WIFI_PREFERRED):
        """
            Enable Wi-Fi calling in Wi-Fi Preferred mode and connect to a
            valid Wi-Fi AP. Test VoWiFi call under WiFi and cellular area
            -> move to WiFi only area -> move to Cellular only area
            Args:
                loop: repeat this test cases for how many times
                wfc_mode: wfc mode
            Returns:
                True if pass; False if fail
        """
        test_result = True
        if 'wfc_cycle' in self.user_params:
            loop = self.user_params.get('wfc_cycle')
        for x in range (loop):
            self.log.info("%s loop: %s/%s" %(self.current_test_name, x+1, loop))
            self.log.info("Start test at cellular and wifi area")
            self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)
            self.adjust_wifi_signal(IN_SERVICE_POWER_LEVEL)
            self.check_network()
            if self._enable_wifi_calling(wfc_mode):
                if not self._voice_call(self.android_devices, WFC_CALL, False):
                    self.log.info("VoWiFi call failure")
                    return False
                self.log.info("Move to no service area and wifi area")
                self.adjust_cellular_signal(NO_SERVICE_POWER_LEVEL)
                time.sleep(WAIT_TIME_AT_NO_SERVICE_AREA)
                # check call status
                for ad in self.android_devices:
                    get_voice_call_type(ad)
                self.log.info("Move back to service area and no wifi area")
                self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)
                self.adjust_wifi_signal(NO_SERVICE_POWER_LEVEL)
            self.log.info("Verify device state after in-out service")
            tasks = [(check_back_to_service_time, (ad,)) for ad in self.android_devices]
            test_result = multithread_func(self.log, tasks)
            if test_result:
                test_result = self._voice_call(self.android_devices, VOICE_CALL)
            else:
                self.log.info("device is not back to service")
        return test_result

    def _enable_wifi_calling(self, wfc_mode, is_airplane_mode=False, call_type=None, end_call=True, talk_time=30):
        """ Enable Wi-Fi calling in Wi-Fi Preferred mode and connect to a
            valid Wi-Fi AP.

            Args:
                wfc_mode: wfc mode
                is_airplane_mode: toggle airplane mode on or off
                voice_call_type: None would not make any calls

            Returns:
                True if pass; False if fail.
        """
        self.log.info("Move in WiFi area and set WFC mode to %s, airplane mode=%s" %(wfc_mode, is_airplane_mode))
        self.adjust_wifi_signal(IN_SERVICE_POWER_LEVEL)
        time.sleep(10)
        # enable WiFi
        tasks = [(set_wfc_mode, (self.log, ad, wfc_mode )) for ad in self.android_devices]
        #tasks = [(phone_setup_iwlan, (self.log, ad, is_airplane_mode ,wfc_mode, self. wifi_ssid)) for ad in self.android_devices]
        if not multithread_func(self.log, tasks):
            error_msg = "fail to setup WFC mode to %s" %(wfc_mode)
            self.log.error(error_msg)
            asserts.skip(error_msg)
        if call_type != None:
            if not self._voice_call(self.android_devices, call_type, end_call, talk_time):
                self.log.error("%s failuer" %call_type)
                return False
        return True

    def _voice_call(self, ads, call_type, end_call=True, talk_time=30):
        """ Enable Wi-Fi calling in Wi-Fi Preferred mode and connect to a
            valid Wi-Fi AP.
            Args:
                ads: android devices
                call_type: WFC call, VOLTE call. CSFB call, voice call
                end_call: hangup call after voice call flag
                talk_time: in call duration in sec
            Returns:
                True if pass; False if fail.
        """
        tasks = [(mo_voice_call, (self.log, ad, call_type, end_call, talk_time))
            for ad in ads]
        if not multithread_func(self.log, tasks):
            error_msg = "%s failure" %(call_type)
            self.log.error(error_msg)
            self.my_error_msg += error_msg
            return False
        return True

    @test_tracker_info(uuid="3ca05651-a6c9-4b6b-84c0-a5d761757061")
    @TelephonyBaseTest.tel_test_wrap
    def test_in_out_idle_wifi_preferred(self, wfc_mode=WFC_MODE_WIFI_PREFERRED):
        ''' In/Out Service - Idle + VoWiFi registered in Wi-Fi Preferred mode
            Enable Wi-Fi calling in Wi-Fi Preferred mode and connect to a valid Wi-Fi AP.
            Idle in service area.
            Move to no service area for 1 minute when idle.
            Move back to service area and verfiy device status.

            Args:
                loop: repeat this test cases for how many times
                wfc_mode: wfc mode

            Returns:
                True if pass; False if fail
            Raises:
                TestFailure if not success.
        '''
        return self._in_out_wifi_wfc_mode(1, wfc_mode)


    @test_tracker_info(uuid="b06121de-f458-4fc0-b9ef-efac02e46181")
    @TelephonyBaseTest.tel_test_wrap
    def test_in_out_idle_cellular_preferred(self, loop=1, wfc_mode=WFC_MODE_CELLULAR_PREFERRED):
        ''' In/Out Service - Idle + VoLTE registered in Cellular preferred mode
            Enable Wi-Fi calling in Cellular preferred mode and connect to a valid Wi-Fi AP.
            Idle in service area.
            Move to no service area for 1 minute when idle.
            Move back to service area and verify device status

            Args:
                loop: repeat this test cases for how many times
                wfc_mode: wfc mode

            Returns:
                True if pass; False if fail
            Raises:
                TestFailure if not success.
        '''
        test_result = self._in_out_wifi_wfc_mode(1, WFC_MODE_CELLULAR_PREFERRED)
        asserts.assert_true(test_result, "Fail: %s." %(self.my_error_msg),
            extras={"failure_cause": self.my_error_msg})

    def _in_out_wifi_wfc_mode(self, loop=1, wfc_mode=WFC_MODE_CELLULAR_PREFERRED):
        error_msg = ""
        test_result = True
        if 'wfc_cycle' in self.user_params:
            loop = self.user_params.get('wfc_cycle')

        for x in range (loop):
            self.log.info("%s loop: %s/%s" %(self.current_test_name, x+1, loop))
            self.my_error_msg += "cylce%s: " %(x+1)
            self.log.info("Move in Wi-Fi area and set to %s" %(wfc_mode))
            self.adjust_wifi_signal(IN_SERVICE_POWER_LEVEL)
            if not self._enable_wifi_calling(wfc_mode):
                error_msg = "Fail to setup WFC mode"
                self.log.info(error_msg)
                self.my_error_msg += error_msg
                return False
            self.log.info("Idle in service area")
            self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)
            self.check_network()

            self.log.info("Move to no service area in idle mode for 1 min")
            self.adjust_cellular_signal(NO_SERVICE_POWER_LEVEL)
            time.sleep(NO_SERVICE_TIME)

            self.log.info("Move back to service area and verify device status")
            self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)
            self.log.info("Verify device status after in-out service")
            tasks = [(check_back_to_service_time, (ad,)) for ad in self.android_devices]
            test_result = multithread_func(self.log, tasks)
            if test_result:
                tasks = [(self.verify_device_status, (ad, VOICE_CALL))
                    for ad in self.android_devices]
                if not  multithread_func(self.log, tasks):
                    error_msg = "verify_device_status fail, "
                    self.log.info(error_msg)
            else:
                error_msg = "device is not back to service, "
                self.log.info(error_msg)
            self.my_error_msg += error_msg
        return test_result

    @test_tracker_info(uuid="95bf5006-4ff6-4e7e-a02d-156e6b43f129")
    def test_in_out_wifi_apm_on(self):
        '''
            1.1.4 In/Out Service - Idle + VoWiFi registered in Airplane on
            + Wi-Fi on in default mode

            Returns:
                True if pass; False if fail
            Raises:
                TestFailure if not success.
        '''
        test_result = True
        test_result = self._ID_1_1_4_in_out_vowifi(1, 60)
        if test_result:
            test_result = self._ID_1_1_4_in_out_vowifi(1, 180)
        asserts.assert_true(test_result, "Fail: %s." %(self.my_error_msg),
            extras={"failure_cause": self.my_error_msg})
        return test_result

    def _ID_1_1_4_in_out_vowifi(self, loop=1, idle_time=60):
        '''
            1.1.4 In/Out Service - Idle + VoWiFi registered in Airplane on
            + Wi-Fi on in default mode

            Args:
                loop: repeat this test cases for how many times
                idle_time: at no service area

            Returns:
                True if pass; False if fail
        '''
        error_msg = ""
        test_result = True
        for x in range(self.user_params.get("wfc_cycle", 1)):
            self.log.info("%s loop: %s/%s" %(self.current_test_name, x+1, loop))
            self.my_error_msg += "cylce%s: " %(x+1)
            self.log.info("Enable Wi-Fi calling in Airplane on")
            self.adjust_wifi_signal(IN_SERVICE_POWER_LEVEL)

            ad = self.android_devices[0]
            wfc_mode = ad.droid.imsGetWfcMode()
            if not self._enable_wifi_calling(wfc_mode):
                error_msg = "Fail to setup WFC mode"
                self.log.info(error_msg)
                self.my_error_msg += error_msg
                return False
            tasks = [(toggle_airplane_mode, (self.log, ad, True)) for ad
                in self.android_devices]
            if not multithread_func(self.log, tasks):
                error_msg += "fail turn on airplane mode"
                self.my_error_msg += error_msg
                test_result = False
                return False

            self.log.info("idle in service area")
            self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)
            time.sleep(10)
            self.log.info("Move to no service area for %s sec" %(idle_time))
            self.adjust_cellular_signal(NO_SERVICE_POWER_LEVEL)
            time.sleep(idle_time)

            self.log.info("Move back to service area and verify device status")
            self.adjust_cellular_signal(IN_SERVICE_POWER_LEVEL)
            self.log.info("Verify device status after in-out service")
            tasks = [(check_back_to_service_time, (ad,)) for ad in self.android_devices]
            test_result = multithread_func(self.log, tasks)
            if test_result:
                tasks = [(self.verify_device_status, (ad, VOICE_CALL))
                    for ad in self.android_devices]
                test_result = multithread_func(self.log, tasks)
                if not test_result:
                    error_msg = "verify_device_status fail, "
            else:
                error_msg = "device is not back to service, "
                self.log.info(error_msg)
        return test_result





