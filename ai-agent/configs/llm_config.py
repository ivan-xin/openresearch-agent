"""
大语言模型配置 - Together.ai专用
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class LLMConfig(BaseSettings):
    """LLM配置 - 专用于Together.ai"""
    
    # Together.ai配置
    together_api_key: str = Field(..., env="TOGETHER_API_KEY")
    together_model: str = Field(default="Qwen/Qwen2.5-VL-72B-Instruct", env="TOGETHER_MODEL")
    together_base_url: str = Field(default="https://api.together.xyz/v1/chat/completions", env="TOGETHER_BASE_URL")
    
    # 通用配置
    max_tokens: int = Field(default=2000, env="LLM_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    timeout: int = Field(default=30, env="LLM_TIMEOUT")
    
    # Together.ai特有配置
    context_length_exceeded_behavior: str = Field(default="error")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow"
    }
    
    def validate_config(self):
        """验证配置"""
        if not self.together_api_key:
            raise ValueError("TOGETHER_API_KEY is required")
        if not self.together_model:
            raise ValueError("TOGETHER_MODEL is required")

# 全局LLM配置实例
llm_config = LLMConfig()
