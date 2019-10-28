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
import logging
import math
import os
import time
import acts.controllers.iperf_server as ipf
from acts import asserts
from acts import base_test
from acts import utils
from acts.controllers import monsoon
from acts.metrics.loggers.blackbox import BlackboxMetricLogger
from acts.test_utils.power.loggers.power_metric_logger import PowerMetricLogger
from acts.test_utils.wifi import wifi_test_utils as wutils
from acts.test_utils.wifi import wifi_power_test_utils as wputils

RESET_BATTERY_STATS = 'dumpsys batterystats --reset'
IPERF_TIMEOUT = 180
THRESHOLD_TOLERANCE = 0.2
GET_FROM_PHONE = 'get_from_dut'
GET_FROM_AP = 'get_from_ap'
PHONE_BATTERY_VOLTAGE = 4.2
MONSOON_MAX_CURRENT = 8.0
MONSOON_RETRY_INTERVAL = 300
DEFAULT_MONSOON_FREQUENCY = 500
MEASUREMENT_RETRY_COUNT = 3
RECOVER_MONSOON_RETRY_COUNT = 3
MIN_PERCENT_SAMPLE = 95
ENABLED_MODULATED_DTIM = 'gEnableModulatedDTIM='
MAX_MODULATED_DTIM = 'gMaxLIModulatedDTIM='
TEMP_FILE = '/sdcard/Download/tmp.log'


class ObjNew():
    """Create a random obj with unknown attributes and value.

    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, item):
        """Function to check if one attribute is contained in the object.

        Args:
            item: the item to check
        Return:
            True/False
        """
        return hasattr(self, item)


class PowerBaseTest(base_test.BaseTestClass):
    """Base class for all wireless power related tests.

    """
    def __init__(self, controllers):

        base_test.BaseTestClass.__init__(self, controllers)
        self.power_result = BlackboxMetricLogger.for_test_case(
            metric_name='avg_power')
        self.start_meas_time = 0
        self.rockbottom_script = None
        self.img_name = ''
        self.power_logger = PowerMetricLogger.for_test_case()

    def setup_class(self):

        self.log = logging.getLogger()
        self.tests = self._get_all_test_names()

        # Setup the must have controllers, phone and monsoon
        self.dut = self.android_devices[0]
        self.mon_data_path = os.path.join(self.log_path, 'Monsoon')
        self.mon = self.monsoons[0]
        self.mon.set_max_current(8.0)
        self.mon.set_voltage(PHONE_BATTERY_VOLTAGE)
        self.mon.attach_device(self.dut)

        # Obtain test parameters from user_params
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
        req_params = ['custom_files', 'mon_duration']
        self.unpack_userparams(req_params,
                               mon_freq=DEFAULT_MONSOON_FREQUENCY,
                               mon_offset=0,
                               bug_report=False,
                               extra_wait=None,
                               iperf_duration=None)

        # Unpack the custom files based on the test configs
        for file in self.custom_files:
            if 'pass_fail_threshold_' + self.dut.model in file:
                self.threshold_file = file
            elif 'attenuator_setting' in file:
                self.attenuation_file = file
            elif 'network_config' in file:
                self.network_file = file
            elif 'rockbottom_' + self.dut.model in file:
                self.rockbottom_script = file
        #Abort the class if threshold and rockbottom file is missing
        asserts.abort_class_if(
            not self.threshold_file,
            'Required test pass/fail threshold file is missing')
        asserts.abort_class_if(
            not self.rockbottom_script,
            'Required rockbottom setting script is missing')

        if hasattr(self, 'attenuators'):
            self.num_atten = self.attenuators[0].instrument.num_atten
            self.atten_level = self.unpack_custom_file(self.attenuation_file)
        self.threshold = self.unpack_custom_file(self.threshold_file)
        self.mon_info = self.create_monsoon_info()

        # Sync device time, timezone and country code
        utils.require_sl4a((self.dut, ))
        utils.sync_device_time(self.dut)
        self.dut.droid.wifiSetCountryCode('US')

        screen_on_img = self.user_params.get('screen_on_img', [])
        if screen_on_img:
            img_src = screen_on_img[0]
            img_dest = '/sdcard/Pictures/'
            success = self.dut.push_system_file(img_src, img_dest)
            if success:
                self.img_name = os.path.basename(img_src)

    def setup_test(self):
        """Set up test specific parameters or configs.

        """
        # Reset the power consumption to 0 before each tests
        self.power_result.metric_value = 0
        # Set the device into rockbottom state
        self.dut_rockbottom()
        wutils.reset_wifi(self.dut)
        wutils.wifi_toggle_state(self.dut, False)

        # Wait for extra time if needed for the first test
        if self.extra_wait:
            self.more_wait_first_test()

    def teardown_test(self):
        """Tear down necessary objects after test case is finished.

        """
        self.log.info('Tearing down the test case')
        self.mon.usb('on')
        self.power_logger.set_avg_power(self.power_result.metric_value)
        self.power_logger.set_testbed(self.testbed_name)

        # Take Bugreport
        if self.bug_report:
            begin_time = utils.get_current_epoch_time()
            self.dut.take_bug_report(self.test_name, begin_time)

        # Allow the device to cooldown before executing the next test
        last_test = self.current_test_name == self.results.requested[-1]
        cooldown = self.test_params.get('cooldown', None)
        if cooldown and not last_test:
            time.sleep(cooldown)

    def teardown_class(self):
        """Clean up the test class after tests finish running

        """
        self.log.info('Tearing down the test class')
        self.mon.usb('on')

    def dut_rockbottom(self):
        """Set the dut to rockbottom state

        """
        # The rockbottom script might include a device reboot, so it is
        # necessary to stop SL4A during its execution.
        self.dut.stop_services()
        self.log.info('Executing rockbottom script for ' + self.dut.model)
        os.chmod(self.rockbottom_script, 0o777)
        os.system('{} {} {}'.format(self.rockbottom_script, self.dut.serial,
                                    self.img_name))
        # Make sure the DUT is in root mode after coming back
        self.dut.root_adb()
        # Restart SL4A
        self.dut.start_services()

    def unpack_custom_file(self, file, test_specific=True):
        """Unpack the pass_fail_thresholds from a common file.

        Args:
            file: the common file containing pass fail threshold.
        """
        with open(file, 'r') as f:
            params = json.load(f)
        if test_specific:
            try:
                return params[self.TAG]
            except KeyError:
                pass
        else:
            return params

    def decode_test_configs(self, attrs, indices):
        """Decode the test config/params from test name.

        Remove redundant function calls when tests are similar.
        Args:
            attrs: a list of the attrs of the test config obj
            indices: a list of the location indices of keyword in the test name.
        """
        # Decode test parameters for the current test
        test_params = self.current_test_name.split('_')
        values = [test_params[x] for x in indices]
        config_dict = dict(zip(attrs, values))
        self.test_configs = ObjNew(**config_dict)

    def more_wait_first_test(self):
        # For the first test, increase the offset for longer wait time
        if self.current_test_name == self.tests[0]:
            self.mon_info.offset = self.mon_offset + self.extra_wait
        else:
            self.mon_info.offset = self.mon_offset

    def set_attenuation(self, atten_list):
        """Function to set the attenuator to desired attenuations.

        Args:
            atten_list: list containing the attenuation for each attenuator.
        """
        if len(atten_list) != self.num_atten:
            raise Exception('List given does not have the correct length')
        for i in range(self.num_atten):
            self.attenuators[i].set_atten(atten_list[i])

    def measure_power_and_validate(self):
        """The actual test flow and result processing and validate.

        """
        self.collect_power_data()
        self.pass_fail_check()

    def collect_power_data(self):
        """Measure power, plot and take log if needed.

        """
        tag = ''
        # Collecting current measurement data and plot
        self.file_path, self.test_result = self.monsoon_data_collect_save()
        self.power_result.metric_value = (self.test_result *
                                          PHONE_BATTERY_VOLTAGE)
        wputils.monsoon_data_plot(self.mon_info, self.file_path, tag=tag)

    def pass_fail_check(self):
        """Check the test result and decide if it passed or failed.

        The threshold is provided in the config file. In this class, result is
        current in mA.
        """

        if not self.threshold or self.test_name not in self.threshold:
            self.log.error("No threshold is provided for the test '{}' in "
                           "the configuration file.".format(self.test_name))
            return

        current_threshold = self.threshold[self.test_name]
        if self.test_result:
            asserts.assert_true(
                abs(self.test_result - current_threshold) / current_threshold <
                THRESHOLD_TOLERANCE,
                'Measured average current in [{}]: {:.2f}mA, which is '
                'out of the acceptable range {:.2f}±{:.2f}mA'.format(
                    self.test_name, self.test_result, current_threshold,
                    self.pass_fail_tolerance * current_threshold))
            asserts.explicit_pass(
                'Measurement finished for [{}]: {:.2f}mA, which is '
                'within the acceptable range {:.2f}±{:.2f}'.format(
                    self.test_name, self.test_result, current_threshold,
                    self.pass_fail_tolerance * current_threshold))
        else:
            asserts.fail(
                'Something happened, measurement is not complete, test failed')

    def create_monsoon_info(self):
        """Creates the config dictionary for monsoon

        Returns:
            mon_info: Dictionary with the monsoon packet config
        """
        if self.iperf_duration:
            self.mon_duration = self.iperf_duration - 10
        mon_info = ObjNew(dut=self.mon,
                          freq=self.mon_freq,
                          duration=self.mon_duration,
                          offset=self.mon_offset,
                          data_path=self.mon_data_path)
        return mon_info

    def monsoon_recover(self):
        """Test loop to wait for monsoon recover from unexpected error.

        Wait for a certain time duration, then quit.0
        Args:
            mon: monsoon object
        Returns:
            True/False
        """
        try:
            self.mon.reconnect_monsoon()
            time.sleep(2)
            self.mon.usb('on')
            logging.info('Monsoon recovered from unexpected error')
            time.sleep(2)
            return True
        except monsoon.MonsoonError:
            logging.info(self.mon.mon.ser.in_waiting)
            logging.warning('Unable to recover monsoon from unexpected error')
            return False

    def monsoon_data_collect_save(self):
        """Current measurement and save the log file.

        Collect current data using Monsoon box and return the path of the
        log file. Take bug report if requested.

        Returns:
            data_path: the absolute path to the log file of monsoon current
                       measurement
            avg_current: the average current of the test
        """

        tag = '{}_{}_{}'.format(self.test_name, self.dut.model,
                                self.dut.build_info['build_id'])
        data_path = os.path.join(self.mon_info.data_path, '{}.txt'.format(tag))
        total_expected_samples = self.mon_info.freq * (self.mon_info.duration +
                                                       self.mon_info.offset)
        min_required_samples = total_expected_samples * MIN_PERCENT_SAMPLE / 100
        # Retry counter for monsoon data aquisition
        retry_measure = 1
        # Indicator that need to re-collect data
        need_collect_data = 1
        result = None
        while retry_measure <= MEASUREMENT_RETRY_COUNT:
            try:
                # If need to retake data
                if need_collect_data == 1:
                    #Resets the battery status right before the test started
                    self.dut.adb.shell(RESET_BATTERY_STATS)
                    self.log.info(
                        'Starting power measurement with monsoon box, try #{}'.
                        format(retry_measure))
                    #Start the power measurement using monsoon
                    self.mon_info.dut.monsoon_usb_auto()
                    result = self.mon_info.dut.measure_power(
                        self.mon_info.freq,
                        self.mon_info.duration,
                        tag=tag,
                        offset=self.mon_info.offset)
                    self.mon_info.dut.reconnect_dut()
                # Reconnect to dut
                else:
                    self.mon_info.dut.reconnect_dut()
                # Reconnect and return measurement results if no error happens
                avg_current = result.average_current
                monsoon.MonsoonData.save_to_text_file([result], data_path)
                self.log.info('Power measurement done within {} try'.format(
                    retry_measure))
                return data_path, avg_current
            # Catch monsoon errors during measurement
            except monsoon.MonsoonError:
                self.log.info(self.mon_info.dut.mon.ser.in_waiting)
                # Break early if it's one count away from limit
                if retry_measure == MEASUREMENT_RETRY_COUNT:
                    self.log.error(
                        'Test failed after maximum measurement retry')
                    break

                self.log.warning('Monsoon error happened, now try to recover')
                # Retry loop to recover monsoon from error
                retry_monsoon = 1
                while retry_monsoon <= RECOVER_MONSOON_RETRY_COUNT:
                    mon_status = self.monsoon_recover()
                    if mon_status:
                        break
                    else:
                        retry_monsoon += 1
                        self.log.warning(
                            'Wait for {} second then try again'.format(
                                MONSOON_RETRY_INTERVAL))
                        time.sleep(MONSOON_RETRY_INTERVAL)

                # Break the loop to end test if failed to recover monsoon
                if not mon_status:
                    self.log.error(
                        'Tried our best, still failed to recover monsoon')
                    break
                else:
                    # If there is no data, or captured samples are less than min
                    # required, re-take
                    if not result:
                        self.log.warning('No data taken, need to remeasure')
                    elif len(result._data_points) <= min_required_samples:
                        self.log.warning(
                            'More than {} percent of samples are missing due to monsoon error. Need to remeasure'
                            .format(100 - MIN_PERCENT_SAMPLE))
                    else:
                        need_collect_data = 0
                        self.log.warning(
                            'Data collected is valid, try reconnect to DUT to finish test'
                        )
                    retry_measure += 1

        if retry_measure > MEASUREMENT_RETRY_COUNT:
            self.log.error('Test failed after maximum measurement retry')

    def process_iperf_results(self):
        """Get the iperf results and process.

        Returns:
             throughput: the average throughput during tests.
        """
        # Get IPERF results and add this to the plot title
        RESULTS_DESTINATION = os.path.join(
            self.iperf_server.log_path,
            'iperf_client_output_{}.log'.format(self.current_test_name))
        self.dut.pull_files(TEMP_FILE, RESULTS_DESTINATION)
        # Calculate the average throughput
        if self.use_client_output:
            iperf_file = RESULTS_DESTINATION
        else:
            iperf_file = self.iperf_server.log_files[-1]
        try:
            iperf_result = ipf.IPerfResult(iperf_file)

            # Compute the throughput in Mbit/s
            throughput = (math.fsum(
                iperf_result.instantaneous_rates[self.start_meas_time:-1]
            ) / len(iperf_result.instantaneous_rates[self.start_meas_time:-1])
                          ) * 8 * (1.024**2)

            self.log.info('The average throughput is {}'.format(throughput))
        except ValueError:
            self.log.warning('Cannot get iperf result. Setting to 0')
            throughput = 0
        return throughput
