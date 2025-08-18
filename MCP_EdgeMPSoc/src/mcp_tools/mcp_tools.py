#!/usr/bin/env python3
"""
WattMCP AI Agent Tools
Provides simple, pre-built functions for AI agents to interact with WattMCP
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional, List
import requests
import paho.mqtt.publish as publish
import time
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WattMCPTools:
    """
    Collection of tools for AI agents to interact with WattMCP system
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_base_url = config.get('api_base_url', 'http://localhost:8000')
        self.api_key = config.get('api_key', 'your_secret_api_key')
        self.mqtt_broker = config.get('mqtt_broker', 'localhost')
        self.mqtt_port = config.get('mqtt_port', 1883)
        self.mqtt_username = config.get('mqtt_username', 'ai-agent-01')
        self.mqtt_password = config.get('mqtt_password', 'agent_secret_password')
        
        # Headers for REST API
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """
        Retrieve static information for a specific device including location, IP address, and system parameters
        
        Args:
            device_id (str): The ID of the device to query
            
        Returns:
            Dict containing device information
        """
        try:
            url = f"{self.api_base_url}/devices/{device_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            device_info = response.json()
            logger.info(f"Retrieved device info for {device_id}: {device_info}")
            return device_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting device info for {device_id}: {e}")
            return {"error": str(e)}
    
    def get_device_live_data(self, device_id: str) -> Dict[str, Any]:
        """
        Get latest operational data for a device including temperature and control strategy
        
        Args:
            device_id (str): The ID of the device to query
            
        Returns:
            Dict containing live operational data
        """
        try:
            url = f"{self.api_base_url}/devices/{device_id}/live"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            live_data = response.json()
            logger.info(f"Retrieved live data for {device_id}")
            return live_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting live data for {device_id}: {e}")
            return {"error": str(e)}
    
    def set_control_target(self, device_id: str, target_voltage: float, 
                          slew_rate: Optional[float] = None) -> Dict[str, Any]:
        """
        Send command to change control target voltage for a device
        
        Args:
            device_id (str): The ID of the target device
            target_voltage (float): New target voltage in volts
            slew_rate (float, optional): Rate of voltage change (V/s)
            
        Returns:
            Dict containing command confirmation
        """
        try:
            command = {
                "commandId": f"cmd-{uuid.uuid4()}",
                "action": "SET_CONTROL_TARGET",
                "payload": {
                    "targetVoltage": target_voltage
                }
            }
            
            if slew_rate is not None:
                command["payload"]["slewRate"] = slew_rate
            
            topic = f"wattagent/device/{device_id}/command"
            payload = json.dumps(command)
            
            publish.single(
                topic,
                payload=payload,
                hostname=self.mqtt_broker,
                port=self.mqtt_port,
                auth={'username': self.mqtt_username, 'password': self.mqtt_password}
            )
            
            logger.info(f"Sent SET_CONTROL_TARGET command to {device_id}: {target_voltage}V")
            return {
                "success": True,
                "message": f"Command sent to set target voltage to {target_voltage}V",
                "commandId": command["commandId"]
            }
            
        except Exception as e:
            logger.error(f"Error sending control target command: {e}")
            return {"error": str(e)}
    
    def get_device_temperature(self, device_id: str) -> Dict[str, Any]:
        """
        Get current temperature reading from a device
        
        Args:
            device_id (str): The ID of the device to query
            
        Returns:
            Dict containing temperature data
        """
        live_data = self.get_device_live_data(device_id)
        if "error" in live_data:
            return live_data
        
        return {
            "deviceId": device_id,
            "temperature": live_data.get("temperature", {}),
            "timestamp": live_data.get("timestamp", datetime.now(timezone.utc).isoformat())
        }
    
    def list_devices(self) -> List[str]:
        """
        List all registered devices in the system
        
        Returns:
            List of device IDs
        """
        try:
            url = f"{self.api_base_url}/devices"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            devices = response.json().get("devices", [])
            logger.info(f"Retrieved device list: {devices}")
            return devices
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing devices: {e}")
            return []
    
    def get_device_power_consumption(self, device_id: str, 
                                   duration_minutes: int = 5) -> Dict[str, Any]:
        """
        Calculate average power consumption over specified duration
        
        Args:
            device_id (str): The ID of the device to query
            duration_minutes (int): Duration to average over (default: 5 minutes)
            
        Returns:
            Dict containing power consumption analysis
        """
        live_data = self.get_device_live_data(device_id)
        if "error" in live_data:
            return live_data
        
        # For now, just return current power
        # In future, this could query historical data
        temperature = live_data.get("temperature", {}).get("value", 0)
        
        # Simulate power calculation based on temperature
        # This is a placeholder - real implementation would use actual power data
        estimated_power = max(0, (temperature - 25) * 0.5 + 25)
        
        return {
            "deviceId": device_id,
            "currentPower": estimated_power,
            "unit": "W",
            "timestamp": live_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "temperature": temperature
        }
    
    def send_custom_command(self, device_id: str, action: str, 
                          payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a custom command to a device
        
        Args:
            device_id (str): The ID of the target device
            action (str): The action to perform
            payload (Dict): Additional parameters for the command
            
        Returns:
            Dict containing command confirmation
        """
        try:
            command = {
                "commandId": f"cmd-{uuid.uuid4()}",
                "action": action,
                "payload": payload
            }
            
            topic = f"wattagent/device/{device_id}/command"
            payload_str = json.dumps(command)
            
            publish.single(
                topic,
                payload=payload_str,
                hostname=self.mqtt_broker,
                port=self.mqtt_port,
                auth={'username': self.mqtt_username, 'password': self.mqtt_password}
            )
            
            logger.info(f"Sent custom command to {device_id}: {action}")
            return {
                "success": True,
                "message": f"Custom command {action} sent to device",
                "commandId": command["commandId"]
            }
            
        except Exception as e:
            logger.error(f"Error sending custom command: {e}")
            return {"error": str(e)}
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health status
        
        Returns:
            Dict containing system health information
        """
        try:
            url = f"{self.api_base_url}/health"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            health = response.json()
            
            # Add additional context
            devices = self.list_devices()
            health["registeredDevices"] = len(devices)
            health["deviceIds"] = devices
            
            return health
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting system health: {e}")
            return {"error": str(e), "status": "unhealthy"}


# Convenience functions for direct use
class WattMCPAgentTools:
    """
    Simplified interface for AI agents using these tools
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {
                'api_base_url': 'http://localhost:8000',
                'api_key': 'your_secret_api_key',
                'mqtt_broker': 'localhost',
                'mqtt_port': 1883,
                'mqtt_username': 'ai-agent-01',
                'mqtt_password': 'agent_secret_password'
            }
        self.tools = WattMCPTools(config)
    
    # Convenience methods that wrap the main tools
    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get device information"""
        return self.tools.get_device_info(device_id)
    
    def get_device_temperature(self, device_id: str) -> float:
        """Get device temperature as float"""
        result = self.tools.get_device_temperature(device_id)
        return result.get("temperature", {}).get("value", 0.0)
    
    def set_voltage_target(self, device_id: str, voltage: float) -> bool:
        """Set voltage target and return success status"""
        result = self.tools.set_control_target(device_id, voltage)
        return "success" in result and result["success"]
    
    def get_all_devices(self) -> List[str]:
        """Get list of all devices"""
        return self.tools.list_devices()
    
    def monitor_device(self, device_id: str, duration_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Monitor device for specified duration and collect telemetry
        
        Args:
            device_id (str): Device to monitor
            duration_seconds (int): How long to monitor
            
        Returns:
            List of telemetry readings
        """
        readings = []
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            try:
                data = self.tools.get_device_live_data(device_id)
                if "error" not in data:
                    readings.append(data)
                time.sleep(5)  # Sample every 5 seconds
            except KeyboardInterrupt:
                break
        
        return readings


# Example usage and testing
if __name__ == "__main__":
    # Test configuration
    test_config = {
        'api_base_url': 'http://localhost:8000',
        'api_key': 'your_secret_api_key',
        'mqtt_broker': 'localhost',
        'mqtt_port': 1883,
        'mqtt_username': 'ai-agent-01',
        'mqtt_password': 'agent_secret_password'
    }
    
    # Create tools instance
    tools = WattMCPAgentTools(test_config)
    
    # Test basic functionality
    print("Testing WattMCP Tools...")
    
    # List devices
    devices = tools.get_all_devices()
    print(f"Devices: {devices}")
    
    if devices:
        device_id = devices[0]
        
        # Get device info
        info = tools.get_device_info(device_id)
        print(f"Device info: {json.dumps(info, indent=2)}")
        
        # Get temperature
        temp = tools.get_device_temperature(device_id)
        print(f"Temperature: {temp}°C")
        
        # Monitor for 10 seconds
        readings = tools.monitor_device(device_id, 10)
        print(f"Collected {len(readings)} readings")