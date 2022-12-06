#!/usr/bin/env python3
#
#   Copyright 20022 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
import time

from acts_contrib.test_utils.power.cellular.ims_api_connector_utils import ImsApiConnector
import acts_contrib.test_utils.power.cellular.cellular_power_base_test as PWCEL
from acts_contrib.test_utils.tel.tel_test_utils import set_phone_silent_mode
from acts_contrib.test_utils.tel.tel_voice_utils import hangup_call

class PowerTelImsPresetTest(PWCEL.PowerCellularLabBaseTest):
    ADB_CMD_ENABLE_IMS = ('am broadcast '
        '-a com.google.android.carrier.action.LOCAL_OVERRIDE '
        '-n com.google.android.carrier/.ConfigOverridingReceiver '
        '--ez carrier_volte_available_bool true '
        '--ez carrier_wfc_ims_available_bool true '
        '--ez carrier_vt_available_bool true '
        '--ez carrier_supports_ss_over_ut_bool true '
        '--ez vonr_setting_visibility_bool true '
        '--ez vonr_enabled_bool true')

    ADB_CMD_DISABLE_IMS = ('am broadcast '
        '-a com.google.android.carrier.action.LOCAL_OVERRIDE '
        '-n com.google.android.carrier/.ConfigOverridingReceiver '
        '--ez carrier_volte_available_bool false '
        '--ez carrier_wfc_ims_available_bool false '
        '--ez carrier_vt_available_bool false '
        '--ez carrier_supports_ss_over_ut_bool false '
        '--ez vonr_setting_visibility_bool false '
        '--ez vonr_enabled_bool false')

    # set NV command
    # !NRCAPA.Gen.VoiceOverNr, 0, 01
    ADB_SET_GOOG_NV = 'echo at+googsetnv="{nv_name}",{index},"{value}" > /dev/umts_router'

    # Key IMS simulator default value
    IMS_CLIENT_DEFAULT_IP = '127.0.0.1'
    IMS_CLIENT_DEFAULT_PORT = 8250
    IMS_CLIENT_DEFAULT_API_TOKEN = 'myclient'

    # IMS available app
    IMS_CLIENT = 'client'
    IMS_SERVER = 'server'

    def setup_class(self):
        """ Executed only once when initializing the class. """
        super().setup_class()

        # switch to HCCU correct settings.
        self.cellular_simulator.switch_HCCU_settings(is_fr2=False)

        self.log.info('Disable mobile data.')
        self.dut.adb.shell('svc data disable')

        # Enable IMS on UE
        self.log.info('Enable VoLTE using adb command.')
        self.dut.adb.shell(self.ADB_CMD_ENABLE_IMS)

        # reboot device for settings to update
        self.log.info('Reboot for VoLTE settings to update.')
        self.dut.reboot()

        # Set voice call volume to minimum
        set_phone_silent_mode(self.log, self.dut)

        # initialize ims simulator connector wrapper
        self.unpack_userparams(api_connector_ip=None,
                               api_connector_port=None,
                               api_token=self.IMS_CLIENT_DEFAULT_API_TOKEN,
                               ims_client_ip=self.IMS_CLIENT_DEFAULT_IP,
                               ims_client_port=self.IMS_CLIENT_DEFAULT_PORT)
        for param in ('api_connector_ip', 'api_connector_port'):
            if getattr(self, param) is None:
                raise RuntimeError('The uxm cellular simulator '
                                   'requires %s to be set in the '
                                   'config file.' % param)
        self.ims_client = ImsApiConnector(
            self.api_connector_ip,
            self.api_connector_port,
            self.IMS_CLIENT,
            self.api_token,
            self.ims_client_ip,
            self.ims_client_port,
            self.log
        )

    def setup_test(self):
        # Enable NR if it is VoNR test case
        self.log.info(f'test name: {self.test_name}')
        if 'NR' in self.test_name:
            self.log.info('Enable VoNR for UE.')
            self.enable_ims_nr()
        super().setup_test()

    def set_nv(self, nv_name, index, value):
        self.log.info(f'Set NV: [{nv_name}] at index [{index}] to [{value}].')
        cmd = self.ADB_SET_GOOG_NV.format(
            nv_name = nv_name,
            index = index,
            value = value
        )
        self.cellular_dut.ad.adb.shell(cmd)
        time.sleep(2)

    def enable_ims_nr(self):
        # TODO: set value for registries (hex byte)
        # set PSS.AIMS.Enable.NRSACONTROL
        self.set_nv(
            nv_name = '!NRCAPA.Gen.VoiceOverNr',
            index = '0',
            value = '01'
        )
        # set PSS.AIMS.Enable.NRSACONTROL
        self.set_nv(
            nv_name = 'PSS.AIMS.Enable.NRSACONTROL',
            index = '0',
            value = '00'
        )
        # set DS.PSS.AIMS.Enable.NRSACONTROL
        self.set_nv(
            nv_name = 'DS.PSS.AIMS.Enable.NRSACONTROL',
            index = '0',
            value = '00'
        )
        if self.cellular_dut.ad.model == 'oriole':
            # For P21, NR.CONFIG.MODE/DS.NR.CONFIG.MODE to 11
            self.set_nv(
                nv_name = 'NR.CONFIG.MODE',
                index = '0',
                value = '11'
            )
            # set DS.NR.CONFIG.MODE
            self.set_nv(
                nv_name = 'DS.NR.CONFIG.MODE',
                index = '0',
                value = '11'
            )
        else:
            # For P22, NASU.NR.CONFIG.MODE to 11
            self.set_nv(
                nv_name = 'NASU.NR.CONFIG.MODE',
                index = '0',
                value = '11'
            )

        self.dut.reboot()

        #TODO(hmtuan): confirm all registries are expected

    def power_ims_call_test(self):
        """ Measures power during a VoLTE call.

        Measurement step in this test. Starts the voice call and
        initiates power measurement. Pass or fail is decided with a
        threshold value. """
        # create dedicated bearer
        self.log.info('create dedicated bearer.')
        if 'LTE' in self.test_name:
            self.cellular_simulator.create_dedicated_bearer()

        time.sleep(5)

        # Initiate the voice call
        self.log.info('Callbox initiates call to UE.')
        self.ims_client.initiate_call('001010123456789')

        time.sleep(5)

        # pick up call
        self.log.info('UE pick up call.')
        self.dut.adb.shell('input keyevent KEYCODE_CALL')

        # Mute the call
        self.dut.droid.telecomCallMute()

        # Turn of screen
        self.dut.droid.goToSleepNow()

        # Measure power
        self.collect_power_data()

        # End the call
        hangup_call(self.log, self.dut)

        # Check if power measurement is within the required values
        self.pass_fail_check()

    def teardown_test(self):
        super().teardown_test()
        #self.cellular_simulator.deregister_ue_ims()
        self.ims_client.remove_ims_app_link()
        self.cellular_dut.toggle_airplane_mode(True)
        self.cellular_simulator.detach()

    def teardown_class(self):
        super().teardown_class()
        self.log.info('Disable IMS.')
        self.dut.adb.shell(self.ADB_CMD_DISABLE_IMS)


class PowerTelIms_Preset_Test(PowerTelImsPresetTest):
    def teardown_test(self):
        super().teardown_test()
        self.log.info('Enable mobile data.')
        self.dut.adb.shell('svc data enable')
        self.cellular_simulator.detach()
        self.cellular_dut.toggle_airplane_mode(True)
        self.sponge_upload()

    def test_preset_LTE_voice(self):
        self.power_ims_call_test()

    def test_preset_NR_voice(self):
        self.power_ims_call_test()
