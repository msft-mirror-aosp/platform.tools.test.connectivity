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
import re

from acts.error import ActsError
from acts_contrib.test_utils.instrumentation.device.command.instrumentation_command_builder import DEFAULT_INSTRUMENTATION_LOG_OUTPUT
from acts_contrib.test_utils.instrumentation.proto.gen import instrumentation_data_pb2


class InstrumentationOutputError(ActsError):
    """Class for exceptions raised by instrumentation_test_output_parser"""


def pull_output(ad, dest_dir, source_path=None):
    """Pulls a file from the target device. The default file to be pulled
    is defined by
    instrumentation_command_builder.DEFAULT_INSTRUMENTATION_LOG_OUTPUT.

    Args:
        ad: AndroidDevice object.
        dest_dir: Directory on the host where the file will be put.
        source_path: Absolute path on the device where the file will be pulled
        from. By default
        instrumentation_command_builder.DEFAULT_INSTRUMENTATION_LOG_OUTPUT.
    """
    if source_path is None:
        source_path = os.path.join(ad.external_storage_path,
                                   DEFAULT_INSTRUMENTATION_LOG_OUTPUT)
    ad.pull_files(source_path, dest_dir)
    dest_path = os.path.join(dest_dir, os.path.basename(source_path))
    if not os.path.exists(dest_path):
        raise InstrumentationOutputError(
            'Failed to pull instrumentation text output: %s -> %s'
            % (source_path, dest_path))
    return dest_path


class _Markers(object):
    """Markers used to delimit sections in the instrumentation's output.
    Standard instrumentation output follows the format::

        INSTRUMENTATION_STATUS: <key>=<value>
        INSTRUMENTATION_STATUS: <key>=<value>
        INSTRUMENTATION_STATUS: <key>=<value>
        INSTRUMENTATION_STATUS_CODE: <code>
        ...
        INSTRUMENTATION_STATUS: <key>=<value>
        INSTRUMENTATION_STATUS: <key>=<value>
        INSTRUMENTATION_STATUS: <key>=<value>
        INSTRUMENTATION_STATUS_CODE: <code>
        INSTRUMENTATION_RESULT: <key>=<value>
        INSTRUMENTATION_CODE: <code>


    The parts marked as <value> can span several lines, this normally happens
    for INSTRUMENTATION_RESULT and INSTRUMENTATION_STATUS only.
    """
    STATUS = "INSTRUMENTATION_STATUS:"
    STATUS_CODE = "INSTRUMENTATION_STATUS_CODE:"
    RESULT = 'INSTRUMENTATION_RESULT:'
    CODE = 'INSTRUMENTATION_CODE:'


def _remove_prefix(line, marker):
    match = re.match('(\\S*%s).*' % marker, line)
    prefix = match.group(1)
    return line[len(prefix):].lstrip()


def _extract_key_value(line, marker):
    key_value = _remove_prefix(line, marker)
    return key_value.split('=', 1)


def _extract_status_code(line, marker):
    return int(_remove_prefix(line, marker))


class InstrumentationParserStateMachine(object):
    """Stateful class that understands transitions in between instrumentation
    output markers and how they translate into corresponding fragments of the
    instrumentation_data_pb2.Session equivalent object."""

    def __init__(self):
        self.session = instrumentation_data_pb2.Session()
        self._test_status = instrumentation_data_pb2.TestStatus()
        self._result_entry = instrumentation_data_pb2.ResultsBundleEntry()
        self._results_bundle = instrumentation_data_pb2.ResultsBundle()
        self._session_status = instrumentation_data_pb2.SessionStatus()
        self._value_lines = []
        self._status_result_entry_is_open = False
        self._session_result_entry_is_open = False

    def _add_unmarked_line(self, line):
        """An unmarked line is either part of a status result entry or
        a session result entry."""
        if (self._status_result_entry_is_open
                or self._session_result_entry_is_open):
            self._value_lines.append(line)
        else:
            raise InstrumentationOutputError(
                'Unmarked line misplacement. Line: %s' % line)

    def _add_test_status_result_code(self, code):
        """Adds the test_status to the session since the result_code is the
        last token that appears."""
        self._close_open_states()
        self._test_status.result_code = code
        self._test_status.results.CopyFrom(self._results_bundle)
        self.session.test_status.add().CopyFrom(self._test_status)

        # clear holders for next additions
        self._results_bundle.Clear()
        self._test_status.Clear()

    def _add_session_result_code(self, code):
        """Adds the results bundle to the session_status since the result_code
        is the last token that appears."""
        self._close_open_states()
        self.session.session_status.result_code = code
        self.session.session_status.results.CopyFrom(self._results_bundle)
        self._results_bundle.Clear()

    def _add_status_result_entry(self, key):
        self._close_open_states()
        self._status_result_entry_is_open = True
        self._result_entry.key = key

    def _add_session_result_entry(self, key):
        self._close_open_states()
        self._session_result_entry_is_open = True
        self._result_entry.key = key

    def _close_open_states(self):
        """If a marker is found, open states can be wrapped."""
        self._wrap_session_result_entry_if_open()
        self._wrap_sesion_result_entry_if_open()

    def _wrap_sesion_result_entry_if_open(self):
        if not self._session_result_entry_is_open:
            return
        self._result_entry.value_string = '\n'.join(self._value_lines)
        self._results_bundle.entries.add().CopyFrom(self._result_entry)

        # clear holders for next additions
        self._value_lines.clear()
        self._result_entry.Clear()
        self._session_result_entry_is_open = False

    def _wrap_session_result_entry_if_open(self):
        if not self._status_result_entry_is_open:
            return
        self._result_entry.value_string = '\n'.join(self._value_lines)
        self._results_bundle.entries.add().CopyFrom(self._result_entry)

        # clear holders for next additions
        self._value_lines.clear()
        self._result_entry.Clear()
        self._status_result_entry_is_open = False

    def add_line(self, line):
        if re.match('\\S*%s.*' % _Markers.STATUS, line):
            (key, value) = _extract_key_value(line, _Markers.STATUS)
            self._add_status_result_entry(key)
            self._add_unmarked_line(value)
        elif re.match('\\S*%s.*' % _Markers.STATUS_CODE, line):
            code = _extract_status_code(line, _Markers.STATUS_CODE)
            self._add_test_status_result_code(code)
        elif re.match('\\S*%s.*' % _Markers.RESULT, line):
            (key, value) = _extract_key_value(line, _Markers.RESULT)
            self._add_session_result_entry(key)
            self._add_unmarked_line(value)
        elif re.match('\\S*%s.*' % _Markers.CODE, line):
            code = _extract_status_code(line, _Markers.CODE)
            self._add_session_result_code(code)
        else:
            self._add_unmarked_line(line)

def parse_from_file(source_path):
    """Parses a file into a instrumentation_data_pb2.Session object. All values
    are casted as string."""
    state_machine = InstrumentationParserStateMachine()

    with open(source_path, 'r') as f:
        for line in f:
            line = line.rstrip()
            state_machine.add_line(line)
    return state_machine.session
