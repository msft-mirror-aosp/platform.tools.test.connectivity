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
from acts import utils
from acts.test_utils.instrumentation import instrumentation_proto_parser as proto_parser
from acts.test_utils.instrumentation.config_wrapper import ConfigWrapper
from acts.test_utils.instrumentation.device.command.adb_command_types import GenericCommand

RESOLVE_FILE_MARKER = 'FILE'
FILE_NOT_FOUND = 'File is missing from ACTS config'
DEFAULT_INSTRUMENTATION_CONFIG_FILE = 'instrumentation_config.yaml'


class InstrumentationTestError(error.ActsError):
    pass


class InstrumentationBaseTest(base_test.BaseTestClass):
    """Base class for tests based on am instrument."""

    def __init__(self, configs):
        """Initialize an InstrumentationBaseTest

        Args:
            configs: Dict representing the test configuration
        """
        super().__init__(configs)
        if 'instrumentation_config' in self.user_params:
            instrumentation_config_path = (
                self.user_params['instrumentation_config'][0])
        else:
            raise InstrumentationTestError(
                'Instrumentation config file not specified. Please add a valid '
                '"instrumentation_config" path to the ACTS config.')
        self._instrumentation_config = ConfigWrapper()
        if os.path.exists(instrumentation_config_path):
            self._instrumentation_config = self._load_instrumentation_config(
                instrumentation_config_path)
            self._class_config = self._instrumentation_config.get_config(
                self.__class__.__name__)
        else:
            raise InstrumentationTestError(
                'Instrumentation config file %s does not exist'
                % instrumentation_config_path)

    def _load_instrumentation_config(self, path):
        """Load the instrumentation config file into an
        InstrumentationConfigWrapper object.

        Args:
            path: Path to the instrumentation config file.

        Returns: The loaded instrumentation config as an
        InstrumentationConfigWrapper
        """
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
        except Exception as e:
            raise InstrumentationTestError(
                'Cannot open or parse instrumentation config file %s'
                % path) from e

        # Write out a copy of the instrumentation config
        with open(os.path.join(
                self.log_path, 'instrumentation_config.yaml'),
                  mode='w', encoding='utf-8') as f:
            yaml.safe_dump(config_dict, f)

        return ConfigWrapper(config_dict)

    def setup_class(self):
        """Class setup"""
        self.ad_dut = self.android_devices[0]

    def teardown_test(self):
        """Test teardown. Takes bugreport and cleans up device."""
        self._cleanup_device()

    def on_exception(self, test_name, begin_time):
        self._take_bug_report(test_name,
                              utils.get_current_epoch_time())

    def on_pass(self, test_name, begin_time):
        self._take_bug_report(test_name,
                              utils.get_current_epoch_time())

    def on_fail(self, test_name, begin_time):
        self._take_bug_report(test_name,
                              utils.get_current_epoch_time())


    def _prepare_device(self):
        """Prepares the device for testing."""
        pass

    def _cleanup_device(self):
        """Clean up device after test completion."""
        pass

    def _get_merged_config(self, config_name):
        """Takes the configs with config_name from the base, testclass, and
        testcase levels and merges them together. When the same parameter is
        defined in different contexts, the value from the most specific context
        is taken.

        Example:
            self._instrumentation_config = {
                'sample_config': {
                    'val_a': 5,
                    'val_b': 7
                },
                'ActsTestClass': {
                    'sample_config': {
                        'val_b': 3,
                        'val_c': 6
                    },
                    'acts_test_case': {
                        'sample_config': {
                            'val_c': 10,
                            'val_d': 2
                        }
                    }
                }
            }

            self._get_merged_config('sample_config') returns
            {
                'val_a': 5,
                'val_b': 3,
                'val_c': 10,
                'val_d': 2
            }

        Args:
            config_name: Name of the config to fetch
        Returns: The merged config, as a ConfigWrapper
        """
        merged_config = self._instrumentation_config.get_config(
            config_name)
        merged_config.update(self._class_config.get_config(config_name))
        if self.current_test_name:
            case_config = self._class_config.get_config(self.current_test_name)
            merged_config.update(case_config.get_config(config_name))
        return merged_config

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

    def adb_run(self, cmds):
        """Run the specified command, or list of commands, with the ADB shell.

        Args:
            cmds: A string, A GenericCommand, a list of strings or a list of
                  GenericCommand representing ADB shell command(s)

        Returns: dict mapping command to resulting stdout
        """
        if isinstance(cmds, str) or isinstance(cmds, GenericCommand):
            cmds = [cmds]

        out = {}
        for cmd in cmds:
            if isinstance(cmd, GenericCommand):
                if cmd.desc:
                    self.log.debug('Applying command that: %s' % cmd.desc)
                cmd = cmd.cmd
            out[cmd] = self.ad_dut.adb.shell(cmd)
        return out

    def adb_run_async(self, cmds):
        """Run the specified command, or list of commands, with the ADB shell.
        (async)

        Args:
            cmds: A string or list of strings representing ADB shell command(s)

        Returns: dict mapping command to resulting subprocess.Popen object
        """
        if isinstance(cmds, str) or isinstance(cmds, GenericCommand):
            cmds = [cmds]

        procs = {}
        for cmd in cmds:
            if isinstance(cmd, GenericCommand):
                if cmd.desc:
                    self.log.debug('Applying command to: %s' % cmd.desc)
                cmd = cmd.cmd
            procs[cmd] = self.ad_dut.adb.shell(cmd)
        return procs

    def parse_instrumentation_result_proto(self):
        """Parse the instrumentation result proto and write it to a
        human-readable txt file in the log directory.

        Returns: The parsed instrumentation_data_pb2.Session
        """
        log_path = context.get_current_context().get_full_output_path()
        proto_file = proto_parser.pull_proto(self.ad_dut, log_path)
        session = proto_parser.get_session_from_local_file(proto_file)
        proto_txt_path = os.path.join(log_path, 'instrumentation_proto.txt')
        with open(proto_txt_path, 'w') as f:
            f.write(str(session))
        return session

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
