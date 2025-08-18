#!/usr/bin/env python3
"""
WattMCP Server - Central Communication Hub
Implements REST API and MQTT broker for AI agent communication with MPSoC devices
"""

import asyncio
import json
import logging
import ssl
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import uuid4

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import redis
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
API_KEYS = {
    "ai-agent-01": "agent_secret_password",
    "mpsoc-01": "supersecretpassword"
}

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials not in API_KEYS.values():
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return credentials.credentials

# Data Models
class DeviceInfo(BaseModel):
    deviceId: str
    ipAddress: str
    geoLocation: str
    modelParameters: Dict[str, Any]

class TelemetryData(BaseModel):
    deviceId: str
    timestamp: str
    temperature: Dict[str, Any]
    controlStrategy: Dict[str, Any]

class CommandPayload(BaseModel):
    commandId: str = Field(default_factory=lambda: f"cmd-{uuid4()}")
    action: str
    payload: Dict[str, Any]

class CommandResponse(BaseModel):
    commandId: str
    status: str
    message: str

# Global state
devices: Dict[str, DeviceInfo] = {}
telemetry_cache: Dict[str, Dict] = {}
command_responses: Dict[str, CommandResponse] = {}

# Redis for persistence
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TLS_PORT = 8883

class MQTTManager:
    def __init__(self):
        self.client = mqtt.Client(client_id="mcp_server")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"MQTT connected with result code {rc}")
        # Subscribe to all device telemetry and status topics
        client.subscribe("wattagent/device/+/telemetry")
        client.subscribe("wattagent/device/+/status")
        client.subscribe("wattagent/device/+/command/response")
        
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received message on {topic}: {payload}")
            
            # Parse topic to extract device_id
            parts = topic.split('/')
            if len(parts) >= 3:
                device_id = parts[2]
                
                if topic.endswith("/telemetry"):
                    telemetry_cache[device_id] = payload
                    # Store in Redis with TTL
                    redis_client.setex(f"telemetry:{device_id}", 300, json.dumps(payload))
                    
                elif topic.endswith("/status"):
                    # Handle device status updates
                    redis_client.setex(f"status:{device_id}", 300, json.dumps(payload))
                    
                elif topic.endswith("/command/response"):
                    command_id = payload.get("commandId")
                    if command_id:
                        command_responses[command_id] = CommandResponse(**payload)
                        
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
            
    def start(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            logger.info("MQTT client started")
        except Exception as e:
            logger.error(f"Failed to start MQTT client: {e}")
            
    def publish_command(self, device_id: str, command: CommandPayload):
        topic = f"wattagent/device/{device_id}/command"
        payload = json.dumps(command.dict())
        self.client.publish(topic, payload)
        logger.info(f"Published command to {topic}: {payload}")

# Initialize MQTT manager
mqtt_manager = MQTTManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    mqtt_manager.start()
    
    # Load device configurations
    devices["mpsoc-01"] = DeviceInfo(
        deviceId="mpsoc-01",
        ipAddress="192.168.1.105",
        geoLocation="West Lafayette, Indiana, USA",
        modelParameters={
            "type": "BuckConverter",
            "L_uH": 22.0,
            "C_uF": 470.0
        }
    )
    
    yield
    
    # Shutdown
    mqtt_manager.client.loop_stop()
    mqtt_manager.client.disconnect()

# FastAPI app
app = FastAPI(
    title="WattMCP Server",
    description="Central communication hub for WattAgent system",
    version="1.0.0",
    lifespan=lifespan
)

# REST API Endpoints

@app.get("/")
async def root():
    return {"message": "WattMCP Server is running"}

@app.get("/devices")
async def list_devices():
    """List all registered devices"""
    return {"devices": list(devices.keys())}

@app.get("/devices/{device_id}", response_model=DeviceInfo)
async def get_device_info(device_id: str, api_key: str = Depends(verify_api_key)):
    """Get static information for a specific device"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    return devices[device_id]

@app.get("/devices/{device_id}/live")
async def get_device_live_data(device_id: str, api_key: str = Depends(verify_api_key)):
    """Get latest operational data for a device"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Try to get from Redis first
    telemetry_data = redis_client.get(f"telemetry:{device_id}")
    if telemetry_data:
        telemetry = json.loads(telemetry_data)
    else:
        telemetry = telemetry_cache.get(device_id, {})
    
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry data available")
    
    # Construct response
    return {
        "deviceId": device_id,
        "timestamp": telemetry.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "temperature": {
            "value": telemetry.get("temperature_C", 0.0),
            "unit": "C"
        },
        "controlStrategy": {
            "name": "PID",
            "targetVoltage": telemetry.get("voltage_out", 12.0)
        }
    }

@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, command: CommandPayload, api_key: str = Depends(verify_api_key)):
    """Send a command to a specific device"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    mqtt_manager.publish_command(device_id, command)
    return {"message": "Command sent successfully", "commandId": command.commandId}

@app.get("/devices/{device_id}/command/{command_id}")
async def get_command_response(device_id: str, command_id: str, api_key: str = Depends(verify_api_key)):
    """Get the response for a specific command"""
    response = command_responses.get(command_id)
    if not response:
        raise HTTPException(status_code=404, detail="Command response not found")
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)