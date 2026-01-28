# VPPctl AI Agent

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![VPP](https://img.shields.io/badge/VPP-fd.io-orange.svg)](https://fd.io/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](.github/CONTRIBUTING.md)

> Natural language CLI for fd.io VPP | High-performance packet processing made easy

An AI-powered assistant for learning and using VPP (Vector Packet Processing). Type natural language, get VPP commands. Perfect for network engineers exploring fd.io, DPDK, and software-defined networking.

```
vpp-ai> show me all interfaces with IP addresses
Extracted command: show interface addr
Execute 'show interface addr'? [Y/n]: y

              Name               Idx    State  MTU   IP Address
GigabitEthernet0/0/0              1      up    9000  10.0.0.1/24
local0                            0     down    0

vpp-ai> explain what local0 is
local0 is VPP's internal loopback interface used for
punt/inject operations. It stays down during normal use.
```

## Quick Start

```bash
# Prerequisites: VPP running, OpenRouter API key (free)
git clone https://github.com/garyachy/vppctl-ai.git
cd vppctl-ai
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key"  # Get free at openrouter.ai/keys
./run_agent.sh
```

**[→ Full Getting Started Guide](docs/getting-started.md)**

## Features

- **Natural language** → VPP commands
- **Auto-correction** when you make typos
- **Explanations** of command output
- **TAB completion** from VPP itself
- **Hallucination prevention** via command validation

## Documentation

| Document | Description |
|----------|-------------|
| **[Getting Started](docs/getting-started.md)** | Zero to running in 5 minutes |
| [Install VPP](docs/install-vpp.md) | VPP installation only |
| [Quick Reference](docs/quickstart.md) | Commands and options |
| [Why This Tool?](docs/learning-vpp-with-ai.md) | How it helps you learn VPP |

## Resources

- [VPP Networking Blog](https://haryachyy.wordpress.com/) — Deep-dive tutorials on VPP IPsec, IKEv2, Linux Control Plane, and high-performance networking

## License

Apache 2.0
