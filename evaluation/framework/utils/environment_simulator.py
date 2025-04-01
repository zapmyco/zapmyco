import time


class EnvironmentSimulator:
    def __init__(self):
        """初始化家庭环境模拟器"""
        self.devices = {}
        self.sensors = {}
        self.state_history = []

    def setup(self, context):
        """根据测试上下文设置环境状态"""
        if "device_status" in context:
            self.devices = context["device_status"].copy()

        if "sensor_readings" in context:
            self.sensors = context["sensor_readings"].copy()

        # 记录初始状态
        self._record_state()

    def execute_action(self, device, action, parameters=None):
        """执行设备动作并返回结果"""
        if device not in self.devices:
            return {"success": False, "error": "Device not found"}

        # 根据动作类型更新设备状态
        if action == "turn_on":
            self.devices[device] = "on"
        elif action == "turn_off":
            self.devices[device] = "off"
        # ... 其他动作类型

        # 记录状态变化
        self._record_state()
        return {"success": True}

    def get_changes(self):
        """获取环境变化"""
        if len(self.state_history) < 2:
            return {}

        initial_state = self.state_history[0]
        current_state = self.state_history[-1]

        changes = {"devices": {}, "sensors": {}}

        # 计算设备状态变化
        for device, state in current_state["devices"].items():
            if (
                device in initial_state["devices"]
                and initial_state["devices"][device] != state
            ):
                changes["devices"][device] = {
                    "from": initial_state["devices"][device],
                    "to": state,
                }

        return changes

    def _record_state(self):
        """记录当前环境状态"""
        self.state_history.append(
            {
                "timestamp": time.time(),
                "devices": self.devices.copy(),
                "sensors": self.sensors.copy(),
            }
        )
