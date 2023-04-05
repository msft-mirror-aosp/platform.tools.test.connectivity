import requests
import time
import logging
from typing import List, Optional, Any
from acts_contrib.test_utils.power.cellular.ssh_app_starter import SshAppStarter

class ImsApiConnector:
  """A wrapper class for Keysight Ims API Connector.

  Keysight provided an API Connector application which is a HTTP server
  running on the same host as Keysight IMS server app and client app.
  It allows IMS simulator/app to be controlled via HTTP request.

  Attributes:
    api_connector_ip: ip of host where API Connector reside.
    api_connector_port: port of API Connector server.
    ims_app: a string the type of ims app. Keysight has predenied value for this
      includes "client", "server".
    api_token: an arbitrary and unique string to identify the link between API
      connector and ims app.
  """

  _BASE_URL_FORMAT = 'http://{addr}:{port}/ims/api/{app}s/{api_token}'

  _SSH_USERNAME = 'User'
  _APP_BOOT_TIME = 30

  _IMS_CLIENT_IDLE_STATUS = 'Idle'
  _IMS_CLIENT_APP = 'Keysight.ImsSip.Client.exe'
  _IMS_CLIENT_APP_LOC = 'C:\Program Files (x86)\Keysight\C8700201A\IMS-SIP Client\\'
  _IMS_SERVER_APP = 'Keysight.ImsSip.Server.exe'
  _IMS_SERVER_APP_LOC = 'C:\Program Files (x86)\Keysight\C8700201A\IMS-SIP Server\\'

  def __init__(
      self,
      api_connector_ip: str,
      api_connector_port: int,
      ims_app: str,
      api_token: str,
      ims_app_ip: str,
      ims_app_port: int,
      log
  ):
    self.log = log

    # create ssh connection to host pc
    self.ssh = SshAppStarter(api_connector_ip, self._SSH_USERNAME)

    # api connector info
    self.api_connector_ip = api_connector_ip
    self.api_connector_port = api_connector_port

    # ims app info
    self.ims_app = ims_app
    self.api_token = api_token
    self.ims_app_ip = ims_app_ip
    self.ims_app_port = ims_app_port

    # construct base url
    self.base_url = self._BASE_URL_FORMAT.format(
        addr=self.api_connector_ip,
        port=self.api_connector_port,
        app=self.ims_app,
        api_token=self.api_token,
    )

    # start server and client if they are not started
    self._start_client_server_if_down()
    # create IMS-Client API link
    is_app_linked = self.create_ims_app_link()

    if not is_app_linked:
      raise RuntimeError('Fail to create link to IMS app.')

  def log_response_info(self, r: requests.Response):
    self.log.debug('HTTP request sent:')
    self.log.debug('-> method: ' + str(r.request.method))
    self.log.debug('-> url: ' + str(r.url))
    self.log.debug('-> status_code: ' + str(r.status_code))

  def create_ims_app_link(self) -> bool:
    """Creates link between Keysight API Connector to ims app.

    Returns:
      True if API connector server linked/connected with ims app,
      False otherwise.
    """
    self.log.info('Create ims app link: token:ip:port')
    self.log.info(
        f'Creating ims_{self.ims_app} link: '
        '{self.api_token}:{self.ims_app_ip}:{self.ims_app_port}'
    )

    request_data = {
        'targetIpAddress': self.ims_app_ip,
        'targetWcfPort': self.ims_app_port,
    }

    r = requests.post(url=self.base_url, json=request_data)
    self.log_response_info(r)

    return r.status_code == requests.codes.created

  def remove_ims_app_link(self) -> bool:
    """Removes link between Keysight API Connector to ims app.

    Returns:
      True if successfully disconnected/unlinked,
      False otherwise.
    """
    self.log.info(f'Remove ims_{self.ims_app} link: {self.api_token}')

    r = requests.delete(url=self.base_url)
    self.log_response_info(r)

    return r.status_code == requests.codes.ok

  def get_ims_app_property(self, property_name: str) -> Optional[str]:
    """Gets property value of IMS app.

    Attributes:
    property_name: Name of property to get value.

    Returns:
      Value of property which is inquired.
    """
    self.log.info('Getting ims app property: ' + property_name)

    request_url = self.base_url + '/get_property'
    request_params = {'propertyName': property_name}
    r = requests.get(url=request_url, params=request_params)
    self.log_response_info(r)

    try:
      res_json = r.json()
    except:
      res_json = {'propertyValue': None}
    prop_value = res_json['propertyValue']

    return prop_value

  def set_ims_app_property(
      self, property_name: str, property_value: Optional[Any]
  ) -> bool:
    """Sets property value of IMS app.

    Attributes:
      property_name: Name of property to set value.
      property_value: Value to be set.
    """
    self.log.info(
        'Setting ims property: ' + property_name + ' = ' + str(property_value)
    )

    request_url = self.base_url + '/set_property'
    data = {'propertyName': property_name, 'propertyValue': property_value}
    r = requests.post(url=request_url, json=data)
    self.log_response_info(r)

    return r.status_code == requests.codes.ok

  def ims_api_call_method(
      self, method_name: str, method_args: List = []
  ) -> Optional[str]:
    """Call Keysight API to control simulator.

    API Connector allows us to call Keysight Simulators' API without using C#.
    To invoke an API, we are sending post request to API Connector (http
    server).

    Attributes:
      method_name: A name of method from Keysight API in string.
      method_args: A python-array contains arguments for the called API.

    Returns:
      A string value parse from response.
    """
    self.log.info('Calling Keysight simulator API: ' + method_name)

    if not isinstance(method_args, list):
      method_args = [method_args]
    request_url = self.base_url + '/call_method'
    request_data = {'methodName': method_name, 'arguments': method_args}
    r = requests.post(url=request_url, json=request_data)

    ret_val = None

    if r.status_code == requests.codes.ok:
      return_value_key = 'returnValue'
      if ('Content-Type' in r.headers) and r.headers[
          'Content-Type'
      ] == 'application/json':
        response_body = r.json()
        if (response_body != None) and (return_value_key in response_body):
          ret_val = response_body[return_value_key]
    else:
      raise requests.HTTPError(r.status_code, r.text)

    self.log_response_info(r)

    return ret_val

  def _is_line_idle(self, call_line_number) -> bool:
    is_line_idle_prop = self.get_ims_app_property(
        f'IVoip.CallLineParams({call_line_number}).SessionState'
    )
    return is_line_idle_prop == self._IMS_CLIENT_IDLE_STATUS

  def hangup_call(self):
    self.ims_api_call_method('IVoip.HangUp()')

  def _is_ims_client_app_registered(self) -> bool:
    is_registered_prop = self.get_ims_app_property(
        'IComponentControl.IsRegistered'
    )
    return is_registered_prop == 'True'

  def restart_server(self) -> bool:
    self.ims_api_call_method('IServer.StopListeners()')
    result = self.ims_api_call_method('IServer.Start()')
    return result == 'True'

  def deregister_client(self):
    self.ims_api_call_method('ISipConnection.Unregister()')

  def reregister_client(self):
    self.ims_api_call_method('ISipConnection.Unregister()')
    self.ims_api_call_method('ISipConnection.Register()')

    # failed to re-register client, so try restarting server and client
    if not self._is_ims_client_app_registered():
      self.ssh.close_app(self._IMS_CLIENT_APP)
      self.ssh.close_app(self._IMS_SERVER_APP)
      self.ssh.start_app(self._IMS_CLIENT_APP, self._IMS_CLIENT_APP_LOC)
      self.ssh.start_app(self._IMS_SERVER_APP, self._IMS_SERVER_APP_LOC)
      time.sleep(self._APP_BOOT_TIME)

      self.ims_api_call_method('ISipConnection.Unregister()')
      self.ims_api_call_method('ISipConnection.Register()')

  def _start_client_server_if_down(self):
    self.log.info('checking if server/client are running')
    if not self.ssh.check_app_running(self._IMS_CLIENT_APP):
      self.log.info('client was not running, starting now')
      self.ssh.start_app(self._IMS_CLIENT_APP, self._IMS_CLIENT_APP_LOC)

    if not self.ssh.check_app_running(self._IMS_SERVER_APP):
      self.log.info('server was not running, starting now')
      self.ssh.start_app(self._IMS_SERVER_APP, self._IMS_SERVER_APP_LOC)
    time.sleep(self._APP_BOOT_TIME)

  def initiate_call(self, callee_number: str, call_line_idx: int = 0):
    """Dials to callee_number.

    Attributes:
      callee_number: a string value of number to be dialed to.
      call_line_idx: an inteter index for call line.
    """
    sleep_time = 5

    self.log.info('checking if server/client are registered and running')
    # Check if client and server are running, if not, start them
    self._start_client_server_if_down()

    # Check if client is registered to server
    if not self._is_ims_client_app_registered():
      self.log.info('re-registering client to server')
      self.reregister_client()

    is_registered = self._is_ims_client_app_registered()
    if not is_registered:
      raise RuntimeError('Failed to register IMS-client to IMS-server.')

    # switch to call-line #1 (idx = 0)
    self.log.info('Switching to call-line #1.')
    self.set_ims_app_property('IVoip.SelectedCallLine', call_line_idx)

    # check whether the call-line #1 is ready for dialling
    is_line1_idle = self._is_line_idle(call_line_idx)
    if not is_line1_idle:
      raise RuntimeError('Call-line not is not in indle state.')

    # entering callee number for call-line #1
    self.log.info(f'Enter callee number: {callee_number}.')
    self.set_ims_app_property(
        'IVoip.CallLineParams(0).CallLocation', callee_number
    )

    # dial entered callee number
    self.log.info('Dialling call.')
    self.ims_api_call_method('IVoip.Dial()')

    time.sleep(sleep_time)

    # check if dial success (not idle)
    if self._is_line_idle(call_line_idx):
      raise RuntimeError('Fail to dial.')

  def __del__(self):
    self.remove_ims_app_link()
