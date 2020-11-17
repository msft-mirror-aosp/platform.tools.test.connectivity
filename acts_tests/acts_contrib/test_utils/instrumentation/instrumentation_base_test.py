#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
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
import yaml

from acts import base_test
from acts import context
from acts import error

from acts.controllers.adb import DEFAULT_ADB_TIMEOUT

from acts_contrib.test_utils.instrumentation import instrumentation_proto_parser as proto_parser
from acts_contrib.test_utils.instrumentation import instrumentation_text_output_parser
from acts_contrib.test_utils.instrumentation.config_wrapper import ContextualConfigWrapper
from acts_contrib.test_utils.instrumentation.device.command.adb_command_types import GenericCommand
from acts_contrib.test_utils.instrumentation.device.command.instrumentation_command_builder import DEFAULT_INSTRUMENTATION_LOG_OUTPUT

RESOLVE_FILE_MARKER = 'FILE'
FILE_NOT_FOUND = 'File is missing from ACTS config'
DEFAULT_TEST_OPTIONS_FILE = 'test_options.yaml'


class InstrumentationTestError(error.ActsError):
    """Raised for general instrumentation test errors."""


class InstrumentationBaseTest(base_test.BaseTestClass):
    """Base class for tests based on am instrument."""

    def __init__(self, configs):
        """Initialize an InstrumentationBaseTest

        Args:
            configs: Dict representing the test configuration
        """
        super().__init__(configs)
        if 'test_options' in self.user_params:
            test_options_path = self.user_params['test_options'][0]
        elif 'instrumentation_config' in self.user_params:
            test_options_path = self.user_params['instrumentation_config'][0]
        else:
            raise InstrumentationTestError(
                'Test options file not specified. Please add a valid '
                '"test_options" path to the ACTS config.')
        self._test_options = ContextualConfigWrapper()
        if os.path.exists(test_options_path):
            self._test_options = self._load_test_options(test_options_path)
        else:
            raise InstrumentationTestError(
                'Test options file %s does not exist'
                % test_options_path)
        self._instrumentation_config = self._test_options

    def _load_test_options(self, path):
        """Load the test options file into a ContextualConfigWrapper object.

        Args:
            path: Path to the test options file.

        Returns: The loaded test options as a ContextualConfigWrapper
        """
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
        except Exception as e:
            raise InstrumentationTestError(
                'Cannot open or parse test options file %s. Error: %s'
                % (path, e))

        # Write out a copy of the test options
        with open(os.path.join(
                self.log_path, DEFAULT_TEST_OPTIONS_FILE),
                mode='w', encoding='utf-8') as f:
            yaml.safe_dump(config_dict, f)

        return ContextualConfigWrapper(config_dict)

    def setup_class(self):
        """Class setup"""
        self.ad_dut = self.android_devices[0]

    def teardown_test(self):
        """Test teardown. Takes bugreport and cleans up device."""
        self._cleanup_device()

    def on_exception(self, test_name, begin_time):
        """Called upon unhandled test exception."""
        if self._test_options.get('bugreport_on_exception', default=True):
            self._take_bug_report(test_name, begin_time)

    def on_pass(self, test_name, begin_time):
        """Called upon test pass."""
        if self._test_options.get('bugreport_on_pass', default=True):
            self._take_bug_report(test_name, begin_time)

    def on_fail(self, test_name, begin_time):
        """Called upon test failure."""
        if self._test_options.get('bugreport_on_fail', default=True):
            self._take_bug_report(test_name, begin_time)

    def _prepare_device(self):
        """Prepares the device for testing."""
        pass

    def _cleanup_device(self):
        """Clean up device after test completion."""
        pass

    def get_files_from_config(self, config_key):
        """Get a list of file paths on host from self.user_params with the
        given key. Verifies that each file exists.

        Args:
            config_key: Key in which the files are found.

        Returns: list of str file paths
        """
        if config_key not in self.user_params:
            raise InstrumentationTestError(
                'Cannot get files for key "%s": Key missing from config.'
                % config_key)
        files = self.user_params[config_key]
        for f in files:
            if not os.path.exists(f):
                raise InstrumentationTestError(
                    'Cannot get files for key "%s": No file exists for %s.' %
                    (config_key, f))
        return files

    def get_file_from_config(self, config_key):
        """Get a single file path on host from self.user_params with the given
        key. See get_files_from_config for details.
        """
        return self.get_files_from_config(config_key)[-1]

    def adb_run(self, cmds, ad=None, timeout=DEFAULT_ADB_TIMEOUT):
        """Run the specified command, or list of commands, with the ADB shell.

        Args:
            cmds: A string, A GenericCommand, a list of strings or a list of
                  GenericCommand representing ADB shell command(s)
            ad: The device to run on. Defaults to self.ad_dut.

        Returns: dict mapping command to resulting stdout
        """
        if ad is None:
            ad = self.ad_dut
        if isinstance(cmds, str) or isinstance(cmds, GenericCommand):
            cmds = [cmds]

        out = {}
        for cmd in cmds:
            if isinstance(cmd, GenericCommand):
                if cmd.desc:
                    ad.log.debug('Applying command that: %s' % cmd.desc)
                cmd = cmd.cmd
            out[cmd] = ad.adb.shell(cmd, timeout=timeout)
        return out

    def fastboot_run(self, cmds, ad=None):
        """Run the specified command, or list of commands, with the FASTBOOT shell.

        Args:
            cmds: A string, A GenericCommand, a list of strings or a list of
                  GenericCommand representing FASTBOOT command(s)
            ad: The device to run on. Defaults to self.ad_dut.

        Returns: dict mapping command to resulting stdout
        """
        if ad is None:
            ad = self.ad_dut
        if isinstance(cmds, str) or isinstance(cmds, GenericCommand):
            cmds = [cmds]

        out = {}
        for cmd in cmds:
            if isinstance(cmd, GenericCommand):
                if cmd.desc:
                    ad.log.debug('Applying command that: %s' % cmd.desc)
                cmd = cmd.cmd
            out[cmd] = ad.fastboot._exec_fastboot_cmd(cmd, '')
        return out

    def adb_run_async(self, cmds, ad=None):
        """Run the specified command, or list of commands, with the ADB shell.
        (async)

        Args:
            cmds: A string or list of strings representing ADB shell command(s)
            ad: The device to run on. Defaults to self.ad_dut.

        Returns: dict mapping command to resulting subprocess.Popen object
        """
        if ad is None:
            ad = self.ad_dut

        if isinstance(cmds, str) or isinstance(cmds, GenericCommand):
            cmds = [cmds]

        procs = {}
        for cmd in cmds:
            if isinstance(cmd, GenericCommand):
                if cmd.desc:
                    ad.log.debug('Applying command to: %s' % cmd.desc)
                cmd = cmd.cmd
            procs[cmd] = ad.adb.shell_nb(cmd)
        return procs

    def parse_instrumentation_result(self):
        """Parse the instrumentation result and write it to a human-readable
        txt file in the log directory.

        Returns: The parsed instrumentation_data_pb2.Session
        """
        log_path = context.get_current_context().get_full_output_path()

        if proto_parser.has_instrumentation_proto(self.ad_dut):
            proto_file = proto_parser.pull_proto(self.ad_dut, log_path)
            proto_txt_path = os.path.join(log_path, 'instrumentation_proto.txt')
            session = proto_parser.get_session_from_local_file(proto_file)
            with open(proto_txt_path, 'w') as f:
                f.write(str(session))
            return session

        on_device = os.path.join(
            self.ad_dut.external_storage_path,
            DEFAULT_INSTRUMENTATION_LOG_OUTPUT)
        if self.file_exists(on_device):
            plain_output = instrumentation_text_output_parser.pull_output(
                self.ad_dut,
                log_path,
                on_device)
            proto_txt_path = os.path.join(
                log_path,
                'instrumentation_proto.from_plain_text.txt')
            session = instrumentation_text_output_parser.parse_from_file(
                plain_output)
            with open(proto_txt_path, 'w') as f:
                f.write(str(session))
            return session

        raise InstrumentationTestError('No instrumentation output was detected '
                                       'in either proto nor text format.')

    def file_exists(self, file_path, ad=None):
        """Returns whether a file exists on a device.

        Args:
            file_path: The path of the file to check for.
            ad: The AndroiDevice to check on. If left undefined the default
            device under test will be used.
        """
        if ad is None:
            ad = self.ad_dut

        cmd = '(test -f %s && echo yes) || echo no' % file_path
        result = self.adb_run(cmd, ad)
        if result[cmd] == 'yes':
            return True
        elif result[cmd] == 'no':
            return False
        raise ValueError('Couldn\'t determine if %s exists. '
                         'Expected yes/no, got %s' % (file_path, result[cmd]))

    def log_instrumentation_result(self, session):
        """Logs instrumentation test result.

        Args:
            session: an instrumentation_data_pb2.Session

        Returns: The parsed instrumentation result
        """
        result = proto_parser.get_instrumentation_result(session)

        if result['status_code']:
            self.log.error('Instrumentation session aborted!')
            if 'error_text' in result:
                self.log.error('Instrumentation error: %s'
                               % result['error_text'])
            return result

        log = self.log.info if result['result_code'] == -1 else self.log.error
        log('Instrumentation command finished with result_code %d.'
            % result['result_code'])
        if 'stream' in result:
            log('Instrumentation output: %s' % result['stream'])
        return result
