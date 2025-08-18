"""
Configuration management for WattMCP
"""

import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class MQTTConfig:
    """MQTT configuration"""
    broker: str = "localhost"
    port: int = 1883
    username: str = None
    password: str = None
    use_tls: bool = False
    ca_certs: str = None
    certfile: str = None
    keyfile: str = None

@dataclass
class APIConfig:
    """REST API configuration"""
    base_url: str = "http://localhost:8000"
    api_key: str = "your_secret_api_key"
    timeout: int = 30

@dataclass
class ServerConfig:
    """MCP Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    log_level: str = "info"
    
@dataclass
class EdgeClientConfig:
    """MPSoC Edge Client configuration"""
    device_id: str = "mpsoc-01"
    geo_location: str = "West Lafayette, Indiana, USA"
    telemetry_interval: float = 1.0
    hw_lib_path: str = "./libpowerdojo.so"
    model_parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.model_parameters is None:
            self.model_parameters = {
                "type": "BuckConverter",
                "L_uH": 22.0,
                "C_uF": 470.0
            }

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    password: str = None
    db: int = 0
    max_connections: int = 10

class ConfigManager:
    """Configuration manager for WattMCP"""
    
    def __init__(self):
        self.mqtt = MQTTConfig()
        self.api = APIConfig()
        self.server = ServerConfig()
        self.edge_client = EdgeClientConfig()
        self.redis = RedisConfig()
        
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        
        # MQTT Configuration
        self.mqtt.broker = os.getenv('MQTT_BROKER', self.mqtt.broker)
        self.mqtt.port = int(os.getenv('MQTT_PORT', self.mqtt.port))
        self.mqtt.username = os.getenv('MQTT_USERNAME', self.mqtt.username)
        self.mqtt.password = os.getenv('MQTT_PASSWORD', self.mqtt.password)
        self.mqtt.use_tls = os.getenv('MQTT_USE_TLS', 'false').lower() == 'true'
        self.mqtt.ca_certs = os.getenv('MQTT_CA_CERTS', self.mqtt.ca_certs)
        self.mqtt.certfile = os.getenv('MQTT_CERTFILE', self.mqtt.certfile)
        self.mqtt.keyfile = os.getenv('MQTT_KEYFILE', self.mqtt.keyfile)
        
        # API Configuration
        self.api.base_url = os.getenv('API_BASE_URL', self.api.base_url)
        self.api.api_key = os.getenv('API_KEY', self.api.api_key)
        self.api.timeout = int(os.getenv('API_TIMEOUT', self.api.timeout))
        
        # Server Configuration
        self.server.host = os.getenv('SERVER_HOST', self.server.host)
        self.server.port = int(os.getenv('SERVER_PORT', self.server.port))
        self.server.reload = os.getenv('SERVER_RELOAD', 'false').lower() == 'true'
        self.server.workers = int(os.getenv('SERVER_WORKERS', self.server.workers))
        self.server.log_level = os.getenv('LOG_LEVEL', self.server.log_level)
        
        # Edge Client Configuration
        self.edge_client.device_id = os.getenv('DEVICE_ID', self.edge_client.device_id)
        self.edge_client.geo_location = os.getenv('GEO_LOCATION', self.edge_client.geo_location)
        self.edge_client.telemetry_interval = float(os.getenv('TELEMETRY_INTERVAL', 
                                                             self.edge_client.telemetry_interval))
        self.edge_client.hw_lib_path = os.getenv('HW_LIB_PATH', self.edge_client.hw_lib_path)
        
        # Redis Configuration
        self.redis.host = os.getenv('REDIS_HOST', self.redis.host)
        self.redis.port = int(os.getenv('REDIS_PORT', self.redis.port))
        self.redis.password = os.getenv('REDIS_PASSWORD', self.redis.password)
        self.redis.db = int(os.getenv('REDIS_DB', self.redis.db))
        self.redis.max_connections = int(os.getenv('REDIS_MAX_CONNECTIONS', 
                                                  self.redis.max_connections))
    
    def get_mqtt_config(self) -> Dict[str, Any]:
        """Get MQTT configuration as dict"""
        return {
            'broker': self.mqtt.broker,
            'port': self.mqtt.port,
            'username': self.mqtt.username,
            'password': self.mqtt.password,
            'use_tls': self.mqtt.use_tls,
            'ca_certs': self.mqtt.ca_certs,
            'certfile': self.mqtt.certfile,
            'keyfile': self.mqtt.keyfile
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration as dict"""
        return {
            'base_url': self.api.base_url,
            'api_key': self.api.api_key,
            'timeout': self.api.timeout
        }
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration as dict"""
        return {
            'host': self.server.host,
            'port': self.server.port,
            'reload': self.server.reload,
            'workers': self.server.workers,
            'log_level': self.server.log_level
        }
    
    def get_edge_client_config(self) -> Dict[str, Any]:
        """Get edge client configuration as dict"""
        return {
            'device_id': self.edge_client.device_id,
            'geo_location': self.edge_client.geo_location,
            'telemetry_interval': self.edge_client.telemetry_interval,
            'hw_lib_path': self.edge_client.hw_lib_path,
            'model_parameters': self.edge_client.model_parameters,
            'mqtt_broker': self.mqtt.broker,
            'mqtt_port': self.mqtt.port,
            'mqtt_username': self.mqtt.username,
            'mqtt_password': self.mqtt.password
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration as dict"""
        return {
            'host': self.redis.host,
            'port': self.redis.port,
            'password': self.redis.password,
            'db': self.redis.db,
            'max_connections': self.redis.max_connections
        }

# Global configuration instance
config = ConfigManager()

# Convenience functions
def get_config() -> ConfigManager:
    """Get the global configuration instance"""
    return config

def load_config_from_file(config_path: str) -> ConfigManager:
    """Load configuration from JSON file"""
    import json
    
    try:
        with open(config_path, 'r') as f:
            file_config = json.load(f)
        
        # Update configuration with file values
        cfg = ConfigManager()
        
        if 'mqtt' in file_config:
            for key, value in file_config['mqtt'].items():
                setattr(cfg.mqtt, key, value)
                
        if 'api' in file_config:
            for key, value in file_config['api'].items():
                setattr(cfg.api, key, value)
                
        if 'server' in file_config:
            for key, value in file_config['server'].items():
                setattr(cfg.server, key, value)
                
        if 'edge_client' in file_config:
            for key, value in file_config['edge_client'].items():
                setattr(cfg.edge_client, key, value)
                
        if 'redis' in file_config:
            for key, value in file_config['redis'].items():
                setattr(cfg.redis, key, value)
        
        return cfg
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading config from file {config_path}: {e}")
        return ConfigManager()

# Example configuration file structure
EXAMPLE_CONFIG = {
    "mqtt": {
        "broker": "localhost",
        "port": 1883,
        "username": "mpsoc-01",
        "password": "supersecretpassword",
        "use_tls": False
    },
    "api": {
        "base_url": "http://localhost:8000",
        "api_key": "your_secret_api_key",
        "timeout": 30
    },
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": False,
        "log_level": "info"
    },
    "edge_client": {
        "device_id": "mpsoc-01",
        "geo_location": "West Lafayette, Indiana, USA",
        "telemetry_interval": 1.0,
        "hw_lib_path": "./libpowerdojo.so",
        "model_parameters": {
            "type": "BuckConverter",
            "L_uH": 22.0,
            "C_uF": 470.0
        }
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0
    }
}

if __name__ == "__main__":
    # Dump example configuration
    import json
    print(json.dumps(EXAMPLE_CONFIG, indent=2))