import os
from typing import Optional, List
import time

from acts import asserts
from acts import signals
from acts.controllers.cellular_lib import AndroidCellularDut
import acts_contrib.test_utils.power.cellular.cellular_power_base_test as PWCEL

# TODO: b/261639867
class AtUtil():
    """Util class for sending at command.

    Attributes:
        dut: AndroidDevice controller object.
    """
    ADB_CMD_DISABLE_TXAS = 'am instrument -w -e request at+googtxas=2 -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
    ADB_CMD_GET_TXAS = 'am instrument -w -e request at+googtxas? -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
    ADB_MODEM_STATUS = 'cat /sys/bus/platform/devices/cpif/modem_state'

    def __init__(self, dut, log) -> None:
        self.dut = dut
        self.log = log

    # TODO: to be remove when b/261639867 complete,
    # and we are using parent method.
    def send(self, cmd: str, retries: int=5) -> Optional[str]:
        for _ in range(30):
            modem_status = self.dut.adb.shell(self.ADB_MODEM_STATUS)
            self.log.debug(f'Modem status: {modem_status}')
            if modem_status == 'ONLINE':
                break
            time.sleep(1)

        wait_for_device_ready_time = 2
        for i in range(retries):
            res = self.dut.adb.shell(cmd)
            self.log.info(f'cmd sent: {cmd}')
            self.log.debug(f'response: {res}')
            if 'SUCCESS' in res and 'OK' in res:
                return res
            else:
                self.log.warning('Fail to execute cmd, retry to send again.')
                time.sleep(wait_for_device_ready_time)
        self.log.error(f'Fail to execute cmd: {cmd}')
        return res

    def lock_band(self):
        """Lock lte and nr bands.

        LTE bands to be locked include B1, B4.
        NR bands to belocked include n71, n78, n260.
        """
        adb_enable_band_lock_lte = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Band.Select\ Enb\/\ Dis\",00,\"01\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_bitmap_0 = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\",0,\"09,00,00,00,00,00,00,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_bitmap_1 = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\",1,\"00,00,00,00,00,00,00,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_bitmap_2 = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\",2,\"00,00,00,00,00,00,00,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_bitmap_3 = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\",3,\"00,00,00,00,00,00,00,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        # enable lte
        self.send(adb_enable_band_lock_lte)
        time.sleep(2)

        # lock to B1 and B4
        self.send(adb_set_band_lock_bitmap_0)
        time.sleep(2)
        self.send(adb_set_band_lock_bitmap_1)
        time.sleep(2)
        self.send(adb_set_band_lock_bitmap_2)
        time.sleep(2)
        self.send(adb_set_band_lock_bitmap_3)
        time.sleep(2)

        adb_enable_band_lock_nr = r'am instrument -w -e request at+GOOGSETNV=\"!NRRRC.SIM_BASED_BAND_LIST_SUPPORT\",00,\"01\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        self.send(adb_enable_band_lock_nr)
        time.sleep(2)
        adb_add_band_list_n71 = r'am instrument -w -e request at+GOOGSETNV=\"!NRRRC.SIM_OPERATOR_BAND_LIST\",00,\"47,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        self.send(adb_add_band_list_n71)
        time.sleep(2)
        adb_add_band_list_n78 = r'am instrument -w -e request at+GOOGSETNV=\"!NRRRC.SIM_OPERATOR_BAND_LIST\",01,\"4E,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        self.send(adb_add_band_list_n78)
        time.sleep(2)
        adb_add_band_list_n260 = r'am instrument -w -e request at+GOOGSETNV=\"!NRRRC.SIM_OPERATOR_BAND_LIST\",02,\"04,01\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        self.send(adb_add_band_list_n260)
        time.sleep(2)

    def disable_lock_band_lte(self):
        adb_disable_band_lock_lte = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Band.Select\ Enb\/\ Dis\",0,\"01\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'

        # disable band lock lte
        self.send(adb_disable_band_lock_lte)
        time.sleep(2)

    def disable_txas(self):
        res = self.send(self.ADB_CMD_GET_TXAS)
        if '+GOOGGETTXAS:2' in res:
            self.log.info('TXAS is in default.')
            return res
        cmd = self.ADB_CMD_DISABLE_TXAS
        response = self.send(cmd)
        return 'OK' in response

    def get_band_lock_info(self):
        cmd = r'am instrument -w -e request at+GOOGGETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        res = self.send(cmd)
        cmd = r'am instrument -w -e request at+GOOGGETNV=\"!SAEL3.Manual.Band.Select\ Enb\/\ Dis\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        res = self.send(cmd)
        return res

class PowerCellularPresetLabBaseTest(PWCEL.PowerCellularLabBaseTest):
    # Key for ODPM report
    ODPM_ENERGY_TABLE_NAME = 'PowerStats HAL 2.0 energy meter'
    ODPM_MODEM_CHANNEL_NAME = '[VSYS_PWR_MODEM]:Modem'

    # Key for custom_property in Sponge
    CUSTOM_PROP_KEY_BUILD_ID = 'build_id'
    CUSTOM_PROP_KEY_INCR_BUILD_ID = 'incremental_build_id'
    CUSTOM_PROP_KEY_BUILD_TYPE = 'build_type'
    CUSTOM_PROP_KEY_SYSTEM_POWER = 'system_power'
    CUSTOM_PROP_KEY_MODEM_BASEBAND = 'baseband'
    CUSTOM_PROP_KEY_MODEM_ODPM_POWER= 'modem_odpm_power'
    CUSTOM_PROP_KEY_DEVICE_NAME = 'device'
    CUSTOM_PROP_KEY_DEVICE_BUILD_PHASE = 'device_build_phase'
    CUSTOM_PROP_KEY_MODEM_KIBBLE_POWER = 'modem_kibble_power'
    CUSTOM_PROP_KEY_TEST_NAME = 'test_name'
    CUSTOM_PROP_KEY_MODEM_KIBBLE_WO_PCIE_POWER = 'modem_kibble_power_wo_pcie'
    CUSTOM_PROP_KEY_MODEM_KIBBLE_PCIE_POWER = 'modem_kibble_pcie_power'
    CUSTOM_PROP_KEY_RFFE_POWER = 'rffe_power'
    CUSTOM_PROP_KEY_MMWAVE_POWER = 'mmwave_power'
    # kibble report
    KIBBLE_SYSTEM_RECORD_NAME = '- name: default_device.C10_EVT_1_1.Monsoon:mA'
    MODEM_PCIE_RAIL_NAME_LIST = [
        'PP1800_L2C_PCIEG3',
        'PP1200_L9C_PCIE',
        'PP0850_L8C_PCIE'
    ]

    MODEM_RFFE_RAIL_NAME_LIST = [
        'PP1200_L31C_RFFE',
        'VSYS_PWR_RFFE',
        'PP2800_L33C_RFFE'
    ]

    MODEM_POWER_RAIL_NAME = 'VSYS_PWR_MODEM'

    MODEM_MMWAVE_RAIL_NAME = 'VSYS_PWR_MMWAVE'

    MONSOON_RAIL_NAME = 'Monsoon'

    # params key
    MONSOON_VOLTAGE_KEY = 'mon_voltage'

    MDSTEST_APP_APK_NAME = 'mdstest.apk'
    ADB_CMD_INSTALL = 'install {apk_path}'
    ADB_CMD_DISABLE_TXAS = 'am instrument -w -e request at+googtxas=2 -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
    ADB_CMD_SET_NV = ('am instrument -w '
                      '-e request at+googsetnv=\"{nv_name}\",{nv_index},\"{nv_value}\" '
                      '-e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"')
    ADB_CMD_ENABLE_ALWAYS_ON_LOGGING = (
        'am broadcast -n com.android.pixellogger/.receiver.AlwaysOnLoggingReceiver '
        '-a com.android.pixellogger.service.logging.LoggingService.ACTION_CONFIGURE_ALWAYS_ON_LOGGING '
        '-e intent_key_enable "true" '
        '-e intent_key_config "Lassen\ default" '
        '--ei intent_key_max_log_size_mb 100 '
        '--ei intent_key_max_number_of_files 20'
    )
    ADB_CMD_DISABLE_ALWAYS_ON_LOGGING = (
        'am start-foreground-service -a '
        'com.android.pixellogger.service.logging.LoggingService.ACTION_STOP_LOGGING')

    ADB_CMD_TOGGLE_MODEM_LOG = 'setprop persist.vendor.sys.modem.logging.enable {state}'

    def __init__(self, controllers):
        super().__init__(controllers)
        self.retryable_exceptions = signals.TestFailure
        self.power_rails = {}
        self.pcie_power = 0
        self.rffe_power = 0
        self.mmwave_power = 0
        self.modem_power = 0
        self.monsoon_power = 0
        self.kibble_error_range = 2
        self.system_power = 0
        self.odpm_power = 0

    def setup_class(self):
        super().setup_class()

        # preset callbox
        is_fr2 = 'Fr2' in self.TAG
        self.cellular_simulator.switch_HCCU_settings(is_fr2=is_fr2)

        self.at_util = AtUtil(self.cellular_dut.ad, self.log)

        # preset UE.
        self.log.info(f'Bug report mode: {self.bug_report}')
        if self.bug_report:
            self.toggle_modem_log(True)
        else:
            self.toggle_modem_log(False)
        self.log.info('Installing mdstest app.')
        self.install_apk()

        # UE preset
        self.log.info('Disable antenna switch.')
        self.at_util.disable_txas()
        time.sleep(10)

        self.at_util.lock_band()

        # get sim type
        self.unpack_userparams(has_3gpp_sim=True)

    def collect_power_data_and_validate(self):
        super().collect_power_data()
        # power measurement results
        odpm_power_results = self.get_odpm_values()
        self.odpm_power = odpm_power_results.get(self.ODPM_MODEM_CHANNEL_NAME, 0)
        if hasattr(self, 'bitses'):
            self.parse_power_rails_csv()

        self.threshold_check()

    def setup_test(self):
        try:
            super().setup_test()
        except BrokenPipeError:
            self.log.info('TA crashed test need retry.')
            self.need_retry = True
            self.cellular_simulator.recovery_ta()
            self.cellular_simulator.socket_connect()
            raise signals.TestFailure('TA crashed mid test, retry needed.')
        # except:
        #     # self.log.info('Waiting for device to on.')
        #     # self.dut.adb.wait_for_device()
        #     # self.cellular_dut = AndroidCellularDut.AndroidCellularDut(
        #     # self.android_devices[0], self.log)
        #     # self.dut.root_adb()
        #     # # Restart SL4A
        #     # self.dut.start_services()
        #     # self.need_retry = True
        #     raise signals.TestError('Device reboot mid test, retry needed.')

    def toggle_modem_log(self, new_state: bool, timeout: int=30):
        new_state = str(new_state).lower()
        current_state = self.cellular_dut.ad.adb.shell('getprop vendor.sys.modem.logging.status')
        cmd = self.ADB_CMD_TOGGLE_MODEM_LOG.format(state=new_state)
        if new_state != current_state:
            self.cellular_dut.ad.adb.shell(cmd)
            for _ in range(timeout):
                self.log.debug(f'Wait for modem logging status to be {new_state}.')
                time.sleep(1)
                current_state = self.cellular_dut.ad.adb.shell('getprop vendor.sys.modem.logging.status')
                if new_state == current_state:
                    self.log.info(f'Always-on modem logging status is {new_state}.')
                    return
            raise RuntimeError(f'Fail to set modem logging to {new_state}.')

    def install_apk(self):
        sleep_time = 3
        for file in self.custom_files:
            if self.MDSTEST_APP_APK_NAME in file:
                if not self.cellular_dut.ad.is_apk_installed("com.google.mdstest"):
                    self.cellular_dut.ad.adb.install("-r -g %s" % file, timeout=300, ignore_status=True)
        time.sleep(sleep_time)
        if self.cellular_dut.ad.is_apk_installed("com.google.mdstest"):
            self.log.info('mdstest installed.')
        else:
            self.log.warning('fail to install mdstest.')

    def set_nv(self, nv_name, index, value):
        cmd = self.ADB_CMD_SET_NV.format(
            nv_name=nv_name,
            nv_index=index,
            nv_value=value
        )
        response = str(self.cellular_dut.ad.adb.shell(cmd))
        self.log.info(response)

    def enable_ims_nr(self):
        # set !NRCAPA.Gen.VoiceOverNr
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
            # For P21, NR.CONFIG.MODE/DS.NR.CONFIG.MODE
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

    def get_odpm_values(self):
        """Get power measure from ODPM.

        Parsing energy table in ODPM file
        and convert to.
        Returns:
            odpm_power_results: a dictionary
                has key as channel name,
                and value as power measurement of that channel.
        """
        self.log.info('Start calculating power by channel from ODPM report.')
        odpm_power_results = {}

        # device before P21 don't have ODPM reading
        if not self.odpm_folder:
            return odpm_power_results

        # getting ODPM modem power value
        odpm_file_name = '{}.{}.dumpsys_odpm_{}.txt'.format(
            self.__class__.__name__,
            self.current_test_name,
            'after')
        odpm_file_path = os.path.join(self.odpm_folder, odpm_file_name)
        if os.path.exists(odpm_file_path):
            elapsed_time = None
            with open(odpm_file_path, 'r') as f:
                # find energy table in ODPM report
                for line in f:
                    if self.ODPM_ENERGY_TABLE_NAME in line:
                        break

                # get elapse time 2 adb ODPM cmd (mS)
                elapsed_time_str = f.readline()
                elapsed_time = float(elapsed_time_str
                                        .split(':')[1]
                                        .strip()
                                        .split(' ')[0])
                self.log.info(elapsed_time_str)

                # skip column name row
                next(f)

                # get power of different channel from odpm report
                for line in f:
                    if 'End' in line:
                        break
                    else:
                        # parse columns
                        # example result of line.strip().split()
                        # ['[VSYS_PWR_DISPLAY]:Display', '1039108.42', 'mWs', '(', '344.69)']
                        channel, _, _, _, delta_str = line.strip().split()
                        delta = float(delta_str[:-2].strip())

                        # calculate OPDM power
                        # delta is a different in cumulative energy
                        # between 2 adb ODPM cmd
                        elapsed_time_s = elapsed_time / 1000
                        power = delta / elapsed_time_s
                        odpm_power_results[channel] = power
                        self.log.info(
                            channel + ' ' + str(power) + ' mW'
                        )
        return odpm_power_results

    def _is_any_substring(self, longer_word: str, word_list: List[str]) -> bool:
        """Check if any word in word list a substring of a longer word."""
        return any(w in longer_word for w in word_list)

    def parse_power_rails_csv(self):
        kibble_dir = os.path.join(self.root_output_path, 'Kibble')
        kibble_csv_path = None
        if os.path.exists(kibble_dir):
            for f in os.listdir(kibble_dir):
                if self.test_name in f and '.csv' in f:
                    kibble_csv_path = os.path.join(kibble_dir, f)
                    self.log.info('Kibble csv file path: ' + kibble_csv_path)
                    break

        self.log.info('Parsing power rails from csv.')
        if kibble_csv_path:
            with open(kibble_csv_path, 'r') as f:
                for line in f:
                    # railname,val,mA,val,mV,val,mW
                    railname, _, _, _, _, power, _ = line.split(',')
                    # parse pcie power
                    if self._is_any_substring(railname, self.MODEM_PCIE_RAIL_NAME_LIST):
                        self.log.info(railname + ': ' + power)
                        self.pcie_power += float(power)
                    elif self.MODEM_POWER_RAIL_NAME in railname:
                        self.log.info(railname + ': ' + power)
                        self.modem_power = float(power)
                    elif self._is_any_substring(railname, self.MODEM_RFFE_RAIL_NAME_LIST):
                        self.log.info(railname + ': ' + power)
                        self.rffe_power = float(power)
                    elif self.MODEM_MMWAVE_RAIL_NAME in railname:
                        self.log.info(railname + ': ' + power)
                        self.mmwave_power = float(power)
                    elif self.MONSOON_RAIL_NAME == railname:
                        self.log.info(railname + ': ' + power)
                        self.monsoon_power = float(power)
        if self.modem_power:
            self.power_results[self.test_name] = self.modem_power

    def sponge_upload(self):
        """Upload result to sponge as custom field."""
        # test name
        test_name_arr = self.current_test_name.split('_')
        test_name_for_sponge = ''.join(
            word[0].upper() + word[1:].lower()
                for word in test_name_arr
                    if word not in ('preset', 'test')
        )

        # build info
        build_info = self.cellular_dut.ad.build_info
        build_id = build_info.get('build_id', 'Unknown')
        incr_build_id = build_info.get('incremental_build_id', 'Unknown')
        modem_base_band = self.cellular_dut.ad.adb.getprop(
            'gsm.version.baseband')
        build_type = build_info.get('build_type', 'Unknown')

        # device info
        device_info = self.cellular_dut.ad.device_info
        device_name = device_info.get('model', 'Unknown')
        device_build_phase = self.cellular_dut.ad.adb.getprop(
            'ro.boot.hardware.revision'
        )

        # if kibbles are using, get power from kibble
        modem_kibble_power_wo_pcie = 0
        if hasattr(self, 'bitses'):
            modem_kibble_power_wo_pcie = self.modem_power - self.pcie_power
            self.system_power = self.monsoon_power
        else:
            self.system_power = self.power_results.get(self.test_name, 0)

        self.record_data({
            'Test Name': self.test_name,
            'sponge_properties': {
                self.CUSTOM_PROP_KEY_SYSTEM_POWER: self.system_power,
                self.CUSTOM_PROP_KEY_BUILD_ID: build_id,
                self.CUSTOM_PROP_KEY_INCR_BUILD_ID: incr_build_id,
                self.CUSTOM_PROP_KEY_MODEM_BASEBAND: modem_base_band,
                self.CUSTOM_PROP_KEY_BUILD_TYPE: build_type,
                self.CUSTOM_PROP_KEY_MODEM_ODPM_POWER: self.odpm_power,
                self.CUSTOM_PROP_KEY_DEVICE_NAME: device_name,
                self.CUSTOM_PROP_KEY_DEVICE_BUILD_PHASE: device_build_phase,
                self.CUSTOM_PROP_KEY_MODEM_KIBBLE_POWER: self.modem_power,
                self.CUSTOM_PROP_KEY_TEST_NAME: test_name_for_sponge,
                self.CUSTOM_PROP_KEY_MODEM_KIBBLE_WO_PCIE_POWER: modem_kibble_power_wo_pcie,
                self.CUSTOM_PROP_KEY_MODEM_KIBBLE_PCIE_POWER: self.pcie_power,
                self.CUSTOM_PROP_KEY_RFFE_POWER: self.rffe_power,
                self.CUSTOM_PROP_KEY_MMWAVE_POWER: self.mmwave_power
            },
        })

    def threshold_check(self):
        """Check the test result and decide if it passed or failed.

        The threshold is provided in the config file. In this class, result is
        current in mA.
        """

        if not self.threshold or self.test_name not in self.threshold:
            self.log.error("No threshold is provided for the test '{}' in "
                           "the configuration file.".format(self.test_name))
            return
        voltage = self.cellular_test_params['mon_voltage']
        average_power = self.modem_power if self.modem_power else self.system_power
        average_current = average_power / voltage
        current_threshold = self.threshold[self.test_name]
        acceptable_difference = max(
            self.threshold[self.test_name] * self.pass_fail_tolerance,
            self.kibble_error_range
        )
        if average_current:
            asserts.assert_true(
                abs(average_current - current_threshold) < acceptable_difference,
                'Measured average current in [{}]: {:.2f}mA, which is '
                'out of the acceptable range {:.2f}±{:.2f}mA'.format(
                    self.test_name, average_current, current_threshold,
                    acceptable_difference))
            asserts.explicit_pass(
                'Measurement finished for [{}]: {:.2f}mA, which is '
                'within the acceptable range {:.2f}±{:.2f}'.format(
                    self.test_name, average_current, current_threshold,
                    acceptable_difference))
        else:
            asserts.fail(
                'Something happened, measurement is not complete, test failed')

    def teardown_test(self):
        super().teardown_test()
        # restore device to ready state for next test
        self.log.info('Enable mobile data.')
        self.cellular_dut.ad.adb.shell('svc data enable')
        self.cellular_simulator.detach()
        self.cellular_dut.toggle_airplane_mode(True)

        # processing result
        self.sponge_upload()
        if 'LTE' in self.test_name:
            self.at_util.disable_lock_band_lte()