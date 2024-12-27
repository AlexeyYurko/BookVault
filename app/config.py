import enum
import os
from pathlib import Path

from pydantic_settings import BaseSettings

_ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local')

ENV_DIR_PATH = Path(__file__).resolve().parents[1]
env_file = ENV_DIR_PATH / '.env'


class Environment(enum.StrEnum):
    local = enum.auto()
    prod = enum.auto()
    qa = enum.auto()

    @property
    def is_local(self):
        return self == self.local

    @property
    def is_prod(self):
        return self == self.prod

    @property
    def is_qa(self):
        return self == self.qa


class Settings(BaseSettings):
    temp_dir: str = 'tmp'
    cover_images_path: str = 'cover_images'
    static_path: str = 'static'

    model_config = {
        'env_file': [ENV_DIR_PATH / '.env', ENV_DIR_PATH / f'.env.{_ENVIRONMENT}'],
        'env_file_encoding': 'utf-8',
        'env_nested_delimiter': '__',
        'extra': 'ignore',
    }


settings = Settings(
    environment=getattr(Environment, _ENVIRONMENT),
)
