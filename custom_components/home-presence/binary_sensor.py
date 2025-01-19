"""House Presence integration."""
from enum import StrEnum
import logging
from datetime import datetime

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize config entry."""
    name = config_entry.title
    unique_id = config_entry.entry_id
    graph = config_entry.graph

    _motion_sensors = config_entry.options["motion_sensors"]
    _LOGGER.debug("motion_sensors: %s", _motion_sensors)
    _LOGGER.debug("graph: %s", graph)

    # Validate + resolve entity registry id to entity_id
    registry = er.async_get(hass)
    motion_sensors = [er.async_validate_entity_id(registry, e) for e in _motion_sensors]

    async_add_entities(
        [HomePresenseBinarySensor(hass, unique_id, name, motion_sensors, graph)]
    )


class STATES(StrEnum):
    """Possible states of the home presense binary sensor."""

    S0 = "vacant"
    S1 = "occupied"


class HomePresenseBinarySensor(BinarySensorEntity):
    """Representation of a home presense binary sensor."""

    def __init__(
        self,
        hass,
        unique_id: str,
        name: str,
        motion_sensors,
        graph,
    ) -> None:
        """Initialize the home presense binary sensor."""
        self._hass = hass
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self._attr_should_poll = False
        self._attr_available = True

        self.motion_sensors = motion_sensors
        self.graph = graph

        self._state: STATES = STATES.S0
        self._s1 = True
        self._time = None
        self._listeners = []

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the class of this entity."""
        return self._attr_device_class

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._state in [STATES.S1*self._s1]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "state": self._state,
            "last_triggered": self._time,
        }

    async def async_added_to_hass(self) -> None:
        """Connect listeners when added to hass."""
        self._listeners.append(
            async_track_state_change_event(
                self._hass, self.motion_sensors, self.motion_event_handler
            )
        )

    async def motion_event_handler(self, event):
        """Handle motion events."""
        _entity_id = event.data.get("entity_id")
        _old_state = event.data.get("old_state")
        _new_state = event.data.get("new_state")
        await self._motion_handler(_entity_id, _old_state, _new_state)

    async def _motion_handler(self, entity_id, old_state, new_state):
        match self._state:
            case STATES.S0:
                if new_state.state == "on":
                    self._state = STATES.S1
            case STATES.S1:
                if new_state.state == "off":
                    self._state = STATES.S0
        await self.update_state()


    async def update_state(self):
        """Update the state of the sensor."""
        self._time = datetime.now()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect listeners on removal."""
        for listener in self._listeners:
            listener()
        self._listeners.clear()

    # def get_motion_state(self):
    #     """Return the state of the motion sensors."""
    #     for sensor in self.motion_sensors:
    #         if self._hass.states.get(sensor).state == "on":
    #             return True
    #     return False
