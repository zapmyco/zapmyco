import json
import logging
import Levenshtein
import jieba
from datetime import datetime
from openai.types.chat import ChatCompletion
from .context_provider import ContextProvider, DefaultContextProvider
from typing import Optional


class HomeAssistantMCP:
    """Home Assistant Model Context Protocol"""

    def __init__(self, ha_client, context_provider: Optional[ContextProvider] = None):
        self.ha_client = ha_client
        self.context_provider = context_provider or DefaultContextProvider(ha_client)
        self.logger = logging.getLogger("HomeAssistantMCP")

    async def get_context(self, query=None, entities=None):
        """
        获取模型上下文

        Args:
            query: 用户查询，用于确定相关实体
            entities: 指定需要包含在上下文中的实体

        Returns:
            模型上下文字典
        """
        # 获取设备状态
        states = await self.context_provider.get_states(query, entities)

        entity_ids = []
        for state in states:
            entity_ids.append(state.get("entity_id"))

        # 获取设备能力
        capabilities = await self._get_device_capabilities(entity_ids)

        # 获取区域信息
        areas = await self.context_provider.get_area_registry()

        # 构建上下文
        context = {
            "device_states": states,
            "device_capabilities": capabilities,
            "areas": areas,
            "timestamp": datetime.now().isoformat(),
        }

        return context

    async def _get_relevant_states(self, query=None, entities=None):
        """获取相关实体状态"""
        if None is not entities:
            # 如果指定了实体，只获取这些实体的状态
            return await self.ha_client.get_states(entities)

        if None is not query:
            # 基于查询识别相关实体
            # relevant_entities = await self._identify_relevant_entities(query)
            # return await self.ha_client.get_states(relevant_entities)
            return await self.ha_client.get_states()

        # 默认获取所有状态
        return await self.ha_client.get_states()

    async def _identify_relevant_entities(self, query):
        """基于用户查询识别相关实体"""
        # 这里可以使用更复杂的算法，如基于关键词匹配、实体识别等
        # 简化实现
        relevant_entities = []

        # 获取所有实体
        all_entities = await self.ha_client.get_entity_registry()

        # 提取查询中的关键词
        keywords = self._extract_keywords(query)

        # 匹配实体
        for entity_id, entity_info in all_entities.items():
            # 检查实体ID、名称和区域是否匹配关键词
            entity_name = entity_info.get("name", "").lower()
            area_id = entity_info.get("area_id", "").lower()

            for keyword in keywords:
                if (
                    keyword in entity_id.lower()
                    or keyword in entity_name
                    or keyword in area_id
                ):
                    relevant_entities.append(entity_id)
                    break

        return relevant_entities

    def _extract_keywords(self, query):
        """从查询中提取关键词"""
        # 简化实现，实际可以使用NLP技术提取更准确的关键词
        # 移除停用词，提取名词和形容词
        stop_words = {"的", "了", "在", "是", "我", "你", "请", "把", "将", "和", "与"}
        words = [word for word in jieba.cut(query) if word not in stop_words]
        return words

    async def _get_device_capabilities(self, entity_ids):
        """获取设备能力"""
        capabilities = {}

        # 获取实体注册表
        registry = await self.context_provider.get_entity_registry()

        for entity_id in entity_ids:
            if entity_id in registry:
                entity_info = registry[entity_id]
                domain = entity_id.split(".")[0]

                # 基于域确定基本能力
                base_capabilities = self._get_domain_capabilities(domain)

                # 合并特定实体的能力
                entity_capabilities = entity_info.get("capabilities", {})

                capabilities[entity_id] = {**base_capabilities, **entity_capabilities}

        return capabilities

    def _get_domain_capabilities(self, domain):
        """获取特定域的基本能力"""
        # 不同设备类型的基本能力
        domain_capabilities = {
            "light": {
                "actions": ["turn_on", "turn_off", "toggle"],
                "attributes": ["brightness", "color_temp", "rgb_color"],
            },
            "switch": {"actions": ["turn_on", "turn_off", "toggle"], "attributes": []},
            "climate": {
                "actions": ["set_temperature", "set_hvac_mode", "turn_on", "turn_off"],
                "attributes": ["temperature", "hvac_mode", "fan_mode"],
            },
            "cover": {
                "actions": ["open_cover", "close_cover", "set_cover_position"],
                "attributes": ["position"],
            },
            # 其他设备类型...
        }

        return domain_capabilities.get(domain, {"actions": [], "attributes": []})

    async def _get_area_information(self):
        """获取区域信息"""
        try:
            # 获取区域注册表
            areas = await self.ha_client.get_area_registry()

            # 获取每个区域中的实体
            area_entities = {}
            registry = await self.ha_client.get_entity_registry()

            for entity_id, entity_info in registry.items():
                area_id = entity_info.get("area_id")
                if area_id:
                    if area_id not in area_entities:
                        area_entities[area_id] = []
                    area_entities[area_id].append(entity_id)

            # 构建区域信息
            area_info = {}
            for area_id, area in areas.items():
                area_info[area_id] = {
                    "name": area.get("name", area_id),
                    "entities": area_entities.get(area_id, []),
                }

            return area_info

        except Exception as e:
            self.logger.error(f"Failed to get area information: {str(e)}")
            return {}

    async def execute_intent(self, intent):
        """
        执行意图

        Args:
            intent: LLM生成的意图

        Returns:
            执行结果
        """
        try:
            # 验证意图格式
            if not self._validate_intent(intent):
                return {"success": False, "error": "Invalid intent format"}

            # 解析设备和动作
            function = intent.get("function", {})
            tool_name = function.get("name")
            tool_arguments = function.get("arguments")

            # 映射到Home Assistant实体和服务
            # entity_service = await self._map_to_ha_service(tool_name, tool_arguments)
            # if not entity_service["success"]:
            #     return entity_service

            # # 构建服务调用参数
            # service_data = {"entity_id": entity_service["entity_id"]}

            # # 添加其他参数
            # if "parameters" in execution:
            #     mapped_params = self._map_parameters(
            #         execution["parameters"], entity_service["domain"]
            #     )
            #     service_data.update(mapped_params)

            # 调用服务
            result = await self.ha_client.call_service(**json.loads(tool_arguments))

            # 获取执行后的状态
            # new_state = await self.ha_client.get_states([tool_name])

            return {
                "success": result["success"],
                "device": tool_name,
                "action": tool_arguments,
                "service_called": f"{tool_name}",
                # "new_state": new_state.get(tool_name),
                "message": result.get("message", ""),
            }

        except Exception as e:
            self.logger.error(f"Execution error: {str(e)}")
            return {"success": False, "error": str(e)}

    def _validate_intent(self, intent):
        """验证意图格式"""
        # if not isinstance(intent, openai.types.chat.ChatCompletion.Choice):
        #     return False

        if "function" not in intent:
            return False

        return True

    async def _map_to_ha_service(self, device, action):
        """将设备和动作映射到Home Assistant实体和服务"""
        # 查找匹配的实体
        entity_id = await self._find_entity_by_name(device)
        if not entity_id:
            return {"success": False, "error": f"Device not found: {device}"}

        # 获取实体域
        domain = entity_id.split(".")[0]

        # 映射动作到服务
        service = self._map_action_to_service(domain, action)
        if not service:
            return {
                "success": False,
                "error": f"Unsupported action: {action} for {domain}",
            }

        return {
            "success": True,
            "entity_id": entity_id,
            "domain": domain,
            "service": service,
        }

    async def _find_entity_by_name(self, device_name):
        """根据名称查找实体"""
        # 获取实体注册表
        registry = await self.ha_client.get_entity_registry()

        # 直接匹配实体ID
        if device_name in registry:
            return device_name

        # 匹配友好名称
        for entity_id, entity_info in registry.items():
            if entity_info.get("name", "").lower() == device_name.lower():
                return entity_id

        # 模糊匹配
        best_match = None
        best_score = 0

        for entity_id, entity_info in registry.items():
            entity_name = entity_info.get("name", entity_id)
            score = self._calculate_similarity(device_name, entity_name)

            if score > best_score and score > 0.7:  # 70% 匹配阈值
                best_match = entity_id
                best_score = score

        return best_match

    def _calculate_similarity(self, str1, str2):
        """计算字符串相似度"""
        # 简化实现，可以使用更复杂的算法
        str1 = str1.lower()
        str2 = str2.lower()

        if str1 in str2 or str2 in str1:
            return 0.8

        # Levenshtein距离
        distance = Levenshtein.distance(str1, str2)
        max_len = max(len(str1), len(str2))

        if max_len == 0:
            return 0

        return 1 - (distance / max_len)

    def _map_action_to_service(self, domain, action):
        """将动作映射到服务"""
        # 通用动作映射
        common_actions = {
            "turn_on": "turn_on",
            "open": "turn_on",
            "start": "turn_on",
            "turn_off": "turn_off",
            "close": "turn_off",
            "stop": "turn_off",
            "toggle": "toggle",
        }

        # 特定域的动作映射
        domain_actions = {
            "light": {
                **common_actions,
                "dim": "turn_on",  # 带亮度参数
                "brighten": "turn_on",  # 带亮度参数
                "set_brightness": "turn_on",  # 带亮度参数
                "change_color": "turn_on",  # 带颜色参数
            },
            "cover": {
                "open": "open_cover",
                "close": "close_cover",
                "stop": "stop_cover",
                "set_position": "set_cover_position",
            },
            "climate": {
                **common_actions,
                "set_temperature": "set_temperature",
                "set_mode": "set_hvac_mode",
            },
            # 其他域...
        }

        # 查找特定域的映射
        if domain in domain_actions and action in domain_actions[domain]:
            return domain_actions[domain][action]

        # 回退到通用映射
        return common_actions.get(action)

    def _map_parameters(self, parameters, domain):
        """映射参数到Home Assistant服务数据"""
        mapped = {}

        # 特定域的参数映射
        if domain == "light":
            if "brightness" in parameters:
                # Home Assistant使用0-255的亮度范围
                brightness = parameters["brightness"]
                if isinstance(brightness, (int, float)) and 0 <= brightness <= 100:
                    mapped["brightness"] = int(brightness * 255 / 100)

            if "color" in parameters:
                color = parameters["color"]
                if isinstance(color, str):
                    # 颜色名称到RGB的映射
                    color_map = {
                        "red": [255, 0, 0],
                        "green": [0, 255, 0],
                        "blue": [0, 0, 255],
                        "white": [255, 255, 255],
                        "yellow": [255, 255, 0],
                        "purple": [128, 0, 128],
                        "orange": [255, 165, 0],
                        "pink": [255, 192, 203],
                    }

                    mapped["rgb_color"] = color_map.get(color.lower(), [255, 255, 255])
                elif isinstance(color, list) and len(color) == 3:
                    mapped["rgb_color"] = color

        elif domain == "climate":
            if "temperature" in parameters:
                mapped["temperature"] = parameters["temperature"]

            if "mode" in parameters:
                mapped["hvac_mode"] = parameters["mode"]

        elif domain == "cover":
            if "position" in parameters:
                position = parameters["position"]
                if isinstance(position, (int, float)) and 0 <= position <= 100:
                    mapped["position"] = position

        # 其他域的参数映射...

        return mapped
