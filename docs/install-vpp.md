# Installing VPP

Install VPP on Ubuntu/Debian in under 2 minutes.

## Install

```bash
# Add FD.io repository
curl -s https://packagecloud.io/install/repositories/fdio/release/script.deb.sh | sudo bash

# Install VPP
sudo apt-get install -y vpp vpp-plugin-core vpp-plugin-dpdk

# Start VPP
sudo systemctl start vpp

# Enable on boot (optional)
sudo systemctl enable vpp
```

## Verify

```bash
sudo vppctl show version
```

Expected output:
```
vpp v24.10-release built by root on ...
```

## Uninstall

```bash
sudo systemctl stop vpp
sudo apt-get remove --purge "vpp*"
sudo rm /etc/apt/sources.list.d/fdio*.list
```

## Next Step

**[→ Continue to Getting Started](getting-started.md)**

## Learn More

- [FD.io Official Docs](https://fd.io/docs/vpp/latest/)
- [VPP Networking Blog](https://haryachyy.wordpress.com/) — Hands-on VPP tutorials for IPsec, IKEv2, PPPoE, and Linux Control Plane
