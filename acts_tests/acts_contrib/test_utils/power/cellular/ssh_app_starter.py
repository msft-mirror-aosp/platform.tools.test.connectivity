import logging
import re
import time
from typing import Iterable, List
import paramiko  # type: ignore
from paramiko.client import SSHClient

_LOG = logging.getLogger(__name__)


class SshAppStarter:
  """Utilities for creating ssh connection, closing and opening apps."""

  _PSEXEC_PROC_STARTED_REGEX_FORMAT = 'started on * with process ID {proc_id}'

  _SSH_START_APP_CMD_FORMAT = 'psexec -s -d -i 1 "{exe_path}"'
  _SSH_CHECK_APP_RUNNING_CMD_FORMAT = 'tasklist | findstr /R {regex_app_name}'
  _SSH_KILL_PROCESS_BY_NAME = 'taskkill /IM {process_name} /F'

  def __init__(self, hostname: str, username: str):
    self.log = _LOG
    self.ssh = self.create_ssh_socket(hostname, username)

  def create_ssh_socket(self, hostname: str, username: str) -> SSHClient:
    """Creates ssh session to host."""

    self.log.info('Creating ssh session to %s ' % hostname)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_system_host_keys()
    ssh.connect(hostname=hostname, username=username)
    self.log.info('SSH client to %s is connected' % hostname)
    return ssh

  def run_command_paramiko(self, command: str) -> str:
    """Runs a command using Paramiko and return stdout code."""

    self.log.info('Running command: ' + str(command))
    stdin, stdout, stderr = self.ssh.exec_command(command, timeout=10)
    stdin.close()
    err = ''.join(stderr.readlines())
    out = ''.join(stdout.readlines())

    # psexec return process ID as part of the exit code
    exit_status = stderr.channel.recv_exit_status()
    if err:
      self.log.error(str(err))
    else:
      self.log.info(str(out))
    return out, err, exit_status

  def close_ssh_connection(self):
    """Closes ssh connection."""

    self.log.info('Closing ssh connection')
    self.ssh.close()

  def close_app(self, app: str) -> str:
    """Closes any app whose name passed as an argument."""

    command = self._SSH_KILL_PROCESS_BY_NAME.format(process_name=app)
    result, _, _ = self.run_command_paramiko(command)
    return result

  def start_app(self, app: str, location: str) -> str:
    """Starts any app whose name passed as an argument."""

    command = self._SSH_START_APP_CMD_FORMAT.format(exe_path=location + app)
    results, err, exit_status = self.run_command_paramiko(command)

    id_in_err = re.search(
        self._PSEXEC_PROC_STARTED_REGEX_FORMAT.format(proc_id=exit_status),
        err[-1],
    )
    if id_in_err:
      raise RuntimeError('Fail to start app: ' + out + err)

    return results

  def check_app_running(self, app: str) -> bool:
    """Checks if the given app is running"""
    is_running_cmd1 = self._SSH_CHECK_APP_RUNNING_CMD_FORMAT.format(
        regex_app_name=app
    )
    is_running_cmd2 = self._SSH_CHECK_APP_RUNNING_CMD_FORMAT.format(
        regex_app_name=app[0:-1]
    )

    # Sometimes app is run as .ex instead of .exe
    result1, _, _ = self.run_command_paramiko(is_running_cmd1)
    result2, _, _ = self.run_command_paramiko(is_running_cmd2)
    return result1 != '' or result2 != ''

  def __del__(self):
    self.close_ssh_connection()
