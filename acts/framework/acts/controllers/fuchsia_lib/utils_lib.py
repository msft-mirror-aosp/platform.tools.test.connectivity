#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
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

import backoff
import itertools
import os
import logging
import paramiko
import shutil
import socket
import tarfile
import time
import usbinfo

from acts import utils
from acts.controllers.fuchsia_lib.base_lib import DeviceOffline
from acts.libs.proc import job
from acts.utils import get_fuchsia_mdns_ipv6_address

logging.getLogger("paramiko").setLevel(logging.WARNING)
# paramiko-ng will throw INFO messages when things get disconnect or cannot
# connect perfectly the first time.  In this library those are all handled by
# either retrying and/or throwing an exception for the appropriate case.
# Therefore, in order to reduce confusion in the logs the log level is set to
# WARNING.

MDNS_LOOKUP_RETRY_MAX = 3
FASTBOOT_TIMEOUT = 20
AFTER_FLASH_BOOT_TIME = 30


def get_private_key(ip_address, ssh_config):
    """Tries to load various ssh key types.

    Args:
        ip_address: IP address of ssh server.
        ssh_config: ssh_config location for the ssh server.
    Returns:
        The ssh private key
    """
    exceptions = []
    try:
        logging.debug('Trying to load SSH key type: ed25519')
        return paramiko.ed25519key.Ed25519Key(
            filename=get_ssh_key_for_host(ip_address, ssh_config))
    except paramiko.SSHException as e:
        exceptions.append(e)
        logging.debug('Failed loading SSH key type: ed25519')

    try:
        logging.debug('Trying to load SSH key type: rsa')
        return paramiko.RSAKey.from_private_key_file(
            filename=get_ssh_key_for_host(ip_address, ssh_config))
    except paramiko.SSHException as e:
        exceptions.append(e)
        logging.debug('Failed loading SSH key type: rsa')

    raise Exception('No valid ssh key type found', exceptions)


@backoff.on_exception(
    backoff.constant,
    (paramiko.ssh_exception.SSHException,
     paramiko.ssh_exception.AuthenticationException, socket.timeout,
     socket.error, ConnectionRefusedError, ConnectionResetError),
    interval=1.5,
    max_tries=4)
def create_ssh_connection(ip_address,
                          ssh_username,
                          ssh_config,
                          ssh_port=22,
                          connect_timeout=10,
                          auth_timeout=10,
                          banner_timeout=10):
    """Creates and ssh connection to a Fuchsia device

    Args:
        ip_address: IP address of ssh server.
        ssh_username: Username for ssh server.
        ssh_config: ssh_config location for the ssh server.
        ssh_port: port for the ssh server.
        connect_timeout: Timeout value for connecting to ssh_server.
        auth_timeout: Timeout value to wait for authentication.
        banner_timeout: Timeout to wait for ssh banner.

    Returns:
        A paramiko ssh object
    """
    if not utils.can_ping(job, ip_address):
        raise DeviceOffline("Device %s is not reachable via "
                            "the network." % ip_address)
    ssh_key = get_private_key(ip_address=ip_address, ssh_config=ssh_config)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=ip_address,
                       username=ssh_username,
                       allow_agent=False,
                       pkey=ssh_key,
                       port=ssh_port,
                       timeout=connect_timeout,
                       auth_timeout=auth_timeout,
                       banner_timeout=banner_timeout)
    ssh_client.get_transport().set_keepalive(1)
    return ssh_client


def ssh_is_connected(ssh_client):
    """Checks to see if the SSH connection is alive.
    Args:
        ssh_client: A paramiko SSH client instance.
    Returns:
          True if connected, False or None if not connected.
    """
    return ssh_client and ssh_client.get_transport().is_active()


def get_ssh_key_for_host(host, ssh_config_file):
    """Gets the SSH private key path from a supplied ssh_config_file and the
       host.
    Args:
        host (str): The ip address or host name that SSH will connect to.
        ssh_config_file (str): Path to the ssh_config_file that will be used
            to connect to the host.

    Returns:
        path: A path to the private key for the SSH connection.
    """
    ssh_config = paramiko.SSHConfig()
    user_config_file = os.path.expanduser(ssh_config_file)
    if os.path.exists(user_config_file):
        with open(user_config_file) as f:
            ssh_config.parse(f)
    user_config = ssh_config.lookup(host)

    if 'identityfile' not in user_config:
        raise ValueError('Could not find identity file in %s.' % ssh_config)

    path = os.path.expanduser(user_config['identityfile'][0])
    if not os.path.exists(path):
        raise FileNotFoundError('Specified IdentityFile %s for %s in %s not '
                                'existing anymore.' % (path, host, ssh_config))
    return path


class SshResults:
    """Class representing the results from a SSH command to mimic the output
    of the job.Result class in ACTS.  This is to reduce the changes needed from
    swapping the ssh connection in ACTS to paramiko.

    Attributes:
        stdin: The file descriptor to the input channel of the SSH connection.
        stdout: The file descriptor to the stdout of the SSH connection.
        stderr: The file descriptor to the stderr of the SSH connection.
        exit_status: The file descriptor of the SSH command.
    """
    def __init__(self, stdin, stdout, stderr, exit_status):
        self._raw_stdout = stdout.read()
        self._stdout = self._raw_stdout.decode('utf-8', errors='replace')
        self._stderr = stderr.read().decode('utf-8', errors='replace')
        self._exit_status = exit_status.recv_exit_status()

    @property
    def stdout(self):
        return self._stdout

    @property
    def raw_stdout(self):
        return self._raw_stdout

    @property
    def stderr(self):
        return self._stderr

    @property
    def exit_status(self):
        return self._exit_status


def flash(fuchsia_device):
    """A function to flash, not pave, a fuchsia_device

    Args:
        fuchsia_device: An ACTS fuchsia_device

    Returns:
        True if successful.
    """
    if not fuchsia_device.authorized_file:
        raise ValueError('A ssh authorized_file must be present in the '
                         'ACTS config to flash fuchsia_devices.')
    # This is the product type from the fx set command.
    # Do 'fx list-products' to see options in Fuchsia source tree.
    if not fuchsia_device.product_type:
        raise ValueError('A product type must be specified to flash '
                         'fuchsia_devices.')
    # This is the board type from the fx set command.
    # Do 'fx list-boards' to see options in Fuchsia source tree.
    if not fuchsia_device.board_type:
        raise ValueError('A board type must be specified to flash '
                         'fuchsia_devices.')
    if not fuchsia_device.build_number:
        fuchsia_device.build_number = 'LATEST'
    if not fuchsia_device.server_path:
        fuchsia_device.server_path = 'gs://fuchsia-sdk/development/'
    if (utils.is_valid_ipv4_address(fuchsia_device.orig_ip)
            or utils.is_valid_ipv6_address(fuchsia_device.orig_ip)):
        raise ValueError('The fuchsia_device ip must be the mDNS name to be '
                         'able to flash.')
    time_counter = 0
    while time_counter < FASTBOOT_TIMEOUT:
        logging.info('Checking to see if fuchsia_device(%s) SN: %s is in '
                     'fastboot. (Attempt #%s Timeout: %s)' %
                     (fuchsia_device.orig_ip,
                      fuchsia_device.serial_number,
                      str(time_counter + 1),
                      FASTBOOT_TIMEOUT))
        for usb_device in usbinfo.usbinfo():
            if (usb_device['iSerialNumber'] == fuchsia_device.serial_number and
                    usb_device['iProduct'] == 'USB_download_gadget'):
                logging.info('fuchsia_device(%s) SN: %s is in fastboot.' %
                             (fuchsia_device.orig_ip,
                              fuchsia_device.serial_number))
                time_counter = FASTBOOT_TIMEOUT
        time_counter = time_counter + 1
        if time_counter == FASTBOOT_TIMEOUT:
            for fail_usb_device in usbinfo.usbinfo():
                logging.debug(fail_usb_device)
            raise TimeoutError('fuchsia_device(%s) SN: %s '
                               'never went into fastboot' %
                               (fuchsia_device.orig_ip,
                                fuchsia_device.serial_number))
        time.sleep(1)

    if not fuchsia_device.specific_image:
        file_download_needed = True
        if 'LATEST' in fuchsia_device.build_number:
            gsutil_process = job.run('gsutil ls %s'
                                     % fuchsia_device.server_path).stdout
            build_list = list(
                # filter out builds that are not part of branches
                filter(None, gsutil_process.replace(
                    fuchsia_device.server_path, '').replace(
                    '/', '').split('\n')))
            if 'LATEST_F' in fuchsia_device.build_number:
                build_number = fuchsia_device.build_number.split(
                    'LATEST_F', 1)[1]
                build_list = [x for x in build_list if x.startswith(
                    '%s.' % build_number)]
            elif fuchsia_device.build_number == 'LATEST':
                build_list = [x for x in build_list if '.' in x]
            if build_list:
                fuchsia_device.build_number = build_list[-1]
            else:
                raise FileNotFoundError('No build(%s) on the found on %s.' % (
                    fuchsia_device.build_number, fuchsia_device.server_path))
        image_front_string = fuchsia_device.product_type
        if fuchsia_device.build_type:
            image_front_string = '%s_%s' % (image_front_string,
                                            fuchsia_device.build_type)
        full_image_string = '%s.%s-release.tgz' % (image_front_string,
                                                   fuchsia_device.board_type)
        file_to_download = '%s%s/images/%s' % (fuchsia_device.server_path,
                                               fuchsia_device.build_number,
                                               full_image_string)
    elif 'gs://' in fuchsia_device.specific_image:
        file_download_needed = True
        file_to_download = fuchsia_device.specific_image
    elif tarfile.is_tarfile(fuchsia_device.specific_image):
        file_download_needed = False
        file_to_download = fuchsia_device.specific_image
    else:
        raise ValueError('A suitable build could not be found.')
    tmp_path = '/tmp/%s_%s' % (str(int(time.time()*10000)),
                               fuchsia_device.board_type)
    os.mkdir(tmp_path)
    if file_download_needed:
        job.run('gsutil cp %s %s' % (file_to_download, tmp_path))
        logging.info('Downloading %s to %s' % (file_to_download, tmp_path))
        image_tgz = os.path.basename(file_to_download)
    else:
        job.run('cp %s %s' % (fuchsia_device.specific_image, tmp_path))
        logging.info('Copying %s to %s' % (file_to_download, tmp_path))
        image_tgz = os.path.basename(fuchsia_device.specific_image)

    job.run('tar xfvz %s/%s -C %s' % (tmp_path, image_tgz, tmp_path))
    os.chdir(tmp_path)
    all_files = []
    for root, _dirs, files in itertools.islice(os.walk(tmp_path), 1, None):
        for filename in files:
            all_files.append(os.path.join(root, filename))
    for filename in all_files:
        shutil.move(filename, tmp_path)
    logging.info('Flashing fuchsia_device(%s) with %s/%s.' % (
        fuchsia_device.orig_ip, tmp_path, image_tgz))
    flash_output = job.run('bash flash.sh --ssh-key=%s -s %s' % (
        fuchsia_device.authorized_file, fuchsia_device.serial_number),
                           timeout=90)
    logging.debug(flash_output.stderr)
    try:
        os.rmdir(tmp_path)
    except Exception:
        job.run('rm -fr %s' % tmp_path)
    logging.info('Waiting %s seconds for device'
                 ' to come back up after flashing.' % AFTER_FLASH_BOOT_TIME)
    time.sleep(AFTER_FLASH_BOOT_TIME)
    logging.info('Updating device to new IP addresses.')
    mdns_ip = None
    for retry_counter in range(MDNS_LOOKUP_RETRY_MAX):
        mdns_ip = get_fuchsia_mdns_ipv6_address(fuchsia_device.orig_ip)
        if mdns_ip:
            break
        else:
            time.sleep(1)
    if mdns_ip and utils.is_valid_ipv6_address(mdns_ip):
        logging.info('IP for fuchsia_device(%s) changed from %s to %s' % (
            fuchsia_device.orig_ip,
            fuchsia_device.ip,
            mdns_ip))
        fuchsia_device.ip = mdns_ip
        fuchsia_device.address = "http://[{}]:{}".format(
            fuchsia_device.ip, fuchsia_device.sl4f_port)
        fuchsia_device.init_address = fuchsia_device.address + "/init"
        fuchsia_device.cleanup_address = fuchsia_device.address + "/cleanup"
        fuchsia_device.print_address = fuchsia_device.address + "/print_clients"
        fuchsia_device.init_libraries()
    else:
        raise ValueError('Invalid IP: %s after flashing.' %
                         fuchsia_device.orig_ip)
    return True
