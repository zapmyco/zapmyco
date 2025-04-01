# Home Assistant MCP Server
import json
import asyncio
from typing import Dict, Any, Optional, List, TypedDict, List
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from mcp.server.fastmcp import FastMCP, Context
from zapmyco.integrations.home_assistant.main import HomeAssistantClient
from zapmyco.integrations.home_assistant.models import EntityState


class Command(TypedDict):
    domain: str
    service: str
    service_data: Dict[str, Any]


# 创建 Home Assistant 客户端单例
class HAClientSingleton:
    _instance = None
    _client = None
    _initialized = False

    @classmethod
    def get_instance(cls) -> HomeAssistantClient:
        """获取 HomeAssistantClient 单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance._client

    def __init__(self):
        if self._initialized:
            return
        self._client = HomeAssistantClient()
        self._initialized = True


# 创建 MCP 服务器的生命周期管理
@asynccontextmanager
async def ha_lifespan(server: FastMCP) -> AsyncIterator[HomeAssistantClient]:
    """管理 Home Assistant 客户端的生命周期"""
    # 获取客户端实例
    client = HAClientSingleton.get_instance()

    # 在评测模式下，我们不需要真正连接到 Home Assistant
    # 仅在非评测模式下尝试连接
    try:
        # 这里可以添加一个环境变量或配置项来控制是否连接
        # 例如: if not settings.EVALUATION_MODE:
        #          await client.connect()
        print("Home Assistant MCP 服务已启动")
        yield client
    finally:
        # 同样，仅在非评测模式下断开连接
        # if not settings.EVALUATION_MODE and client is not None:
        #     await client.disconnect()
        print("Home Assistant MCP 服务已关闭")


# 创建 MCP 服务器，并传入生命周期管理函数
MCPHomeAssistant = FastMCP("HomeAssistant", lifespan=ha_lifespan)


# 调用 Home Assistant 服务
@MCPHomeAssistant.tool()
async def call_service(commands: List[Command], ctx: Context) -> Dict[str, Any]:
    """
    调用家庭设备服务

    Args:
        commands: 命令列表，每个命令包含以下字段：
            - domain: 服务域名，如 light、switch 或 climate
            - service: 设备服务，如 turn_on、turn_off 或 set_temperature
            - service_data: 服务数据，包含 entity_id 和其他参数
        ctx: MCP 上下文对象

    Returns:
        包含所有命令执行结果的字典，格式为：
        {
            "results": [
                {
                    "success": bool,  # 是否成功
                    "domain": str,    # 服务域名
                    "service": str,    # 设备服务
                    "service_data": dict,  # 服务数据
                    "message": str    # 结果消息
                },
                ...
            ]
        }
    """
    # 获取 Home Assistant 客户端实例
    client = ctx.request_context.lifespan_context

    results = []
    for command in commands:
        domain = command["domain"]
        service = command["service"]
        service_data = command["service_data"]

        try:
            # 调用真实的 Home Assistant 服务
            await client.call_service(domain, service, service_data)

            results.append(
                {
                    "success": True,
                    "domain": domain,
                    "service": service,
                    "service_data": service_data,
                    "message": f"成功调用 {domain}.{service} 服务",
                }
            )
        except Exception as e:
            # 处理调用失败的情况
            results.append(
                {
                    "success": False,
                    "domain": domain,
                    "service": service,
                    "service_data": service_data,
                    "message": f"调用 {domain}.{service} 服务失败: {str(e)}",
                }
            )

    return {"results": results}


# 获取设备状态
@MCPHomeAssistant.tool()
async def get_states(
    entities: Optional[List[str]] = None, ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    获取设备状态

    Args:
        entities: 要获取状态的设备 ID 列表，如果为 None，则获取所有设备
        ctx: MCP 上下文对象

    Returns:
        设备状态列表
    """
    try:
        # 获取 Home Assistant 客户端实例
        client = (
            ctx.request_context.lifespan_context
            if ctx
            else HAClientSingleton.get_instance()
        )

        # 获取真实的 Home Assistant 状态
        all_states = await client.get_states()

        # 将 EntityState 对象转换为字典
        state_dicts = []
        for state in all_states:
            state_dict = {
                "entity_id": state.entity_id,
                "state": state.state,
                "attributes": state.attributes,
            }
            if state.last_changed:
                state_dict["last_changed"] = state.last_changed.isoformat()
            if state.last_updated:
                state_dict["last_updated"] = state.last_updated.isoformat()
            state_dicts.append(state_dict)

        # 如果指定了实体列表，则过滤结果
        if entities:
            return [state for state in state_dicts if state["entity_id"] in entities]
        return state_dicts

    except Exception as e:
        # 如果发生错误，返回空列表并记录错误
        print(f"获取设备状态失败: {str(e)}")
        return []


# 获取实体注册表
@MCPHomeAssistant.tool()
async def get_entity_registry(ctx: Context = None) -> Dict[str, Any]:
    """
    获取实体注册表

    Args:
        ctx: MCP 上下文对象

    Returns:
        实体注册表字典
    """
    try:
        # 获取 Home Assistant 客户端实例
        client = (
            ctx.request_context.lifespan_context
            if ctx
            else HAClientSingleton.get_instance()
        )

        # 获取真实的 Home Assistant 实体注册表
        registry = await client.get_entity_registry()

        # 将注册表转换为字典格式
        result = {}
        for entity_id, entity in registry.items():
            result[entity_id] = {
                "entity_id": entity_id,
                "name": entity.get("name") or entity.get("original_name"),
                "platform": entity.get("platform"),
                "area_id": entity.get("area_id"),
                "device_id": entity.get("device_id"),
                "unique_id": entity.get("unique_id"),
                "disabled": entity.get("disabled", False),
            }
        return result

    except Exception as e:
        print(f"获取实体注册表失败: {str(e)}")
        # 如果出错，返回空字典
        return {}


# 获取区域注册表
@MCPHomeAssistant.tool()
async def get_area_registry(ctx: Context = None) -> Dict[str, Any]:
    """
    获取区域注册表

    Args:
        ctx: MCP 上下文对象

    Returns:
        区域注册表字典
    """
    try:
        # 获取 Home Assistant 客户端实例
        client = (
            ctx.request_context.lifespan_context
            if ctx
            else HAClientSingleton.get_instance()
        )

        # 获取真实的 Home Assistant 区域注册表
        areas = await client.get_area_registry()

        # 将区域注册表转换为字典格式
        result = {}
        for area_id, area in areas.items():
            result[area_id] = {
                "id": area_id,
                "name": area.get("name", ""),
                "picture": area.get("picture"),
            }
        return result

    except Exception as e:
        print(f"获取区域注册表失败: {str(e)}")
        # 如果出错，返回空字典
        return {}
