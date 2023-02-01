#   Copyright 2022 - The Android Open Source Project
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

import paramiko
import acts_contrib.test_utils.power.cellular.cellular_power_base_test as PWCEL


class PowerTelTrafficPresetTest(PWCEL.PowerCellularLabBaseTest):
    # command to start iperf server on UE
    START_IPERF_SV_UE_CMD = 'nohup > /dev/null 2>&1 sh -c "iperf3 -s -i1 -p5201 > /dev/null  &"'

    # command to start iperf server on UE
    # (require: 1.path to iperf exe 2.hostname/hostIP)
    START_IPERF_CLIENT_UE_CMD = (
        'nohup > /dev/null 2>&1 sh -c '
        '"iperf3 -c {iperf_host_ip} -i1 -p5202 -w8m -t2000 > /dev/null &"')

    #command to start iperf server on host()
    START_IPERF_SV_HOST_CMD = '{exe_path}\\iperf3 -s -p5202'

    # command to start iperf client on host
    # (require: 1.path to iperf exe 2.UE IP)
    START_IPERF_CLIENT_HOST_CMD = (
        '{exe_path}\\iperf3 -c {ue_ip} -w16M -t1000 -p5201')

    def __init__(self, controllers):
        super().__init__(controllers)
        self.ssh_iperf_client = None
        self.ssh_iperf_server = None

    def setup_class(self):
        super().setup_class()

        # Unpack test parameters used in this class
        self.unpack_userparams(ssh_host_ip=None,
                               host_username=None,
                               client_ssh_private_key_file=None,
                               iperf_exe_path=None,
                               ue_ip=None,
                               iperf_host_ip=None)

        # Verify required config
        for param in ('ssh_host_ip', 'host_username', 'client_ssh_private_key_file',
                  'iperf_exe_path', 'ue_ip', 'iperf_host_ip'):
            if getattr(self, param) is None:
                raise RuntimeError(
                    f'Parameter "{param}" is required to run this type of test')

    def setup_test(self):
        # Call parent method first to setup simulation
        if not super().setup_test():
            return False

        # setup ssh client
        self.ssh_iperf_client = self._create_ssh_client()
        self.ssh_iperf_server = self._create_ssh_client()

    def power_tel_traffic_test(self):
        """Measure power while data is transferring."""
        # Start data traffic
        self.start_downlink_process()
        self.start_uplink_process()

        # Measure power
        self.collect_power_data()

    def _create_ssh_client(self):
        """Create a ssh client to host."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        mykey = paramiko.Ed25519Key.from_private_key_file(
            self.client_ssh_private_key_file)
        ssh.connect(hostname=self.ssh_host_ip,
                    username=self.host_username,
                    pkey=mykey)
        self.log.info('SSH client to %s is connected' % self.ssh_host_ip)
        return ssh

    def _exec_ssh_cmd(self, ssh_client, cmd):
        """Execute command on given ssh client.

        Args:
            ssh_client: parmiko ssh client object.
            cmd: command to execute via ssh.
        """
        self.log.info('Sending cmd to ssh host: ' + cmd)
        stdin, _, _ = ssh_client.exec_command(cmd, get_pty=True)
        stdin.close()
        # TODO: stdout.readline cause program to hang
        # implement a workaround to getting response
        # from executed command

    def start_downlink_process(self):
        """UE transfer data to host."""
        self.log.info('Start downlink process')
        # start UE iperf server
        self.cellular_dut.ad.adb.shell(self.START_IPERF_SV_UE_CMD)
        self.log.info('UE iperf server started')
        # start host iperf client
        cmd = self.START_IPERF_CLIENT_HOST_CMD.format(
            exe_path=self.iperf_exe_path,
            ue_ip=self.ue_ip)
        self._exec_ssh_cmd(self.ssh_iperf_client, cmd)
        self.log.info('Host iperf client started')

    def start_uplink_process(self):
        """Host transfer data to UE."""
        self.log.info('Start uplink process')
        # start host iperf server
        cmd = self.START_IPERF_SV_HOST_CMD.format(exe_path=self.iperf_exe_path)
        self._exec_ssh_cmd(self.ssh_iperf_server, cmd)
        self.log.info('Host iperf server started')
        # start UE iperf
        self.cellular_dut.ad.adb.shell(
            self.START_IPERF_CLIENT_UE_CMD.format(iperf_host_ip=self.iperf_host_ip))
        self.log.info('UE iperf client started')


class PowerTelTraffic_Preset_Test(PowerTelTrafficPresetTest):

    def test_preset_LTE_traffic(self):
        self.power_tel_traffic_test()
