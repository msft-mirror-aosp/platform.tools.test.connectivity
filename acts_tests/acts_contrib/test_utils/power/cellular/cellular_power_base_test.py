#!/usr/bin/env python3
#
#   Copyright 2018 - The Android Open Source Project
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
import json
import os

import acts_contrib.test_utils.power.PowerBaseTest as PBT
import acts_contrib.test_utils.cellular.cellular_base_test as CBT
from acts_contrib.test_utils.power import plot_utils
from acts import context


class PowerCellularLabBaseTest(CBT.CellularBaseTest, PBT.PowerBaseTest):
    """ Base class for Cellular power related tests.

    Inherits from both PowerBaseTest and CellularBaseTest so it has methods to
    collect power measurements and run a cellular simulation.
    """
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
        'C4_23__PP1800_L2C_PCIEG3:mW',
        'C2_23__PP1200_L9C_PCIE:mW',
        'C2_06__PP0850_L8C_PCIE:mW'
    ]

    # params key
    MONSOON_VOLTAGE_KEY = 'mon_voltage'

    def __init__(self, controllers):
        """ Class initialization.

        Sets class attributes to None.
        """

        super().__init__(controllers)
        self.power_results = {}

    def setup_test(self):
        """ Turn screen on before starting a test. """

        super().setup_test()
        try:
            # Save a json file for device info
            path = os.path.join(self.log_path, 'device_info.json')

            self.log.info('save the device info to {}'.format(path))
            baseband = self.dut.adb.getprop('gsm.version.baseband')
            self.dut.add_device_info('baseband', baseband)
            with open(path, 'w') as f:
                json.dump(
                    self.dut.device_info,
                    f,
                    indent=2,
                    sort_keys=True)
        except Exception as e:
            self.log.error('error in saving device_info: {}'.format(e))

        # Make the device go to sleep
        self.dut.droid.goToSleepNow()

        return True

    def collect_power_data(self):
        """ Collect power data using base class method and plot result
        histogram. """

        samples = super().collect_power_data()
        plot_title = '{}_{}_{}_histogram'.format(
            self.test_name, self.dut.model, self.dut.build_info['build_id'])
        plot_utils.monsoon_histogram_plot(samples, self.mon_info.data_path,
                                          plot_title)
        return samples

    def teardown_test(self):
        """ Executed after every test case, even if it failed or an exception
        happened.

        Save results to dictionary so they can be displayed after completing
        the test batch.
        """
        super().teardown_test()

        self.power_results[self.test_name] = self.power_result.metric_value

    def teardown_class(self):
        """Clean up the test class after tests finish running.

        Stops the simulation and disconnects from the Anritsu Callbox. Then
        displays the test results.

        """
        super().teardown_class()

        # Log a summary of results
        results_table_log = 'Results for cellular power tests:'

        for test_name, value in self.power_results.items():
            results_table_log += '\n{}\t{}'.format(test_name, value)

        # Save this summary to a csv file in the logs directory
        self.save_summary_to_file()

        self.log.info(results_table_log)

    def save_summary_to_file(self):
        """ Creates CSV format files with a summary of results.

        This CSV files can be easily imported in a spreadsheet to analyze the
        results obtained from the tests.
        """

        # Save a csv file with the power measurements done in all the tests

        path = os.path.join(self.log_path, self.RESULTS_SUMMARY_FILENAME)

        # To avoid the test overwrite each other, open file with 'a' option
        csvfile_exist = os.path.exists(path)

        with open(path, 'a') as csvfile:
            if not csvfile_exist:
                csvfile.write('test,avg_power')
            for test_name, value in self.power_results.items():
                csvfile.write('\n{},{}'.format(test_name, value))

        # Save a csv file with the calibration table for each simulation type

        for sim_type in self.calibration_table:

            path = os.path.join(
                self.log_path, '{}_{}'.format(sim_type,
                                              self.CALIBRATION_TABLE_FILENAME))

            with open(path, 'w') as csvfile:
                csvfile.write('band,dl_pathloss, ul_pathloss')
                for band, pathloss in self.calibration_table[sim_type].items():
                    csvfile.write('\n{},{},{}'.format(
                        band, pathloss.get('dl', 'Error'),
                        pathloss.get('ul', 'Error')))

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
        """Get PCIE MODEM values from kibble json."""
        modem_pcie_power = 0
        # find kibble rail data json file path.
        kibble_dir = os.path.join(self.root_output_path, 'Kibble')
        kibble_json_path = None
        for f in os.listdir(kibble_dir):
            if '.json' in f:
                kibble_json_path = os.path.join(kibble_dir, f)
                self.log.info('Kibble json file path: ' + kibble_json_path)
        kibble_rails_data = None
        if kibble_json_path:
            with open(kibble_json_path, 'r') as f:
                kibble_rails_data = json.load(f)

        # parsing modem pcie power rails.
        self.log.info('Parsing MODEM PCIE power.')
        if kibble_rails_data:
            for data_dict in kibble_rails_data:
                # format of data_dict['name']: _._.rail_name:unit
                channel = data_dict['name'].split('.')[-1]
                if channel in self.MODEM_PCIE_RAIL_LIST:
                    self.log.info(channel + ': ' + str(data_dict['avg']))
                    modem_pcie_power += data_dict['avg']
        return modem_pcie_power

    def sponge_upload(self):
        """Upload result to sponge as custom field."""
        self.log.info('=====> power monitor info')
        for key in self.power_monitor.__dict__.keys():
            self.log.info(key + ': ')
            self.log.info(self.power_monitor.__dict__[key])
            self.log.info('\n')
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
        if hasattr(self, 'bitses'):
            modem_kibble_power = self.power_results.get(self.test_name, None)
            system_power = self.get_system_power()
        else:
            system_power = self.power_results.get(self.test_name, None)

        # modem kibble power without pcie
        modem_kibble_power_wo_pcie = 0
        modem_pcie = 0
        if modem_kibble_power:
            modem_pcie = self.get_modem_pcie_power()
            modem_kibble_power_wo_pcie = modem_kibble_power - modem_pcie

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
