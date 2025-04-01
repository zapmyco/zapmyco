import pytest
import os
import json


# 定义测试数据路径
@pytest.fixture(scope="session")
def fixtures_path():
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="session")
def ha_config_path(fixtures_path):
    return os.path.join(fixtures_path, "configs", "home_assistant")


@pytest.fixture(scope="session")
def ha_data_path(fixtures_path):
    return os.path.join(fixtures_path, "data", "home_assistant")


# 加载配置
@pytest.fixture
def ha_config(ha_config_path):
    with open(os.path.join(ha_config_path, "config.json"), "r") as f:
        return json.load(f)
