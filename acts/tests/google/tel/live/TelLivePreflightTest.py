#!/usr/bin/python3.4
#
#   Copyright 2014 - Google
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
    Test Script for Telephony Pre Flight check.
"""

import time
from queue import Empty
from acts.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts.test_utils.tel.tel_defines import AOSP_PREFIX
from acts.test_utils.tel.tel_defines import CAPABILITY_PHONE
from acts.test_utils.tel.tel_defines import CAPABILITY_VOLTE
from acts.test_utils.tel.tel_defines import CAPABILITY_VT
from acts.test_utils.tel.tel_defines import CAPABILITY_WFC
from acts.test_utils.tel.tel_defines import CAPABILITY_MSIM
from acts.test_utils.tel.tel_defines import CAPABILITY_OMADM
from acts.test_utils.tel.tel_defines import PRECISE_CALL_STATE_LISTEN_LEVEL_BACKGROUND
from acts.test_utils.tel.tel_defines import PRECISE_CALL_STATE_LISTEN_LEVEL_FOREGROUND
from acts.test_utils.tel.tel_defines import PRECISE_CALL_STATE_LISTEN_LEVEL_RINGING
from acts.test_utils.tel.tel_defines import WAIT_TIME_AFTER_REBOOT
from acts.test_utils.tel.tel_defines import WAIT_TIME_NW_SELECTION
from acts.test_utils.tel.tel_lookup_tables import device_capabilities
from acts.test_utils.tel.tel_lookup_tables import operator_capabilities
from acts.test_utils.tel.tel_test_utils import ensure_phones_default_state
from acts.test_utils.tel.tel_test_utils import get_operator_name
from acts.test_utils.tel.tel_test_utils import get_sub_ids_for_sim_slots
from acts.test_utils.tel.tel_test_utils import setup_droid_properties
from acts.test_utils.tel.tel_test_utils import set_phone_screen_on
from acts.test_utils.tel.tel_test_utils import set_phone_silent_mode
from acts.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts.test_utils.tel.tel_test_utils import wait_for_voice_attach_for_subscription
from acts.test_utils.tel.tel_voice_utils import phone_setup_volte
from acts.utils import load_config

class TelLivePreflightTest(TelephonyBaseTest):

    def __init__(self, controllers):
        TelephonyBaseTest.__init__(self, controllers)
        self.tests = (
                      "test_pre_flight_check",
                      )

        self.simconf = load_config(self.user_params["sim_conf_file"])

    """ Tests Begin """
    @TelephonyBaseTest.tel_test_wrap
    def test_pre_flight_check(self):
        def droid_has_phone(log, ad):
            #check for sim and service
            subInfo = ad.droid.subscriptionGetAllSubInfoList()
            if not subInfo or len(subInfo) < 1:
                return False
            toggle_airplane_mode(log, ad, False)
            sub_id = ad.droid.subscriptionGetDefaultVoiceSubId()
            if not wait_for_voice_attach_for_subscription(log, ad, sub_id,
                                                  WAIT_TIME_NW_SELECTION):
                log.error("{} didn't find a cell network".format(ad.serial))
                return False
            return True
        def droid_has_provisioning(log, ad):
            if not ad.droid.imsIsVolteProvisionedOnDevice():
                log.error("{}: VoLTE Not Provisioned on the Platform".
                    format(ad.serial))
                return False
            else:
                log.info("{} VoLTE Provisioned".format(ad.serial))
            return True

        def droid_has_volte(log, ad):
            if not ad.droid.imsIsEnhanced4gLteModeSettingEnabledByPlatform():
                log.error("{}: VoLTE Not Enabled on the Platform".
                    format(ad.serial))
                return False
            else:
                log.info("{} VoLTE Enabled by platform".format(ad.serial))
            return True

        def droid_has_wifi_calling(log, ad):
            if not ad.droid.imsIsWfcEnabledByPlatform():
                log.error("{}: WFC Not Enabled on the Platform".
                    format(ad.serial))
                return False
            else:
                log.info("{} WFC Enabled by platform".format(ad.serial))
            return True

        def droid_has_vt(log, ad):
            if not ad.droid.imsIsVtEnabledByPlatform():
                log.error("{}: VT Not Enabled on the Platform".
                    format(ad.serial))
                return False
            else:
                log.info("{} VT Enabled by platform".format(ad.serial))
            return True

        try:
            for ad in self.android_devices:
                model = ad.model
                # Remove aosp prefix
                if model.startswith(AOSP_PREFIX):
                    model = model[len(AOSP_PREFIX):]

                # Special capability phone, needed to get SIM Operator
                if not CAPABILITY_PHONE in device_capabilities[model]:
                    self.log.info("Skipping {}:{}: not a phone".
                                  format(ad.serial, model))
                    return True

                operator = get_operator_name(self.log, ad)
                self.log.info("Pre-flight check for <{}>, <{}:{}>, build<{}>".
                              format(operator, model, ad.serial,
                                     ad.droid.getBuildID()))

                if("force_provisioning" in self.user_params and
                   CAPABILITY_OMADM in device_capabilities[model] and
                   CAPABILITY_OMADM in operator_capabilities[operator] and
                   not droid_has_provisioning(self.log, ad)):
                    self.log.info("{} not IMS Provisioned!!".format(ad.serial))
                    self.log.info("{} Forcing IMS Provisioning!".format(ad.serial))
                    ad.droid.imsSetVolteProvisioning(True)
                    self.log.info("{} reboot!".format(ad.serial))
                    ad.reboot()
                    self.log.info("{} wait {}s for radio up.".
                        format(ad.serial, WAIT_TIME_AFTER_REBOOT))
                    # This sleep WAIT_TIME_AFTER_REBOOT seconds is waiting for
                    # radio to initiate after phone reboot.
                    time.sleep(WAIT_TIME_AFTER_REBOOT)

                active_capabilities = [CAPABILITY_PHONE, CAPABILITY_OMADM,
                                       CAPABILITY_VOLTE, CAPABILITY_WFC]
                for capability in active_capabilities:
                    if(capability in device_capabilities[model] and
                       capability in operator_capabilities[operator]):
                        if not {
                            # TODO: b/26337715 make the check table global
                            CAPABILITY_PHONE: droid_has_phone,
                            CAPABILITY_OMADM: droid_has_provisioning,
                            CAPABILITY_VOLTE: droid_has_volte,
                            CAPABILITY_WFC: droid_has_wifi_calling,
                            CAPABILITY_VT: droid_has_vt
                        }[capability](self.log, ad):
                            self.abort_all("Pre-flight check FAILED for <{}>, <{}:{}>".
                                           format(operator, model, ad.serial))
        except Exception as e:
            self.abort_all("Pre-flight check exception: {}".format(e))
        return True
""" Tests End """
