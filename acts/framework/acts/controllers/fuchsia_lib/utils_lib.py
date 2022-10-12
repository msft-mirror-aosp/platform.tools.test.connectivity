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
import os
import logging
import paramiko
import psutil
import socket
import tarfile
import tempfile
import time
import usbinfo

from acts import utils
from acts.controllers.fuchsia_lib.base_lib import DeviceOffline
from acts.controllers.fuchsia_lib.ssh import FuchsiaSSHError
from acts.libs.proc import job
from acts.utils import get_fuchsia_mdns_ipv6_address

logging.getLogger("paramiko").setLevel(logging.WARNING)
# paramiko-ng will throw INFO messages when things get disconnect or cannot
# connect perfectly the first time.  In this library those are all handled by
# either retrying and/or throwing an exception for the appropriate case.
# Therefore, in order to reduce confusion in the logs the log level is set to
# WARNING.

MDNS_LOOKUP_RETRY_MAX = 3
FASTBOOT_TIMEOUT = 30
AFTER_FLASH_BOOT_TIME = 30
WAIT_FOR_EXISTING_FLASH_TO_FINISH_SEC = 360
PROCESS_CHECK_WAIT_TIME_SEC = 30

FUCHSIA_SDK_URL = "gs://fuchsia-sdk/development"
FUCHSIA_RELEASE_TESTING_URL = "gs://fuchsia-release-testing/images"


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


# TODO(b/244747218): Remove once IPerfClient and FuchsiaSyslogProcess are
# refactored away from this method.
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


def flash(fuchsia_device,
          use_ssh=False,
          fuchsia_reconnect_after_reboot_time=5):
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
    if not fuchsia_device.mdns_name:
        raise ValueError(
            'Either fuchsia_device mdns_name must be specified or '
            'ip must be the mDNS name to be able to flash.')

    file_to_download = None
    image_archive_path = None
    image_path = None

    if not fuchsia_device.specific_image:
        product_build = fuchsia_device.product_type
        if fuchsia_device.build_type:
            product_build = f'{product_build}_{fuchsia_device.build_type}'
        if 'LATEST' in fuchsia_device.build_number:
            sdk_version = 'sdk'
            if 'LATEST_F' in fuchsia_device.build_number:
                f_branch = fuchsia_device.build_number.split('LATEST_F', 1)[1]
                sdk_version = f'f{f_branch}_sdk'
            file_to_download = (
                f'{FUCHSIA_RELEASE_TESTING_URL}/'
                f'{sdk_version}-{product_build}.{fuchsia_device.board_type}-release.tgz'
            )
        else:
            # Must be a fully qualified build number (e.g. 5.20210721.4.1215)
            file_to_download = (
                f'{FUCHSIA_SDK_URL}/{fuchsia_device.build_number}/images/'
                f'{product_build}.{fuchsia_device.board_type}-release.tgz')
    elif 'gs://' in fuchsia_device.specific_image:
        file_to_download = fuchsia_device.specific_image
    elif os.path.isdir(fuchsia_device.specific_image):
        image_path = fuchsia_device.specific_image
    elif tarfile.is_tarfile(fuchsia_device.specific_image):
        image_archive_path = fuchsia_device.specific_image
    else:
        raise ValueError(
            f'Invalid specific_image "{fuchsia_device.specific_image}"')

    if image_path:
        reboot_to_bootloader(fuchsia_device, use_ssh,
                             fuchsia_reconnect_after_reboot_time)
        logging.info(
            f'Flashing {fuchsia_device.mdns_name} with {image_path} using authorized keys "{fuchsia_device.authorized_file}".'
        )
        run_flash_script(fuchsia_device, image_path)
    else:
        suffix = fuchsia_device.board_type
        with tempfile.TemporaryDirectory(suffix=suffix) as image_path:
            if file_to_download:
                logging.info(f'Downloading {file_to_download} to {image_path}')
                job.run(f'gsutil cp {file_to_download} {image_path}')
                image_archive_path = os.path.join(
                    image_path, os.path.basename(file_to_download))

            if image_archive_path:
                # Use tar command instead of tarfile.extractall, as it takes too long.
                job.run(f'tar xfvz {image_archive_path} -C {image_path}',
                        timeout=120)

            reboot_to_bootloader(fuchsia_device, use_ssh,
                                 fuchsia_reconnect_after_reboot_time)

            logging.info(
                f'Flashing {fuchsia_device.mdns_name} with {image_archive_path} using authorized keys "{fuchsia_device.authorized_file}".'
            )
            run_flash_script(fuchsia_device, image_path)
    return True


def reboot_to_bootloader(fuchsia_device,
                         use_ssh=False,
                         fuchsia_reconnect_after_reboot_time=5):
    if use_ssh:
        logging.info('Sending reboot command via SSH to '
                     'get into bootloader.')
        # Sending this command will put the device in fastboot
        # but it does not guarantee the device will be in fastboot
        # after this command.  There is no check so if there is an
        # expectation of the device being in fastboot, then some
        # other check needs to be done.
        try:
            fuchsia_device.ssh.run(
                'dm rb', timeout_sec=fuchsia_reconnect_after_reboot_time)
        except FuchsiaSSHError as e:
            if 'closed by remote host' not in e.result.stderr:
                raise e
    else:
        pass
        ## Todo: Add elif for SL4F if implemented in SL4F

    time_counter = 0
    while time_counter < FASTBOOT_TIMEOUT:
        logging.info('Checking to see if fuchsia_device(%s) SN: %s is in '
                     'fastboot. (Attempt #%s Timeout: %s)' %
                     (fuchsia_device.mdns_name, fuchsia_device.serial_number,
                      str(time_counter + 1), FASTBOOT_TIMEOUT))
        for usb_device in usbinfo.usbinfo():
            if (usb_device['iSerialNumber'] == fuchsia_device.serial_number
                    and usb_device['iProduct'] == 'USB_download_gadget'):
                logging.info(
                    'fuchsia_device(%s) SN: %s is in fastboot.' %
                    (fuchsia_device.mdns_name, fuchsia_device.serial_number))
                time_counter = FASTBOOT_TIMEOUT
        time_counter = time_counter + 1
        if time_counter == FASTBOOT_TIMEOUT:
            for fail_usb_device in usbinfo.usbinfo():
                logging.debug(fail_usb_device)
            raise TimeoutError(
                'fuchsia_device(%s) SN: %s '
                'never went into fastboot' %
                (fuchsia_device.mdns_name, fuchsia_device.serial_number))
        time.sleep(1)

    end_time = time.time() + WAIT_FOR_EXISTING_FLASH_TO_FINISH_SEC
    # Attempt to wait for existing flashing process to finish
    while time.time() < end_time:
        flash_process_found = False
        for proc in psutil.process_iter():
            if "bash" in proc.name() and "flash.sh" in proc.cmdline():
                logging.info(
                    "Waiting for existing flash.sh process to complete.")
                time.sleep(PROCESS_CHECK_WAIT_TIME_SEC)
                flash_process_found = True
        if not flash_process_found:
            break


def run_flash_script(fuchsia_device, flash_dir):
    try:
        flash_output = job.run(
            f'bash {flash_dir}/flash.sh --ssh-key={fuchsia_device.authorized_file} -s {fuchsia_device.serial_number}',
            timeout=120)
        logging.debug(flash_output.stderr)
    except job.TimeoutError as err:
        raise TimeoutError(err)

    logging.info('Waiting %s seconds for device'
                 ' to come back up after flashing.' % AFTER_FLASH_BOOT_TIME)
    time.sleep(AFTER_FLASH_BOOT_TIME)
    logging.info('Updating device to new IP addresses.')
    mdns_ip = None
    for retry_counter in range(MDNS_LOOKUP_RETRY_MAX):
        mdns_ip = get_fuchsia_mdns_ipv6_address(fuchsia_device.mdns_name)
        if mdns_ip:
            break
        else:
            time.sleep(1)
    if mdns_ip and utils.is_valid_ipv6_address(mdns_ip):
        logging.info('IP for fuchsia_device(%s) changed from %s to %s' %
                     (fuchsia_device.mdns_name, fuchsia_device.ip, mdns_ip))
        fuchsia_device.ip = mdns_ip
        fuchsia_device.address = "http://[{}]:{}".format(
            fuchsia_device.ip, fuchsia_device.sl4f_port)
    else:
        raise ValueError('Invalid IP: %s after flashing.' %
                         fuchsia_device.mdns_name)


def wait_for_port(host: str, port: int, timeout_sec: int = 5) -> None:
    """Wait for the host to start accepting connections on the port.

    Some services take some time to start. Call this after launching the service
    to avoid race conditions.

    Args:
        host: IP of the running service.
        port: Port of the running service.
        timeout_sec: Seconds to wait until raising TimeoutError

    Raises:
        TimeoutError: when timeout_sec has expired without a successful
            connection to the service
    """
    timeout = time.perf_counter() + timeout_sec
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout_sec):
                return
        except ConnectionRefusedError as e:
            if time.perf_counter() > timeout:
                raise TimeoutError(
                    f'Waited over {timeout_sec}s for the service to start '
                    f'accepting connections at {host}:{port}') from e
