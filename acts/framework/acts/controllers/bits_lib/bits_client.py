#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
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

import logging
import os
import uuid
import tempfile
import yaml

from acts.libs.proc import job
from acts import context


class BitsClientError(Exception):
    pass


# An arbitrary large number of seconds.
ONE_YEAR = str(3600 * 24 * 365)


class _BitsCollection(object):
    """Object that represents a bits collection

    Attributes:
        name: The name given to the collection.
        markers_buffer: An array of un-flushed markers, each marker is
        represented by a bi-dimensional tuple with the format
        (nanoseconds_since_epoch, text).
    """
    def __init__(self, name):
        self.name = name
        self.markers_buffer = []

    def add_marker(self, timestamp_ns, marker_text):
        self.markers_buffer.append((timestamp_ns, marker_text))

    def clear_markers_buffer(self):
        self.markers_buffer.clear()


class BitsClient(object):
    """Helper class to issue bits' commands"""

    def __init__(self, binary, service, service_config):
        """Constructs a BitsClient.

        Args:
            binary: The location of the bits.par client binary.
            service: A bits_service.BitsService object. The service is expected
              to be previously setup.
            service_config: The bits_service_config.BitsService object used to
              start the service on service_port.
        """
        self._log = logging.getLogger()
        self._binary = binary
        self._service = service
        self._server_config = service_config
        self._active_collection = None
        self._collections_counter = 0

    def _acquire_monsoon(self):
        """Gets hold of a Monsoon so no other processes can use it.
        Only works if there is a monsoon."""
        cmd = [self._binary,
               '--port',
               self._service.port,
               '--collector',
               'Monsoon',
               '--collector_cmd',
               'acquire_monsoon']
        self._log.info('acquiring monsoon')
        job.run(cmd, timeout=10)

    def _release_monsoon(self):
        cmd = [self._binary,
               '--port',
               self._service.port,
               '--collector',
               'Monsoon',
               '--collector_cmd',
               'release_monsoon']
        self._log.info('releasing monsoon')
        job.run(cmd, timeout=10)

    def _export(self):
        collection_path = os.path.join(
            context.get_current_context().get_full_output_path(),
            '%s.7z.bits' % self._active_collection.name)
        cmd = [self._binary,
               '--port',
               self._service.port,
               '--name',
               self._active_collection.name,
               '--ignore_gaps',
               '--export',
               '--export_path',
               collection_path]
        self._log.info('exporting collection %s to %s',
                       self._active_collection.name,
                       collection_path)
        job.run(cmd)

    def _flush_markers(self):
        for ts, marker in sorted(self._active_collection.markers_buffer,
                                 key=lambda x: x[0]):
            cmd = [self._binary,
                   '--port',
                   self._service.port,
                   '--name',
                   self._active_collection.name,
                   '--log_ts',
                   str(ts),
                   '--log',
                   marker]
            job.run(cmd, timeout=10)
        self._active_collection.clear_markers_buffer()

    def add_marker(self, timestamp_ns, marker_text):
        """Buffers a marker for the active collection.

        Bits does not allow inserting markers with timestamps out of order.
        The buffer of markers will be flushed when the collection is stopped to
        ensure all the timestamps are input in order.
        """
        if not self._active_collection:
            raise BitsClientError(
                'markers can not be added without an active collection')
        self._active_collection.add_marker(timestamp_ns, marker_text)

    def get_metrics(self, start_ns, end_ns):
        """Extracts metrics for a period of time.

        Args:
            start_ns: nano-seconds since epoch until the start of the period of
            interest.
            end_ns: nano-second since epoc until the end of the period of
            interest.
        """
        if not self._active_collection:
            raise BitsClientError(
                'metrics can not be collected without an active collection')

        with tempfile.NamedTemporaryFile(prefix='bits_metrics') as tf:
            cmd = [self._binary,
                   '--port',
                   self._service.port,
                   '--name',
                   self._active_collection.name,
                   '--ignore_gaps',
                   '--abs_start_time',
                   str(start_ns),
                   '--abs_stop_time',
                   str(end_ns),
                   '--aggregates_yaml_path',
                   tf.name]
            job.run(cmd)
            with open(tf.name) as mf:
                self._log.debug(
                    'bits aggregates for collection %s [%s-%s]: %s' % (
                        self._active_collection.name, start_ns, end_ns,
                        mf.read()))

            with open(tf.name) as mf:
                return yaml.safe_load(mf)

    def disconnect_usb(self):
        """Disconnects the monsoon's usb. Only works if there is a monsoon"""
        cmd = [self._binary,
               '--port',
               self._service.port,
               '--collector',
               'Monsoon',
               '--collector_cmd',
               'usb_disconnect']
        self._log.info('disconnecting monsoon\'s usb')
        job.run(cmd, timeout=10)

    def start_collection(self, postfix=None):
        """Indicates Bits to start a collection.

        Args:
            postfix: Optional argument that can be used to identify the
            collection with.
        """
        if self._active_collection:
            raise BitsClientError(
                'Attempted to start a collection while there is still an '
                'active one. Active collection: %s',
                self._active_collection.name)
        self._collections_counter = self._collections_counter + 1
        # The name gets a random 8 characters salt suffix because the Bits
        # client has a bug where files with the same name are considered to be
        # the same collection and it won't load two files with the same name.
        # b/153170987 b/153944171
        if not postfix:
            postfix = str(self._collections_counter)
        postfix = '%s_%s' % (postfix, str(uuid.uuid4())[0:8])
        self._active_collection = _BitsCollection(
            'bits_collection_%s' % postfix)

        if self._server_config.has_monsoon:
            self._acquire_monsoon()

        cmd = [self._binary,
               '--port',
               self._service.port,
               '--name',
               self._active_collection.name,
               '--non_blocking',
               '--time',
               ONE_YEAR,
               '--default_sampling_rate',
               '5000',
               '--disk_space_saver',
               ]
        self._log.info('starting collection %s', self._active_collection.name)
        job.run(cmd, timeout=10)

    def connect_usb(self):
        """Connects the monsoon's usb. Only works if there is a monsoon."""
        cmd = [self._binary,
               '--port',
               self._service.port,
               '--collector',
               'Monsoon',
               '--collector_cmd',
               'usb_connect']
        self._log.info('connecting monsoon\'s usb')
        job.run(cmd, timeout=10)

    def stop_collection(self):
        """Stops the active collection."""
        if not self._active_collection:
            raise BitsClientError(
                'Attempted to stop a collection without starting one')
        self._log.info('stopping collection %s', self._active_collection.name)
        self._flush_markers()
        cmd = [self._binary,
               '--port',
               self._service.port,
               '--name',
               self._active_collection.name,
               '--stop'
               ]
        job.run(cmd)

        if self._server_config.has_monsoon:
            self._release_monsoon()
        self._export()
        self._log.info('stopped collection %s', self._active_collection.name)
        self._active_collection = None
