"""
Home Assistant 数据模型定义。

此模块包含与 Home Assistant 集成相关的所有数据类和类型定义，
用于在系统中表示 Home Assistant 的实体、状态、事件和服务。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Union, TypedDict
import re

# 类型别名
EntityId = str  # 例如 "light.living_room"
StateValue = Union[str, int, float, bool, None]  # 实体状态值类型
AttributeValue = Any  # 属性值可以是任何类型
AttributeDict = Dict[str, AttributeValue]  # 属性字典类型
ServiceData = Dict[str, Any]  # 服务调用数据类型
AreaId = str  # 区域ID类型

# 类型定义


class EntityCategory(Enum):
    """实体分类枚举。"""

    CONFIG = "config"  # 配置类实体
    DIAGNOSTIC = "diagnostic"  # 诊断类实体
    SYSTEM = "system"  # 系统类实体
    NONE = None  # 无分类


class EntityDomain(str, Enum):
    """实体域枚举。"""

    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    CLIMATE = "climate"
    MEDIA_PLAYER = "media_player"
    COVER = "cover"
    FAN = "fan"
    CAMERA = "camera"
    VACUUM = "vacuum"
    LOCK = "lock"
    ALARM_CONTROL_PANEL = "alarm_control_panel"
    AUTOMATION = "automation"
    SCENE = "scene"
    SCRIPT = "script"
    # 更多域...

    @classmethod
    def from_entity_id(cls, entity_id: EntityId) -> "EntityDomain":
        """从实体ID提取域。"""
        domain, _ = entity_id.split(".", 1)
        try:
            return cls(domain)
        except ValueError:
            return domain  # 返回字符串，如果不在枚举中


class DeviceClass(str, Enum):
    """设备类别枚举。"""

    # 传感器设备类别
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    POWER = "power"
    ENERGY = "energy"

    # 二进制传感器设备类别
    MOTION = "motion"
    DOOR = "door"
    WINDOW = "window"
    PRESENCE = "presence"

    # 更多设备类别...


class ConnectionType(str, Enum):
    """连接类型枚举。"""

    ZIGBEE = "zigbee"
    ZWAVE = "zwave"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    MATTER = "matter"
    THREAD = "thread"
    CLOUD = "cloud"
    LOCAL = "local"
    # 更多连接类型...


class EventType(str, Enum):
    """事件类型枚举。"""

    STATE_CHANGED = "state_changed"
    CALL_SERVICE = "call_service"
    SERVICE_REGISTERED = "service_registered"
    SERVICE_EXECUTED = "service_executed"
    DEVICE_REGISTRY_UPDATED = "device_registry_updated"
    ENTITY_REGISTRY_UPDATED = "entity_registry_updated"
    AREA_REGISTRY_UPDATED = "area_registry_updated"
    HOMEASSISTANT_START = "homeassistant_start"
    HOMEASSISTANT_STOP = "homeassistant_stop"
    # 更多事件类型...


# 数据类
@dataclass
class EntityState:
    """实体状态数据类。"""

    entity_id: EntityId
    state: StateValue
    attributes: AttributeDict = field(default_factory=dict)
    last_changed: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    context_id: Optional[str] = None
    context_parent_id: Optional[str] = None
    context_user_id: Optional[str] = None

    @property
    def domain(self) -> str:
        """获取实体的域。"""
        return self.entity_id.split(".", 1)[0]

    @property
    def object_id(self) -> str:
        """获取实体的对象ID。"""
        return self.entity_id.split(".", 1)[1]

    @property
    def name(self) -> str:
        """获取实体的友好名称。"""
        return self.attributes.get("friendly_name", self.object_id)


@dataclass
class EntityRegistry:
    """实体注册信息数据类。"""

    entity_id: EntityId
    unique_id: str
    platform: str
    name: Optional[str] = None
    icon: Optional[str] = None
    device_id: Optional[str] = None
    area_id: Optional[AreaId] = None
    original_name: Optional[str] = None
    # disabled: bool = False
    # hidden: bool = False
    # entity_category: Optional[EntityCategory] = None
    # device_class: Optional[str] = None
    # original_icon: Optional[str] = None
    # capabilities: Dict[str, Any] = field(default_factory=dict)
    # supported_features: int = 0
    # unit_of_measurement: Optional[str] = None
    # original_device_class: Optional[str] = None


@dataclass
class DeviceRegistry:
    """设备注册信息数据类。"""

    id: str
    name: Optional[str] = None
    name_by_user: Optional[str] = None
    identifiers: Set[tuple] = field(default_factory=set)
    connections: Set[tuple] = field(default_factory=set)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    sw_version: Optional[str] = None
    hw_version: Optional[str] = None
    via_device_id: Optional[str] = None
    area_id: Optional[AreaId] = None
    disabled_by: Optional[str] = None
    entry_type: Optional[str] = None
    configuration_url: Optional[str] = None


@dataclass
class AreaRegistry:
    """区域注册信息数据类。"""

    id: AreaId
    name: str
    picture: Optional[str] = None


@dataclass
class Service:
    """服务定义数据类。"""

    domain: str
    service: str
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    target: Optional[Dict[str, Any]] = None

    @property
    def service_id(self) -> str:
        """获取完整的服务ID (domain.service)。"""
        return f"{self.domain}.{self.service}"


@dataclass
class StateChangedEvent:
    """状态变更事件数据类。"""

    entity_id: EntityId
    old_state: Optional[EntityState]
    new_state: Optional[EntityState]
    event_id: Optional[str] = None
    time_fired: Optional[datetime] = None


@dataclass
class ServiceCallEvent:
    """服务调用事件数据类。"""

    domain: str
    service: str
    service_data: ServiceData
    target: Optional[Dict[str, Any]] = None
    event_id: Optional[str] = None
    time_fired: Optional[datetime] = None


class WebSocketMessage(TypedDict, total=False):
    """WebSocket 消息类型定义。"""

    id: int
    type: str
    event: Dict[str, Any]
    result: Any
    success: bool
    error: Dict[str, Any]


# 辅助函数
def parse_entity_id(entity_id: EntityId) -> tuple:
    """
    解析实体ID为域和对象ID。

    Args:
        entity_id: 实体ID字符串，例如 "light.living_room"

    Returns:
        包含域和对象ID的元组

    Raises:
        ValueError: 如果实体ID格式不正确
    """
    parts = entity_id.split(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid entity ID format: {entity_id}")
    return (parts[0], parts[1])


def create_entity_id(domain: str, name: str) -> EntityId:
    """
    从域和名称创建实体ID。

    Args:
        domain: 实体域
        name: 实体名称

    Returns:
        格式化的实体ID
    """
    # 将名称转换为小写并替换非法字符
    object_id = re.sub(r"[^a-z0-9_]", "_", name.lower())
    return f"{domain}.{object_id}"


class EntityStateHelper:
    """实体状态辅助类，提供常见的状态处理方法。"""

    @staticmethod
    def is_on(state: EntityState) -> bool:
        """检查实体是否处于开启状态。"""
        return state.state in ("on", "home", "open", "unlocked", "active", "playing")

    @staticmethod
    def is_off(state: EntityState) -> bool:
        """检查实体是否处于关闭状态。"""
        return state.state in (
            "off",
            "not_home",
            "closed",
            "locked",
            "inactive",
            "idle",
            "paused",
            "standby",
        )

    @staticmethod
    def is_unavailable(state: EntityState) -> bool:
        """检查实体是否不可用。"""
        return state.state in ("unavailable", "unknown", "none", "notset")

    @staticmethod
    def get_numeric_value(state: EntityState) -> Optional[float]:
        """尝试获取状态的数值表示。"""
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None


# 特定域的模型
@dataclass
class LightCapabilities:
    """灯光实体的能力描述。"""

    supports_brightness: bool = False
    supports_color_temp: bool = False
    supports_color: bool = False
    supports_transition: bool = False
    supports_flash: bool = False
    supports_effect: bool = False
    min_mireds: Optional[int] = None
    max_mireds: Optional[int] = None
    effect_list: List[str] = field(default_factory=list)

    @classmethod
    def from_attributes(cls, attributes: AttributeDict) -> "LightCapabilities":
        """从实体属性创建能力对象。"""
        supported_features = attributes.get("supported_features", 0)
        return cls(
            supports_brightness=bool(supported_features & 1),
            supports_color_temp=bool(supported_features & 2),
            supports_color=bool(supported_features & 16),
            supports_transition=bool(supported_features & 32),
            supports_flash=bool(supported_features & 4),
            supports_effect=bool(supported_features & 8),
            min_mireds=attributes.get("min_mireds"),
            max_mireds=attributes.get("max_mireds"),
            effect_list=attributes.get("effect_list", []),
        )


@dataclass
class ClimateCapabilities:
    """空调/恒温器实体的能力描述。"""

    hvac_modes: List[str] = field(default_factory=list)
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    target_temp_step: Optional[float] = None
    supports_preset: bool = False
    preset_modes: List[str] = field(default_factory=list)
    supports_swing_mode: bool = False
    swing_modes: List[str] = field(default_factory=list)
    supports_fan_mode: bool = False
    fan_modes: List[str] = field(default_factory=list)

    @classmethod
    def from_attributes(cls, attributes: AttributeDict) -> "ClimateCapabilities":
        """从实体属性创建能力对象。"""
        supported_features = attributes.get("supported_features", 0)
        return cls(
            hvac_modes=attributes.get("hvac_modes", []),
            min_temp=attributes.get("min_temp"),
            max_temp=attributes.get("max_temp"),
            target_temp_step=attributes.get("target_temp_step"),
            supports_preset=bool(supported_features & 16),
            preset_modes=attributes.get("preset_modes", []),
            supports_swing_mode=bool(supported_features & 8),
            swing_modes=attributes.get("swing_modes", []),
            supports_fan_mode=bool(supported_features & 4),
            fan_modes=attributes.get("fan_modes", []),
        )


# 意图相关的模型
@dataclass
class EntityIntent:
    """表示针对特定实体的意图。"""

    entity_id: EntityId
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_service_call(self) -> tuple:
        """
        将意图转换为服务调用。

        Returns:
            包含域、服务和数据的元组
        """
        domain = self.entity_id.split(".", 1)[0]
        service_data = {"entity_id": self.entity_id, **self.parameters}

        # 基于域和动作确定服务
        if domain == "light":
            if self.action == "turn_on":
                return (domain, "turn_on", service_data)
            elif self.action == "turn_off":
                return (domain, "turn_off", service_data)
            elif self.action == "toggle":
                return (domain, "toggle", service_data)
        # 更多域的处理...

        # 默认情况
        return (domain, self.action, service_data)


@dataclass
class SceneIntent:
    """表示激活场景的意图。"""

    scene_id: str

    def to_service_call(self) -> tuple:
        """转换为服务调用。"""
        return ("scene", "turn_on", {"entity_id": self.scene_id})


@dataclass
class AreaIntent:
    """表示针对特定区域的意图。"""

    area_id: AreaId
    action: str
    domain: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_service_calls(self, area_entities: List[EntityId]) -> List[tuple]:
        """
        将区域意图转换为多个服务调用。

        Args:
            area_entities: 区域内的实体ID列表

        Returns:
            服务调用元组列表
        """
        calls = []
        for entity_id in area_entities:
            entity_domain = entity_id.split(".", 1)[0]

            # 如果指定了域，则只处理该域的实体
            if self.domain and entity_domain != self.domain:
                continue

            # 创建实体意图并转换为服务调用
            entity_intent = EntityIntent(
                entity_id=entity_id, action=self.action, parameters=self.parameters
            )
            calls.append(entity_intent.to_service_call())

        return calls
