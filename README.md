# VPPctl AI Agent

An intelligent Python wrapper around vppctl with AI-powered assistance for VPP (Vector Packet Processing) network management.

## Features

- **AI-Powered Assistance**: Natural language queries about VPP configuration and troubleshooting
- **Intelligent Command Parsing**: Understands and analyzes VPP commands and output
- **State Analysis**: Monitors VPP interfaces, routes, IPsec, and error conditions
- **Problem Diagnosis**: Automated analysis of network issues with suggested solutions
- **Interactive Mode**: Command-line interface with AI assistance
- **Free AI Models**: Uses Ollama with local AI models (no API costs)

## Requirements

- Python 3.7+
- VPP (Vector Packet Processing) running
- Ollama (for AI features)

## Installation

1. **Clone and setup the project**:
```bash
cd /home/denys/projects/vppctl-ai
pip install -r requirements.txt
```

2. **Install Ollama and AI models**:
```bash
chmod +x install_ollama.sh
./install_ollama.sh
```

This will install Ollama and download fast AI models (mistral, llama3.2:3b, phi3).

## Usage

### Quick Start (Recommended)

```bash
# Use the launcher script (handles venv activation and dependencies)
./run_agent.sh

# Or with custom socket
./run_agent.sh -s /run/vpp/cli.sock

# With different model
./run_agent.sh -m mistral -v

# Run demo to see all features
python3 demo.py
```

**Note:** AI responses take 10-20 seconds to generate. The agent will show "🤖 Thinking..." while processing.

### Manual Usage

```bash
# Activate virtual environment first
source venv/bin/activate

# Start interactive mode
python main.py

# Specify custom socket path
python main.py -s /run/vpp/cli.sock

# Use different AI model
python main.py -m mistral

# Enable verbose logging
python main.py -v
```

### Launcher Script

The `run_agent.sh` script automatically handles everything:
- ✅ Activates the virtual environment
- ✅ Checks for and installs missing dependencies (ollama)
- ✅ Starts Ollama service if not running
- ✅ Passes all arguments to the main script

```bash
# Make executable (one time)
chmod +x run_agent.sh

# Run with defaults (connects to /run/vpp/cli.sock)
./run_agent.sh

# Run with custom VPP socket
./run_agent.sh -s /run/vpp/cli.sock

# Run with different AI model and verbose logging
./run_agent.sh -m mistral -v

# Test the launcher
python3 test_launcher.py
```

### Testing

```bash
# Run unit tests
python3 test_agent.py

# Run basic functionality test (no VPP needed)
python3 test_agent.py --basic

# Test launcher script
python3 test_launcher.py
```

### Interactive Commands

Once in interactive mode (`vpp-ai>` prompt):

**Direct VPP Commands:**
```
vpp-ai> show interfaces
vpp-ai> show ip fib
vpp-ai> show ipsec sa
vpp-ai> set interface state GigabitEthernet0/0/0 up
```

**AI-Powered Commands:**
```
vpp-ai> analyze packet loss between interfaces
vpp-ai> configure ipsec tunnel between two sites
vpp-ai> how do I set up VLAN interfaces in VPP?
vpp-ai> explain what LCP does
```

**Special Commands:**
```
vpp-ai> help    # Show help
vpp-ai> quit    # Exit
```

## Testing

Run the comprehensive test suite:

```bash
# Run all unit tests
python test_agent.py

# Run basic functionality test (no VPP required)
python test_agent.py --basic
```

## Architecture

### Core Components

1. **VPPctlAgent** (`main.py`):
   - Main agent class with VPP command execution
   - AI integration via Ollama
   - State management and analysis
   - Interactive command interface

2. **VPPCommandParser** (`vpp_ai_library.py`):
   - Parses VPP commands into structured data
   - Understands command syntax and parameters

3. **VPPStateAnalyzer** (`vpp_ai_library.py`):
   - Analyzes VPP configuration state
   - Provides insights and detects issues
   - Generates diagnostic reports

4. **VPPKnowledgeBase** (`vpp_ai_library.py`):
   - Knowledge base of common VPP issues
   - Diagnostic command suggestions
   - Troubleshooting guides

### AI Integration

The agent uses **Ollama** to run AI models locally:

- **mistral** (default): Fast and capable, great for VPP questions
- **llama3.2:3b**: High-quality alternative
- **phi3**: Fast alternative model
- **llama2**: Original model (slower)

Models are downloaded automatically by the install script.

## VPP Command Examples

The agent understands these VPP command patterns:

### Show Commands
- `show interfaces` - Display interface status
- `show ip fib` - Show IP forwarding table
- `show ipsec sa` - Show IPsec security associations
- `show ipsec spd` - Show IPsec security policies
- `show errors` - Display error counters
- `show lcp` - Show Linux Control Plane state

### Configuration Commands
- `set interface state <interface> <up|down>` - Change interface state
- `set interface ip address <interface> <address>` - Set IP address
- `ip route add <prefix> via <next-hop>` - Add static route
- `create ipsec tunnel` - Create IPsec tunnel

## Troubleshooting

### Common Issues

1. **"AI assistance not available"**
   - Install Ollama: `./install_ollama.sh`
   - Start Ollama service: `ollama serve`
   - Check models: `ollama list`

2. **"Could not connect to VPP"**
   - Verify VPP is running: `ps aux | grep vpp`
   - Check socket path: `ls -la /run/vpp/cli.sock`
   - Use correct socket: `python main.py -s /path/to/socket`

3. **Command timeouts**
   - Increase timeout: Commands have 30-second default
   - Check VPP responsiveness: `vppctl show version`

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python main.py -v
```

## Development

### Adding New Commands

1. Update `VPPCommandParser.command_patterns` in `vpp_ai_library.py`
2. Add parser method following the pattern: `_parse_<command_name>`
3. Update tests in `test_agent.py`

### Extending AI Capabilities

1. Add new analysis methods to `VPPStateAnalyzer`
2. Update `VPPKnowledgeBase` with new issue patterns
3. Modify AI prompts in `VPPctlAgent` methods

### Testing

Add new tests following the unittest pattern:

```python
def test_new_functionality(self):
    # Test code here
    pass
```

## License

This project follows the same Apache 2.0 license as VPP.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Related Projects

- [VPP](https://github.com/FDio/vpp) - Vector Packet Processing
- [Ollama](https://github.com/jmorganca/ollama) - Local AI model runner
- [vyos-labs](https://github.com/dd010101/vyos-labs) - VPP testing environment