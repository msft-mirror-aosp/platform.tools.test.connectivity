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
    Test Script for CellBroadcast Module Test
"""

import xml.etree.ElementTree as ET
import time
import random
import os

from acts import signals
from acts.logger import epoch_to_log_line_timestamp
from acts.keys import Config
from acts.test_decorators import test_tracker_info
from acts.utils import load_config
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import CARRIER_TEST_CONF_XML_PATH
from acts_contrib.test_utils.tel.tel_defines import CLEAR_NOTIFICATION_BAR
from acts_contrib.test_utils.tel.tel_defines import DEFAULT_ALERT_TYPE
from acts_contrib.test_utils.tel.tel_defines import EXPAND_NOTIFICATION_BAR
from acts_contrib.test_utils.tel.tel_defines import COLLAPSE_NOTIFICATION_BAR
from acts_contrib.test_utils.tel.tel_defines import UAE
from acts_contrib.test_utils.tel.tel_defines import JAPAN_KDDI
from acts_contrib.test_utils.tel.tel_defines import NEWZEALAND
from acts_contrib.test_utils.tel.tel_defines import HONGKONG
from acts_contrib.test_utils.tel.tel_defines import CHILE
from acts_contrib.test_utils.tel.tel_defines import PERU
from acts_contrib.test_utils.tel.tel_defines import KOREA
from acts_contrib.test_utils.tel.tel_defines import TAIWAN
from acts_contrib.test_utils.tel.tel_defines import CANADA
from acts_contrib.test_utils.tel.tel_defines import AUSTRALIA
from acts_contrib.test_utils.tel.tel_defines import BRAZIL
from acts_contrib.test_utils.tel.tel_defines import COLUMBIA
from acts_contrib.test_utils.tel.tel_defines import ECUADOR_TELEFONICA
from acts_contrib.test_utils.tel.tel_defines import ECUADOR_CLARO
from acts_contrib.test_utils.tel.tel_defines import FRANCE
from acts_contrib.test_utils.tel.tel_defines import PUERTORICO
from acts_contrib.test_utils.tel.tel_defines import NETHERLANDS
from acts_contrib.test_utils.tel.tel_defines import ROMANIA
from acts_contrib.test_utils.tel.tel_defines import ESTONIA
from acts_contrib.test_utils.tel.tel_defines import LITHUANIA
from acts_contrib.test_utils.tel.tel_defines import LATVIA
from acts_contrib.test_utils.tel.tel_defines import GREECE
from acts_contrib.test_utils.tel.tel_defines import ITALY
from acts_contrib.test_utils.tel.tel_defines import SOUTHAFRICA
from acts_contrib.test_utils.tel.tel_defines import UK
from acts_contrib.test_utils.tel.tel_defines import US_VZW
from acts_contrib.test_utils.tel.tel_defines import US_ATT
from acts_contrib.test_utils.tel.tel_defines import US_TMO
from acts_contrib.test_utils.tel.tel_defines import ISRAEL
from acts_contrib.test_utils.tel.tel_defines import OMAN
from acts_contrib.test_utils.tel.tel_defines import JAPAN_SOFTBANK
from acts_contrib.test_utils.tel.tel_defines import SAUDIARABIA
from acts_contrib.test_utils.tel.tel_defines import MAIN_ACTIVITY
from acts_contrib.test_utils.tel.tel_defines import CBR_PACKAGE
from acts_contrib.test_utils.tel.tel_defines import SYSUI_PACKAGE
from acts_contrib.test_utils.tel.tel_defines import CBR_ACTIVITY
from acts_contrib.test_utils.tel.tel_defines import CBR_TEST_APK
from acts_contrib.test_utils.tel.tel_defines import MCC_MNC
from acts_contrib.test_utils.tel.tel_defines import IMSI
from acts_contrib.test_utils.tel.tel_defines import PLMN_ADB_PROPERTY
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_FOR_ALERTS_TO_POPULATE
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_FOR_UI
from acts_contrib.test_utils.tel.tel_defines import SCROLL_DOWN
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_FOR_ALERT_TO_RECEIVE
from acts_contrib.test_utils.tel.tel_defines import EXIT_ALERT_LIST
from acts_contrib.test_utils.tel.tel_defines import CMD_DND_OFF
from acts_contrib.test_utils.tel.tel_defines import DUMPSYS_VIBRATION
from acts_contrib.test_utils.tel.tel_defines import DEFAULT_SOUND_TIME
from acts_contrib.test_utils.tel.tel_defines import DEFAULT_VIBRATION_TIME
from acts_contrib.test_utils.tel.tel_defines import DEFAULT_OFFSET
from acts_contrib.test_utils.tel.tel_test_utils import reboot_device
from acts_contrib.test_utils.tel.tel_test_utils import log_screen_shot
from acts_contrib.test_utils.tel.tel_test_utils import get_screen_shot_log
from acts_contrib.test_utils.tel.tel_test_utils import get_device_epoch_time
from acts_contrib.test_utils.net import ui_utils as uutils


class CellBroadcastTest(TelephonyBaseTest):
    def setup_class(self):
        super().setup_class()
        req_param = ["region_plmn_list", "emergency_alert_settings", "emergency_alert_channels", "carrier_test_conf"]
        self.unpack_userparams(req_param_names=req_param)
        if hasattr(self, "region_plmn_list"):
            if isinstance(self.region_plmn_list, list):
                self.region_plmn_list = self.region_plmn_list[0]
            if not os.path.isfile(self.region_plmn_list):
                self.region_plmn_list = os.path.join(
                    self.user_params[Config.key_config_path.value],
                    self.region_plmn_list)
        if hasattr(self, "emergency_alert_settings"):
            if isinstance(self.emergency_alert_settings, list):
                self.emergency_alert_settings = self.emergency_alert_settings[0]
            if not os.path.isfile(self.emergency_alert_settings):
                self.emergency_alert_settings = os.path.join(
                    self.user_params[Config.key_config_path.value],
                    self.emergency_alert_settings)
        if hasattr(self, "emergency_alert_channels"):
            if isinstance(self.emergency_alert_channels, list):
                self.emergency_alert_channels = self.emergency_alert_channels[0]
            if not os.path.isfile(self.emergency_alert_channels):
                self.emergency_alert_channels = os.path.join(
                    self.user_params[Config.key_config_path.value],
                    self.emergency_alert_channels)
        if hasattr(self, "carrier_test_conf"):
            if isinstance(self.carrier_test_conf, list):
                self.carrier_test_conf = self.carrier_test_conf[0]
            if not os.path.isfile(self.carrier_test_conf):
                self.carrier_test_conf = os.path.join(
                    self.user_params[Config.key_config_path.value],
                    self.carrier_test_conf)
        self.verify_vibration = self.user_params.get("verify_vibration", True)
        self._disable_vibration_check_for_11()
        self.verify_sound = self.user_params.get("verify_sound", True)
        self.region_plmn_dict = load_config(self.region_plmn_list)
        self.emergency_alert_settings_dict = load_config(self.emergency_alert_settings)
        self.emergency_alert_channels_dict = load_config(self.emergency_alert_channels)
        self._verify_cbr_test_apk_install(self.android_devices[0])

    def setup_test(self):
        TelephonyBaseTest.setup_test(self)
        self.number_of_devices = 1

    def teardown_class(self):
        TelephonyBaseTest.teardown_class(self)


    def _verify_cbr_test_apk_install(self, ad):
        if not ad.is_apk_installed(CBR_TEST_APK):
            cbrtestapk = self.user_params.get("cbrtestapk")
            ad.adb.install("%s" % cbrtestapk)
        else:
            ad.log.debug("%s apk already installed", CBR_TEST_APK)


    def _verify_device_in_specific_region(self, ad, region=None):
        mccmnc = self.region_plmn_dict[region][MCC_MNC]
        current_plmn = ad.adb.getprop(PLMN_ADB_PROPERTY)
        if current_plmn == mccmnc:
            ad.log.info("device in %s region", region.upper())
            return True
        else:
            ad.log.info("device not in %s region", region.upper())
            return False

    def _disable_vibration_check_for_11(self):
        if self.android_devices[0].adb.getprop("ro.build.version.release") in ("11", "R"):
            self.verify_vibration = False

    def _get_toggle_value(self, ad, alert_text=None):
        node = uutils.wait_and_get_xml_node(ad, timeout=30, text=alert_text)
        return node.parentNode.nextSibling.firstChild.attributes['checked'].value


    def _open_wea_settings_page(self, ad):
        ad.adb.shell("am start -a %s -n %s/%s" % (MAIN_ACTIVITY, CBR_PACKAGE, CBR_ACTIVITY))


    def _close_wea_settings_page(self, ad):
        pid = ad.adb.shell("pidof %s" % CBR_PACKAGE, ignore_status=True)
        ad.adb.shell("kill -9 %s" % pid, ignore_status=True)


    def _set_device_to_specific_region(self, ad, region=None):
        """
        Args:
            ad: AndroidDevice
            country: name of country
        """
        # fetch country codes
        mccmnc = self.region_plmn_dict[region][MCC_MNC]
        imsi = self.region_plmn_dict[region][IMSI]
        ad.log.info("setting device to %s with mccmnc %s imsi %s",
                    region.upper(), mccmnc, imsi)

        # update carrier xml file
        tree = ET.parse(self.carrier_test_conf)
        root = tree.getroot()
        root[1].attrib['value'] = mccmnc
        root[2].attrib['value'] = imsi
        tree.write(self.carrier_test_conf)

        # push carrier xml to device
        ad.adb.push("%s %s" % (self.carrier_test_conf, CARRIER_TEST_CONF_XML_PATH))

        # reboot device
        reboot_device(ad)
        time.sleep(WAIT_TIME_FOR_ALERTS_TO_POPULATE)

        # verify adb property
        if not self._verify_device_in_specific_region(ad, region):
            raise signals.TestSkip("unable to set device to %s region" % region.upper())
        return True


    def _verify_wea_default_settings(self, ad, region=None):
        result = True
        for key, value in self.emergency_alert_settings_dict[region].items():
            alert_text = key
            alert_value = value["default_value"]
            self._open_wea_settings_page(ad)
            # scroll till bottom
            if not uutils.has_element(ad, text=alert_text):
                for _ in range(3):
                    ad.adb.shell(SCROLL_DOWN)
                if not uutils.has_element(ad, text=alert_text):
                    ad.log.error("UI - %s missing", alert_text)
                    result = False
                    continue
            current_value = self._get_toggle_value(ad, alert_text)
            if current_value == alert_value:
                ad.log.info("UI - %s, default: %s",
                            alert_text, alert_value)
            else:
                ad.log.error("UI - %s, default: %s, expected: %s",
                             alert_text, current_value, alert_value)
                result = False
        return result


    def _verify_wea_toggle_settings(self, ad, region=None):
        result = True
        for key, value in self.emergency_alert_settings_dict[region].items():
            alert_text = key
            alert_toggle = value["toggle_avail"]
            if alert_toggle == "true":
                self._open_wea_settings_page(ad)
                if not uutils.has_element(ad, text=alert_text):
                    for _ in range(3):
                        ad.adb.shell(SCROLL_DOWN)
                    if not uutils.has_element(ad, text=alert_text):
                        ad.log.error("UI - %s missing", alert_text)
                        result = False
                        continue
                before_toggle = self._get_toggle_value(ad, alert_text)
                uutils.wait_and_click(ad, text=alert_text)
                after_toggle = self._get_toggle_value(ad, alert_text)
                if before_toggle == after_toggle:
                    for _ in range(3):
                        ad.adb.shell(SCROLL_DOWN)
                    uutils.wait_and_click(ad, text=alert_text)
                    after_toggle = self._get_toggle_value(ad, alert_text)
                    if before_toggle == after_toggle:
                        ad.log.error("UI - fail to toggle %s", alert_text)
                        result = False
                else:
                    uutils.wait_and_click(ad, text=alert_text)
                    reset_toggle = self._get_toggle_value(ad, alert_text)
                    if reset_toggle != before_toggle:
                        ad.log.error("UI - fail to reset toggle %s", alert_text)
                        result = False
                    else:
                        ad.log.info("UI - toggle verified for %s", alert_text)
        return result


    def _convert_formatted_time_to_secs(self, formatted_time):
        try:
            time_list = formatted_time.split(":")
            return int(time_list[0]) * 3600 + int(time_list[1]) * 60 + int(time_list[2])
        except Exception as e:
            self.log.error(e)


    def _get_current_time_in_secs(self, ad):
        try:
            c_time = get_device_epoch_time(ad)
            c_time = epoch_to_log_line_timestamp(c_time).split()[1].split('.')[0]
            return self._convert_formatted_time_to_secs(c_time)
        except Exception as e:
            ad.log.error(e)


    def _verify_flashlight(self, ad):
        count = 0
        while(count < 10):
            status = ad.adb.shell("settings get secure flashlight_available")
            if status == "1":
                ad.log.info("LED lights OK")
                return True
        ad.log.error("LED lights not OK")
        return False



    def _verify_vibration(self, ad, begintime, expectedtime, offset):
        if not self.verify_vibration:
            return True
        out = ad.adb.shell(DUMPSYS_VIBRATION)
        if out:
            try:
                starttime = out.split()[2].split('.')[0]
                endtime = out.split()[5].split('.')[0]
                starttime = self._convert_formatted_time_to_secs(starttime)
                endtime = self._convert_formatted_time_to_secs(endtime)
                vibration_time = endtime - starttime
                if (starttime < begintime):
                    ad.log.error("vibration: actualtime:%s logtime:%s Not OK", begintime, starttime)
                    return False
                if not vibration_time in range(expectedtime - offset, expectedtime + offset + 1):
                    ad.log.error("vibration: %d secs Not OK", vibration_time)
                    return False
                ad.log.info("vibration: %d secs OK", vibration_time)
                return True
            except Exception as e:
                ad.log.error("vibration parsing is broken %s", e)
                return False
        return False


    def _verify_sound(self, ad, begintime, expectedtime, offset, calling_package=CBR_PACKAGE):
        if not self.verify_sound:
            return True
        cbr_pid = ad.adb.shell("pidof %s" % calling_package)
        DUMPSYS_START_AUDIO = "dumpsys audio | grep %s | grep requestAudioFocus | tail -1" % cbr_pid
        DUMPSYS_END_AUDIO = "dumpsys audio | grep %s | grep abandonAudioFocus | tail -1" % cbr_pid
        start_audio = ad.adb.shell(DUMPSYS_START_AUDIO)
        end_audio = ad.adb.shell(DUMPSYS_END_AUDIO)
        if start_audio and end_audio:
            try:
                starttime = start_audio.split()[1]
                endtime = end_audio.split()[1]
                starttime = self._convert_formatted_time_to_secs(starttime)
                endtime = self._convert_formatted_time_to_secs(endtime)
                sound_time = endtime - starttime
                if (starttime < begintime):
                    ad.log.error("sound: actualtime:%s logtime:%s Not OK", begintime, starttime)
                    return False
                if not sound_time in range(expectedtime - offset, expectedtime + offset + 1):
                    ad.log.error("sound: %d secs Not OK", sound_time)
                    return False
                ad.log.info("sound: %d secs OK", sound_time)
                return True
            except Exception as e:
                ad.log.error("sound parsing is broken %s", e)
                return False
        return False


    def _exit_alert_pop_up(self, ad):
        for text in EXIT_ALERT_LIST:
            try:
                uutils.wait_and_click(ad, text_contains=text, timeout=1)
            except Exception:
                continue


    def _verify_text_present_on_ui(self, ad, alert_text):
        if uutils.has_element(ad, text=alert_text, timeout=5):
            return True
        elif uutils.has_element(ad, text_contains=alert_text, timeout=5):
            return True
        else:
            return False


    def _log_and_screenshot_alert_fail(self, ad, state, region, channel):
        ad.log.error("Fail for alert: %s for %s: %s", state, region, channel)
        log_screen_shot(ad, "alert_%s_for_%s_%s" % (state, region, channel))


    def _show_statusbar_notifications(self, ad):
        ad.adb.shell(EXPAND_NOTIFICATION_BAR)


    def _hide_statusbar_notifications(self, ad):
        ad.adb.shell(COLLAPSE_NOTIFICATION_BAR)


    def _clear_statusbar_notifications(self, ad):
        ad.adb.shell(CLEAR_NOTIFICATION_BAR)


    def _popup_alert_in_statusbar_notifications(self, ad, alert_text):
        alert_in_notification = False
        # Open status bar notifications.
        self._show_statusbar_notifications(ad)
        # Wait for status bar notifications showing.
        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)
        if self._verify_text_present_on_ui(ad, alert_text):
            # Found alert in notifications, display it.
            uutils.wait_and_click(ad, text=alert_text)
            alert_in_notification = True
        else:
            # Close status bar notifications
            self._hide_statusbar_notifications(ad)
        return alert_in_notification


    def _verify_send_receive_wea_alerts(self, ad, region=None):
        result = True
        # Always clear notifications in the status bar before testing to find alert notification easily.
        self._clear_statusbar_notifications(ad)
        for key, value in self.emergency_alert_channels_dict[region].items():
            # Configs
            iteration_result = True
            channel = int(key)
            alert_text = value["title"]
            alert_expected = value["default_value"]
            wait_for_alert = value.get("alert_time", WAIT_TIME_FOR_ALERT_TO_RECEIVE)
            vibration_time = value.get("vibration_time", DEFAULT_VIBRATION_TIME)
            sound_time = value.get("sound_time", DEFAULT_SOUND_TIME)
            offset = value.get("offset", DEFAULT_OFFSET)
            alert_type = value.get("alert_type", DEFAULT_ALERT_TYPE)

            # Begin Iteration
            begintime = self._get_current_time_in_secs(ad)
            sequence_num = random.randrange(10000, 40000)
            ad.log.info("Iteration: %s for %s: %s", alert_text, region, channel)

            # Send Alert
            ad.droid.cbrSendTestAlert(sequence_num, channel)
            if region == NEWZEALAND:
                if not self._verify_flashlight(ad):
                    iteration_result = False
            time.sleep(wait_for_alert)

            # Receive Alert
            if not self._verify_text_present_on_ui(ad, alert_text):
                alert_in_notification = False
                # Check if alert message is expected to be in the notification drawer
                if alert_expected == "true" and alert_type == "notification":
                    # Verify expected notification in notification drawer and open the message
                    if self._popup_alert_in_statusbar_notifications(ad, alert_text):
                        ad.log.info("Found alert channel %d in status bar notifications, pop it up.", channel)
                        # Verify alert text in message.
                        alert_in_notification = self._verify_text_present_on_ui(ad, alert_text)
                        if alert_in_notification:
                            # Verify vibration and notification sound.
                            # We check sound generated by com.android.systemui package.
                            # For the reason of offset + 1, refer to b/199565843
                            # TODO: The notification sound is initiated by system
                            #  rather than CellBroadcastReceiver. In case there are
                            #  any non-emergency notifications coming during testing, we
                            #  should consider to validate notification id instead of
                            #  com.android.systemui package. b/199565843
                            if not (self._verify_vibration(ad, begintime, vibration_time, offset) and
                                    self._verify_sound(ad, begintime, sound_time, offset+1, SYSUI_PACKAGE)):
                                iteration_result = False
                if alert_expected == "true" and not alert_in_notification:
                    iteration_result = False
                    self._log_and_screenshot_alert_fail(ad, "missing", region, channel)
            else:
                if alert_expected == "true":
                    ad.log.info("Alert received OK")
                    self._exit_alert_pop_up(ad)
                    time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

                    # Vibration and Sound
                    if not self._verify_text_present_on_ui(ad, alert_text):
                        ad.log.info("Alert exited OK")
                        if not (self._verify_vibration(ad, begintime, vibration_time, offset) and
                                self._verify_sound(ad, begintime, sound_time, offset)):
                            iteration_result = False
                    else:
                        iteration_result = False
                        self._log_and_screenshot_alert_fail(ad, "present", region, channel)
                else:
                    iteration_result = False
                    self._log_and_screenshot_alert_fail(ad, "present", region, channel)
            if iteration_result:
                ad.log.info("Success alert: %s for %s: %s", alert_text, region, channel)
            else:
                ad.log.error("Failure alert: %s for %s: %s", alert_text, region, channel)
                result = iteration_result
            self._exit_alert_pop_up(ad)
        return result


    def _settings_test_flow(self, region):
        ad = self.android_devices[0]
        result = True
        self._set_device_to_specific_region(ad, region)
        time.sleep(WAIT_TIME_FOR_UI)
        if not self._verify_wea_default_settings(ad, region):
            result = False
        log_screen_shot(ad, "default_settings_%s" % region)
        self._close_wea_settings_page(ad)
        if not self._verify_wea_toggle_settings(ad, region):
            log_screen_shot(ad, "toggle_settings_%s" % region)
            result = False
        get_screen_shot_log(ad)
        self._close_wea_settings_page(ad)
        return result


    def _send_receive_test_flow(self, region):
        ad = self.android_devices[0]
        result = True
        self._set_device_to_specific_region(ad, region)
        time.sleep(WAIT_TIME_FOR_UI)
        ad.log.info("disable DND: %s", CMD_DND_OFF)
        ad.adb.shell(CMD_DND_OFF)
        if not self._verify_send_receive_wea_alerts(ad, region):
            result = False
        get_screen_shot_log(ad)
        return result


    """ Tests Begin """


    @test_tracker_info(uuid="a4df03a7-2e44-4f8a-8d62-18435d92fc75")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_uae(self):
        """ Verifies Wireless Emergency Alert settings for UAE

        configures the device to UAE
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(UAE)


    @test_tracker_info(uuid="ac4639ca-b77e-4200-b3f0-9079e2783f60")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_australia(self):
        """ Verifies Wireless Emergency Alert settings for Australia

        configures the device to Australia
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(AUSTRALIA)


    @test_tracker_info(uuid="d0255023-d9bb-45c5-bede-446d720e619a")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_france(self):
        """ Verifies Wireless Emergency Alert settings for France

        configures the device to France
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(FRANCE)


    @test_tracker_info(uuid="fd461335-21c0-470c-aca7-74c8ebb67711")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_japan_kddi(self):
        """ Verifies Wireless Emergency Alert settings for Japan (KDDI)

        configures the device to KDDI carrier on Japan
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(JAPAN_KDDI)


    @test_tracker_info(uuid="63806dbe3-3cce-4b03-b92c-18529f81b7c5")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_newzealand(self):
        """ Verifies Wireless Emergency Alert settings for NZ

        configures the device to NZ
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(NEWZEALAND)


    @test_tracker_info(uuid="426a295e-f64b-43f7-a0df-3959f07ff568")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_hongkong(self):
        """ Verifies Wireless Emergency Alert settings for HongKong

        configures the device to HongKong
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(HONGKONG)


    @test_tracker_info(uuid="d9e2dca2-4965-48d5-9d79-352c4ccf9e0f")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_chile(self):
        """ Verifies Wireless Emergency Alert settings for Chile

        configures the device to Chile
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(CHILE)


    @test_tracker_info(uuid="77cff297-fe3b-4b4c-b502-5324b4e91506")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_peru(self):
        """ Verifies Wireless Emergency Alert settings for Peru

        configures the device to Peru
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(PERU)


    @test_tracker_info(uuid="4c3c4e65-c624-4eba-9a81-263f4ee01e12")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_korea(self):
        """ Verifies Wireless Emergency Alert settings for Korea

        configures the device to Korea
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(KOREA)


    @test_tracker_info(uuid="fbaf258e-b596-4bfa-a20f-4b93fc4ccc4c")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_taiwan(self):
        """ Verifies Wireless Emergency Alert settings for Taiwan

        configures the device to Taiwan
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(TAIWAN)


    @test_tracker_info(uuid="3f8e4110-a7d3-4b3b-ac2b-36ea17cfc141")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_canada(self):
        """ Verifies Wireless Emergency Alert settings for Canada

        configures the device to Canada
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(CANADA)


    @test_tracker_info(uuid="fa0cd219-b0f2-4a38-8733-cd4212a954c5")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_brazil(self):
        """ Verifies Wireless Emergency Alert settings for Brazil

        configures the device to Brazil
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(BRAZIL)


    @test_tracker_info(uuid="581ecebe-9f68-4270-ab5d-182b1ee4e13b")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_columbia(self):
        """ Verifies Wireless Emergency Alert settings for Columbia

        configures the device to Columbia
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(COLUMBIA)


    @test_tracker_info(uuid="2ebfc05b-3512-4eff-9c09-5d8f49fe0b5e")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_ecuador_telefonica(self):
        """ Verifies Wireless Emergency Alert settings for Ecuador Telefonica

        configures the device to Ecuador Telefonica
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(ECUADOR_TELEFONICA)


    @test_tracker_info(uuid="694bf8f6-9e6e-46b4-98df-c7ab1a9a3ec8")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_ecuador_claro(self):
        """ Verifies Wireless Emergency Alert settings for Ecuador Claro

        configures the device to Ecuador Claro
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(ECUADOR_CLARO)


    @test_tracker_info(uuid="96628975-a23f-47f7-ab18-1aa7a7dc08b5")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_puertorico(self):
        """ Verifies Wireless Emergency Alert settings for Puertorico

        configures the device to Puertorico
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(PUERTORICO)


    @test_tracker_info(uuid="9f73f7ec-cb2a-45e5-8829-db14798dcdac")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_netherlands(self):
        """ Verifies Wireless Emergency Alert settings for Netherlands

        configures the device to Netherlands
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(NETHERLANDS)


    @test_tracker_info(uuid="b3caf3b4-3024-4431-9a7a-4982e20b178b")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_romania(self):
        """ Verifies Wireless Emergency Alert settings for Romania

        configures the device to Romania
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(ROMANIA)


    @test_tracker_info(uuid="081a5329-d23f-4df8-b472-d4f3ca5ee3c1")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_estonia(self):
        """ Verifies Wireless Emergency Alert settings for Estonia

        configures the device to Estonia
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(ESTONIA)


    @test_tracker_info(uuid="7e0d3b96-f11c-44d9-b3a3-9ce9e21bf37d")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_lithuania(self):
        """ Verifies Wireless Emergency Alert settings for Lithuania

        configures the device to Lithuania
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(LITHUANIA)


    @test_tracker_info(uuid="b40648a0-d04f-4c45-9051-76e64756ef00")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_latvia(self):
        """ Verifies Wireless Emergency Alert settings for Latvia

        configures the device to Latvia
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(LATVIA)


    @test_tracker_info(uuid="9488a6ef-2903-421d-adec-fd65df3aac60")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_greece(self):
        """ Verifies Wireless Emergency Alert settings for Greece

        configures the device to Greece
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(GREECE)


    @test_tracker_info(uuid="53cf276e-8617-45ce-b3f5-e8995b4be279")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_italy(self):
        """ Verifies Wireless Emergency Alert settings for Italy

        configures the device to Italy
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(ITALY)


    @test_tracker_info(uuid="a1a57aa8-c229-4f04-bc65-1f17688159a1")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_southafrica(self):
        """ Verifies Wireless Emergency Alert settings for SouthAfrica

        configures the device to SouthAfrica
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(SOUTHAFRICA)


    @test_tracker_info(uuid="a0ed231e-07e0-4dc8-a071-14ec7818e96f")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_uk(self):
        """ Verifies Wireless Emergency Alert settings for UK

        configures the device to UK
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(UK)


    @test_tracker_info(uuid="00c77647-0986-41f8-9202-cc0e2e51e278")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_israel(self):
        """ Verifies Wireless Emergency Alert settings for Israel

        configures the device to Israel
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(ISRAEL)


    @test_tracker_info(uuid="7f2ca9f5-31f6-4477-9383-5acd1ed2598f")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_oman(self):
        """ Verifies Wireless Emergency Alert settings for Oman

        configures the device to Oman
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(OMAN)


    @test_tracker_info(uuid="97525c27-3cba-4472-b00d-d5dabc5a2fe5")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_japan_softbank(self):
        """ Verifies Wireless Emergency Alert settings for Japan (Softbank)

        configures the device to Japan (Softbank)
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(JAPAN_SOFTBANK)


    @test_tracker_info(uuid="109494df-3ae2-4b77-ae52-fb0c22e654c8")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_saudiarabia(self):
        """ Verifies Wireless Emergency Alert settings for SaudiArabia

        configures the device to SaudiArabia
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(SAUDIARABIA)


    @test_tracker_info(uuid="a5f232c4-e0fa-4ce6-aa00-c838f0d86272")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_us_att(self):
        """ Verifies Wireless Emergency Alert settings for US ATT

        configures the device to US ATT
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(US_ATT)


    @test_tracker_info(uuid="a712c136-8ce9-4bc2-9dda-05ecdd11e8ad")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_us_tmo(self):
        """ Verifies Wireless Emergency Alert settings for US TMO

        configures the device to US TMO
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(US_TMO)


    @test_tracker_info(uuid="20403705-f627-42d7-9dc2-4e820273a622")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_alert_settings_us_vzw(self):
        """ Verifies Wireless Emergency Alert settings for US VZW

        configures the device to US VZW
        verifies alert names and its default values
        toggles the alert twice if available

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._settings_test_flow(US_VZW)


    @test_tracker_info(uuid="f3a99475-a23f-427c-a371-d2a46d357d75")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_australia(self):
        """ Verifies Wireless Emergency Alerts for AUSTRALIA

        configures the device to AUSTRALIA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(AUSTRALIA)


    @test_tracker_info(uuid="73c98624-2935-46ea-bf7c-43c431177ebd")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_brazil(self):
        """ Verifies Wireless Emergency Alerts for BRAZIL

        configures the device to BRAZIL
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(BRAZIL)


    @test_tracker_info(uuid="8c2e16f8-9b7f-4733-a65e-f087d2480e92")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_canada(self):
        """ Verifies Wireless Emergency Alerts for CANADA

        configures the device to CANADA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(CANADA)


    @test_tracker_info(uuid="feea4e42-99cc-4075-bd78-15b149cb2e4c")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_chile(self):
        """ Verifies Wireless Emergency Alerts for CHILE

        configures the device to CHILE
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(CHILE)


    @test_tracker_info(uuid="4af30b94-50ea-4e19-8866-31fd3573a059")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_columbia(self):
        """ Verifies Wireless Emergency Alerts for COLUMBIA

        configures the device to COLUMBIA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(COLUMBIA)


    @test_tracker_info(uuid="2378b651-2097-48e6-b409-885bde9f4586")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_ecuador_telefonica(self):
        """ Verifies Wireless Emergency Alerts for ECUADOR Telefonica

        configures the device to ECUADOR Telefonica
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(ECUADOR_TELEFONICA)


    @test_tracker_info(uuid="cd064259-6cb2-460b-8225-de613f6cf967")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_ecuador_claro(self):
        """ Verifies Wireless Emergency Alerts for ECUADOR Claro

        configures the device to ECUADOR Claro
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(ECUADOR_CLARO)


    @test_tracker_info(uuid="46d6c612-21df-476e-a41b-3baa621b52f0")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_estonia(self):
        """ Verifies Wireless Emergency Alerts for ESTONIA

        configures the device to ESTONIA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(ESTONIA)


    @test_tracker_info(uuid="6de32af0-9545-4143-b327-146e4d0af28c")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_france(self):
        """ Verifies Wireless Emergency Alerts for FRANCE

        configures the device to FRANCE
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(FRANCE)


    @test_tracker_info(uuid="9c5826db-0457-4c6f-9d06-6973b5f77e3f")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_greece(self):
        """ Verifies Wireless Emergency Alerts for GREECE

        configures the device to GREECE
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(GREECE)


    @test_tracker_info(uuid="57dd9a79-6ac2-41c7-b7eb-3afb01f35bd2")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_hongkong(self):
        """ Verifies Wireless Emergency Alerts for Japan HONGKONG

        configures the device to HONGKONG
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(HONGKONG)


    @test_tracker_info(uuid="8ffdfaf8-5925-4e66-be22-e1ac25165784")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_israel(self):
        """ Verifies Wireless Emergency Alerts for ISRAEL

        configures the device to ISRAEL
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(ISRAEL)


    @test_tracker_info(uuid="f38e289c-4c7d-48a7-9b21-f7d872e3eb98")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_italy(self):
        """ Verifies Wireless Emergency Alerts for ITALY

        configures the device to ITALY
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(ITALY)


    @test_tracker_info(uuid="d434dbf8-72e8-44a7-ab15-d418133088c6")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_japan_kddi(self):
        """ Verifies Wireless Emergency Alerts for JAPAN_KDDI

        configures the device to JAPAN_KDDI
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(JAPAN_KDDI)


    @test_tracker_info(uuid="c597995f-8937-4987-91db-7f83a0f5f4ec")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_japan_softbank(self):
        """ Verifies Wireless Emergency Alerts for JAPAN_SOFTBANK

        configures the device to JAPAN_SOFTBANK
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(JAPAN_SOFTBANK)


    @test_tracker_info(uuid="b159d6b2-b900-4329-9b77-c9ba9e83dddc")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_korea(self):
        """ Verifies Wireless Emergency Alerts for KOREA

        configures the device to KOREA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(KOREA)


    @test_tracker_info(uuid="9b59c594-179a-44d6-9dbf-68adc43aa820")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_latvia(self):
        """ Verifies Wireless Emergency Alerts for LATVIA

        configures the device to LATVIA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(LATVIA)


    @test_tracker_info(uuid="af7d916b-42f0-4420-8a1c-b39d3f184953")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_lithuania(self):
        """ Verifies Wireless Emergency Alerts for LITHUANIA

        configures the device to LITHUANIA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(LITHUANIA)


    @test_tracker_info(uuid="a9c7cdbe-5a9e-49fb-af60-953e8c1547c0")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_netherlands(self):
        """ Verifies Wireless Emergency Alerts for NETHERLANDS

        configures the device to NETHERLANDS
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(NETHERLANDS)


    @test_tracker_info(uuid="23db0b77-1a1c-494c-bcc6-1355fb037a6f")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_newzealand(self):
        """ Verifies Wireless Emergency Alerts for NEWZEALAND

        configures the device to NEWZEALAND
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(NEWZEALAND)


    @test_tracker_info(uuid="a4216cbb-4ed7-4e72-98e7-2ebebe904956")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_oman(self):
        """ Verifies Wireless Emergency Alerts for OMAN

        configures the device to OMAN
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(OMAN)


    @test_tracker_info(uuid="35f0f156-1555-4bf1-98b1-b5848d8e2d39")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_peru(self):
        """ Verifies Wireless Emergency Alerts for PERU

        configures the device to PERU
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(PERU)


    @test_tracker_info(uuid="fefb293a-5c22-45b2-9323-ccb355245c9a")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_puertorico(self):
        """ Verifies Wireless Emergency Alerts for PUERTORICO

        configures the device to PUERTORICO
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(PUERTORICO)


    @test_tracker_info(uuid="7df5a2fd-fc20-46a1-8a57-c7690daf97ff")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_romania(self):
        """ Verifies Wireless Emergency Alerts for ROMANIA

        configures the device to ROMANIA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(ROMANIA)


    @test_tracker_info(uuid="cb1a2e92-eddb-4d8a-8b8d-96a0b8c558dd")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_saudiarabia(self):
        """ Verifies Wireless Emergency Alerts for SAUDIARABIA

        configures the device to SAUDIARABIA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(SAUDIARABIA)


    @test_tracker_info(uuid="0bf0196a-e456-4fa8-a735-b8d6d014ce7f")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_southafrica(self):
        """ Verifies Wireless Emergency Alerts for SOUTHAFRICA

        configures the device to SOUTHAFRICA
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(SOUTHAFRICA)


    @test_tracker_info(uuid="513c7d24-4957-49a4-98a2-f8a9444124ae")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_taiwan(self):
        """ Verifies Wireless Emergency Alerts for TAIWAN

        configures the device to TAIWAN
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(TAIWAN)


    @test_tracker_info(uuid="43d54588-95e2-4e8a-b322-f6c99b9d3fbb")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_uae(self):
        """ Verifies Wireless Emergency Alerts for UAE

        configures the device to UAE
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(UAE)


    @test_tracker_info(uuid="b44425c3-0d5b-498a-8322-86cc03eefd7d")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_uk(self):
        """ Verifies Wireless Emergency Alerts for UK

        configures the device to UK
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(UK)


    @test_tracker_info(uuid="b3e73b61-6232-44f0-9507-9954387ab25b")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_us_att(self):
        """ Verifies Wireless Emergency Alerts for US ATT

        configures the device to US ATT
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(US_ATT)


    @test_tracker_info(uuid="f993d21d-c240-4196-8015-ea8f5967fdb3")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_us_tmo(self):
        """ Verifies Wireless Emergency Alerts for US TMO

        configures the device to US TMO
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(US_TMO)


    @test_tracker_info(uuid="173293f2-4876-4891-ad2c-2b0d5269b2e0")
    @TelephonyBaseTest.tel_test_wrap
    def test_send_receive_alerts_us_vzw(self):
        """ Verifies Wireless Emergency Alerts for US Verizon

        configures the device to US Verizon
        send alerts across all channels,
        verify if alert is received correctly
        verify sound and vibration timing
        click on OK/exit alert and verify text

        Returns:
            True if pass; False if fail and collects screenshot
        """
        return self._send_receive_test_flow(US_VZW)
