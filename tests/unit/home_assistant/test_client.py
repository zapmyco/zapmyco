import asyncio
import unittest
from unittest.mock import MagicMock, patch
from tests.integration.home_assistant.test_api import TEST_CONFIG
from integrations.home_assistant.main import (
    AuthenticationError,
    HomeAssistantClient,
    RequestError,
)


class HomeAssistantClientTests(unittest.TestCase):
    """HomeAssistantClient 单元测试类"""

    def setUp(self):
        """设置测试环境"""
        self.client = HomeAssistantClient(TEST_CONFIG)

        # 创建异步事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # 模拟 HTTP 会话
        self.mock_session = MagicMock()
        self.mock_response = MagicMock()
        self.mock_ws = MagicMock()

        # 设置默认响应
        self.mock_response.status = 200
        self.mock_response.text = asyncio.coroutine(lambda: '{"error": "Test error"}')
        self.mock_response.json = asyncio.coroutine(lambda: {})
        self.mock_response.read = asyncio.coroutine(lambda: b"test_data")

        # 设置 WebSocket 响应
        self.mock_ws.receive_json = asyncio.coroutine(lambda: {"type": "auth_required"})
        self.mock_ws.closed = False

        # 模拟 ClientSession
        self.client._session = self.mock_session
        self.mock_session.request = asyncio.coroutine(
            lambda method, url, **kwargs: self.mock_response
        )
        self.mock_session.ws_connect = asyncio.coroutine(
            lambda url, **kwargs: self.mock_ws
        )

    def tearDown(self):
        """清理测试环境"""
        self.loop.close()

    def test_init(self):
        """测试初始化"""
        client = HomeAssistantClient(TEST_CONFIG)
        self.assertEqual(client.base_url, TEST_CONFIG["base_url"])
        self.assertEqual(client.access_token, TEST_CONFIG["access_token"])
        self.assertEqual(client.verify_ssl, TEST_CONFIG["verify_ssl"])
        self.assertEqual(client.websocket_timeout, 30)  # 默认值

        # 测试自定义超时
        custom_config = TEST_CONFIG.copy()
        custom_config["websocket_timeout"] = 60
        client = HomeAssistantClient(custom_config)
        self.assertEqual(client.websocket_timeout, 60)

    def test_api_call_success(self):
        """测试成功的 API 调用"""

        async def test():
            # 设置模拟响应
            self.mock_response.json = asyncio.coroutine(lambda: {"key": "value"})

            # 调用 API
            result = await self.client._api_call("GET", "/api/test")

            # 验证结果
            self.assertEqual(result, {"key": "value"})
            self.mock_session.request.assert_called_once()
            args, kwargs = self.mock_session.request.call_args
            self.assertEqual(args[0], "GET")
            self.assertEqual(args[1], f"{TEST_CONFIG['base_url']}/api/test")

        self.loop.run_until_complete(test())

    def test_api_call_auth_error(self):
        """测试认证错误的 API 调用"""

        async def test():
            # 设置模拟响应
            self.mock_response.status = 401

            # 调用 API，应该抛出认证错误
            with self.assertRaises(AuthenticationError):
                await self.client._api_call("GET", "/api/test")

        self.loop.run_until_complete(test())

    def test_api_call_request_error(self):
        """测试请求错误的 API 调用"""

        async def test():
            # 设置模拟响应
            self.mock_response.status = 404

            # 调用 API，应该抛出请求错误
            with self.assertRaises(RequestError):
                await self.client._api_call("GET", "/api/test")

        self.loop.run_until_complete(test())

    def test_connect_success(self):
        """测试成功连接"""

        async def test():
            # 设置模拟响应
            self.mock_response.json = asyncio.coroutine(lambda: {})

            # 设置 WebSocket 响应序列
            ws_responses = [
                {"type": "auth_required"},
                {"type": "auth_ok"},
            ]

            # 修改 receive_json 以返回序列中的下一个响应
            response_iter = iter(ws_responses)
            self.mock_ws.receive_json = asyncio.coroutine(lambda: next(response_iter))

            # 屏蔽 WebSocket 循环
            with patch.object(
                self.client,
                "_websocket_loop",
                return_value=asyncio.create_task(asyncio.sleep(0)),
            ):
                # 屏蔽订阅事件
                with patch.object(self.client, "subscribe_events", return_value=None):
                    # 连接
                    result = await self.client.connect()

                    # 验证结果
                    self.assertTrue(result)
                    self.assertTrue(self.client._ws_connected)
                    self.mock_session.request.assert_called()
                    self.mock_session.ws_connect.assert_called_once()

        self.loop.run_until_complete(test())

    def test_connect_api_error(self):
        """测试 API 连接错误"""

        async def test():
            # 设置模拟响应
            self.mock_response.status = 401

            # 连接应该失败
            result = await self.client.connect()

            # 验证结果
            self.assertFalse(result)
            self.mock_session.request.assert_called_once()
            self.mock_session.ws_connect.assert_not_called()

        self.loop.run_until_complete(test())

    def test_connect_websocket_error(self):
        """测试 WebSocket 连接错误"""

        async def test():
            # 设置模拟响应
            self.mock_response.json = asyncio.coroutine(lambda: {})

            # 设置 WebSocket 连接失败
            self.mock_session.ws_connect = asyncio.coroutine(
                lambda url, **kwargs: (_ for _ in ()).throw(
                    ConnectionError("WebSocket 连接失败")
                )
            )

            # 连接应该失败
            result = await self.client.connect()

            # 验证结果
            self.assertFalse(result)
            self.mock_session.request.assert_called_once()
            self.mock_session.ws_connect.assert_called_once()

        self.loop.run_until_complete(test())

    def test_disconnect(self):
        """测试断开连接"""

        async def test():
            # 设置客户端状态
            self.client._ws_connected = True
            self.client._ws_connection = self.mock_ws
            self.client._ws_task = asyncio.create_task(asyncio.sleep(0))

            # 断开连接
            await self.client.disconnect()

            # 验证结果
            self.assertFalse(self.client._ws_connected)
            self.assertIsNone(self.client._ws_connection)
            self.mock_ws.close.assert_called_once()
            self.mock_session.close.assert_called_once()

        self.loop.run_until_complete(test())

    def test_get_states(self):
        """测试获取所有实体状态"""

        async def test():
            # 设置模拟响应
            mock_states = [
                {
                    "entity_id": "light.test",
                    "state": "on",
                    "attributes": {"brightness": 255},
                    "last_changed": "2023-01-01T00:00:00+00:00",
                    "last_updated": "2023-01-01T00:00:00+00:00",
                    "context": {"id": "test_id", "parent_id": None, "user_id": None},
                }
            ]
            self.mock_response.json = asyncio.coroutine(lambda: mock_states)

            # 获取状态
            states = await self.client.get_states()

            # 验证结果
            self.assertEqual(len(states), 1)
            self.assertEqual(states[0].entity_id, "light.test")
            self.assertEqual(states[0].state, "on")
            self.assertEqual(states[0].attributes["brightness"], 255)
            self.assertEqual(states[0].context_id, "test_id")

            # 验证缓存
            self.assertIn("light.test", self.client._states_cache)

        self.loop.run_until_complete(test())

    def test_get_state(self):
        """测试获取单个实体状态"""

        async def test():
            # 设置模拟响应
            mock_state = {
                "entity_id": "light.test",
                "state": "on",
                "attributes": {"brightness": 255},
                "last_changed": "2023-01-01T00:00:00+00:00",
                "last_updated": "2023-01-01T00:00:00+00:00",
                "context": {"id": "test_id", "parent_id": None, "user_id": None},
            }
            self.mock_response.json = asyncio.coroutine(lambda: mock_state)

            # 获取状态
            state = await self.client.get_state("light.test")

            # 验证结果
            self.assertEqual(state.entity_id, "light.test")
            self.assertEqual(state.state, "on")
            self.assertEqual(state.attributes["brightness"], 255)

            # 验证缓存
            self.assertIn("light.test", self.client._states_cache)

            # 测试从缓存获取
            self.mock_response.json = asyncio.coroutine(
                lambda: {"error": "Should not be called"}
            )
            state2 = await self.client.get_state("light.test")
            self.assertEqual(state2.entity_id, "light.test")

        self.loop.run_until_complete(test())

    def test_get_state_not_found(self):
        """测试获取不存在的实体状态"""

        async def test():
            # 设置模拟响应
            self.mock_response.status = 404

            # 获取状态
            state = await self.client.get_state("non_existent")

            # 验证结果
            self.assertIsNone(state)

        self.loop.run_until_complete(test())

    def test_call_service(self):
        """测试调用服务"""

        async def test():
            # 设置模拟响应
            self.mock_response.json = asyncio.coroutine(lambda: [{"result": "success"}])

            # 调用服务
            result = await self.client.call_service(
                "light", "turn_on", {"entity_id": "light.test"}
            )

            # 验证结果
            self.assertEqual(result, [{"result": "success"}])
            self.mock_session.request.assert_called_once()
            args, kwargs = self.mock_session.request.call_args
            self.assertEqual(args[0], "POST")
            self.assertEqual(
                args[1], f"{TEST_CONFIG['base_url']}/api/services/light/turn_on"
            )
            self.assertEqual(kwargs["json"], {"entity_id": "light.test"})

        self.loop.run_until_complete(test())

    def test_get_history(self):
        """测试获取历史数据"""

        async def test():
            # 设置模拟响应
            mock_history = [
                [
                    {
                        "entity_id": "light.test",
                        "state": "on",
                        "attributes": {},
                        "last_changed": "2023-01-01T00:00:00+00:00",
                        "last_updated": "2023-01-01T00:00:00+00:00",
                    }
                ]
            ]
            self.mock_response.json = asyncio.coroutine(lambda: mock_history)

            # 获取历史数据
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            history = await self.client.get_history(
                entity_ids=["light.test"], start_time=one_hour_ago, end_time=now
            )

            # 验证结果
            self.assertEqual(history, mock_history)
            self.mock_session.request.assert_called_once()
            args, kwargs = self.mock_session.request.call_args
            self.assertEqual(args[0], "GET")
            self.assertIn("/api/history/period", args[1])
            self.assertIn("filter_entity_id=light.test", args[1])
            self.assertIn("start_time=", args[1])
            self.assertIn("end_time=", args[1])

        self.loop.run_until_complete(test())

    def test_get_config(self):
        """测试获取配置"""

        async def test():
            # 设置模拟响应
            mock_config = {
                "version": "2023.1.1",
                "location_name": "Home",
                "time_zone": "UTC",
            }
            self.mock_response.json = asyncio.coroutine(lambda: mock_config)

            # 获取配置
            config = await self.client.get_config()

            # 验证结果
            self.assertEqual(config, mock_config)
            self.mock_session.request.assert_called_once()
            args, kwargs = self.mock_session.request.call_args
            self.assertEqual(args[0], "GET")
            self.assertEqual(args[1], f"{TEST_CONFIG['base_url']}/api/config")

        self.loop.run_until_complete(test())

    def test_get_services(self):
        """测试获取服务列表"""

        async def test():
            # 设置模拟响应
            mock_services = [
                {
                    "domain": "light",
                    "services": {
                        "turn_on": {
                            "name": "Turn on",
                            "description": "Turn on the light",
                            "fields": {
                                "entity_id": {
                                    "description": "Entity ID",
                                    "example": "light.kitchen",
                                }
                            },
                        }
                    },
                }
            ]
            self.mock_response.json = asyncio.coroutine(lambda: mock_services)

            # 获取服务
            services = await self.client.get_services()

            # 验证结果
            self.assertEqual(len(services), 1)
            self.assertEqual(services[0].domain, "light")
            self.assertEqual(services[0].service, "turn_on")
            self.assertEqual(services[0].name, "Turn on")
            self.assertEqual(services[0].description, "Turn on the light")
            self.assertIn("entity_id", services[0].fields)

            # 验证缓存
            self.assertIn("light.turn_on", self.client._service_cache)

        self.loop.run_until_complete(test())

    def test_get_entity_registry(self):
        """测试获取实体注册表"""

        async def test():
            # 设置模拟响应
            mock_registry = [
                {
                    "entity_id": "light.test",
                    "unique_id": "test_unique_id",
                    "platform": "test_platform",
                    "name": "Test Light",
                    "icon": "mdi:light",
                    "device_id": "test_device_id",
                    "area_id": "test_area_id",
                    "disabled": False,
                    "hidden": False,
                }
            ]
            self.mock_response.json = asyncio.coroutine(lambda: mock_registry)

            # 获取实体注册表
            registry = await self.client.get_entity_registry()

            # 验证结果
            self.assertEqual(len(registry), 1)
            self.assertEqual(registry[0].entity_id, "light.test")
            self.assertEqual(registry[0].unique_id, "test_unique_id")
            self.assertEqual(registry[0].platform, "test_platform")
            self.assertEqual(registry[0].name, "Test Light")
            self.assertEqual(registry[0].device_id, "test_device_id")

            # 验证缓存
            self.assertIn("light.test", self.client._registry_cache)

        self.loop.run_until_complete(test())

    def test_get_device_registry(self):
        """测试获取设备注册表"""

        async def test():
            # 设置模拟响应
            mock_registry = [
                {
                    "id": "test_device_id",
                    "name": "Test Device",
                    "manufacturer": "Test Manufacturer",
                    "model": "Test Model",
                    "identifiers": [["test_domain", "test_identifier"]],
                    "connections": [["mac", "00:11:22:33:44:55"]],
                    "area_id": "test_area_id",
                }
            ]
            self.mock_response.json = asyncio.coroutine(lambda: mock_registry)

            # 获取设备注册表
            registry = await self.client.get_device_registry()

            # 验证结果
            self.assertEqual(len(registry), 1)
            self.assertEqual(registry[0].id, "test_device_id")
            self.assertEqual(registry[0].name, "Test Device")
            self.assertEqual(registry[0].manufacturer, "Test Manufacturer")
            self.assertEqual(registry[0].model, "Test Model")
            self.assertEqual(len(registry[0].identifiers), 1)
            self.assertEqual(len(registry[0].connections), 1)

            # 验证缓存
            self.assertIn("test_device_id", self.client._device_cache)

        self.loop.run_until_complete(test())

    def test_get_area_registry(self):
        """测试获取区域注册表"""

        async def test():
            # 设置模拟响应
            mock_registry = [
                {"area_id": "test_area_id", "name": "Test Area", "picture": None}
            ]
            self.mock_response.json = asyncio.coroutine(lambda: mock_registry)

            # 获取区域注册表
            registry = await self.client.get_area_registry()

            # 验证结果
            self.assertEqual(len(registry), 1)
            self.assertEqual(registry[0].id, "test_area_id")
            self.assertEqual(registry[0].name, "Test Area")

            # 验证缓存
            self.assertIn("test_area_id", self.client._area_cache)

        self.loop.run_until_complete(test())

    def test_get_camera_image(self):
        """测试获取摄像头图像"""

        async def test():
            # 设置模拟响应
            self.mock_response.read = asyncio.coroutine(lambda: b"image_data")

            # 获取摄像头图像
            image = await self.client.get_camera_image("camera.test")

            # 验证结果
            self.assertEqual(image, b"image_data")
            self.mock_session.request.assert_not_called()
            self.mock_session.get.assert_called_once()
            args, kwargs = self.mock_session.get.call_args
            self.assertEqual(
                args[0], f"{TEST_CONFIG['base_url']}/api/camera_proxy/camera.test"
            )

        # 模拟 get 方法
        self.mock_session.get = asyncio.coroutine(
            lambda url, **kwargs: self.mock_response
        )

        self.loop.run_until_complete(test())

    def test_get_template(self):
        """测试渲染模板"""

        async def test():
            # 设置模拟响应
            self.mock_response.json = asyncio.coroutine(lambda: "Rendered template")

            # 渲染模板
            result = await self.client.get_template("{{ states('light.test') }}")

            # 验证结果
            self.assertEqual(result, "Rendered template")
            self.mock_session.request.assert_called_once()
            args, kwargs = self.mock_session.request.call_args
            self.assertEqual(args[0], "POST")
            self.assertEqual(args[1], f"{TEST_CONFIG['base_url']}/api/template")
            self.assertEqual(kwargs["json"], {"template": "{{ states('light.test') }}"})

        self.loop.run_until_complete(test())

    def test_fire_event(self):
        """测试触发事件"""

        async def test():
            # 设置模拟响应
            self.mock_response.json = asyncio.coroutine(lambda: {})

            # 触发事件
            await self.client.fire_event("test_event", {"data": "test"})

            # 验证结果
            self.mock_session.request.assert_called_once()
            args, kwargs = self.mock_session.request.call_args
            self.assertEqual(args[0], "POST")
            self.assertEqual(
                args[1], f"{TEST_CONFIG['base_url']}/api/events/test_event"
            )
            self.assertEqual(kwargs["json"], {"data": "test"})

        self.loop.run_until_complete(test())

    def test_check_api(self):
        """测试检查 API"""

        async def test():
            # 设置模拟响应
            self.mock_response.json = asyncio.coroutine(lambda: {})

            # 检查 API
            result = await self.client.check_api()

            # 验证结果
            self.assertTrue(result)
            self.mock_session.request.assert_called_once()

            # 测试 API 不可用
            self.mock_session.request.reset_mock()
            self.mock_response.status = 401
            result = await self.client.check_api()
            self.assertFalse(result)

        self.loop.run_until_complete(test())

    def test_ping(self):
        """测试 ping"""

        async def test():
            # 设置模拟响应
            self.mock_response.json = asyncio.coroutine(lambda: {})

            # 模拟时间
            with patch("time.time", side_effect=[100.0, 100.5]):
                # 执行 ping
                result = await self.client.ping()

                # 验证结果
                self.assertEqual(result, 0.5)
                self.mock_session.request.assert_called_once()

        self.loop.run_until_complete(test())

    def test_register_state_change_callback(self):
        """测试注册状态变化回调"""

        # 创建回调函数
        def callback(event):
            pass

        # 注册回调
        self.client.register_state_change_callback(callback)

        # 验证结果
        self.assertIn("state_changed", self.client._ws_event_callbacks)
        self.assertIn(callback, self.client._ws_event_callbacks["state_changed"])

        # 测试取消注册
        self.client.unregister_state_change_callback(callback)
        self.assertNotIn(callback, self.client._ws_event_callbacks["state_changed"])

    def test_get_entity_info(self):
        """测试获取实体详细信息"""

        async def test():
            # 设置模拟状态响应
            mock_state = {
                "entity_id": "light.test",
                "state": "on",
                "attributes": {"brightness": 255},
                "last_changed": "2023-01-01T00:00:00+00:00",
                "last_updated": "2023-01-01T00:00:00+00:00",
                "context": {"id": "test_id", "parent_id": None, "user_id": None},
            }

            # 设置模拟注册表响应
            mock_registry = [
                {
                    "entity_id": "light.test",
                    "unique_id": "test_unique_id",
                    "platform": "test_platform",
                    "name": "Test Light",
                    "device_id": "test_device_id",
                    "area_id": "test_area_id",
                }
            ]

            # 设置模拟设备响应
            mock_devices = [
                {
                    "id": "test_device_id",
                    "name": "Test Device",
                    "manufacturer": "Test Manufacturer",
                }
            ]

            # 设置模拟区域响应
            mock_areas = [{"area_id": "test_area_id", "name": "Test Area"}]

            # 模拟方法
            with patch.object(
                self.client,
                "get_state",
                return_value=asyncio.coroutine(lambda *args, **kwargs: mock_state)(),
            ) as mock_get_state:
                with patch.object(
                    self.client,
                    "get_entity_registry",
                    return_value=asyncio.coroutine(
                        lambda *args, **kwargs: mock_registry
                    )(),
                ) as mock_get_registry:
                    with patch.object(
                        self.client,
                        "get_device_registry",
                        return_value=asyncio.coroutine(
                            lambda *args, **kwargs: mock_devices
                        )(),
                    ) as mock_get_devices:
                        with patch.object(
                            self.client,
                            "get_area_registry",
                            return_value=asyncio.coroutine(
                                lambda *args, **kwargs: mock_areas
                            )(),
                        ) as mock_get_areas:
                            # 获取实体信息
                            info = await self.client.get_entity_info("light.test")

                            # 验证结果
                            self.assertEqual(info["entity_id"], "light.test")
                            self.assertIsNotNone(info["state"])
                            self.assertIsNotNone(info["registry"])
                            self.assertIsNotNone(info["device"])
                            self.assertIsNotNone(info["area"])

                            # 验证方法调用
                            mock_get_state.assert_called_once_with("light.test")
                            mock_get_registry.assert_called_once()
                            mock_get_devices.assert_called_once()
                            mock_get_areas.assert_called_once()

        self.loop.run_until_complete(test())

    def test_get_entities_by_area(self):
        """测试获取区域关联的实体"""

        async def test():
            # 设置模拟注册表响应
            mock_registry = [
                {
                    "entity_id": "light.direct",
                    "unique_id": "direct_unique_id",
                    "platform": "test_platform",
                    "area_id": "test_area_id",
                },
                {
                    "entity_id": "light.device",
                    "unique_id": "device_unique_id",
                    "platform": "test_platform",
                    "device_id": "test_device_id",
                },
            ]

            # 设置模拟设备响应
            mock_devices = [
                {
                    "id": "test_device_id",
                    "name": "Test Device",
                    "area_id": "test_area_id",
                }
            ]

            # 模拟方法
            with patch.object(
                self.client,
                "get_entity_registry",
                return_value=asyncio.coroutine(lambda *args, **kwargs: mock_registry)(),
            ) as mock_get_registry:
                with patch.object(
                    self.client,
                    "get_device_registry",
                    return_value=asyncio.coroutine(
                        lambda *args, **kwargs: mock_devices
                    )(),
                ) as mock_get_devices:
                    # 获取区域实体
                    entities = await self.client.get_entities_by_area("test_area_id")

                    # 验证结果
                    self.assertEqual(len(entities), 2)
                    self.assertIn("light.direct", entities)
                    self.assertIn("light.device", entities)

                    # 验证方法调用
                    mock_get_registry.assert_called_once()
                    mock_get_devices.assert_called_once()

        self.loop.run_until_complete(test())
