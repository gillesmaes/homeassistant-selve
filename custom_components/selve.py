"""
Support for Selve devices.
"""
from collections import defaultdict
import logging
import voluptuous as vol
from requests.exceptions import RequestException

from homeassistant.const import CONF_PORT
from homeassistant.helpers import discovery
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['python-selve==0.0.1dev11']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'selve'

TAHOMA_ID_FORMAT = '{}_{}'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PORT): cv.string,
        ,
    }),
}, extra=vol.ALLOW_EXTRA)

SELVE_COMPONENTS = [
    'cover'
]

SELVE_TYPES = {
    'rts:RollerShutterRTSComponent': 'cover',
    'rts:CurtainRTSComponent': 'cover',
    'io:RollerShutterWithLowSpeedManagementIOComponent': 'cover',
    'io:RollerShutterVeluxIOComponent': 'cover',
    'io:RollerShutterGenericIOComponent': 'cover',
    'io:WindowOpenerVeluxIOComponent': 'cover',
    'io:LightIOSystemSensor': 'sensor',
}


def setup(hass, config):
    """Activate Selve component."""
    from python_selve import Gateway

    port = config[CONF_PORT]
    try:
        selve = Gateway(port)
    except RequestException:
        _LOGGER.exception("Error when trying to connect to the selve gateway")
        return False

    try:
        api.get_setup()
        devices = api.get_devices()
        scenes = api.get_action_groups()
    except RequestException:
        _LOGGER.exception("Error when getting devices from the Selve API")
        return False

    hass.data[DOMAIN] = {
        'controller': api,
        'devices': defaultdict(list),
        'scenes': []
    }

    for device in devices:
        _device = api.get_device(device)
        if all(ext not in _device.type for ext in exclude):
            device_type = map_tahoma_device(_device)
            if device_type is None:
                _LOGGER.warning('Unsupported type %s for Selve device %s',
                                _device.type, _device.label)
                continue
            hass.data[DOMAIN]['devices'][device_type].append(_device)

    for scene in scenes:
        hass.data[DOMAIN]['scenes'].append(scene)

    for component in TAHOMA_COMPONENTS:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    return True


def map_selve_device(selve_device):
    """Map Selve device types to Home Assistant components."""
    return SELVE_TYPES.get(selve_device.type)


class SelveDevice(Entity):
    """Representation of a Selve device entity."""

    def __init__(self, selve_device, controller):
        """Initialize the device."""
        self.selve_device = selve_device
        self.controller = controller
        self._name = self.selve_device.name

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return {'tahoma_device_id': self.tahoma_device.url}

    def apply_action(self, cmd_name, *args):
        """Apply Action to Device."""
        from tahoma_api import Action
        action = Action(self.tahoma_device.url)
        action.add_command(cmd_name, *args)
        self.controller.apply_actions('HomeAssistant', [action])