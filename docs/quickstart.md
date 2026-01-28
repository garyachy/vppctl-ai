# Quick Reference

Command-line options and usage patterns.

## Running the Agent

```bash
# Default (connects to /run/vpp/cli.sock)
./run_agent.sh

# Custom socket
./run_agent.sh -s /path/to/cli.sock

# Different AI model
./run_agent.sh -m anthropic/claude-3-sonnet

# Verbose logging
./run_agent.sh -v
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `-s` | `/run/vpp/cli.sock` | VPP socket path |
| `-m` | `anthropic/claude-3-haiku` | AI model |
| `-v` | off | Verbose logging |

## AI Models

| Model | Speed | Quality |
|-------|-------|---------|
| `anthropic/claude-3-haiku` | Fast | Good |
| `anthropic/claude-3-sonnet` | Medium | Better |
| `openai/gpt-4o-mini` | Fast | Good |
| `google/gemini-pro` | Medium | Good |
| `meta-llama/llama-3.1-8b` | Fast | Basic |

## Usage Patterns

### Direct VPP Commands
```
vpp-ai> show version
vpp-ai> show interface
vpp-ai> show ip fib
vpp-ai> set interface state loop0 up
```

### Natural Language
```
vpp-ai> show me all interfaces
vpp-ai> what's my routing table?
vpp-ai> add IP 10.0.0.1/24 to loop0
```

### With Explanations
```
vpp-ai> show interface and explain
vpp-ai> show ip fib explain this
```

### Tab Completion
```
vpp-ai> show int<TAB>
→ interface

vpp-ai> show interface <TAB>
→ addr, rx-placement, ...
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | API key from openrouter.ai |

## Special Commands

| Command | Action |
|---------|--------|
| `help` | Show help |
| `quit` / `exit` | Exit agent |
| `↑` / `↓` | Command history |

## Learn More

- [VPP Networking Blog](https://haryachyy.wordpress.com/) — Step-by-step VPP tutorials for IPsec, IKEv2, PPPoE, and Linux Control Plane
