import time
import logging
import voluptuous as vol

from homeassistant.components.cover import (PLATFORM_SCHEMA, CoverDevice,
                                            SUPPORT_OPEN, SUPPORT_CLOSE)
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
import custom_components.util.algorithm as checkcrc
from homeassistant.helpers.event import track_utc_time_change

DOMAIN = 'polycurtain2'
EVENT_MQTT_RECV = 'poly_mqtt_json'
POLY_ZIGBEE_DOMAIN = 'poly_zb_uart'
POLY_ZIGBEE_SERVICE = 'send_d'
EVENT_ZIGBEE_RECV = 'zigbee_data_event'

BYTES_OPEN = [
    0x80, 0x00, 0x1f, 0xa4, 0x10, 0x44, 0x1f, 0xa4, 0x60, 0x3, 0x0, 0x2, 0x0,
    0x7, 0x0, 0x6, 0x1, 0x5, 0x0, 0x4, 0x0, 0xb4
]
BYTES_CLOSE = [
    0x80, 0x00, 0x1f, 0xa4, 0x10, 0x44, 0x1f, 0xa4, 0x60, 0x3, 0x0, 0x2, 0x0,
    0x7, 0x0, 0x6, 0x0, 0x5, 0x1, 0x4, 0x0, 0xb4
]
BYTES_STOP = [
    0x80, 0x00, 0x1f, 0xa4, 0x10, 0x44, 0x1f, 0xa4, 0x60, 0x3, 0x0, 0x2, 0x0,
    0x7, 0x0, 0x6, 0x0, 0x5, 0x0, 0x4, 0x1, 0xb4
]

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional('name'): cv.string,
    vol.Optional('type'): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Polyhome CoverDevice platform."""

    curtains2 = []
    if discovery_info is not None:
        # Not using hostname, as it seems to vary.
        device = {'name': discovery_info['name'] + '1', 'mac': discovery_info['mac'], 'way': '1'}
        device1 = {'name': discovery_info['name'] + '2', 'mac': discovery_info['mac'], 'way': '2'}
        curtains2.append(RMCover(hass, device, None))
        curtains2.append(RMCover(hass, device1, None))
    else:
        for mac, device_config in config['devices'].items():
            device = {'name': device_config['name'] + '1', 'mac': mac, 'way': '1'}
            device1 = {'name': device_config['name'] + '2', 'mac': mac, 'way': '2'}
            curtains2.append(RMCover(hass, device, device_config))
            curtains2.append(RMCover(hass, device1, device_config))

    add_devices(curtains2, True)

    def handle_event(event):
        """Listener to handle fired events."""
        bytearr = event.data.get('data')
        if bytearr[0] == '0xa0' and bytearr[5] == '0x1':
            mac_1 = bytearr[6].replace('0x', '')
            mac_h = bytearr[7].replace('0x', '')
            mac_str = mac_1 + "#" + mac_h
            for dev in curtains2:
                if dev.mac == mac_str:
                    # 1关
                    if bytearr[9] == '0x0':
                        if dev.way == '1':
                            dev.set_closed(True)
                            hass.services.call("poly_mqtt", "pub_data", {
                                "data": "curtain2_1 close"
                            })
                    # 1开
                    elif bytearr[9] == '0x1':
                        if dev.way == '1':
                            dev.set_closed(False)
                            hass.services.call("poly_mqtt", "pub_data", {
                                "data": "curtain2_1 open"
                            })
                    else:
                        if dev.way == '1':
                            dev.set_closed(True)
                            hass.services.call("poly_mqtt", "pub_data", {
                                "data": "curtain2_1 stop"
                            })
                    # 2关
                    if bytearr[10] == '0x0':
                        if dev.way == '2':
                            dev.set_closed(True)
                            hass.services.call("poly_mqtt", "pub_data", {
                                "data": "curtain2_2 close"
                            })
                    # 2开
                    elif bytearr[10] == '0x1':
                        if dev.way == '2':
                            dev.set_closed(False)
                            hass.services.call("poly_mqtt", "pub_data", {
                                "data": "curtain2_2 open"
                            })
                    else:
                        if dev.way == '2':
                            dev.set_closed(True)
                            hass.services.call("poly_mqtt", "pub_data", {
                                "data": "curtain2_2 stop"
                            })

        if bytearr[0] == '0xc0':
            mac_l, mac_h = bytearr[2].replace('0x', ''), bytearr[3].replace(
                '0x', '')
            mac_str = mac_l + '#' + mac_h
            dev = next((dev for dev in curtains2 if dev.mac == mac_str), None)
            if dev is None:
                return
            if bytearr[6] == '0x41':
                dev.set_available(False)
            if bytearr[6] == '0x40':
                dev.set_available(True)

    # Listen for when zigbee_data_event is fired
    hass.bus.listen(EVENT_ZIGBEE_RECV, handle_event)

    return True


class RMCover(CoverDevice):
    """Representation of a cover"""

    def __init__(self, hass, device, dev_conf):
        """Initialize the cover."""
        self._hass = hass
        self._device = device
        self._name = device['name']
        self._mac = device['mac']
        self._way = device['way']
        self._config = dev_conf
        self._state = None
        self._closed = True
        self._available = True

    @property
    def name(self):
        """Return the display name of this curtain."""
        return self._name

    @property
    def mac(self):
        """Return the display mac of this curtain."""
        return self._mac

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._closed

    @property
    def way(self):
        return self._way

    @property
    def available(self):
        """Return if bulb is available."""
        return self._available

    def set_available(self, available):
        self._available = available

    def set_closed(self, value=True):
        self._closed = value
        self.schedule_update_ha_state()

    def close_cover(self, **kwargs):
        """Close the cover."""
        # 0x80, 0x00, 0x1f, 0xa4, 0x10, 0x44, 0x1f, 0xa4, 0x60, 0x3, 0x0, 0x2, 0x0,
        # 0x7, 0x0, 0x6, 0x0, 0x5, 0x1, 0x4, 0x0, 0xb4
        if self._way == '1':
            self._closed = True
            mac = self._mac.split('#')
            BYTES_CLOSE[2], BYTES_CLOSE[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_CLOSE[6], BYTES_CLOSE[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_CLOSE[-4] = 0x1
            resu_crc = checkcrc.xorcrc_hex(BYTES_CLOSE)
            BYTES_CLOSE[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_CLOSE
            })
            time.sleep(0.4)
            BYTES_CLOSE[2], BYTES_CLOSE[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_CLOSE[6], BYTES_CLOSE[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_CLOSE[-4] = 0x0
            resu_crc = checkcrc.xorcrc_hex(BYTES_CLOSE)
            BYTES_CLOSE[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_CLOSE
            })
        if self._way == '2':
            # 0x80, 0x00, 0x1f, 0xa4, 0x10, 0x44, 0x1f, 0xa4, 0x60, 0x3, 0x0, 0x2, 0x0,
            # 0x7, 0x0, 0x6, 0x0, 0x5, 0x1, 0x4, 0x0, 0xb4
            self._closed = True
            mac = self._mac.split('#')
            BYTES_CLOSE[2], BYTES_CLOSE[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_CLOSE[6], BYTES_CLOSE[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_CLOSE[12] = 0x1
            BYTES_CLOSE[-4] = 0x0
            resu_crc = checkcrc.xorcrc_hex(BYTES_CLOSE)
            BYTES_CLOSE[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_CLOSE
            })
            time.sleep(0.4)
            BYTES_CLOSE[2], BYTES_CLOSE[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_CLOSE[6], BYTES_CLOSE[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_CLOSE[12] = 0x0
            BYTES_CLOSE[-4] = 0x0
            resu_crc = checkcrc.xorcrc_hex(BYTES_CLOSE)
            BYTES_CLOSE[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_CLOSE
            })

    def open_cover(self, **kwargs):
        """Open the cover."""
        # 0x80, 0x00, 0x1f, 0xa4, 0x10, 0x44, 0x1f, 0xa4, 0x60, 0x3, 0x0, 0x2, 0x0,
        # 0x7, 0x0, 0x6, 0x1, 0x5, 0x0, 0x4, 0x0, 0xb4
        if self._way == '1':
            self._closed = False
            mac = self._mac.split('#')
            BYTES_OPEN[2], BYTES_OPEN[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_OPEN[6], BYTES_OPEN[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_OPEN[-6] = 0x1
            resu_crc = checkcrc.xorcrc_hex(BYTES_OPEN)
            BYTES_OPEN[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_OPEN
            })
            time.sleep(0.4)
            BYTES_OPEN[2], BYTES_OPEN[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_OPEN[6], BYTES_OPEN[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_OPEN[-6] = 0x0
            resu_crc = checkcrc.xorcrc_hex(BYTES_OPEN)
            BYTES_OPEN[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_OPEN
            })
        elif self._way == '2':
            # 0x80, 0x00, 0x1f, 0xa4, 0x10, 0x44, 0x1f, 0xa4, 0x60, 0x3, 0x0, 0x2, 0x0,
            # 0x7, 0x0, 0x6, 0x1, 0x5, 0x0, 0x4, 0x0, 0xb4
            self._closed = False
            mac = self._mac.split('#')
            BYTES_OPEN[2], BYTES_OPEN[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_OPEN[6], BYTES_OPEN[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_OPEN[10] = 0x1
            BYTES_OPEN[-6] = 0x0
            resu_crc = checkcrc.xorcrc_hex(BYTES_OPEN)
            BYTES_OPEN[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_OPEN
            })
            time.sleep(0.4)
            BYTES_OPEN[2], BYTES_OPEN[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_OPEN[6], BYTES_OPEN[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_OPEN[10] = 0x0
            BYTES_OPEN[-6] = 0x0
            resu_crc = checkcrc.xorcrc_hex(BYTES_OPEN)
            BYTES_OPEN[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_OPEN
            })

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        # 0x80, 0x00, 0x1f, 0xa4, 0x10, 0x44, 0x1f, 0xa4, 0x60, 0x3, 0x0, 0x2, 0x0,
        # 0x7, 0x0, 0x6, 0x0, 0x5, 0x0, 0x4, 0x1, 0xb4
        if self._way == '1':
            self._closed = True
            mac = self._mac.split('#')
            BYTES_STOP[2], BYTES_STOP[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_STOP[6], BYTES_STOP[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_STOP[-2] = 0x1
            resu_crc = checkcrc.xorcrc_hex(BYTES_STOP)
            BYTES_STOP[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_STOP
            })
            time.sleep(0.4)
            BYTES_STOP[2], BYTES_STOP[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_STOP[6], BYTES_STOP[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_STOP[-2] = 0x0
            resu_crc = checkcrc.xorcrc_hex(BYTES_STOP)
            BYTES_STOP[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_STOP
            })
        elif self._way == '2':
            self._closed = True
            mac = self._mac.split('#')
            BYTES_STOP[2], BYTES_STOP[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_STOP[6], BYTES_STOP[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_STOP[-8] = 0x1
            resu_crc = checkcrc.xorcrc_hex(BYTES_STOP)
            BYTES_STOP[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_STOP
            })
            time.sleep(0.4)
            BYTES_STOP[2], BYTES_STOP[3] = int(mac[0], 16), int(mac[1], 16)
            BYTES_STOP[6], BYTES_STOP[7] = int(mac[0], 16), int(mac[1], 16)
            BYTES_STOP[-8] = 0x0
            resu_crc = checkcrc.xorcrc_hex(BYTES_STOP)
            BYTES_STOP[-1] = resu_crc
            self._hass.services.call(POLY_ZIGBEE_DOMAIN, POLY_ZIGBEE_SERVICE, {
                "data": BYTES_STOP
            })

    def heart_beat(self):
        entity_id = 'cover.' + self.name
        self._hass.services.call('gateway', 'publish_heart_beat', {'entity_id': entity_id})