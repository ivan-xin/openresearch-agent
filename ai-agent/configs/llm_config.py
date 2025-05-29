"""
大语言模型配置
"""
from pydantic import BaseSettings, Field
from typing import Optional

class LLMConfig(BaseSettings):
    """LLM配置"""
    
    provider: str = Field(default="openai", env="LLM_PROVIDER")
    
    # OpenAI配置
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    
    # 通用配置
    max_tokens: int = Field(default=2000, env="LLM_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    timeout: int = Field(default=30, env="LLM_TIMEOUT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局LLM配置实例
llm_config = LLMConfig()
