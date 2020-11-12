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

SERVICE_DNSMASQ = "dnsmasq"
SERVICE_STUNNEL = "stunnel"
SERVICE_NETWORK = "network"
STUNNEL_CONFIG_PATH = "/etc/stunnel/DoTServer.conf"
HISTORY_CONFIG_PATH = "/etc/dirty_configs"


class NetworkSettings(object):
    """Class for network settings.

    Attributes:
        ssh: ssh connection object.
        service_manager: Object manage service configuration
        ip: ip address for AccessPoint.
        log: Logging object for AccessPoint.
        config: A list to store changes on network settings.
        cleanup_map: A dict for compare oppo functions.
    """

    def __init__(self, ssh, ip, logger):
        """Initialize wireless settings.

        Args:
            ssh: ssh connection object.
            ip: ip address for AccessPoint.
            logger: Logging object for AccessPoint.
        """
        self.ssh = ssh
        self.service_manager = ServiceManager(ssh)
        self.ip = ip
        self.log = logger
        self.config = set()
        self.cleanup_map = {
            "setup_dns_server": self.remove_dns_server,
            "disable_ipv6": self.enable_ipv6
        }
        # This map contains cleanup functions to restore the configuration to
        # its default state. We write these keys to HISTORY_CONFIG_PATH prior to
        # making any changes to that subsystem.
        # This makes it easier to recover after an aborted test.
        self.cleanup_network_settings()

    def cleanup_network_settings(self):
        """Reset all changes on Access point."""

        # Detect if any changes that is not clean up.
        if self.file_exists(HISTORY_CONFIG_PATH):
            out = self.ssh.run("cat %s" % HISTORY_CONFIG_PATH).stdout
            if out:
                self.config = set(out.split("\n"))

        if self.config:
            temp = self.config.copy()
            for change in temp:
                self.cleanup_map[change]()
            self.config = set()

        if self.file_exists(HISTORY_CONFIG_PATH):
            out = self.ssh.run("cat %s" % HISTORY_CONFIG_PATH).stdout
            if not out:
                self.ssh.run("rm %s" % HISTORY_CONFIG_PATH)

    def commit_changes(self):
        """Apply changes on Access point."""
        self.ssh.run("uci commit")
        self.service_manager.restart_services()
        self.create_config_file("\n".join(self.config),
                                HISTORY_CONFIG_PATH)

    def install(self, package_name):
        """Install package on OpenWrtAP via opkg.

        Args:
          package_name: package name want to install.
        """
        self.ssh.run("opkg update")
        self.ssh.run("opkg install %s" % package_name)

    def package_installed(self, package_name):
        """Check if target package installed on OpenWrtAP.

        Args:
          package_name: package name want to check.

        Returns:
          True if installed.
        """
        if self.ssh.run("opkg list-installed %s" % package_name).stdout:
            return True
        return False

    def file_exists(self, abs_file_path):
        """Check if target file exist on specific path.

        Args:
          abs_file_path: Absolute path for the file.

        Returns:
          True if Existed.
        """
        path, file_name = abs_file_path.rsplit("/", 1)
        if self.ssh.run("ls %s | grep %s" % (path, file_name),
                        ignore_status=True).stdout:
            return True
        return False

    def setup_dns_server(self, domain_name):
        """Setup DNS server on OpenWrtAP.

        Args:
          domain_name: Local dns domain name.
        """
        self.log.info("Setup DNS server with domain name %s" % domain_name)
        self.ssh.run("uci set dhcp.@dnsmasq[0].local='/%s/'" % domain_name)
        self.ssh.run("uci set dhcp.@dnsmasq[0].domain='%s'" % domain_name)
        self.add_resource_record(domain_name, self.ip)
        self.service_manager.need_restart(SERVICE_DNSMASQ)
        self.config.add("setup_dns_server")
        self.commit_changes()

        # Check stunnel package is installed
        if not self.package_installed("stunnel"):
            self.install("stunnel")
            self.service_manager.stop(SERVICE_STUNNEL)
            self.service_manager.disable(SERVICE_STUNNEL)

        # Enable stunnel
        self.create_stunnel_config()
        self.ssh.run("stunnel /etc/stunnel/DoTServer.conf")

    def remove_dns_server(self):
        """Remove DNS server on OpenWrtAP."""
        if self.file_exists("/var/run/stunnel.pid"):
            self.ssh.run("kill $(cat /var/run/stunnel.pid)")
        self.ssh.run("uci set dhcp.@dnsmasq[0].local='/lan/'")
        self.ssh.run("uci set dhcp.@dnsmasq[0].domain='lan'")
        self.clear_resource_record()
        self.service_manager.need_restart(SERVICE_DNSMASQ)
        self.config.discard("setup_dns_server")
        self.commit_changes()

    def add_resource_record(self, domain_name, domain_ip):
        """Add resource record.

        Args:
          domain_name: A string for domain name.
          domain_ip: A string for domain ip.
        """
        self.ssh.run("uci add dhcp domain")
        self.ssh.run("uci set dhcp.@domain[-1].name='%s'" % domain_name)
        self.ssh.run("uci set dhcp.@domain[-1].ip='%s'" % domain_ip)
        self.service_manager.need_restart(SERVICE_DNSMASQ)

    def del_resource_record(self):
        """Delete the last resource record."""
        self.ssh.run("uci delete dhcp.@domain[-1]")
        self.service_manager.need_restart(SERVICE_DNSMASQ)

    def clear_resource_record(self):
        """Delete the all resource record."""
        rr = self.ssh.run("uci show dhcp | grep =domain",
                          ignore_status=True).stdout
        if rr:
            for _ in rr.split("\n"):
                self.del_resource_record()
        self.service_manager.need_restart(SERVICE_DNSMASQ)

    def create_stunnel_config(self):
        """Create config for stunnel service."""
        stunnel_config = [
            "pid = /var/run/stunnel.pid",
            "[dns]",
            "accept = 853",
            "connect = 127.0.0.1:53",
            "cert = /etc/stunnel/fullchain.pem",
            "key = /etc/stunnel/privkey.pem",
        ]
        config_string = "\n".join(stunnel_config)
        self.create_config_file(config_string, STUNNEL_CONFIG_PATH)

    def create_config_file(self, config, file_path):
        """Create config file.

        Args:
          config: A string of content of config.
          file_path: Config's abs_path.
        """
        self.ssh.run("echo -e \"%s\" > %s" % (config, file_path))

    def enable_ipv6(self):
        """Enable ipv6 on OpenWrt."""
        self.ssh.run("uci set network.lan.ipv6=1")
        self.ssh.run("uci set network.wan.ipv6=1")
        self.service_manager.enable("odhcpd")
        self.service_manager.reload(SERVICE_NETWORK)
        self.config.discard("disable_ipv6")
        self.commit_changes()

    def disable_ipv6(self):
        """Disable ipv6 on OpenWrt."""
        self.ssh.run("uci set network.lan.ipv6=0")
        self.ssh.run("uci set network.wan.ipv6=0")
        self.service_manager.disable("odhcpd")
        self.service_manager.reload(SERVICE_NETWORK)
        self.config.add("disable_ipv6")
        self.commit_changes()


class ServiceManager(object):
    """Class for service on OpenWrt.

        Attributes:
        ssh: ssh object for the AP.
        _need_restart: Record service need to restart.
    """

    def __init__(self, ssh):
        self.ssh = ssh
        self._need_restart = set()

    def enable(self, service_name):
        """Enable service auto start."""
        self.ssh.run("/etc/init.d/%s enable" % service_name)

    def disable(self, service_name):
        """Disable service auto start."""
        self.ssh.run("/etc/init.d/%s disable" % service_name)

    def restart(self, service_name):
        """Restart the service."""
        self.ssh.run("/etc/init.d/%s restart" % service_name)

    def reload(self, service_name):
        """Restart the service."""
        self.ssh.run("/etc/init.d/%s reload" % service_name)

    def restart_services(self):
        """Restart all services need to restart."""
        for service in self._need_restart:
            self.restart(service)
        self._need_restart = set()

    def stop(self, service_name):
        """Stop the service."""
        self.ssh.run("/etc/init.d/%s stop" % service_name)

    def need_restart(self, service_name):
        self._need_restart.add(service_name)
