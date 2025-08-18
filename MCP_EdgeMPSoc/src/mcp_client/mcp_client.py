#!/usr/bin/env python3
"""
MPSoC Edge Client for WattMCP
Runs on ARM core (PS) of MPSoC to interface with PowerDojo-RT and communicate with WattMCP server
"""

import json
import time
import logging
import socket
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import paho.mqtt.client as mqtt
import requests
import ctypes
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MPSoCEdgeClient:
    """
    Edge client running on MPSoC ARM core to interface with PowerDojo-RT
    and communicate with WattMCP server via MQTT
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.device_id = config.get('device_id', 'mpsoc-01')
        self.mqtt_broker = config.get('mqtt_broker', 'localhost')
        self.mqtt_port = config.get('mqtt_port', 1883)
        self.mqtt_username = config.get('mqtt_username', self.device_id)
        self.mqtt_password = config.get('mqtt_password', 'supersecretpassword')
        
        # Hardware interface
        self.hw_lib = None
        self.hw_ptr = None
        
        # MQTT client
        self.mqtt_client = None
        
        # Device information
        self.device_info = {
            "deviceId": self.device_id,
            "ipAddress": self._get_ip_address(),
            "geoLocation": config.get('geo_location', 'Unknown'),
            "modelParameters": config.get('model_parameters', {})
        }
        
        # Telemetry data
        self.last_telemetry = {}
        
    def _get_ip_address(self) -> str:
        """Get the IP address of the device"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _load_hardware_library(self):
        """Load the PowerDojo-RT C library"""
        try:
            # Try to load the shared library
            lib_path = self.config.get('hw_lib_path', './libpowerdojo.so')
            if os.path.exists(lib_path):
                self.hw_lib = ctypes.CDLL(lib_path)
                logger.info(f"Loaded hardware library: {lib_path}")
                
                # Define function prototypes (adjust based on actual library)
                self.hw_lib.initialize_accelerator.restype = ctypes.c_void_p
                self.hw_lib.initialize_accelerator.argtypes = []
                
                self.hw_lib.get_temperature.restype = ctypes.c_float
                self.hw_lib.get_temperature.argtypes = [ctypes.c_void_p]
                
                self.hw_lib.get_voltage_out.restype = ctypes.c_float
                self.hw_lib.get_voltage_out.argtypes = [ctypes.c_void_p]
                
                self.hw_lib.get_current_in.restype = ctypes.c_float
                self.hw_lib.get_current_in.argtypes = [ctypes.c_void_p]
                
                self.hw_lib.set_voltage_reference.restype = ctypes.c_int
                self.hw_lib.set_voltage_reference.argtypes = [ctypes.c_void_p, ctypes.c_float]
                
                # Initialize hardware
                self.hw_ptr = self.hw_lib.initialize_accelerator()
                logger.info("Hardware accelerator initialized")
            else:
                logger.warning(f"Hardware library not found: {lib_path}")
                
        except Exception as e:
            logger.error(f"Failed to load hardware library: {e}")
            self.hw_lib = None
    
    def _read_hardware_sensors(self) -> Dict[str, float]:
        """Read sensor data from hardware"""
        data = {
            "temperature_C": 25.0,  # Default fallback
            "voltage_out": 12.0,
            "current_in": 2.5,
            "power_W": 30.0
        }
        
        if self.hw_lib and self.hw_ptr:
            try:
                data["temperature_C"] = float(self.hw_lib.get_temperature(self.hw_ptr))
                data["voltage_out"] = float(self.hw_lib.get_voltage_out(self.hw_ptr))
                data["current_in"] = float(self.hw_lib.get_current_in(self.hw_ptr))
                data["power_W"] = data["voltage_out"] * data["current_in"]
            except Exception as e:
                logger.error(f"Error reading hardware sensors: {e}")
        else:
            # Simulate data for testing
            import random
            data["temperature_C"] = 45.0 + random.uniform(-5.0, 15.0)
            data["voltage_out"] = 12.0 + random.uniform(-0.5, 0.5)
            data["current_in"] = 2.5 + random.uniform(-0.5, 0.5)
            data["power_W"] = data["voltage_out"] * data["current_in"]
            
        return data
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info(f"Connected to MQTT broker with result code {rc}")
            
            # Subscribe to command topics
            command_topic = f"wattagent/device/{self.device_id}/command"
            client.subscribe(command_topic)
            logger.info(f"Subscribed to {command_topic}")
            
            # Publish device status
            self._publish_status("online")
            
        else:
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received command on {topic}: {payload}")
            
            self._handle_command(payload)
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
    
    def _handle_command(self, command: Dict[str, Any]):
        """Handle incoming commands"""
        try:
            command_id = command.get("commandId")
            action = command.get("action")
            payload = command.get("payload", {})
            
            response = {
                "commandId": command_id,
                "status": "SUCCESS",
                "message": "Command processed successfully"
            }
            
            if action == "SET_CONTROL_TARGET":
                target_voltage = payload.get("targetVoltage")
                if target_voltage is not None:
                    success = self._set_voltage_reference(target_voltage)
                    if success:
                        response["message"] = f"Control target updated to {target_voltage}V"
                    else:
                        response["status"] = "ERROR"
                        response["message"] = "Failed to update control target"
            
            elif action == "GET_DEVICE_STATUS":
                response["payload"] = self._get_device_status()
                
            else:
                response["status"] = "ERROR"
                response["message"] = f"Unknown action: {action}"
            
            # Publish response
            response_topic = f"wattagent/device/{self.device_id}/command/response"
            self.mqtt_client.publish(response_topic, json.dumps(response))
            
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            
    def _set_voltage_reference(self, target_voltage: float) -> bool:
        """Set voltage reference on hardware"""
        try:
            if self.hw_lib and self.hw_ptr:
                result = self.hw_lib.set_voltage_reference(self.hw_ptr, ctypes.c_float(target_voltage))
                return result == 0
            else:
                logger.warning("Hardware not available, simulating voltage change")
                return True
        except Exception as e:
            logger.error(f"Error setting voltage reference: {e}")
            return False
    
    def _get_device_status(self) -> Dict[str, Any]:
        """Get current device status"""
        sensors = self._read_hardware_sensors()
        return {
            "deviceId": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensors": sensors,
            "status": "online"
        }
    
    def _publish_telemetry(self):
        """Publish telemetry data"""
        try:
            telemetry = self._read_hardware_sensors()
            telemetry["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            topic = f"wattagent/device/{self.device_id}/telemetry"
            payload = json.dumps(telemetry)
            
            result = self.mqtt_client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published telemetry: {telemetry}")
                self.last_telemetry = telemetry
            else:
                logger.error(f"Failed to publish telemetry: {result.rc}")
                
        except Exception as e:
            logger.error(f"Error publishing telemetry: {e}")
    
    def _publish_status(self, status: str):
        """Publish device status"""
        try:
            status_data = {
                "deviceId": self.device_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": status
            }
            
            topic = f"wattagent/device/{self.device_id}/status"
            self.mqtt_client.publish(topic, json.dumps(status_data))
            logger.info(f"Published status: {status}")
            
        except Exception as e:
            logger.error(f"Error publishing status: {e}")
    
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.mqtt_client = mqtt.Client(client_id=f"{self.device_id}-client")
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # Set callbacks
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_message = self._on_message
            
            # Connect
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            logger.info(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def run(self):
        """Main run loop"""
        logger.info(f"Starting MPSoC Edge Client for device: {self.device_id}")
        
        # Load hardware library
        self._load_hardware_library()
        
        # Connect to MQTT
        self.connect_mqtt()
        
        try:
            # Main telemetry loop
            telemetry_interval = self.config.get('telemetry_interval', 1.0)
            
            while True:
                if self.mqtt_client and self.mqtt_client.is_connected():
                    self._publish_telemetry()
                else:
                    logger.warning("MQTT client not connected")
                
                time.sleep(telemetry_interval)
                
        except KeyboardInterrupt:
            logger.info("Shutting down edge client")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            if self.mqtt_client:
                self._publish_status("offline")
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()


def main():
    """Main entry point"""
    config = {
        'device_id': 'mpsoc-01',
        'mqtt_broker': 'localhost',
        'mqtt_port': 1883,
        'mqtt_username': 'mpsoc-01',
        'mqtt_password': 'supersecretpassword',
        'geo_location': 'West Lafayette, Indiana, USA',
        'model_parameters': {
            'type': 'BuckConverter',
            'L_uH': 22.0,
            'C_uF': 470.0
        },
        'telemetry_interval': 1.0,
        'hw_lib_path': './libpowerdojo.so'
    }
    
    # Allow override from environment
    config.update({
        'device_id': os.getenv('DEVICE_ID', config['device_id']),
        'mqtt_broker': os.getenv('MQTT_BROKER', config['mqtt_broker']),
        'mqtt_port': int(os.getenv('MQTT_PORT', config['mqtt_port'])),
        'mqtt_username': os.getenv('MQTT_USERNAME', config['mqtt_username']),
        'mqtt_password': os.getenv('MQTT_PASSWORD', config['mqtt_password']),
        'telemetry_interval': float(os.getenv('TELEMETRY_INTERVAL', config['telemetry_interval']))
    })
    
    client = MPSoCEdgeClient(config)
    client.run()


if __name__ == "__main__":
    main()