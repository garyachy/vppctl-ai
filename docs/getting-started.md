# Getting Started

Get from zero to running in 5 minutes.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Install    │ ──▶ │  Get API    │ ──▶ │    Run      │
│    VPP      │     │    Key      │     │   Agent     │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Before You Start

- [ ] Ubuntu/Debian system
- [ ] Internet connection
- [ ] 5 minutes

---

## Step 1: Install VPP

```bash
# Add FD.io repository
curl -s https://packagecloud.io/install/repositories/fdio/release/script.deb.sh | sudo bash

# Install VPP
sudo apt-get install -y vpp vpp-plugin-core vpp-plugin-dpdk

# Start VPP
sudo systemctl start vpp
```

**Verify it works:**
```bash
sudo vppctl show version
```

You should see:
```
vpp v24.10-release built by root on ...
```

---

## Step 2: Get API Key (Free)

1. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
2. Sign in with Google/GitHub
3. Click "Create Key"
4. Copy the key (starts with `sk-or-...`)

```bash
export OPENROUTER_API_KEY="sk-or-your-key-here"
```

**Tip:** Add to `~/.bashrc` to persist:
```bash
echo 'export OPENROUTER_API_KEY="sk-or-your-key-here"' >> ~/.bashrc
```

---

## Step 3: Install & Run

```bash
# Clone the repo
git clone https://github.com/garyachy/vppctl-ai.git
cd vppctl-ai

# Install dependencies
pip install -r requirements.txt

# Run
./run_agent.sh
```

---

## What You'll See

```
$ ./run_agent.sh
VPPctl AI Agent v1.0
Connected to VPP via /run/vpp/cli.sock
Using model: anthropic/claude-3-haiku
Type 'help' for commands, 'quit' to exit

vpp-ai>
```

---

## Try These First

```
vpp-ai> show version
```
→ Runs VPP command directly

```
vpp-ai> show me all interfaces
```
→ AI extracts command, asks to confirm

```
vpp-ai> what routes do I have?
```
→ AI translates to `show ip fib`

```
vpp-ai> show interface and explain
```
→ Runs command + explains output

---

## Common Issues

| Problem | Solution |
|---------|----------|
| `Could not connect to VPP` | `sudo systemctl start vpp` |
| `OPENROUTER_API_KEY not set` | `export OPENROUTER_API_KEY="your-key"` |
| `Permission denied` | `chmod +x run_agent.sh` |
| `No module named 'openai'` | `pip install -r requirements.txt` |

---

## Next Steps

- Press **TAB** for command completion
- Make a typo — watch AI correct it
- Ask "explain" after any command

## Learn More

- [VPP Networking Blog](https://haryachyy.wordpress.com/) - In-depth VPP tutorials on IPsec, IKEv2, PPPoE, and Linux Control Plane
