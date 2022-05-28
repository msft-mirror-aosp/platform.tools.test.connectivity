#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
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

import os
import time
import glob
import errno
from collections import namedtuple
from pandas import DataFrame
from acts import utils
from acts import signals
from acts.base_test import BaseTestClass
from acts.controllers.gnss_lib import GnssSimulator
from acts.context import get_current_context
from acts_contrib.test_utils.gnss import dut_log_test_utils as diaglog
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils
from acts_contrib.test_utils.gnss import gnss_testlog_utils as glogutils
from acts_contrib.test_utils.gnss.gnss_defines import DEVICE_GPSLOG_FOLDER
from acts_contrib.test_utils.gnss.gnss_defines import GPS_PKG_NAME
from acts_contrib.test_utils.gnss.gnss_defines import BCM_GPS_XML_PATH


class LabTtffTestBase(BaseTestClass):
    """ LAB TTFF Tests Base Class"""
    GTW_GPSTOOL_APP = 'gtw_gpstool_apk'
    GNSS_SIMULATOR_KEY = 'gnss_sim_params'
    CUSTOM_FILES_KEY = 'custom_files'
    CSTTFF_CRITERIA = 'cs_criteria'
    HSTTFF_CRITERIA = 'hs_criteria'
    WSTTFF_CRITERIA = 'ws_criteria'
    CSTTFF_PECRITERIA = 'cs_ttff_pecriteria'
    HSTTFF_PECRITERIA = 'hs_ttff_pecriteria'
    WSTTFF_PECRITERIA = 'ws_ttff_pecriteria'
    TTFF_ITERATION = 'ttff_iteration'
    SIMULATOR_LOCATION = 'simulator_location'
    DIAG_OPTION = 'diag_option'
    SCENARIO_POWER = 'scenario_power'
    MDSAPP = 'mdsapp'
    MASKFILE = 'maskfile'
    MODEMPARFILE = 'modemparfile'
    NV_DICT = 'nv_dict'

    def __init__(self, controllers):
        """ Initializes class attributes. """

        super().__init__(controllers)
        self.dut = None
        self.gnss_simulator = None
        self.rockbottom_script = None
        self.gnss_log_path = self.log_path
        self.gps_xml_bk_path = BCM_GPS_XML_PATH + '.bk'

    def setup_class(self):
        super().setup_class()

        # Update parameters by test case configurations.
        TEST_PARAMS = self.TAG + '_params'
        self.test_params = self.user_params.get(TEST_PARAMS, {})
        if not self.test_params:
            self.log.warning(TEST_PARAMS + ' was not found in the user '
                             'parameters defined in the config file.')

        # Override user_param values with test parameters
        self.user_params.update(self.test_params)

        # Unpack user_params with default values. All the usages of user_params
        # as self attributes need to be included either as a required parameter
        # or as a parameter with a default value.

        # Required parameters
        req_params = [
            self.CSTTFF_PECRITERIA, self.WSTTFF_PECRITERIA, self.HSTTFF_PECRITERIA,
            self.CSTTFF_CRITERIA, self.HSTTFF_CRITERIA, self.WSTTFF_CRITERIA,
            self.TTFF_ITERATION, self.GNSS_SIMULATOR_KEY, self.DIAG_OPTION,
            self.GTW_GPSTOOL_APP
        ]
        self.unpack_userparams(req_param_names=req_params)

        # Optional parameters
        self.custom_files = self.user_params.get(self.CUSTOM_FILES_KEY,[])
        self.maskfile = self.user_params.get(self.MASKFILE,'')
        self.mdsapp = self.user_params.get(self.MDSAPP,'')
        self.modemparfile = self.user_params.get(self.MODEMPARFILE,'')
        self.nv_dict = self.user_params.get(self.NV_DICT,{})
        self.scenario_power = self.user_params.get(self.SCENARIO_POWER, [])

        # Set TTFF Spec.
        test_type = namedtuple('Type', ['command', 'criteria'])
        self.test_types = {
            'cs': test_type('Cold Start', self.cs_criteria),
            'ws': test_type('Warm Start', self.ws_criteria),
            'hs': test_type('Hot Start', self.hs_criteria)
        }

        self.dut = self.android_devices[0]

        # GNSS Simulator Setup
        self.simulator_location = self.gnss_sim_params.get(
            self.SIMULATOR_LOCATION, [])
        self.gnss_simulator_scenario = self.gnss_sim_params.get('scenario')
        self.gnss_simulator_power_level = self.gnss_sim_params.get('power_level')

        # Create gnss_simulator instance
        gnss_simulator_key = self.gnss_sim_params.get('type')
        gnss_simulator_ip = self.gnss_sim_params.get('ip')
        gnss_simulator_port = self.gnss_sim_params.get('port')
        if gnss_simulator_key == 'gss7000':
            gnss_simulator_port_ctrl = self.gnss_sim_params.get('port_ctrl')
        else:
            gnss_simulator_port_ctrl = None
        self.gnss_simulator = GnssSimulator.AbstractGnssSimulator(
            gnss_simulator_key, gnss_simulator_ip, gnss_simulator_port,
            gnss_simulator_port_ctrl)

        # Unpack the rockbottom script file if its available.
        if self.custom_files:
            for file in self.custom_files:
                if 'rockbottom_' + self.dut.model in file:
                    self.rockbottom_script = file
                    break

    def setup_test(self):

        self.clear_gps_log()
        self.gnss_simulator.stop_scenario()
        self.gnss_simulator.close()
        if self.rockbottom_script:
            self.log.info('Running rockbottom script for this device ' +
                          self.dut.model)
            self.dut_rockbottom()
        else:
            self.log.info('Not running rockbottom for this device ' +
                          self.dut.model)

        utils.set_location_service(self.dut, True)
        gutils.reinstall_package_apk(self.dut, GPS_PKG_NAME,
                                     self.gtw_gpstool_apk)

        # For BCM DUTs, delete gldata.sto and set IgnoreRomAlm="true" based on b/196936791#comment20
        if self.diag_option == "BCM":
            gutils.remount_device(self.dut)
            # Backup gps.xml
            copy_cmd = "cp {} {}".format(BCM_GPS_XML_PATH, self.gps_xml_bk_path)
            self.dut.adb.shell(copy_cmd)
            gutils.delete_bcm_nvmem_sto_file(self.dut)
            gutils.bcm_gps_ignore_rom_alm(self.dut)
            # Reboot DUT to apply the setting
            gutils.reboot(self.dut)
        self.gnss_simulator.connect()

    def dut_rockbottom(self):
        """
        Set the dut to rockbottom state

        """
        # The rockbottom script might include a device reboot, so it is
        # necessary to stop SL4A during its execution.
        self.dut.stop_services()
        self.log.info('Executing rockbottom script for ' + self.dut.model)
        os.chmod(self.rockbottom_script, 0o777)
        os.system('{} {}'.format(self.rockbottom_script, self.dut.serial))
        # Make sure the DUT is in root mode after coming back
        self.dut.root_adb()
        # Restart SL4A
        self.dut.start_services()

    def teardown_test(self):
        """Teardown settings for the test class"""
        super().teardown_test()
        # Restore the gps.xml everytime after the test.
        if self.diag_option == "BCM":
            # Restore gps.xml
            rm_cmd = "rm -rf {}".format(BCM_GPS_XML_PATH)
            restore_cmd = "mv {} {}".format(self.gps_xml_bk_path,
                                            BCM_GPS_XML_PATH)
            self.dut.adb.shell(rm_cmd)
            self.dut.adb.shell(restore_cmd)

    def teardown_class(self):
        """ Executed after completing all selected test cases."""
        self.clear_gps_log()
        if self.gnss_simulator:
            self.gnss_simulator.stop_scenario()
            self.gnss_simulator.close()

    def start_and_set_gnss_simulator_power(self):
        """
        Start GNSS simulator secnario and set power level.

        """

        self.gnss_simulator.start_scenario(self.gnss_simulator_scenario)
        time.sleep(25)
        if self.scenario_power:
            self.log.info('Set GNSS simulator power with power_level by scenario_power')
            for setting in self.scenario_power:
                power_level = setting.get('power_level', -130)
                sat_system = setting.get('sat_system', '')
                freq_band = setting.get('freq_band', 'ALL')
                sat_id = setting.get('sat_id', '')
                self.log.debug(f'sat: {sat_system}; freq_band: {freq_band}, '
                               f'power_level: {power_level}, sat_id: {sat_id}')
                self.gnss_simulator.set_scenario_power(power_level,
                                                       sat_id,
                                                       sat_system,
                                                       freq_band)
        else:
            self.log.debug('Set GNSS simulator power '
                           f'with power_level: {self.gnss_simulator_power_level}')
            self.gnss_simulator.set_power(self.gnss_simulator_power_level)

    def get_and_verify_ttff(self, mode):
        """Retrieve ttff with designate mode.

            Args:
                mode: A string for identify gnss test mode.
        """
        if mode not in self.test_types:
            raise signals.TestError('Unrecognized mode %s' % mode)
        test_type = self.test_types.get(mode)

        if mode != 'cs':
            wait_time = 900
        else:
            wait_time = 300

        gutils.process_gnss_by_gtw_gpstool(self.dut,
                                           self.test_types['cs'].criteria)
        begin_time = gutils.get_current_epoch_time()
        gutils.start_ttff_by_gtw_gpstool(self.dut,
                                         ttff_mode=mode,
                                         iteration=self.ttff_iteration,
                                         raninterval=True,
                                         hot_warm_sleep=wait_time)
        # Since Wear takes little longer to update the TTFF info.
        # Workround to solve the wearable timing issue
        if gutils.is_device_wearable(self.dut):
            time.sleep(20)

        ttff_data = gutils.process_ttff_by_gtw_gpstool(self.dut, begin_time,
                                                       self.simulator_location)

        # Create folder for GTW GPStool's log
        gps_log_path = os.path.join(self.gnss_log_path, 'GPSLogs')
        os.makedirs(gps_log_path, exist_ok=True)

        self.dut.adb.pull("{} {}".format(DEVICE_GPSLOG_FOLDER, gps_log_path))

        gps_api_log = glob.glob(gps_log_path + '/*/GNSS_*.txt')
        ttff_loop_log = glob.glob(gps_log_path +
                                  '/*/GPS_{}_*.txt'.format(mode.upper()))

        if not gps_api_log and ttff_loop_log:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    gps_log_path)

        df = DataFrame(glogutils.parse_gpstool_ttfflog_to_df(gps_api_log[0]))

        ttff_dict = {}
        for i in ttff_data:
            d = ttff_data[i]._asdict()
            ttff_dict[i] = dict(d)

        ttff_time = []
        ttff_pe = []
        ttff_haccu = []
        for i in ttff_dict.keys():
            ttff_time.append(ttff_dict[i]['ttff_sec'])
            ttff_pe.append(ttff_dict[i]['ttff_pe'])
            ttff_haccu.append(ttff_dict[i]['ttff_haccu'])
        df['ttff_sec'] = ttff_time
        df['ttff_pe'] = ttff_pe
        df['ttff_haccu'] = ttff_haccu
        df.to_json(gps_log_path + '/gps_log.json', orient='table')
        result = gutils.check_ttff_data(self.dut,
                                        ttff_data,
                                        ttff_mode=test_type.command,
                                        criteria=test_type.criteria)
        if not result:
            raise signals.TestFailure('%s TTFF fails to reach '
                                      'designated criteria' % test_type.command)
        return ttff_data

    def verify_pe(self, mode):
        """
        Verify ttff Position Error with designate mode.

        Args:
             mode: A string for identify gnss test mode.
        """

        ffpe_type = namedtuple('Type', ['command', 'pecriteria'])
        ffpe_types = {
            'cs': ffpe_type('Cold Start', self.cs_ttff_pecriteria),
            'ws': ffpe_type('Warm Start', self.ws_ttff_pecriteria),
            'hs': ffpe_type('Hot Start', self.hs_ttff_pecriteria)
        }

        if mode not in ffpe_types:
            raise signals.TestError('Unrecognized mode %s' % mode)
        test_type = ffpe_types.get(mode)

        ttff_data = self.get_and_verify_ttff(mode)
        result = gutils.check_ttff_pe(self.dut,
                                      ttff_data,
                                      ttff_mode=test_type.command,
                                      pe_criteria=test_type.pecriteria)
        if not result:
            raise signals.TestFailure('%s TTFF fails to reach '
                                      'designated criteria' % test_type.command)
        return ttff_data

    def clear_gps_log(self):
        """
        Delete the existing GPS GTW Log from DUT.

        """
        self.dut.adb.shell("rm -rf {}".format(DEVICE_GPSLOG_FOLDER))

    def gnss_ttff_ffpe(self, mode, sub_context_path=''):
        """
        Base ttff and ffpe function
            Args:
                mode: Set the TTFF mode for testing. Definitions are as below.
                      cs(cold start), ws(warm start), hs(hot start)
                sub_context_path: Set specifc log pathfor ttff_ffpe
        """
        # Create log file path
        full_output_path = get_current_context().get_full_output_path()
        self.gnss_log_path = os.path.join(full_output_path, sub_context_path)
        os.makedirs(self.gnss_log_path, exist_ok=True)
        self.log.debug('Create log path: {}'.format(self.gnss_log_path))

        # Start and set GNSS simulator
        self.start_and_set_gnss_simulator_power()

        # Start GNSS chip log
        if self.diag_option == "QCOM":
            diaglog.start_diagmdlog_background(self.dut, maskfile=self.maskfile)
        else:
            gutils.start_pixel_logger(self.dut)

        # Start verifying TTFF and FFPE
        self.verify_pe(mode)

        # Set gnss_vendor_log_path based on GNSS solution vendor
        gnss_vendor_log_path = os.path.join(self.gnss_log_path,
                                            self.diag_option)
        os.makedirs(gnss_vendor_log_path, exist_ok=True)

        # Stop GNSS chip log and pull the logs to local file system
        if self.diag_option == "QCOM":
            diaglog.stop_background_diagmdlog(self.dut,
                                              gnss_vendor_log_path,
                                              keep_logs=False)
        else:
            gutils.stop_pixel_logger(self.dut)
            self.log.info('Getting Pixel BCM Log!')
            diaglog.get_pixellogger_bcm_log(self.dut,
                                            gnss_vendor_log_path,
                                            keep_logs=False)
