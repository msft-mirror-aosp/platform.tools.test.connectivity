from acts.test_utils.instrumentation.power import instrumentation_power_test


class ApolloIdleTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running a test with no setup being applied to the device.
     Useful for when you need to manually do some changes that could be
     reversed with the regular preparation steps. Tests in this class should be
     executed assuming there is no SL4A installed."""

    def _prepare_device(self):
        super()._prepare_device()

    def __init__(self, configs):
        super().__init__(configs)
        # clear additional command options that won't work on the average
        # OEM devices.
        self._instrumentation_command_options = {}

    def test_screen_off(self):
        """Calls an instrumentation test that turns the screen off and measures
        power."""
        self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testIdleScreenOff')
        self.validate_power_results()