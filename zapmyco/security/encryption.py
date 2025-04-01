from cryptography.fernet import Fernet
import os
import json


class SecureStorage:
    def __init__(self):
        key_path = os.path.expanduser("~/.zapmyco/secret.key")
        creds_path = os.path.expanduser("~/.zapmyco/credentials.enc")
        self.key_file_path = key_path
        self.credentials_file_path = creds_path

        # 检查密钥文件是否存在，不存在则创建
        if not os.path.exists(self.key_file_path):
            self._generate_key()

        # 加载密钥
        with open(self.key_file_path, "rb") as key_file:
            self.key = key_file.read()
        self.cipher = Fernet(self.key)

    def _generate_key(self):
        """生成新密钥并保存"""
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(self.key_file_path), exist_ok=True)
        with open(self.key_file_path, "wb") as key_file:
            key_file.write(key)
        # 设置文件权限（仅在类Unix系统有效）
        os.chmod(self.key_file_path, 0o600)

    def save_credentials(self, credentials_dict):
        """加密并保存凭证"""
        encrypted_data = self.cipher.encrypt(json.dumps(credentials_dict).encode())
        os.makedirs(os.path.dirname(self.credentials_file_path), exist_ok=True)
        with open(self.credentials_file_path, "wb") as file:
            file.write(encrypted_data)
        # 设置文件权限
        os.chmod(self.credentials_file_path, 0o600)

    def load_credentials(self):
        """加载并解密凭证"""
        if not os.path.exists(self.credentials_file_path):
            return {}

        with open(self.credentials_file_path, "rb") as file:
            encrypted_data = file.read()

        decrypted_data = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted_data)


# 使用示例
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    storage = SecureStorage()

    # 保存API密钥
    storage.save_credentials(
        {
            "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY"),
            "doubao_api_key": os.getenv("DOUBAO_API_KEY"),
            "hass_access_token": os.getenv("HASS_ACCESS_TOKEN"),
            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY"),
        }
    )

    # 读取API密钥
    loaded_creds = storage.load_credentials()
    print(json.dumps(loaded_creds, indent=2))
