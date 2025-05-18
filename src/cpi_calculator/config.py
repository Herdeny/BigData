# config.py
import logging
from dynaconf import Dynaconf
from pathlib import Path

# 初始化日志配置
def init_logging(log_conf='logging.yaml'):
    """初始化日志配置（保持原有逻辑）"""
    # ...原有日志初始化代码...

# 创建配置实例
settings = Dynaconf(
    settings_files=["settings.yml", ".secrets.yml"],
    environments=True,
    envvar_prefix="CPI",
    root_path=Path(__file__).parent,
    default_env="default",
    env="prod"  # 可通过环境变量 DYNACONF_ENV 覆盖
)

__all__ = ['settings']
