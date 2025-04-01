"""
HomeAssistantClient 集成测试

此脚本测试与实际 Home Assistant 实例的交互。
请确保在运行前更新配置。
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 导入客户端
from integrations.home_assistant.main import HomeAssistantClient, EntityState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("ha_integration_test")

# Home Assistant 配置 - 请在运行前更新
HA_CONFIG = {
    "base_url": "http://homeassistant.local:8123",  # 修改为你的 Home Assistant URL
    "access_token": "YOUR_LONG_LIVED_ACCESS_TOKEN",  # 修改为你的访问令牌
    "verify_ssl": True,
}

# 测试配置
TEST_CONFIG = {
    # 要测试的实体
    "light_entity": "light.living_room",  # 修改为你环境中存在的灯实体
    "switch_entity": "switch.office",  # 修改为你环境中存在的开关实体
    "sensor_entity": "sensor.temperature",  # 修改为你环境中存在的传感器实体
    "camera_entity": "camera.front_door",  # 修改为你环境中存在的摄像头实体
    # 测试区域
    "area_id": "living_room",  # 修改为你环境中存在的区域ID
    # 测试服务
    "notification_target": "mobile_app_phone",  # 修改为你环境中存在的通知目标
}


class IntegrationTest:
    """Home Assistant 客户端集成测试类"""

    def __init__(self, ha_config: Dict[str, Any], test_config: Dict[str, Any]):
        """初始化测试"""
        self.ha_config = ha_config
        self.test_config = test_config
        self.client = HomeAssistantClient(ha_config)
        self.results = {"passed": 0, "failed": 0, "skipped": 0, "total": 0, "tests": []}

    async def setup(self) -> bool:
        """设置测试环境"""
        logger.info("正在连接到 Home Assistant...")
        connected = await self.client.connect()
        if not connected:
            logger.error("无法连接到 Home Assistant，请检查配置")
            return False

        logger.info("已连接到 Home Assistant")
        return True

    async def teardown(self):
        """清理测试环境"""
        logger.info("正在断开连接...")
        await self.client.disconnect()
        logger.info("已断开连接")

    async def run_tests(self):
        """运行所有测试"""
        if not await self.setup():
            return False

        try:
            # 基本连接测试
            await self.test_connection()

            # 状态测试
            await self.test_get_states()
            await self.test_get_specific_state()

            # 服务测试
            await self.test_get_services()

            # 注册表测试
            await self.test_get_registries()

            # 历史和统计测试
            await self.test_get_history()
            await self.test_get_statistics()

            # 区域和设备测试
            await self.test_area_entities()

            # 摄像头测试
            await self.test_camera_image()

            # 模板测试
            await self.test_template()

            # 服务调用测试 (可选)
            should_test_services = (
                input("\n是否测试服务调用? 这可能会改变设备状态 (y/n): ").lower() == "y"
            )
            if should_test_services:
                await self.test_call_service()
                await self.test_notification()
            else:
                self.skip_test("test_call_service", "用户选择跳过")
                self.skip_test("test_notification", "用户选择跳过")

            # WebSocket 测试
            await self.test_websocket_subscription()

            # 系统信息测试
            await self.test_system_info()

        except Exception as e:
            logger.error(f"测试过程中出错: {str(e)}")
            raise
        finally:
            await self.teardown()
            self.print_results()

        return self.results["failed"] == 0

    def record_result(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        result = {
            "name": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        self.results["tests"].append(result)
        self.results["total"] += 1

        if passed:
            self.results["passed"] += 1
            logger.info(f"✅ 通过: {test_name}")
            if message:
                logger.info(f"   {message}")
        else:
            self.results["failed"] += 1
            logger.error(f"❌ 失败: {test_name}")
            logger.error(f"   {message}")

    def skip_test(self, test_name: str, reason: str):
        """跳过测试"""
        self.results["skipped"] += 1
        self.results["total"] += 1
        self.results["tests"].append(
            {
                "name": test_name,
                "passed": None,
                "message": f"跳过: {reason}",
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.info(f"⏭️ 跳过: {test_name} ({reason})")

    def print_results(self):
        """打印测试结果摘要"""
        logger.info("\n========== 测试结果摘要 ==========")
        logger.info(f"总计: {self.results['total']} 测试")
        logger.info(f"通过: {self.results['passed']} 测试")
        logger.info(f"失败: {self.results['failed']} 测试")
        logger.info(f"跳过: {self.results['skipped']} 测试")
        logger.info("==================================")

        if self.results["failed"] > 0:
            logger.info("\n失败的测试:")
            for test in self.results["tests"]:
                if test.get("passed") is False:
                    logger.info(f"- {test['name']}: {test['message']}")

    async def test_connection(self):
        """测试连接状态"""
        try:
            # 检查 API 连接
            api_ok = await self.client.check_api()

            # 检查连接状态
            status = await self.client.check_connection_status()

            # 测试 ping
            ping_time = await self.client.ping()

            # 验证结果
            all_ok = (
                api_ok
                and status["api_connected"]
                and status["websocket_connected"]
                and ping_time is not None
            )

            message = (
                f"API连接: {'成功' if api_ok else '失败'}, "
                f"WebSocket连接: {'成功' if status['websocket_connected'] else '失败'}, "
                f"Ping: {ping_time * 1000:.2f}ms"
            )

            self.record_result("test_connection", all_ok, message)

        except Exception as e:
            self.record_result("test_connection", False, f"出错: {str(e)}")

    async def test_get_states(self):
        """测试获取所有实体状态"""
        try:
            # 获取所有状态
            states = await self.client.get_states()

            # 验证结果
            success = len(states) > 0
            domains = {}
            for state in states:
                domain = state.domain
                if domain not in domains:
                    domains[domain] = 0
                domains[domain] += 1

            top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]
            domain_str = ", ".join([f"{d}: {c}" for d, c in top_domains])

            message = f"找到 {len(states)} 个实体。前5个域: {domain_str}"
            self.record_result("test_get_states", success, message)

        except Exception as e:
            self.record_result("test_get_states", False, f"出错: {str(e)}")

    async def test_get_specific_state(self):
        """测试获取特定实体状态"""
        # 测试几个不同类型的实体
        entities_to_test = [
            self.test_config.get("light_entity"),
            self.test_config.get("switch_entity"),
            self.test_config.get("sensor_entity"),
        ]

        for entity_id in entities_to_test:
            if not entity_id:
                continue

            try:
                # 获取状态
                state = await self.client.get_state(entity_id)

                # 验证结果
                if state:
                    message = f"实体 {entity_id} 的状态: {state.state}"
                    self.record_result(f"test_get_state_{entity_id}", True, message)
                else:
                    self.record_result(
                        f"test_get_state_{entity_id}", False, f"找不到实体 {entity_id}"
                    )

            except Exception as e:
                self.record_result(
                    f"test_get_state_{entity_id}", False, f"出错: {str(e)}"
                )

    async def test_get_services(self):
        """测试获取服务列表"""
        try:
            # 获取所有服务
            services = await self.client.get_services()

            # 验证结果
            success = len(services) > 0
            domains = await self.client.get_domains_with_services()

            message = f"找到 {len(services)} 个服务，跨越 {len(domains)} 个域"
            self.record_result("test_get_services", success, message)

            # 测试获取特定域的服务
            if domains:
                test_domain = domains[0]
                domain_services = await self.client.get_domain_services(test_domain)

                domain_success = len(domain_services) > 0
                domain_message = f"域 {test_domain} 有 {len(domain_services)} 个服务"
                self.record_result(
                    f"test_get_domain_services_{test_domain}",
                    domain_success,
                    domain_message,
                )

        except Exception as e:
            self.record_result("test_get_services", False, f"出错: {str(e)}")

    async def test_get_registries(self):
        """测试获取各种注册表"""
        try:
            # 获取实体注册表
            entity_registry = await self.client.get_entity_registry()
            entity_success = len(entity_registry) > 0
            entity_message = f"找到 {len(entity_registry)} 个注册实体"
            self.record_result(
                "test_get_entity_registry", entity_success, entity_message
            )

            # 获取设备注册表
            device_registry = await self.client.get_device_registry()
            device_success = len(device_registry) > 0
            device_message = f"找到 {len(device_registry)} 个注册设备"
            self.record_result(
                "test_get_device_registry", device_success, device_message
            )

            # 获取区域注册表
            area_registry = await self.client.get_area_registry()
            area_success = len(area_registry) > 0
            area_message = f"找到 {len(area_registry)} 个注册区域"
            self.record_result("test_get_area_registry", area_success, area_message)

            # 测试缓存
            cached_entities = self.client.get_cached_registry()
            cached_devices = self.client.get_cached_devices()
            cached_areas = self.client.get_cached_areas()

            cache_success = (
                len(cached_entities) > 0
                and len(cached_devices) > 0
                and len(cached_areas) > 0
            )

            cache_message = (
                f"缓存包含 {len(cached_entities)} 个实体, "
                f"{len(cached_devices)} 个设备, "
                f"{len(cached_areas)} 个区域"
            )

            self.record_result("test_registry_cache", cache_success, cache_message)

        except Exception as e:
            self.record_result("test_get_registries", False, f"出错: {str(e)}")

    async def test_get_history(self):
        """测试获取历史数据"""
        try:
            # 选择一个实体进行测试
            entity_id = self.test_config.get("sensor_entity")
            if not entity_id:
                self.skip_test("test_get_history", "未配置传感器实体")
                return

            # 获取过去24小时的历史数据
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)

            history = await self.client.get_history(
                entity_ids=[entity_id], start_time=start_time, end_time=end_time
            )

            # 验证结果
            success = len(history) > 0 and len(history[0]) > 0

            if success:
                entity_history = history[0]
                message = (
                    f"获取到 {len(entity_history)} 条历史记录，"
                    f"从 {entity_history[0]['last_changed']} 到 {entity_history[-1]['last_changed']}"
                )
            else:
                message = "未获取到历史数据"

            self.record_result("test_get_history", success, message)

            # 测试日志本
            logbook = await self.client.get_logbook(
                entity_ids=[entity_id], start_time=start_time, end_time=end_time
            )

            logbook_success = isinstance(logbook, list)
            logbook_message = f"获取到 {len(logbook)} 条日志记录"
            self.record_result("test_get_logbook", logbook_success, logbook_message)

        except Exception as e:
            self.record_result("test_get_history", False, f"出错: {str(e)}")

    async def test_get_statistics(self):
        """测试获取统计数据"""
        try:
            # 获取可用统计指标
            available_stats = await self.client.get_available_statistics()

            # 验证结果
            success = isinstance(available_stats, list)
            message = f"找到 {len(available_stats)} 个可用统计指标"
            self.record_result("test_get_available_statistics", success, message)

            # 如果有可用的统计指标，测试获取统计数据
            if available_stats:
                # 选择第一个统计指标
                statistic_id = available_stats[0].get("statistic_id")
                if statistic_id:
                    # 获取过去24小时的统计数据
                    end_time = datetime.now()
                    start_time = end_time - timedelta(hours=24)

                    statistics = await self.client.get_statistics(
                        statistic_ids=[statistic_id],
                        start_time=start_time,
                        end_time=end_time,
                        period="hour",
                    )

                    # 验证结果
                    stats_success = (
                        isinstance(statistics, dict) and statistic_id in statistics
                    )
                    stats_message = (
                        f"获取到 {statistic_id} 的统计数据: "
                        f"{len(statistics.get(statistic_id, [])) if isinstance(statistics, dict) else 0} 条记录"
                    )
                    self.record_result(
                        "test_get_statistics_data", stats_success, stats_message
                    )

        except Exception as e:
            self.record_result("test_get_statistics", False, f"出错: {str(e)}")

    async def test_area_entities(self):
        """测试区域和实体关系"""
        try:
            # 获取测试区域
            area_id = self.test_config.get("area_id")
            if not area_id:
                self.skip_test("test_area_entities", "未配置区域ID")
                return

            # 获取区域内的实体
            entities = await self.client.get_entities_by_area(area_id)

            # 验证结果
            success = isinstance(entities, list)
            message = f"区域 {area_id} 包含 {len(entities)} 个实体"
            self.record_result("test_area_entities", success, message)

            # 获取区域信息
            areas = await self.client.get_area_registry()
            area = next((a for a in areas if a.id == area_id), None)

            if area:
                area_message = f"区域名称: {area.name}"
                self.record_result("test_get_area_info", True, area_message)
            else:
                self.record_result("test_get_area_info", False, f"找不到区域 {area_id}")

        except Exception as e:
            self.record_result("test_area_entities", False, f"出错: {str(e)}")

    async def test_camera_image(self):
        """测试获取摄像头图像"""
        try:
            # 获取测试摄像头
            camera_entity = self.test_config.get("camera_entity")
            if not camera_entity:
                self.skip_test("test_camera_image", "未配置摄像头实体")
                return

            # 检查实体是否存在
            camera_state = await self.client.get_state(camera_entity)
            if not camera_state:
                self.skip_test(
                    "test_camera_image", f"摄像头实体 {camera_entity} 不存在"
                )
                return

            # 获取摄像头图像
            image_data = await self.client.get_camera_image(camera_entity)

            # 验证结果
            success = isinstance(image_data, bytes) and len(image_data) > 0
            message = f"获取到 {len(image_data)} 字节的图像数据"
            self.record_result("test_camera_image", success, message)

        except Exception as e:
            self.record_result("test_camera_image", False, f"出错: {str(e)}")

    async def test_template(self):
        """测试模板渲染"""
        try:
            # 创建一个简单的模板
            template = "{{ states('sun.sun') }}"

            # 渲染模板
            result = await self.client.get_template(template)

            # 验证结果
            success = isinstance(result, str) and result
            message = f"模板渲染结果: {result}"
            self.record_result("test_template", success, message)

            # 测试更复杂的模板
            complex_template = """
            {% set domains = namespace(list=[]) %}
            {% for entity in states %}
              {% set domain = entity.entity_id.split('.')[0] %}
              {% if domain not in domains.list %}
                {% set domains.list = domains.list + [domain] %}
              {% endif %}
            {% endfor %}
            {{ domains.list | sort | join(', ') }}
            """

            complex_result = await self.client.get_template(complex_template)
            complex_success = isinstance(complex_result, str) and "," in complex_result
            complex_message = f"复杂模板渲染结果: {complex_result[:50]}..."
            self.record_result(
                "test_complex_template", complex_success, complex_message
            )

        except Exception as e:
            self.record_result("test_template", False, f"出错: {str(e)}")

    async def test_call_service(self):
        """测试调用服务"""
        try:
            # 获取测试灯实体
            light_entity = self.test_config.get("light_entity")
            if not light_entity:
                self.skip_test("test_call_service", "未配置灯实体")
                return

            # 检查实体是否存在
            light_state = await self.client.get_state(light_entity)
            if not light_state:
                self.skip_test("test_call_service", f"灯实体 {light_entity} 不存在")
                return

            # 获取当前状态
            current_state = light_state.state
            logger.info(f"当前灯状态: {current_state}")

            # 切换灯的状态
            result = await self.client.call_service(
                "light", "toggle", {"entity_id": light_entity}
            )

            # 等待状态更新
            await asyncio.sleep(2)

            # 获取新状态
            new_state = await self.client.get_state(light_entity)
            new_state_value = new_state.state if new_state else "unknown"

            # 验证结果
            success = new_state_value != current_state
            message = f"灯状态从 {current_state} 变为 {new_state_value}"
            self.record_result("test_call_service", success, message)

            # 恢复原始状态
            await self.client.call_service(
                "light", "toggle", {"entity_id": light_entity}
            )
            logger.info(f"已恢复灯的原始状态")

        except Exception as e:
            self.record_result("test_call_service", False, f"出错: {str(e)}")

    async def test_notification(self):
        """测试发送通知"""
        try:
            # 获取通知目标
            target = self.test_config.get("notification_target")
            if not target:
                self.skip_test("test_notification", "未配置通知目标")
                return

            # 发送测试通知
            message = f"这是一条测试通知 - {datetime.now().strftime('%H:%M:%S')}"
            title = "Home Assistant 客户端测试"

            result = await self.client.send_notification(
                message=message, title=title, target=[target]
            )

            # 验证结果
            success = result is not None
            self.record_result("test_notification", success, f"已发送通知到 {target}")

        except Exception as e:
            self.record_result("test_notification", False, f"出错: {str(e)}")

    async def test_websocket_subscription(self):
        """测试 WebSocket 订阅"""
        try:
            # 创建事件处理函数
            events = []

            def handle_state_change(event):
                entity_id = event.entity_id
                old_state = event.old_state.state if event.old_state else None
                new_state = event.new_state.state if event.new_state else None
                events.append((entity_id, old_state, new_state))
                logger.info(f"状态变化: {entity_id} 从 {old_state} 变为 {new_state}")

            # 注册回调
            self.client.register_state_change_callback(handle_state_change)

            # 等待 5 秒钟，观察状态变化
            logger.info("正在监听状态变化，等待 5 秒...")
            await asyncio.sleep(5)

            # 取消注册回调
            self.client.unregister_state_change_callback(handle_state_change)

            # 验证结果
            message = f"捕获到 {len(events)} 个状态变化事件"
            self.record_result("test_websocket_subscription", True, message)

        except Exception as e:
            self.record_result("test_websocket_subscription", False, f"出错: {str(e)}")

    async def test_system_info(self):
        """测试获取系统信息"""
        try:
            # 获取 Home Assistant 配置
            config = await self.client.get_config()

            # 获取前端版本
            version = await self.client.get_frontend_version()

            # 获取位置信息
            location = await self.client.get_location_info()

            # 获取系统健康信息
            try:
                health = await self.client.get_system_health()
                health_success = isinstance(health, dict)
            except Exception:
                health_success = False
                health = {}

            # 获取实体类别
            categories = await self.client.get_entity_categories()

            # 获取每个域的实体数量
            domain_counts = await self.client.get_entity_count_by_domain()

            # 验证结果
            success = (
                isinstance(config, dict)
                and isinstance(version, str)
                and isinstance(location, dict)
                and isinstance(categories, dict)
                and isinstance(domain_counts, dict)
            )

            message = (
                f"Home Assistant 版本: {version}, "
                f"位置: {location.get('location_name', '未知')}, "
                f"时区: {location.get('time_zone', '未知')}, "
                f"实体类别: {len(categories)}, "
                f"域数量: {len(domain_counts)}"
            )

            self.record_result("test_system_info", success, message)

            # 记录系统健康信息
            if health_success:
                health_message = ", ".join(
                    [f"{k}: {v}" for k, v in list(health.items())[:5]]
                )
                self.record_result(
                    "test_system_health", True, f"系统健康信息: {health_message}..."
                )
            else:
                self.record_result("test_system_health", False, "无法获取系统健康信息")

        except Exception as e:
            self.record_result("test_system_info", False, f"出错: {str(e)}")


async def main():
    """主函数"""
    # 询问是否更新配置
    print("Home Assistant 集成测试")
    print("======================")
    print(f"当前配置:")
    print(f"  URL: {HA_CONFIG['base_url']}")
    print(f"  验证SSL: {HA_CONFIG['verify_ssl']}")
    print()

    update_config = input("是否需要更新配置? (y/n): ").lower() == "y"
    if update_config:
        HA_CONFIG["base_url"] = (
            input(f"Home Assistant URL [{HA_CONFIG['base_url']}]: ")
            or HA_CONFIG["base_url"]
        )
        HA_CONFIG["access_token"] = input("长期访问令牌: ") or HA_CONFIG["access_token"]
        HA_CONFIG["verify_ssl"] = (
            input(f"验证SSL (true/false) [{HA_CONFIG['verify_ssl']}]: ").lower()
            in ("true", "t", "yes", "y", "1")
            if input(f"验证SSL (true/false) [{HA_CONFIG['verify_ssl']}]: ")
            else HA_CONFIG["verify_ssl"]
        )

    # 询问是否更新测试配置
    update_test_config = input("是否需要更新测试实体配置? (y/n): ").lower() == "y"
    if update_test_config:
        for key, value in TEST_CONFIG.items():
            TEST_CONFIG[key] = input(f"{key} [{value}]: ") or value

    # 创建并运行测试
    test = IntegrationTest(HA_CONFIG, TEST_CONFIG)
    success = await test.run_tests()

    # 返回退出码
    return 0 if success else 1


if __name__ == "__main__":
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
