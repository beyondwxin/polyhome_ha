import logging

from homeassistant.const import (CONF_API_KEY, CONF_NAME, ATTR_ATTRIBUTION, CONF_ID)
import voluptuous as vol
from datetime import timedelta
from homeassistant.const import (
    CONF_API_KEY, CONF_NAME, CONF_MONITORED_CONDITIONS, ATTR_ATTRIBUTION,
    CONF_LATITUDE, CONF_LONGITUDE)
from homeassistant.const import TEMP_CELSIUS ,CONF_LATITUDE, CONF_LONGITUDE,CONF_API_KEY
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS)
import requests


_Log=logging.getLogger(__name__)

CONF_REALTIME = 'realtime'
CONF_PRECIPITATION = 'precipitation'
CONF_HOURLY = 'hourly'
CONF_MINUTELY = 'minutely'
CONF_DAILY = 'daily'

REALTIME_TYPES = {
    'temperature': ['temperature', '°C', 'mdi:thermometer'],
    'skycon': ['skycon', None, None],
    'cloudrate': ['cloudrate', '%', 'mdi:weather-partlycloudy'],
    'aqi': ['AQI', None, 'mdi:cloud-outline'],
    'humidity': ['humidity', '%', 'mdi:water-percent'],
    'pm25': ['pm25', 'μg/m3', 'mdi:blur'],
}
PRECIPITATION_TYPE = {
    'nearest_precipitation_distance': ['distance', 'km', 'mdi:near-me'],
    'nearest_precipitation_intensity': ['intensity', 'mm', 'mdi:weather-pouring'],
    'local_precipitation_intensity': ['intensity', 'mm', 'mdi:weather-pouring'],
    'local_datasource': ['datasource', None, 'mdi:database'],
    'wind_direction': ['direction', '°', 'mdi:compass'],
    'wind_speed': ['speed', 'Km/h', 'mdi:weather-windy'],
}
HOURLY_TYPE = {
    'skycon': ['skycon', None,None],
    'cloudrate': ['cloudrate', '%','mdi:weather-partlycloudy'],
    'aqi': ['AQI', None,'mdi:cloud-outline'],
    'humidity': ['humidity', '%','mdi:water-percent'],
    'pm25': ['pm25', 'μg/m3','mdi:blur'],
    'precipitation': ['precipitation', 'mm','mdi:weather-rainy'],
    'wind': ['speed','Km/h','mdi:weather-windy'],
    'temperature': ['temperature', '°C','mdi:thermometer'],
}
MINUTELY_TYPE = {
    'description':['description', None,'mdi:cloud-print-outline'],
    'probability_0':['probability' ,'%','mdi:weather-pouring'],
    'probability_1':['probability' ,'%','mdi:weather-pouring'],
    'probability_2':['probability' ,'%','mdi:weather-pouring'],
    'probability_3':['probability' ,'%','mdi:weather-pouring'],
}
DAILY_TYPE = {
    'coldRisk': ['desc',None,'mdi:hospital'],
    'temperature_max' :['max','°C','mdi:thermometer'],
    'temperature_avg': ['avg','°C','mdi:thermometer'],
    'temperature_min': ['min','°C','mdi:thermometer'],
    'skycon': ['skycon', None,None],
    'cloudrate_max': ['max', '%','mdi:weather-partlycloudy'],
    'cloudrate_avg': ['avg', '%','mdi:weather-partlycloudy'],
    'cloudrate_min': ['min', '%','mdi:weather-partlycloudy'],
    'aqi_max': ['max', None,'mdi:cloud-outline'],
    'aqi_avg': ['avg', None,'mdi:cloud-outline'],
    'aqi_min': ['min', None,'mdi:cloud-outline'],
    'humidity_max': ['max', '%','mdi:water-percent'],
    'humidity_avg': ['avg', '%','mdi:water-percent'],
    'humidity_min': ['min', '%','mdi:water-percent'],
    'sunset':['sunset',None,'mdi:weather-sunset-down'],
    'sunrise':['sunrise',None,'mdi:weather-sunset-up'],
    'ultraviolet':['ultraviolet',None,'mdi:umbrella'],
    'pm25_max': ['max', 'μg/m3','mdi:blur'],
    'pm25_avg': ['avg', 'μg/m3','mdi:blur'],
    'pm25_min': ['min', 'μg/m3','mdi:blur'],
    'dressing':['desc',None,'mdi:tshirt-crew'],
    'carWashing':['carWashing',None,'mdi:car'],
    'precipitation_max' : ['max','mm','mdi:weather-rainy'],
    'precipitation_avg': ['avg','mm','mdi:weather-rainy'],
    'precipitation_min': ['min','mm','mdi:weather-rainy'],
}

MODULE_SCHEMA = vol.Schema({
    vol.Required(CONF_REALTIME,default=[]):vol.All(cv.ensure_list,[vol.In(REALTIME_TYPES)]),
    vol.Required(CONF_PRECIPITATION,default=[]):vol.All(cv.ensure_list,[vol.In(PRECIPITATION_TYPE)]),
    vol.Required(CONF_HOURLY,default=[]):vol.All(cv.ensure_list,[vol.In(HOURLY_TYPE)]),
    vol.Required(CONF_MINUTELY,default=[]):vol.All(cv.ensure_list,[vol.In(MINUTELY_TYPE)]),
    vol.Required(CONF_DAILY,default=[]):vol.All(cv.ensure_list,[vol.In(DAILY_TYPE)]),
})
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS): MODULE_SCHEMA,
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    latitude = hass.config.latitude
    longitude = hass.config.longitude
    api_key = config.get(CONF_API_KEY,None)
    sensor_name = config.get(CONF_NAME)
    monitored_conditions = config[CONF_MONITORED_CONDITIONS]
    if api_key == None:
        _Log.error('Pls enter api_key!')
        return False

    dev = []
    if  CONF_REALTIME in monitored_conditions:
        realtimeSensor = monitored_conditions['realtime']
        if isinstance(realtimeSensor, list):
            if len(realtimeSensor) == 0:
                sensor_name = REALTIME_TYPES['temperature'][0]
                measurement =  REALTIME_TYPES['temperature'][1]
                icon = REALTIME_TYPES['temperature'][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_REALTIME, 'temperature', sensor_name,measurement))
            for sensor in realtimeSensor:
                sensor_name = REALTIME_TYPES[sensor][0]
                measurement = REALTIME_TYPES[sensor][1]
                icon = REALTIME_TYPES[sensor][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_REALTIME, sensor, sensor_name,measurement,icon))
    if  CONF_PRECIPITATION in monitored_conditions:
        precipitationSensor = monitored_conditions['precipitation']
        if isinstance(precipitationSensor, list):
            if len(precipitationSensor) == 0:
                sensor_name = PRECIPITATION_TYPE['nearest_precipitation_distance'][0]
                measurement =  PRECIPITATION_TYPE['nearest_precipitation_distance'][1]
                icon =  PRECIPITATION_TYPE['nearest_precipitation_distance'][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_PRECIPITATION, 'nearest_precipitation_distance', sensor_name,measurement))
            for sensor in precipitationSensor:
                sensor_name = PRECIPITATION_TYPE[sensor][0]
                measurement = PRECIPITATION_TYPE[sensor][1]
                icon =  PRECIPITATION_TYPE[sensor][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_PRECIPITATION, sensor, sensor_name,measurement,icon))

    if  CONF_HOURLY in monitored_conditions:
        hourlySensor = monitored_conditions['hourly']
        if isinstance(hourlySensor, list):
            if len(hourlySensor) == 0:
                sensor_name = HOURLY_TYPE['description'][0]
                measurement =  HOURLY_TYPE['description'][1]
                icon =  HOURLY_TYPE['description'][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_HOURLY, 'description', sensor_name,measurement))
            for sensor in hourlySensor:
                sensor_name = HOURLY_TYPE[sensor][0]
                measurement = HOURLY_TYPE[sensor][1]
                icon =  HOURLY_TYPE[sensor][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_HOURLY, sensor, sensor_name,measurement,icon))
    if  CONF_MINUTELY in monitored_conditions:
        minutelySensor = monitored_conditions['minutely']
        if isinstance(minutelySensor, list):
            if len(minutelySensor) == 0:
                sensor_name = MINUTELY_TYPE['description'][0]
                measurement =  MINUTELY_TYPE['description'][1]
                icon =  MINUTELY_TYPE['description'][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_MINUTELY, 'description', sensor_name,measurement))
            for sensor in minutelySensor:
                sensor_name = MINUTELY_TYPE[sensor][0]
                measurement = MINUTELY_TYPE[sensor][1]
                icon =  MINUTELY_TYPE[sensor][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_MINUTELY, sensor, sensor_name,measurement,icon))
    if  CONF_DAILY in monitored_conditions:
        dailySensor = monitored_conditions['daily']
        if isinstance(dailySensor, list):
            if len(dailySensor) == 0:
                sensor_name = DAILY_TYPE['coldRisk'][0]
                measurement =  DAILY_TYPE['coldRisk'][1]
                icon =  DAILY_TYPE['coldRisk'][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_DAILY, 'coldRisk', sensor_name,measurement))
            for sensor in dailySensor:
                sensor_name = DAILY_TYPE[sensor][0]
                measurement = DAILY_TYPE[sensor][1]
                icon = DAILY_TYPE[sensor][2]
                dev.append(CaiyunSensor(latitude,longitude,api_key, CONF_DAILY, sensor, sensor_name,measurement,icon))
    
    add_devices(dev,True)


class CaiyunSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, latitude, longitude, api_key, sensor_Type, sensor,sensor_name, measurement,icon):
        self.latitude = latitude
        self.longitude = longitude
        self._sensor_Type = sensor_Type
        self.api_key = api_key
        self._sensor = sensor
        self.attributes = {}
        self._state = None
        self._name = sensor_name
        self.data = None
        self.measurement = measurement
        self._icon = icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'CaiYun' + '_'  + self._sensor_Type + '_' + self._sensor

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self.attributes
    
    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self.measurement

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        resp = requests.get("https://api.caiyunapp.com/v2/%s/%s,%s/realtime" % (self.api_key,self.longitude,self.latitude))
        if resp.status_code != 200:
            _Log.error('http get data Error StatusCode:%s' % resp.status_code)
            return
        self.data_currently = resp.json()
        if not 'result' in self.data_currently:
            _Log.error('Json Status Error1!')
            return
        if self._sensor_Type == CONF_REALTIME:
            if self._sensor ==  'skycon':
                self.data_currently = self.data_currently['result']
                if self.data_currently ['skycon'] == 'CLEAR_DAY':
                    self._state = '晴天'
                elif self.data_currently ['skycon'] == 'CLEAR_NIGHT':
                    self._state = '晴夜'
                elif self.data_currently ['skycon'] == 'PARTLY_CLOUDY_DAY':
                    self._state = '多云'
                elif self.data_currently ['skycon'] == 'PARTLY_CLOUDY_NIGHT':
                    self._state = '多云'
                elif self.data_currently ['skycon'] == 'CLOUDY':
                    self._state = '阴'
                elif self.data_currently ['skycon'] == 'RAIN':
                    self._state = '雨'
                elif self.data_currently ['skycon'] == 'SNOW':
                    self._state = '雪'
                elif self.data_currently ['skycon'] == 'WIND':
                    self._state = '风'
                elif self.data_currently ['skycon'] == 'FOG':
                    self._state = '雾'
                else:
                    self._state = '无数据'
            elif self._sensor == 'cloudrate':
                self._state = self.data_currently['result']['cloudrate']*100
            elif sel._sensor == 'humidity':
                self._state = self.data_currently['result']['humidity']*100
            else:
                self.data_currently = self.data_currently['result']
                self._state = self.data_currently [self._sensor]

        if self._sensor_Type == CONF_PRECIPITATION:
            if self._sensor ==  'nearest_precipitation_distance':
                self.data_currently = self.data_currently['result']['precipitation']['nearest']
                self._state = self.data_currently ['distance']
            if self._sensor ==  'nearest_precipitation_intensity':
                self.data_currently = self.data_currently['result']['precipitation']['nearest']
                self._state = self.data_currently ['intensity']
            if self._sensor ==  'local_precipitation_intensity':
                self.data_currently = self.data_currently['result']['precipitation']['local']
                self._state = self.data_currently ['intensity']
            if self._sensor ==  'local_datasource':
                self.data_currently = self.data_currently['result']['precipitation']['local']
                self._state = self.data_currently ['datasource']
            if self._sensor ==  'wind_direction':
                self.data_currently = self.data_currently['result']['wind']
                self._state = self.data_currently ['direction']
            if self._sensor ==  'wind_speed':
                self.data_currently = self.data_currently['result']['wind']
                self._state = self.data_currently ['speed']

        resp2 = requests.get("https://api.caiyunapp.com/v2/%s/%s,%s/forecast" % (self.api_key,self.longitude,self.latitude))
        if resp2.status_code != 200:
            _Log.error('http get data Error StatusCode:%s' % resp2.status_code)
            return
        self.data_forecast = resp2.json()
        if not 'result' in self.data_forecast:
            _Log.error('Json Status Error1!')
            return
        if self._sensor_Type == CONF_HOURLY:
            if self._sensor ==  'description':
                self.data_forecast = self.data_forecast['result']['hourly']
                self._state = self.data_forecast ['description']
            if self._sensor ==  'skycon':
                self.data_forecast = self.data_forecast['result']['hourly']
                if self.data_forecast ['skycon'][0]['value'] == 'CLEAR_DAY':
                    self._state = '晴天'
                elif self.data_forecast ['skycon'][0]['value'] == 'CLEAR_NIGHT':
                    self._state = '晴夜'
                elif self.data_forecast ['skycon'][0]['value'] == 'PARTLY_CLOUDY_DAY':
                    self._state = '多云'
                elif self.data_forecast ['skycon'][0]['value'] == 'PARTLY_CLOUDY_NIGHT':
                    self._state = '多云'
                elif self.data_forecast ['skycon'][0]['value'] == 'CLOUDY':
                    self._state = '阴'
                elif self.data_forecast ['skycon'][0]['value'] == 'RAIN':
                    self._state = '雨'
                elif self.data_forecast ['skycon'][0]['value'] == 'SNOW':
                    self._state = '雪'
                elif self.data_forecast ['skycon'][0]['value'] == 'WIND':
                    self._state = '风'
                elif self.data_forecast ['skycon'][0]['value'] == 'FOG':
                    self._state = '雾'
                else:
                    self._state = '无数据'
            if self._sensor ==  'cloudrate':
                self.data_forecast = self.data_forecast['result']['hourly']
                self._state = int(self.data_forecast ['cloudrate'][0]['value']*100)
            if self._sensor ==  'aqi':
                self.data_forecast = self.data_forecast['result']['hourly']
                self._state = self.data_forecast ['aqi'][0]['value']
            if self._sensor ==  'humidity':
                self.data_forecast = self.data_forecast['result']['hourly']
                self._state = int(self.data_forecast ['humidity'][0]['value']*100)

            if self._sensor ==  'pm25':
                self.data_forecast = self.data_forecast['result']['hourly']
                self._state = self.data_forecast ['pm25'][0]['value']
            if self._sensor ==  'precipitation':
                self.data_forecast = self.data_forecast['result']['hourly']
                self._state = self.data_forecast ['precipitation'][0]['value']
            if self._sensor ==  'wind':
                self.data_forecast = self.data_forecast['result']['hourly']
                self._state = self.data_forecast ['wind'][0]['speed']
            if self._sensor ==  'temperature':
                self.data_forecast = self.data_forecast['result']['hourly']
                self._state = self.data_forecast ['temperature'][0]['value']
        if self._sensor_Type == CONF_MINUTELY:
            if self._sensor ==  'description':
                self.data_forecast = self.data_forecast['result']['minutely']
                self._state = self.data_forecast ['description']
            if self._sensor ==  'probability_0':
                self.data_forecast = self.data_forecast['result']['minutely']['probability']
                self._state = self.data_forecast [0]*100
            if self._sensor ==  'probability_1':
                self.data_forecast = self.data_forecast['result']['minutely']['probability']
                self._state = self.data_forecast [1]*100
            if self._sensor ==  'probability_2':
                self.data_forecast = self.data_forecast['result']['minutely']['probability']
                self._state = self.data_forecast [2]*100
            if self._sensor ==  'probability_3':
                self.data_forecast = self.data_forecast['result']['minutely']['probability']
                self._state = self.data_forecast [3]*100
        if self._sensor_Type == CONF_DAILY:
            if self._sensor ==  'coldRisk':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['coldRisk'][0]['desc']
            if self._sensor ==  'temperature_max':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['temperature'][0]['max']
            if self._sensor ==  'temperature_avg':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['temperature'][0]['avg']
            if self._sensor ==  'temperature_min':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['temperature'][0]['min']
            if self._sensor ==  'skycon':
                self.data_forecast = self.data_forecast['result']['daily']
                if self.data_forecast ['skycon'][0]['value'] == 'CLEAR_DAY':
                    self._state = '晴天'
                elif self.data_forecast ['skycon'][0]['value'] == 'CLEAR_NIGHT':
                    self._state = '晴夜'
                elif self.data_forecast ['skycon'][0]['value'] == 'PARTLY_CLOUDY_DAY':
                    self._state = '多云'
                elif self.data_forecast ['skycon'][0]['value'] == 'PARTLY_CLOUDY_NIGHT':
                    self._state = '多云'
                elif self.data_forecast ['skycon'][0]['value'] == 'CLOUDY':
                    self._state = '阴'
                elif self.data_forecast ['skycon'][0]['value'] == 'RAIN':
                    self._state = '雨'
                elif self.data_forecast ['skycon'][0]['value'] == 'SNOW':
                    self._state = '雪'
                elif self.data_forecast ['skycon'][0]['value'] == 'WIND':
                    self._state = '风'
                elif self.data_forecast ['skycon'][0]['value'] == 'FOG':
                    self._state = '雾'
                else:
                    self._state = '无数据'
            if self._sensor ==  'cloudrate_max':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = int(self.data_forecast ['cloudrate'][0]['max']*100)
            if self._sensor ==  'cloudrate_avg':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = int(self.data_forecast ['cloudrate'][0]['avg']*100)
            if self._sensor ==  'cloudrate_min':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = int(self.data_forecast ['cloudrate'][0]['min'])*100
            if self._sensor ==  'aqi_max':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['aqi'][0]['max']
            if self._sensor ==  'aqi_avg':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['aqi'][0]['avg']
            if self._sensor ==  'aqi_min':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['aqi'][0]['min']
            if self._sensor ==  'humidity_max':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = int(self.data_forecast ['humidity'][0]['max']*100)
            if self._sensor ==  'humidity_avg':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = int(self.data_forecast ['humidity'][0]['avg']*100)
            if self._sensor ==  'humidity_min':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = int(self.data_forecast ['humidity'][0]['min']*100)
            if self._sensor ==  'sunset':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['astro'][0]['sunset']
            if self._sensor ==  'sunrise':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['astro'][0]['sunrise']
            if self._sensor ==  'ultraviolet':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['ultraviolet'][0]['desc']
            if self._sensor ==  'pm25_max':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['pm25'][0]['max']
            if self._sensor ==  'pm25_avg':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['pm25'][0]['avg']
            if self._sensor ==  'pm25_min':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['pm25'][0]['min']
            if self._sensor ==  'dressing':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['dressing'][0]['desc']
            if self._sensor ==  'carWashing':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['carWashing'][0]['desc']
            if self._sensor ==  'precipitation_max':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['precipitation'][0]['max']
            if self._sensor ==  'precipitation_avg':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['precipitation'][0]['avg']
            if self._sensor ==  'precipitation_min':
                self.data_forecast = self.data_forecast['result']['daily']
                self._state = self.data_forecast ['precipitation'][0]['min']
