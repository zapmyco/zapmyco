"""
Home Assistant 客户端模块。

此模块提供了与 Home Assistant 实例交互的客户端实现，
支持 REST API 和 WebSocket API，用于获取状态、调用服务和接收事件。
"""

import asyncio
import json
import logging
import ssl
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, cast
import aiohttp
import async_timeout
from dataclasses import asdict
from zapmyco.config import settings
from zapmyco.integrations.home_assistant.models import (
    AreaRegistry,
    DeviceRegistry,
    EntityRegistry,
    EntityState,
    EventType,
    Service,
    StateChangedEvent,
    ServiceCallEvent,
)

logger = logging.getLogger(__name__)


class HomeAssistantError(Exception):
    """Home Assistant 客户端错误基类。"""

    pass


class AuthenticationError(HomeAssistantError):
    """认证错误。"""

    pass


class ConnectionError(HomeAssistantError):
    """连接错误。"""

    pass


class RequestError(HomeAssistantError):
    """请求错误。"""

    pass


class WebSocketError(HomeAssistantError):
    """WebSocket 错误。"""

    pass


class HomeAssistantClient:
    """
    Home Assistant 客户端类。

    提供与 Home Assistant 实例交互的方法，包括：
    - REST API 调用
    - WebSocket 连接管理
    - 状态获取和监听
    - 服务调用
    - 事件订阅
    """

    def __init__(self):
        """
        初始化 Home Assistant 客户端。
        """
        self.base_url = settings.HASS_URL.rstrip("/")
        self.access_token = settings.HASS_ACCESS_TOKEN
        self.verify_ssl = settings.HASS_VERIFY_SSL
        self.websocket_timeout = settings.HASS_WEBSOCKET_TIMEOUT

        # API 会话
        self._session: Optional[aiohttp.ClientSession] = None

        # WebSocket 连接
        self._ws_connection: Optional[aiohttp.ClientWebSocketResponse] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._ws_id = 0
        self._ws_callbacks: Dict[int, asyncio.Future] = {}
        self._ws_event_callbacks: Dict[str, List[Callable]] = {}
        self._ws_connected = False
        self._ws_reconnect_interval = 1
        self._ws_max_reconnect_interval = 300  # 5 分钟
        self._ws_shutdown = False

        # 缓存
        self._states_cache: Dict[str, EntityState] = {}
        self._registry_cache: Dict[str, EntityRegistry] = {}
        self._device_cache: Dict[str, DeviceRegistry] = {}
        self._area_cache: Dict[str, AreaRegistry] = {}
        self._service_cache: Dict[str, Service] = {}

    async def __aenter__(self) -> "HomeAssistantClient":
        """异步上下文管理器入口。"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器退出。"""
        await self.disconnect()

    async def connect(self) -> bool:
        """
        连接到 Home Assistant 实例。

        Returns:
            连接是否成功
        """
        logger.info("正在连接到 Home Assistant: %s", self.base_url)

        # 创建 HTTP 会话
        if self._session is None or self._session.closed:
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                connector=aiohttp.TCPConnector(ssl=ssl_context),
            )

        # 测试 API 连接
        try:
            await self._api_call("GET", "/api/")
            logger.info("已成功连接到 Home Assistant REST API")
        except Exception as e:
            logger.error("连接到 Home Assistant REST API 失败: %s", str(e))
            await self.disconnect()
            return False

        # 连接 WebSocket
        try:
            await self._connect_websocket()
            logger.info("已成功连接到 Home Assistant WebSocket API")
        except Exception as e:
            logger.error("连接到 Home Assistant WebSocket API 失败: %s", str(e))
            await self.disconnect()
            return False

        return True

    async def disconnect(self) -> None:
        """断开与 Home Assistant 的连接。"""
        logger.info("正在断开与 Home Assistant 的连接")

        # 停止 WebSocket 任务
        self._ws_shutdown = True
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        # 关闭 WebSocket 连接
        if self._ws_connection and not self._ws_connection.closed:
            await self._ws_connection.close()
        self._ws_connection = None
        self._ws_connected = False

        # 清理回调
        for future in self._ws_callbacks.values():
            if not future.done():
                future.cancel()
        self._ws_callbacks.clear()
        self._ws_event_callbacks.clear()

        # 关闭 HTTP 会话
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _api_call(
        self, method: str, path: str, data: Any = None, timeout: int = 10
    ) -> Any:
        """
        执行 REST API 调用。

        Args:
            method: HTTP 方法 (GET, POST, etc.)
            path: API 路径
            data: 请求数据
            timeout: 超时时间（秒）

        Returns:
            API 响应数据

        Raises:
            AuthenticationError: 认证失败
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        if self._session is None or self._session.closed:
            raise ConnectionError("未连接到 Home Assistant")

        url = f"{self.base_url}{path}"

        try:
            async with async_timeout.timeout(timeout):
                async with self._session.request(
                    method, url, json=data if data else None
                ) as resp:
                    if resp.status == 401:
                        raise AuthenticationError("认证失败")
                    elif resp.status >= 400:
                        error_text = await resp.text()
                        raise RequestError(f"请求失败: {resp.status} - {error_text}")

                    if resp.status == 204:  # No content
                        return None

                    return await resp.json()
        except asyncio.TimeoutError:
            raise ConnectionError(f"请求超时: {url}")
        except aiohttp.ClientError as e:
            raise ConnectionError(f"请求错误: {str(e)}")

    async def _connect_websocket(self) -> None:
        """
        连接到 WebSocket API。

        Raises:
            ConnectionError: 连接错误
            AuthenticationError: 认证失败
            WebSocketError: WebSocket 错误
        """
        if self._session is None or self._session.closed:
            raise ConnectionError("未连接到 Home Assistant")

        # 构建 WebSocket URL
        ws_url = f"{self.base_url.replace('http://', 'ws://').replace('https://', 'wss://')}/api/websocket"

        try:
            self._ws_connection = await self._session.ws_connect(
                ws_url, heartbeat=55, ssl=not self.verify_ssl
            )

            # 等待 auth_required 消息
            msg = await self._ws_connection.receive_json()
            if msg["type"] != "auth_required":
                raise WebSocketError(f"意外的初始消息: {msg['type']}")

            # 发送认证
            await self._ws_connection.send_json(
                {
                    "type": "auth",
                    "access_token": self.access_token,
                }
            )

            # 等待 auth_ok 消息
            msg = await self._ws_connection.receive_json()
            if msg["type"] != "auth_ok":
                raise AuthenticationError(
                    f"认证失败: {msg.get('message', 'Unknown error')}"
                )

            # 启动 WebSocket 处理任务
            self._ws_id = 0
            self._ws_connected = True
            self._ws_shutdown = False
            self._ws_task = asyncio.create_task(self._websocket_loop())

            # 重置重连间隔
            self._ws_reconnect_interval = 1

            # 订阅状态变更事件
            await self.subscribe_events(EventType.STATE_CHANGED)

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise ConnectionError(f"WebSocket 连接错误: {str(e)}")

    async def _websocket_loop(self) -> None:
        """WebSocket 消息处理循环。"""
        try:
            while (
                not self._ws_shutdown
                and self._ws_connection
                and not self._ws_connection.closed
            ):
                try:
                    msg = await self._ws_connection.receive_json()

                    if msg["type"] == "pong":
                        continue

                    elif msg["type"] == "event":
                        await self._handle_event(msg)

                    elif "id" in msg:
                        await self._handle_response(msg)

                except (json.JSONDecodeError, KeyError) as e:
                    logger.error("解析 WebSocket 消息失败: %s", str(e))

                except asyncio.CancelledError:
                    break

                except Exception as e:
                    logger.exception("处理 WebSocket 消息时出错: %s", str(e))

        except asyncio.CancelledError:
            # 任务被取消，正常退出
            pass

        except Exception as e:
            if not self._ws_shutdown:
                logger.error("WebSocket 连接中断: %s", str(e))
                await self._handle_websocket_disconnect()

    async def _handle_websocket_disconnect(self) -> None:
        """处理 WebSocket 断开连接。"""
        self._ws_connected = False

        # 取消所有等待中的回调
        for future in self._ws_callbacks.values():
            if not future.done():
                future.set_exception(WebSocketError("WebSocket 连接已断开"))
        self._ws_callbacks.clear()

        if self._ws_shutdown:
            return

        # 尝试重新连接
        logger.info("尝试在 %d 秒后重新连接 WebSocket", self._ws_reconnect_interval)
        await asyncio.sleep(self._ws_reconnect_interval)

        # 指数退避重连
        self._ws_reconnect_interval = min(
            self._ws_reconnect_interval * 2, self._ws_max_reconnect_interval
        )

        try:
            await self._connect_websocket()
            logger.info("已成功重新连接到 WebSocket")
        except Exception as e:
            logger.error("重新连接 WebSocket 失败: %s", str(e))
            asyncio.create_task(self._handle_websocket_disconnect())

    async def _handle_event(self, msg: Dict[str, Any]) -> None:
        """
        处理事件消息。

        Args:
            msg: 事件消息
        """
        event_type = msg["event"]["event_type"]
        event_data = msg["event"]["data"]

        # 处理状态变更事件
        if event_type == EventType.STATE_CHANGED:
            entity_id = event_data["entity_id"]
            old_state_data = event_data.get("old_state")
            new_state_data = event_data.get("new_state")

            old_state = None
            if old_state_data:
                old_state = EntityState(
                    entity_id=old_state_data["entity_id"],
                    state=old_state_data["state"],
                    attributes=old_state_data["attributes"],
                    last_changed=datetime.fromisoformat(old_state_data["last_changed"]),
                    last_updated=datetime.fromisoformat(old_state_data["last_updated"]),
                    context_id=old_state_data["context"]["id"],
                    context_parent_id=old_state_data["context"].get("parent_id"),
                    context_user_id=old_state_data["context"].get("user_id"),
                )

            new_state = None
            if new_state_data:
                new_state = EntityState(
                    entity_id=new_state_data["entity_id"],
                    state=new_state_data["state"],
                    attributes=new_state_data["attributes"],
                    last_changed=datetime.fromisoformat(new_state_data["last_changed"]),
                    last_updated=datetime.fromisoformat(new_state_data["last_updated"]),
                    context_id=new_state_data["context"]["id"],
                    context_parent_id=new_state_data["context"].get("parent_id"),
                    context_user_id=new_state_data["context"].get("user_id"),
                )

                # 更新缓存
                self._states_cache[entity_id] = new_state

            # 创建事件对象
            event = StateChangedEvent(
                entity_id=entity_id,
                old_state=old_state,
                new_state=new_state,
                event_id=msg["event"]["id"],
                time_fired=datetime.fromisoformat(msg["event"]["time_fired"]),
            )

            # 调用回调
            await self._dispatch_event(event_type, event)

        # 处理其他事件类型
        elif event_type in self._ws_event_callbacks:
            await self._dispatch_event(event_type, event_data)

    async def _dispatch_event(self, event_type: str, event_data: Any) -> None:
        """
        分发事件到回调函数。

        Args:
            event_type: 事件类型
            event_data: 事件数据
        """
        if event_type in self._ws_event_callbacks:
            for callback in self._ws_event_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_data)
                    else:
                        callback(event_data)
                except Exception as e:
                    logger.exception("事件回调执行出错: %s", str(e))

    async def _handle_response(self, msg: Dict[str, Any]) -> None:
        """
        处理 WebSocket 响应消息。

        Args:
            msg: 响应消息
        """
        msg_id = msg["id"]
        if msg_id in self._ws_callbacks:
            future = self._ws_callbacks.pop(msg_id)
            if not future.done():
                if msg.get("success", True):
                    future.set_result(msg.get("result"))
                else:
                    future.set_exception(
                        WebSocketError(
                            f"WebSocket 请求失败: {msg.get('error', {}).get('message', 'Unknown error')}"
                        )
                    )

    async def _send_websocket_command(
        self, command_type: str, payload: Dict[str, Any] = None, timeout: int = 10
    ) -> Any:
        """
        发送 WebSocket 命令并等待响应。

        Args:
            command_type: 命令类型
            payload: 命令负载
            timeout: 超时时间（秒）

        Returns:
            响应结果

        Raises:
            ConnectionError: WebSocket 未连接
            WebSocketError: WebSocket 错误
            asyncio.TimeoutError: 响应超时
        """
        if (
            not self._ws_connected
            or not self._ws_connection
            or self._ws_connection.closed
        ):
            raise ConnectionError("WebSocket 未连接")

        # 生成消息 ID
        self._ws_id += 1
        msg_id = self._ws_id

        # 创建消息
        message = {"id": msg_id, "type": command_type}
        if payload:
            message.update(payload)

        # 创建 Future 对象
        future = asyncio.get_event_loop().create_future()
        self._ws_callbacks[msg_id] = future

        # 发送消息
        await self._ws_connection.send_json(message)

        try:
            # 等待响应
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self._ws_callbacks.pop(msg_id, None)
            raise asyncio.TimeoutError(f"WebSocket 命令超时: {command_type}")

    async def subscribe_events(
        self, event_type: Union[str, EventType], callback: Optional[Callable] = None
    ) -> None:
        """
        订阅事件。

        Args:
            event_type: 事件类型
            callback: 事件回调函数

        Raises:
            ConnectionError: WebSocket 未连接
            WebSocketError: 订阅失败
        """
        if isinstance(event_type, EventType):
            event_type = event_type.value

        # 发送订阅命令
        try:
            await self._send_websocket_command(
                "subscribe_events", {"event_type": event_type}
            )
        except Exception as e:
            raise WebSocketError(f"订阅事件失败: {str(e)}")

        # 注册回调
        if callback:
            if event_type not in self._ws_event_callbacks:
                self._ws_event_callbacks[event_type] = []
            self._ws_event_callbacks[event_type].append(callback)

    def register_state_change_callback(
        self, callback: Callable[[StateChangedEvent], None]
    ) -> None:
        """
        注册状态变更回调。

        Args:
            callback: 状态变更回调函数
        """
        event_type = EventType.STATE_CHANGED.value
        if event_type not in self._ws_event_callbacks:
            self._ws_event_callbacks[event_type] = []
        self._ws_event_callbacks[event_type].append(callback)

    def unregister_state_change_callback(self, callback: Callable) -> None:
        """
        取消注册状态变更回调。

        Args:
            callback: 要取消的回调函数
        """
        event_type = EventType.STATE_CHANGED.value
        if event_type in self._ws_event_callbacks:
            self._ws_event_callbacks[event_type] = [
                cb for cb in self._ws_event_callbacks[event_type] if cb != callback
            ]

    async def get_states(self) -> List[EntityState]:
        """
        获取所有实体状态。

        Returns:
            实体状态列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            raw_states = await self._api_call("GET", "/api/states")
            states = []

            for item in raw_states:
                state = EntityState(
                    entity_id=item["entity_id"],
                    state=item["state"],
                    attributes=item["attributes"],
                    last_changed=datetime.fromisoformat(item["last_changed"]),
                    last_updated=datetime.fromisoformat(item["last_updated"]),
                    context_id=item["context"]["id"],
                    context_parent_id=item["context"].get("parent_id"),
                    context_user_id=item["context"].get("user_id"),
                )
                states.append(state)
                self._states_cache[state.entity_id] = state

            return states

        except Exception as e:
            logger.error("获取实体状态失败: %s", str(e))
            raise

    async def get_state(self, entity_id: str) -> Optional[EntityState]:
        """
        获取单个实体状态。

        Args:
            entity_id: 实体 ID

        Returns:
            实体状态，如果不存在则返回 None

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            # 尝试从缓存获取
            if entity_id in self._states_cache:
                return self._states_cache[entity_id]

            # 从 API 获取
            item = await self._api_call("GET", f"/api/states/{entity_id}")
            if not item:
                return None

            state = EntityState(
                entity_id=item["entity_id"],
                state=item["state"],
                attributes=item["attributes"],
                last_changed=datetime.fromisoformat(item["last_changed"]),
                last_updated=datetime.fromisoformat(item["last_updated"]),
                context_id=item["context"]["id"],
                context_parent_id=item["context"].get("parent_id"),
                context_user_id=item["context"].get("user_id"),
            )

            # 更新缓存
            self._states_cache[entity_id] = state
            return state

        except RequestError as e:
            if "404" in str(e):
                return None
            raise
        except Exception as e:
            logger.error("获取实体状态失败: %s", str(e))
            raise

    async def get_entity_registry(self) -> List[EntityRegistry]:
        """
        获取实体注册表。

        Returns:
            实体注册信息列表

        Raises:
            ConnectionError: 连接错误
            WebSocketError: WebSocket 错误
        """
        try:
            # 使用 WebSocket 命令获取原始注册表数据
            raw_registry = await self._send_websocket_command(
                "config/entity_registry/list"
            )
            # registry = []

            for item in raw_registry:
                # entity_reg = EntityRegistry(
                #     entity_id=item["entity_id"],
                #     unique_id=item["unique_id"],
                #     platform=item["platform"],
                #     name=item.get("name"),
                #     icon=item.get("icon"),
                #     device_id=item.get("device_id"),
                #     area_id=item.get("area_id"),
                #     original_name=item.get("original_name"),
                #     # disabled=item.get(
                #     #     "disabled", False
                #     # ),  # TODO: recheck the field is exist
                #     # hidden=item.get(
                #     #     "hidden", False
                #     # ),  # TODO: recheck the field is exist
                #     # entity_category=item.get("entity_category"),
                #     # device_class=item.get(
                #     #     "device_class"
                #     # ),  # TODO: recheck the field is exist
                #     # original_icon=item.get(
                #     #     "original_icon"
                #     # ),  # TODO: recheck the field is exist
                #     # capabilities=item.get(
                #     #     "capabilities", {}
                #     # ),  # TODO: recheck the field is exist
                #     # supported_features=item.get("supported_features", 0),
                #     # unit_of_measurement=item.get("unit_of_measurement"),
                #     # original_device_class=item.get("original_device_class"),
                # )
                # registry.append(entity_reg)
                self._registry_cache[item["entity_id"]] = item
                # entity_reg

            return self._registry_cache

        except Exception as e:
            logger.error("获取实体注册表失败: %s", str(e))
            raise

    async def get_device_registry(self) -> List[DeviceRegistry]:
        """
        获取设备注册表。

        Returns:
            设备注册信息列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            raw_registry = await self._api_call(
                "GET", "/api/config/device_registry/list"
            )
            registry = []

            for item in raw_registry:
                device_reg = DeviceRegistry(
                    id=item["id"],
                    name=item.get("name"),
                    name_by_user=item.get("name_by_user"),
                    identifiers=set(tuple(i) for i in item.get("identifiers", [])),
                    connections=set(tuple(c) for c in item.get("connections", [])),
                    manufacturer=item.get("manufacturer"),
                    model=item.get("model"),
                    sw_version=item.get("sw_version"),
                    hw_version=item.get("hw_version"),
                    via_device_id=item.get("via_device_id"),
                    area_id=item.get("area_id"),
                    disabled_by=item.get("disabled_by"),
                    entry_type=item.get("entry_type"),
                    configuration_url=item.get("configuration_url"),
                )
                registry.append(device_reg)
                self._device_cache[device_reg.id] = device_reg

            return registry

        except Exception as e:
            logger.error("获取设备注册表失败: %s", str(e))
            raise

    async def get_area_registry(self) -> List[AreaRegistry]:
        """
        获取区域注册表。

        Returns:
            区域注册信息列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            raw_registry = await self._send_websocket_command(
                "config/area_registry/list"
            )
            # registry = []

            for item in raw_registry:
                # area_reg = AreaRegistry(
                #     id=item["area_id"],
                #     name=item["name"],
                #     picture=item.get("picture"),
                # )
                # registry.append(area_reg)
                self._area_cache[item["area_id"]] = item

            return self._area_cache

        except Exception as e:
            logger.error("获取区域注册表失败: %s", str(e))
            raise

    async def get_services(self) -> List[Service]:
        """
        获取可用服务列表。

        Returns:
            服务列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            raw_services = await self._api_call("GET", "/api/services")
            services = []

            for domain_item in raw_services:
                domain = domain_item["domain"]
                for service_name, service_data in domain_item["services"].items():
                    service = Service(
                        domain=domain,
                        service=service_name,
                        name=service_data.get("name"),
                        description=service_data.get("description"),
                        fields=service_data.get("fields", {}),
                        target=service_data.get("target"),
                    )
                    services.append(service)
                    self._service_cache[service.service_id] = service

            return services

        except Exception as e:
            logger.error("获取服务列表失败: %s", str(e))
            raise

    async def call_service(
        self, domain: str, service: str, service_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用服务。

        Args:
            domain: 服务域
            service: 服务名称
            service_data: 服务数据

        Returns:
            服务调用结果

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            result = await self._api_call(
                "POST", f"/api/services/{domain}/{service}", service_data or {}
            )

            # 创建事件对象用于日志记录
            event = ServiceCallEvent(
                domain=domain,
                service=service,
                service_data=service_data or {},
                time_fired=datetime.now(),
            )

            # 记录服务调用
            logger.info(
                "已调用服务: %s.%s %s", domain, service, json.dumps(service_data or {})
            )

            return result or {}

        except Exception as e:
            logger.error("调用服务失败: %s.%s - %s", domain, service, str(e))
            raise

    async def get_history(
        self,
        entity_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        minimal_response: bool = False,
        significant_changes_only: bool = False,
    ) -> List[List[Dict[str, Any]]]:
        """
        获取历史数据。

        Args:
            entity_ids: 实体ID列表，如果为None则获取所有实体
            start_time: 开始时间
            end_time: 结束时间
            minimal_response: 是否返回最小响应
            significant_changes_only: 是否只返回重要变化

        Returns:
            历史数据列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            params = []

            # 构建过滤参数
            if entity_ids:
                filter_str = ",".join(entity_ids)
                params.append(f"filter_entity_id={filter_str}")

            if start_time:
                start_str = start_time.isoformat()
                params.append(f"start_time={start_str}")

            if end_time:
                end_str = end_time.isoformat()
                params.append(f"end_time={end_str}")

            if minimal_response:
                params.append("minimal_response")

            if significant_changes_only:
                params.append("significant_changes_only")

            # 构建URL
            url = "/api/history/period"
            if params:
                url += "?" + "&".join(params)

            # 发送请求
            return await self._api_call("GET", url)

        except Exception as e:
            logger.error("获取历史数据失败: %s", str(e))
            raise

    async def get_logbook(
        self,
        entity_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取日志本数据。

        Args:
            entity_ids: 实体ID列表，如果为None则获取所有实体
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            日志本数据列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            params = []

            # 构建过滤参数
            if entity_ids:
                filter_str = ",".join(entity_ids)
                params.append(f"entity={filter_str}")

            # 构建URL
            url = "/api/logbook"
            if start_time:
                start_str = start_time.isoformat()
                url += f"/{start_str}"

            if params:
                url += "?" + "&".join(params)

            # 发送请求
            return await self._api_call("GET", url)

        except Exception as e:
            logger.error("获取日志本数据失败: %s", str(e))
            raise

    async def get_config(self) -> Dict[str, Any]:
        """
        获取Home Assistant配置。

        Returns:
            配置数据

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            return await self._api_call("GET", "/api/config")
        except Exception as e:
            logger.error("获取配置失败: %s", str(e))
            raise

    async def get_discovery_info(self) -> Dict[str, Any]:
        """
        获取发现信息。

        Returns:
            发现信息

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            return await self._api_call("GET", "/api/discovery_info")
        except Exception as e:
            logger.error("获取发现信息失败: %s", str(e))
            raise

    async def check_api(self) -> bool:
        """
        检查API是否可用。

        Returns:
            API是否可用
        """
        try:
            await self._api_call("GET", "/api/")
            return True
        except Exception:
            return False

    async def update_entity_registry(
        self,
        entity_id: str,
        name: Optional[str] = None,
        icon: Optional[str] = None,
        area_id: Optional[str] = None,
        disabled_by: Optional[str] = None,
        new_entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新实体注册表。

        Args:
            entity_id: 要更新的实体ID
            name: 新名称
            icon: 新图标
            area_id: 新区域ID
            disabled_by: 禁用原因
            new_entity_id: 新实体ID

        Returns:
            更新结果

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            data = {}
            if name is not None:
                data["name"] = name
            if icon is not None:
                data["icon"] = icon
            if area_id is not None:
                data["area_id"] = area_id
            if disabled_by is not None:
                data["disabled_by"] = disabled_by
            if new_entity_id is not None:
                data["new_entity_id"] = new_entity_id

            result = await self._api_call(
                "POST", f"/api/config/entity_registry/update/{entity_id}", data
            )

            # 更新缓存
            if result and "entity_id" in result:
                entity_reg = EntityRegistry(
                    entity_id=result["entity_id"],
                    unique_id=result["unique_id"],
                    platform=result["platform"],
                    name=result.get("name"),
                    icon=result.get("icon"),
                    device_id=result.get("device_id"),
                    area_id=result.get("area_id"),
                    disabled=result.get("disabled", False),
                    hidden=result.get("hidden", False),
                    entity_category=result.get("entity_category"),
                    device_class=result.get("device_class"),
                    original_name=result.get("original_name"),
                    original_icon=result.get("original_icon"),
                    capabilities=result.get("capabilities", {}),
                    supported_features=result.get("supported_features", 0),
                    unit_of_measurement=result.get("unit_of_measurement"),
                    original_device_class=result.get("original_device_class"),
                )
                self._registry_cache[entity_reg.entity_id] = entity_reg

            return result

        except Exception as e:
            logger.error("更新实体注册表失败: %s", str(e))
            raise

    async def create_area(self, name: str) -> Dict[str, Any]:
        """
        创建区域。

        Args:
            name: 区域名称

        Returns:
            创建结果

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            result = await self._api_call(
                "POST", "/api/config/area_registry/create", {"name": name}
            )

            # 更新缓存
            if result and "area_id" in result:
                area_reg = AreaRegistry(
                    id=result["area_id"],
                    name=result["name"],
                    picture=result.get("picture"),
                )
                self._area_cache[area_reg.id] = area_reg

            return result

        except Exception as e:
            logger.error("创建区域失败: %s", str(e))
            raise

    async def update_area(
        self, area_id: str, name: Optional[str] = None, picture: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新区域。

        Args:
            area_id: 区域ID
            name: 新名称
            picture: 新图片

        Returns:
            更新结果

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            data = {}
            if name is not None:
                data["name"] = name
            if picture is not None:
                data["picture"] = picture

            result = await self._api_call(
                "POST", f"/api/config/area_registry/update/{area_id}", data
            )

            # 更新缓存
            if result and "area_id" in result:
                area_reg = AreaRegistry(
                    id=result["area_id"],
                    name=result["name"],
                    picture=result.get("picture"),
                )
                self._area_cache[area_reg.id] = area_reg

            return result

        except Exception as e:
            logger.error("更新区域失败: %s", str(e))
            raise

    async def delete_area(self, area_id: str) -> Dict[str, Any]:
        """
        删除区域。

        Args:
            area_id: 区域ID

        Returns:
            删除结果

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            result = await self._api_call(
                "DELETE", f"/api/config/area_registry/delete/{area_id}"
            )

            # 更新缓存
            if area_id in self._area_cache:
                del self._area_cache[area_id]

            return result

        except Exception as e:
            logger.error("删除区域失败: %s", str(e))
            raise

    async def get_camera_image(self, entity_id: str) -> bytes:
        """
        获取摄像头图像。

        Args:
            entity_id: 摄像头实体ID

        Returns:
            图像数据

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        if self._session is None or self._session.closed:
            raise ConnectionError("未连接到Home Assistant")

        url = f"{self.base_url}/api/camera_proxy/{entity_id}"

        try:
            async with async_timeout.timeout(30):
                async with self._session.get(url) as resp:
                    if resp.status == 401:
                        raise AuthenticationError("认证失败")
                    elif resp.status >= 400:
                        error_text = await resp.text()
                        raise RequestError(f"请求失败: {resp.status} - {error_text}")

                    return await resp.read()

        except asyncio.TimeoutError:
            raise ConnectionError(f"请求超时: {url}")
        except aiohttp.ClientError as e:
            raise ConnectionError(f"请求错误: {str(e)}")

    async def get_template(self, template: str) -> str:
        """
        渲染模板。

        Args:
            template: 模板字符串

        Returns:
            渲染结果

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            result = await self._api_call(
                "POST", "/api/template", {"template": template}
            )
            return result

        except Exception as e:
            logger.error("渲染模板失败: %s", str(e))
            raise

    async def fire_event(
        self, event_type: str, event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        触发事件。

        Args:
            event_type: 事件类型
            event_data: 事件数据

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            await self._api_call("POST", f"/api/events/{event_type}", event_data or {})
            logger.info("已触发事件: %s %s", event_type, json.dumps(event_data or {}))

        except Exception as e:
            logger.error("触发事件失败: %s", str(e))
            raise

    async def validate_config(self) -> Dict[str, Any]:
        """
        验证配置。

        Returns:
            验证结果

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            return await self._api_call("POST", "/api/config/core/check_config")
        except Exception as e:
            logger.error("验证配置失败: %s", str(e))
            raise

    async def get_entity_sources(self) -> Dict[str, Dict[str, Any]]:
        """
        获取实体来源信息。

        Returns:
            实体来源信息

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            return await self._api_call("GET", "/api/config/entity_sources")
        except Exception as e:
            logger.error("获取实体来源信息失败: %s", str(e))
            raise

    async def get_panels(self) -> Dict[str, Dict[str, Any]]:
        """
        获取面板信息。

        Returns:
            面板信息

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            return await self._api_call("GET", "/api/panels")
        except Exception as e:
            logger.error("获取面板信息失败: %s", str(e))
            raise

    async def get_entity_by_device(self, device_id: str) -> List[str]:
        """
        获取设备关联的实体。

        Args:
            device_id: 设备ID

        Returns:
            实体ID列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            # 获取实体注册表
            registry = await self.get_entity_registry()

            # 筛选设备关联的实体
            return [
                entity.entity_id for entity in registry if entity.device_id == device_id
            ]

        except Exception as e:
            logger.error("获取设备关联实体失败: %s", str(e))
            raise

    async def get_entities_by_area(self, area_id: str) -> List[str]:
        """
        获取区域关联的实体。

        Args:
            area_id: 区域ID

        Returns:
            实体ID列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            # 获取实体注册表
            registry = await self.get_entity_registry()

            # 直接关联到区域的实体
            direct_entities = [
                entity.entity_id for entity in registry if entity.area_id == area_id
            ]

            # 获取设备注册表
            devices = await self.get_device_registry()

            # 找到区域内的设备
            area_devices = [
                device.id for device in devices if device.area_id == area_id
            ]

            # 设备关联的实体
            device_entities = []
            for entity in registry:
                if entity.device_id in area_devices:
                    device_entities.append(entity.entity_id)

            # 合并并去重
            return list(set(direct_entities + device_entities))

        except Exception as e:
            logger.error("获取区域关联实体失败: %s", str(e))
            raise

    async def get_entity_info(self, entity_id: str) -> Dict[str, Any]:
        """
        获取实体详细信息。

        Args:
            entity_id: 实体ID

        Returns:
            实体详细信息

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            # 获取实体状态
            state = await self.get_state(entity_id)
            if not state:
                raise RequestError(f"实体不存在: {entity_id}")

            # 获取实体注册信息
            registry = await self.get_entity_registry()
            entity_reg = next((r for r in registry if r.entity_id == entity_id), None)

            # 获取设备信息
            device = None
            if entity_reg and entity_reg.device_id:
                devices = await self.get_device_registry()
                device = next(
                    (d for d in devices if d.id == entity_reg.device_id), None
                )

            # 获取区域信息
            area = None
            area_id = None
            if entity_reg and entity_reg.area_id:
                area_id = entity_reg.area_id
            elif device and device.area_id:
                area_id = device.area_id

            if area_id:
                areas = await self.get_area_registry()
                area = next((a for a in areas if a.id == area_id), None)

            # 构建结果
            result = {
                "entity_id": entity_id,
                "state": asdict(state) if state else None,
                "registry": asdict(entity_reg) if entity_reg else None,
                "device": asdict(device) if device else None,
                "area": asdict(area) if area else None,
            }

            return result

        except Exception as e:
            logger.error("获取实体详细信息失败: %s", str(e))
            raise

    async def get_statistics(
        self,
        statistic_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        period: str = "hour",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取统计数据。

        Args:
            statistic_ids: 统计ID列表
            start_time: 开始时间
            end_time: 结束时间
            period: 周期 (hour, day, month)

        Returns:
            统计数据

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            data = {"period": period}

            if statistic_ids:
                data["statistic_ids"] = statistic_ids

            if start_time:
                data["start_time"] = start_time.isoformat()

            if end_time:
                data["end_time"] = end_time.isoformat()

            return await self._api_call("POST", "/api/history/statistics", data)

        except Exception as e:
            logger.error("获取统计数据失败: %s", str(e))
            raise

    async def get_available_statistics(self) -> List[Dict[str, Any]]:
        """
        获取可用统计指标。

        Returns:
            可用统计指标列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            return await self._api_call("GET", "/api/history/statistics")
        except Exception as e:
            logger.error("获取可用统计指标失败: %s", str(e))
            raise

    async def get_domains_with_services(self) -> List[str]:
        """
        获取有服务的域列表。

        Returns:
            域列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            services = await self.get_services()
            domains = set(service.domain for service in services)
            return sorted(list(domains))

        except Exception as e:
            logger.error("获取域列表失败: %s", str(e))
            raise

    async def get_domain_services(self, domain: str) -> List[Service]:
        """
        获取指定域的服务列表。

        Args:
            domain: 域名

        Returns:
            服务列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            all_services = await self.get_services()
            return [service for service in all_services if service.domain == domain]

        except Exception as e:
            logger.error("获取域服务列表失败: %s", str(e))
            raise

    async def get_service_by_id(self, service_id: str) -> Optional[Service]:
        """
        通过服务ID获取服务。

        Args:
            service_id: 服务ID (domain.service)

        Returns:
            服务对象，如果不存在则返回None

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            # 尝试从缓存获取
            if service_id in self._service_cache:
                return self._service_cache[service_id]

            # 从API获取所有服务
            all_services = await self.get_services()

            # 查找匹配的服务
            for service in all_services:
                if service.service_id == service_id:
                    return service

            return None

        except Exception as e:
            logger.error("获取服务失败: %s", str(e))
            raise

    async def get_entity_states_by_domain(self, domain: str) -> List[EntityState]:
        """
        获取指定域的所有实体状态。

        Args:
            domain: 域名

        Returns:
            实体状态列表

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            all_states = await self.get_states()
            return [state for state in all_states if state.domain == domain]

        except Exception as e:
            logger.error("获取域实体状态失败: %s", str(e))
            raise

    async def ping(self) -> float:
        """
        测试与Home Assistant的连接延迟。

        Returns:
            延迟时间（秒）

        Raises:
            ConnectionError: 连接错误
        """
        try:
            start_time = time.time()
            await self._api_call("GET", "/api/")
            end_time = time.time()
            return end_time - start_time

        except Exception as e:
            logger.error("Ping失败: %s", str(e))
            raise ConnectionError(f"Ping失败: {str(e)}")

    async def send_notification(
        self,
        message: str,
        title: Optional[str] = None,
        target: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        发送通知。

        Args:
            message: 通知消息
            title: 通知标题
            target: 目标设备列表

        Returns:
            服务调用结果

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            service_data = {"message": message}

            if title:
                service_data["title"] = title

            if target:
                service_data["target"] = target

            return await self.call_service("notify", "notify", service_data)

        except Exception as e:
            logger.error("发送通知失败: %s", str(e))
            raise

    async def get_frontend_version(self) -> str:
        """
        获取前端版本。

        Returns:
            前端版本

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            config = await self.get_config()
            return config.get("version", "unknown")

        except Exception as e:
            logger.error("获取前端版本失败: %s", str(e))
            raise

    async def get_location_info(self) -> Dict[str, Any]:
        """
        获取位置信息。

        Returns:
            位置信息

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            config = await self.get_config()
            return {
                "latitude": config.get("latitude"),
                "longitude": config.get("longitude"),
                "elevation": config.get("elevation"),
                "location_name": config.get("location_name"),
                "time_zone": config.get("time_zone"),
                "country": config.get("country"),
                "currency": config.get("currency"),
                "unit_system": config.get("unit_system"),
            }

        except Exception as e:
            logger.error("获取位置信息失败: %s", str(e))
            raise

    async def get_entity_categories(self) -> Dict[str, List[str]]:
        """
        获取按类别分组的实体。

        Returns:
            按类别分组的实体字典

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            registry = await self.get_entity_registry()
            categories = {}

            for entity in registry:
                category = entity.entity_category or "default"
                if category not in categories:
                    categories[category] = []
                categories[category].append(entity.entity_id)

            return categories

        except Exception as e:
            logger.error("获取实体类别失败: %s", str(e))
            raise

    async def get_entity_count_by_domain(self) -> Dict[str, int]:
        """
        获取每个域的实体数量。

        Returns:
            域实体数量字典

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            states = await self.get_states()
            counts = {}

            for state in states:
                domain = state.domain
                if domain not in counts:
                    counts[domain] = 0
                counts[domain] += 1

            return counts

        except Exception as e:
            logger.error("获取域实体数量失败: %s", str(e))
            raise

    async def get_system_health(self) -> Dict[str, Any]:
        """
        获取系统健康信息。

        Returns:
            系统健康信息

        Raises:
            ConnectionError: 连接错误
            RequestError: 请求错误
        """
        try:
            return await self._api_call("GET", "/api/system_health/info")
        except Exception as e:
            logger.error("获取系统健康信息失败: %s", str(e))
            raise

    async def check_connection_status(self) -> Dict[str, Any]:
        """
        检查连接状态。

        Returns:
            连接状态信息

        Raises:
            ConnectionError: 连接错误
        """
        status = {
            "api_connected": False,
            "websocket_connected": self._ws_connected,
            "latency": None,
        }

        try:
            # 检查API连接
            latency = await self.ping()
            status["api_connected"] = True
            status["latency"] = latency

            return status

        except Exception as e:
            logger.error("检查连接状态失败: %s", str(e))
            return status

    def get_cached_states(self) -> Dict[str, EntityState]:
        """
        获取缓存的实体状态。

        Returns:
            实体状态字典
        """
        return self._states_cache.copy()

    def get_cached_registry(self) -> Dict[str, EntityRegistry]:
        """
        获取缓存的实体注册信息。

        Returns:
            实体注册信息字典
        """
        return self._registry_cache.copy()

    def get_cached_devices(self) -> Dict[str, DeviceRegistry]:
        """
        获取缓存的设备注册信息。

        Returns:
            设备注册信息字典
        """
        return self._device_cache.copy()

    def get_cached_areas(self) -> Dict[str, AreaRegistry]:
        """
        获取缓存的区域注册信息。

        Returns:
            区域注册信息字典
        """
        return self._area_cache.copy()

    def get_cached_services(self) -> Dict[str, Service]:
        """
        获取缓存的服务信息。

        Returns:
            服务信息字典
        """
        return self._service_cache.copy()


if __name__ == "__main__":
    import os
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        config = {
            "base_url": os.getenv("HASS_URL"),
            "access_token": os.getenv("HASS_ACCESS_TOKEN"),
        }
        ha_client = HomeAssistantClient(config)
        await ha_client.connect()
        try:
            # self, domain: str, service: str, service_data: Optional[Dict[str, Any]] = None
            result = await ha_client.call_service(
                domain="light",
                service="turn_off",
                service_data={
                    "entity_id": "light.yeelink_cn_1132894958_mbulb3_s_2",
                },
            )
            print(result)
            # registry = await ha_client.get_entity_registry()
            # print(json.dumps(registry, indent=4))
        finally:
            await ha_client.disconnect()

    asyncio.run(main())
