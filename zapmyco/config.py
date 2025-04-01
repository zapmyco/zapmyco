from zapmyco.security.encryption import SecureStorage


class Config:
    """
    应用程序配置类。
    从环境变量加载配置项。
    """

    def __init__(self):
        storage = SecureStorage()
        loaded_creds = storage.load_credentials()
        # self.LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.LLM_BASE_URL = "https://api.deepseek.com"
        self.LLM_API_KEY = loaded_creds.get("deepseek_api_key")
        self.LLM_MODEL = "deepseek-chat"

        self.DASHSCOPE_API_KEY = loaded_creds.get("dashscope_api_key")
        self.DOUBAO_API_KEY = loaded_creds.get("doubao_api_key")
        self.DEEPSEEK_API_KEY = loaded_creds.get("deepseek_api_key")

        self.HASS_ACCESS_TOKEN = loaded_creds.get("hass_access_token")
        self.HASS_URL = "http://localhost:8123"
        self.HASS_VERIFY_SSL = False
        self.HASS_WEBSOCKET_TIMEOUT = 30
        # Add other configurations here as needed
        # Example:
        # self.DATABASE_URL: str | None = os.getenv("DATABASE_URL")
        # self.SECRET_KEY: str | None = os.getenv("SECRET_KEY")

    def __post_init__(self):
        # Perform validation if necessary
        if not self.DASHSCOPE_API_KEY:
            print("Warning: DASHSCOPE_API_KEY is not set in environment variables.")
        if not self.LLM_BASE_URL:
            print("Warning: LLM_BASE_URL is not set, using default.")


# Create a single instance of the Config class
_settings = Config()


def get_settings() -> Config:
    """
    获取配置实例。

    Returns:
        Config: 配置类的实例。
    """
    return _settings


# You can directly import 'settings' as well if you prefer
settings = get_settings()

if __name__ == "__main__":
    config = get_settings()
    print(f"DASHSCOPE_API_KEY: {config.DASHSCOPE_API_KEY}")
    print(f"DOUBAO_API_KEY: {config.DOUBAO_API_KEY}")
    print(f"HASS_ACCESS_TOKEN: {config.HASS_ACCESS_TOKEN}")
