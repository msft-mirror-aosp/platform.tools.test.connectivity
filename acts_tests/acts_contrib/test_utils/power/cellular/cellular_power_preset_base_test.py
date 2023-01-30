import os
from typing import Optional
import time
from acts import context
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

    def __init__(self, dut, log) -> None:
        self.dut = dut
        self.log = log

    # TODO: to be remove when b/261639867 complete,
    # and we are using parent method.
    def send(self, cmd: str,) -> Optional[str]:
        res = str(self.dut.adb.shell(cmd))
        self.log.info(f'cmd sent: {cmd}')
        self.log.debug(f'response: {res}')
        if 'OK' in res:
            self.log.info('Command executed.')
        else:
            self.log.error('Fail to executed command.')
        return res

    def lock_LTE(self):
        adb_enable_band_lock_lte = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Band.Select\ Enb\/\ Dis\",00,\"01\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_mode_lte = r'am instrument -w -e request at+GOOGSETNV=\"NASU.SIPC.NetworkMode.ManualMode\",0,\"0D\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_bitmap_0 = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\",0,\"09,00,00,00,00,00,00,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_bitmap_1 = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\",1,\"00,00,00,00,00,00,00,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_bitmap_2 = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\",2,\"00,00,00,00,00,00,00,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_set_band_lock_bitmap_3 = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Enabled.RFBands.BitMap\",3,\"00,00,00,00,00,00,00,00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'

        # enable lte
        self.send(adb_enable_band_lock_lte)
        time.sleep(2)

        # OD is for NR/LTE in 4412 menu
        self.send(adb_set_band_lock_mode_lte)
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

    def clear_lock_band(self):
        adb_set_band_lock_mode_auto = r'am instrument -w -e request at+GOOGSETNV=\"NASU.SIPC.NetworkMode.ManualMode\",0,\"03\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
        adb_disable_band_lock_lte = r'am instrument -w -e request at+GOOGSETNV=\"!SAEL3.Manual.Band.Select\ Enb\/\ Dis\",0,\"00\" -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'

        # band lock mode auto
        self.send(adb_set_band_lock_mode_auto)
        time.sleep(2)

        # disable band lock lte
        self.send(adb_disable_band_lock_lte)
        time.sleep(2)

    def disable_txas(self):
        cmd = self.ADB_CMD_DISABLE_TXAS
        response = self.send(cmd)
        return 'OK' in response

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

    # kibble report
    KIBBLE_SYSTEM_RECORD_NAME = '- name: default_device.C10_EVT_1_1.Monsoon:mA'
    MODEM_PCIE_RAIL_LIST = [
        'C4_23__PP1800_L2C_PCIEG3',
        'C2_23__PP1200_L9C_PCIE',
        'C2_06__PP0850_L8C_PCIE'
    ]

    MODEM_RAIL_LIST = [
        'C1_43__VSENSE_VSYS_PWR_MODEM',
        'C1_43__VSYS_PWR_MODEM'
    ]

    # params key
    MONSOON_VOLTAGE_KEY = 'mon_voltage'

    MDSTEST_APP_APK_NAME = 'mdstest.apk'
    ADB_CMD_INSTALL = 'install {apk_path}'
    ADB_CMD_DISABLE_TXAS = 'am instrument -w -e request at+googtxas=2 -e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"'
    ADB_CMD_SET_NV = ('am instrument -w '
                      '-e request at+googsetnv=\"{nv_name}\",{nv_index},\"{nv_value}\" '
                      '-e response wait "com.google.mdstest/com.google.mdstest.instrument.ModemATCommandInstrumentation"')

    def __init__(self, controllers):
        super().__init__(controllers)
        self.retryable_exceptions = signals.TestFailure

    def setup_class(self):
        super().setup_class()

        # preset callbox
        is_fr2 = 'Fr2' in self.TAG
        self.cellular_simulator.switch_HCCU_settings(is_fr2=is_fr2)

        self.at_util = AtUtil(self.cellular_dut.ad, self.log)

        # preset UE.
        self.log.info('Installing mdstest app.')
        self.install_apk()

        self.log.info('Disable antenna switch.')
        is_txas_disabled = self.at_util.disable_txas()
        self.log.info('Disable txas: ' + str(is_txas_disabled))

        # get sim type
        self.unpack_userparams(has_3gpp_sim=True)

    def setup_test(self):
        self.cellular_simulator.set_sim_type(self.has_3gpp_sim)
        try:
            if 'LTE' in self.test_name:
                self.at_util.lock_LTE()
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


    def install_apk(self):
        for file in self.custom_files:
            if self.MDSTEST_APP_APK_NAME in file:
                self.log.info('Found mdstest apk: ' + file)
                self.cellular_dut.ad.adb.install(file)

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

    def get_system_power(self):
        """Parsing system power from test_run_debug file.

        Kibble measurements are available in test_run_debug.
        This frunction iterates through test_run_debug file
        to get system power.
        Returns:
            kibble_system_power: system power value in mW.
        """
        kibble_system_power = 0

        # getting system power if kibble is on
        context_path = context.get_current_context().get_full_output_path()
        test_run_debug_log_path = os.path.join(
            context_path, 'test_run_debug.txt'
        )
        self.log.debug('test_run_debug path: ' + test_run_debug_log_path)
        with open(test_run_debug_log_path, 'r') as f:
            while True:
                line = f.readline()
                if not line:
                    break
                if self.KIBBLE_SYSTEM_RECORD_NAME in line:
                    value_line = f.readline()
                    system_power_str = value_line.split(':')[1].strip()
                    monsoon_voltage = self.test_params[self.MONSOON_VOLTAGE_KEY]
                    kibble_system_power = float(system_power_str) * monsoon_voltage
                    break
        return kibble_system_power

    def get_modem_pcie_power(self):
        """Get PCIE MODEM values from kibble csv."""
        modem_pcie_power = 0
        # find kibble rail data csv file path.
        kibble_dir = os.path.join(self.root_output_path, 'Kibble')
        if os.path.exists(kibble_dir):
            kibble_csv_path = None
            for f in os.listdir(kibble_dir):
                if self.test_name in f and '.csv' in f:
                    kibble_csv_path = os.path.join(kibble_dir, f)
                    self.log.info('Kibble csv file path: ' + kibble_csv_path)
                    break

        # parsing modem pcie power rails.
        self.log.info('Parsing MODEM PCIE power.')
        modem_rail = 0
        if kibble_csv_path:
            with open(kibble_csv_path, 'r') as f:
                for line in f:
                    # railname,val,mA,val,mV,val,mW
                    railname, _, _, _, _, power, _ = line.split(',')
                    if railname in self.MODEM_PCIE_RAIL_LIST:
                        self.log.info(railname + ': ' + power)
                        modem_pcie_power += float(power)
                    elif railname in self.MODEM_RAIL_LIST:
                        self.log.info(railname + ': ' + power)
                        modem_rail = float(power)
        if modem_rail:
            self.power_results[self.test_name] = modem_rail
        return modem_pcie_power

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

        # power measurement results
        odpm_power_results = self.get_odpm_values()
        odpm_power = odpm_power_results.get(self.ODPM_MODEM_CHANNEL_NAME, 0)
        system_power = 0
        modem_kibble_power = 0

        # if kibbles are using, get power from kibble
        modem_kibble_power_wo_pcie = 0
        modem_pcie = 0
        if hasattr(self, 'bitses'):
            # modem kibble power without pcie
            modem_pcie = self.get_modem_pcie_power()
            modem_kibble_power = self.power_results.get(self.test_name, None)
            modem_kibble_power_wo_pcie = modem_kibble_power - modem_pcie
            system_power = self.get_system_power()
        else:
            system_power = self.power_results.get(self.test_name, None)


        self.record_data({
            'Test Name': self.test_name,
            'sponge_properties': {
                self.CUSTOM_PROP_KEY_SYSTEM_POWER: system_power,
                self.CUSTOM_PROP_KEY_BUILD_ID: build_id,
                self.CUSTOM_PROP_KEY_INCR_BUILD_ID: incr_build_id,
                self.CUSTOM_PROP_KEY_MODEM_BASEBAND: modem_base_band,
                self.CUSTOM_PROP_KEY_BUILD_TYPE: build_type,
                self.CUSTOM_PROP_KEY_MODEM_ODPM_POWER: odpm_power,
                self.CUSTOM_PROP_KEY_DEVICE_NAME: device_name,
                self.CUSTOM_PROP_KEY_DEVICE_BUILD_PHASE: device_build_phase,
                self.CUSTOM_PROP_KEY_MODEM_KIBBLE_POWER: modem_kibble_power,
                self.CUSTOM_PROP_KEY_TEST_NAME: test_name_for_sponge,
                self.CUSTOM_PROP_KEY_MODEM_KIBBLE_WO_PCIE_POWER: modem_kibble_power_wo_pcie,
                self.CUSTOM_PROP_KEY_MODEM_KIBBLE_PCIE_POWER: modem_pcie
            },
        })

    def teardown_test(self):
        super().teardown_test()
        self.log.info('Enable mobile data.')
        self.dut.adb.shell('svc data enable')
        self.cellular_simulator.detach()
        self.cellular_dut.toggle_airplane_mode(True)
        self.sponge_upload()
        if 'LTE' in self.test_name:
            self.at_util.clear_lock_band()