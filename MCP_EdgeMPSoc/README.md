# WattMCP - Monitoring and Control Platform

WattMCP is a robust communication and control platform designed to act as the central nervous system for the WattAgent project. It facilitates secure, bi-directional communication between AI Agents (running in the cloud or on a local server) and distributed PowerDojo-RT instances running on MPSoC hardware at the edge.

## 🎯 Core Objectives

1. **Telemetry Upload**: Reliably stream system parameters and real-time operational data from MPSoC to central server
2. **Remote Information Access**: Provide AI Agents with secure tools to query static and dynamic device information
3. **Command & Control**: Enable authenticated AI Agents to send high-level commands to MPSoC devices
4. **Decoupling & Scalability**: Decouple AI logic from edge hardware for scalable multi-agent, multi-device interactions

## 🏗️ System Architecture

WattMCP uses a hybrid communication architecture:
- **REST API** for synchronous requests
- **MQTT Broker** for asynchronous, real-time messaging

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   AI Agent Tools    │    │   AI Agent Tools    │    │   AI Agent Tools    │
│  (Design Agent)     │    │  (Control Agent)    │    │ (Maintenance Agent) │
└──────────┬──────────┘    └──────────┬──────────┘    └──────────┬──────────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                   │
            ┌───────────────────────┴───────────────────────┐
            │          WattMCP Server (Cloud/On-Prem)        │
            │  ┌─────────────────┐    ┌─────────────────┐   │
            │  │   REST API      │    │   MQTT Broker   │   │
            │  │   FastAPI       │    │   Mosquitto     │   │
            │  └─────────────────┘    └─────────────────┘   │
            └───────────────────────┬───────────────────────┘
                                   │
            ┌───────────────────────┴───────────────────────┐
            │            Edge Device (MPSoC)                │
            │  ┌─────────────────┐    ┌─────────────────┐   │
            │  │  PowerDojo-RT   │    │  MCP Edge Client │   │
            │  │   (PL FPGA)     │    │  (PS ARM Core)  │   │
            │  └─────────────────┘    └─────────────────┘   │
            └───────────────────────────────────────────────┘
```

## 📦 Components

### 1. MCP Server (`src/mcp_server/`)
Central backend service providing:
- **RESTful API** (FastAPI) for agent interactions
- **MQTT Broker** interface for real-time messaging
- **Device management** and authentication
- **Telemetry caching** with Redis

### 2. MPSoC Edge Client (`src/mcp_client/`)
Lightweight service running on ARM core (PS) of MPSoC:
- **Hardware interface** to PowerDojo-RT via shared library
- **Telemetry collection** from sensors and simulation state
- **Command execution** from AI agents
- **MQTT communication** with central server

### 3. AI Agent Tools (`src/mcp_tools/`)
Python library for AI agents:
- **Simple interfaces** for complex operations
- **Pre-built functions** for common tasks
- **LangChain integration** ready
- **Monitoring capabilities**

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Redis server
- MQTT broker (Mosquitto recommended)
- MPSoC with ARM Linux (for edge client)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd WattMCP
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
# Copy example config
cp config/example.env .env

# Edit configuration
nano .env
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_BROKER` | MQTT broker host | `localhost` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `API_BASE_URL` | REST API base URL | `http://localhost:8000` |
| `API_KEY` | API authentication key | `your_secret_api_key` |
| `DEVICE_ID` | Edge device identifier | `mpsoc-01` |
| `TELEMETRY_INTERVAL` | Telemetry publish interval (seconds) | `1.0` |

### Running the System

#### 1. Start Redis
```bash
redis-server
```

#### 2. Start MQTT Broker
```bash
# Using Mosquitto
mosquitto -c /etc/mosquitto/mosquitto.conf
```

#### 3. Start MCP Server
```bash
# Development mode
python src/mcp_server/mcp_server.py

# Production mode
uvicorn src.mcp_server.mcp_server:app --host 0.0.0.0 --port 8000
```

#### 4. Start Edge Client (on MPSoC)
```bash
python src/mcp_client/mcp_client.py
```

#### 5. Test with AI Tools
```python
from src.mcp_tools.mcp_tools import WattMCPAgentTools

# Create tools instance
tools = WattMCPAgentTools()

# List devices
devices = tools.list_devices()
print("Devices:", devices)

# Get device info
info = tools.get_device_info("mpsoc-01")
print("Device Info:", info)

# Set control target
result = tools.set_voltage_target("mpsoc-01", 13.5)
print("Command sent:", result)
```

## 📡 API Reference

### REST API Endpoints

#### Device Management
- `GET /devices` - List all devices
- `GET /devices/{device_id}` - Get device information
- `GET /devices/{device_id}/live` - Get live telemetry data

#### Command Interface
- `POST /devices/{device_id}/command` - Send command to device
- `GET /devices/{device_id}/command/{command_id}` - Get command response

#### System Health
- `GET /health` - System health check

### MQTT Topics

| Topic Pattern | Direction | Description |
|---------------|-----------|-------------|
| `wattagent/device/{device_id}/telemetry` | MPSoC → Server | Telemetry data |
| `wattagent/device/{device_id}/status` | MPSoC → Server | Device status |
| `wattagent/device/{device_id}/command` | Server → MPSoC | Commands |
| `wattagent/device/{device_id}/command/response` | MPSoC → Server | Command responses |

### Data Models

#### Telemetry Payload
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "temperature_C": 55.3,
  "voltage_out": 12.01,
  "current_in": 2.5,
  "power_W": 30.02
}
```

#### Command Payload
```json
{
  "commandId": "cmd-a1b2c3d4",
  "action": "SET_CONTROL_TARGET",
  "payload": {
    "targetVoltage": 13.5,
    "slewRate": 0.5
  }
}
```

## 🔧 Development

### Project Structure
```
WattMCP/
├── src/
│   ├── mcp_server/          # MCP server implementation
│   ├── mcp_client/          # MPSoC edge client
│   ├── mcp_tools/           # AI agent tools
│   └── config/              # Configuration management
├── tests/                   # Unit tests
├── docs/                    # Documentation
├── docker/                  # Docker configurations
├── requirements.txt         # Python dependencies
├── Dockerfile               # Main Dockerfile
├── docker-compose.yml       # Docker Compose setup
└── README.md               # This file
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_mcp_tools.py

# Run with coverage
pytest --cov=src tests/
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 src/
black src/

# Type checking
mypy src/
```

## 🐳 Docker Deployment

### Quick Docker Setup
```bash
# Build and run with Docker Compose
docker-compose up --build

# Run individual services
docker-compose up mcp-server
docker-compose up mqtt-broker
docker-compose up redis
```

### Docker Services
- **mcp-server**: FastAPI server
- **mqtt-broker**: Mosquitto MQTT broker
- **redis**: Redis cache
- **edge-client**: MPSoC edge client (run on target device)

## 🔐 Security

### Authentication
- **REST API**: Bearer token authentication
- **MQTT**: Username/password authentication
- **TLS**: Optional TLS encryption for MQTT

### Security Best Practices
1. Use strong API keys and passwords
2. Enable TLS for production deployments
3. Implement rate limiting
4. Regular security updates
5. Network segmentation

## 📊 Monitoring

### Built-in Monitoring
- **Health endpoints** for system status
- **Telemetry streaming** for real-time data
- **Command tracking** for audit logs

### Integration Options
- **Prometheus** metrics endpoint
- **Grafana** dashboards
- **ELK stack** for log aggregation

## 🛠️ Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Check MQTT connectivity
mosquitto_sub -h localhost -t "wattagent/#" -v

# Check Redis connectivity
redis-cli ping

# Check API health
curl http://localhost:8000/health
```

#### Permission Issues
```bash
# Check file permissions
ls -la /path/to/libpowerdojo.so

# Check MQTT user permissions
mosquitto_ctrl dynsec listClients
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=debug
python src/mcp_server/mcp_server.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/WattMCP/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/WattMCP/discussions)
- **Documentation**: [Wiki](https://github.com/your-org/WattMCP/wiki)

## 🔄 Changelog

### v1.0.0 (Initial Release)
- Initial MCP implementation
- REST API and MQTT integration
- MPSoC edge client
- AI agent tools
- Docker deployment support