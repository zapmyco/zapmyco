import httpx
from config.secrets import MI_API_CONFIG

async def set_device_state(device_id: str, siid: int, piid: int, value: bool) -> dict:
    """
    设置小米设备状态
    
    Args:
        device_id: 设备ID
        siid: 服务ID
        piid: 属性ID
        value: 要设置的值
    
    Returns:
        API响应内容
    """
    payload = {
        "params": [{
            "did": device_id,
            "siid": siid,
            "piid": piid,
            "value": value
        }]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MI_API_CONFIG['url'],
            headers=MI_API_CONFIG['headers'],
            json=payload
        )
        return response.json() 