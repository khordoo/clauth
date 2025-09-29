# CLAUTH
**Claude + AWS SSO helper for Bedrock**

A simple CLI tool to launch Claude Code with AWS Bedrock authentication. Supports **AWS SSO** and **direct AWS keys**.

---
## 🚀 Quick Start

Install from PyPI:
```bash
pip install clauth
```

Run the setup wizard:
```bash
clauth init
```

👉 This will configure AWS SSO (or keys), discover Bedrock models, and launch Claude Code instantly.

On later runs, just use:
```bash
clauth
```
…and Claude Code will start with your saved credentials.

---
## ✨ Features

- Works with **AWS SSO** and **direct AWS keys**
- **One-time setup** with `clauth init`
- **Instant launch** with `clauth` on subsequent runs
- **Model discovery & switching** with `clauth model switch`—no more manual environment variables!
- **Simple config management** (`clauth config show`, `clauth delete`)
- **Modern CLI UI** featuring banners, cards, and spinners for each step

![CLAUTH init wizard](assets/images/clauth-init.png)

---
## 📋 Requirements

- Python 3.10+
- AWS CLI v2
- Claude Code CLI
- Access to AWS Bedrock

---
## 📖 More Documentation

- [Full usage guide](https://github.com/khordoo/clauth#usage)
- [Configuration details](https://github.com/khordoo/clauth#configuration)
- [Troubleshooting](https://github.com/khordoo/clauth#troubleshooting)

---
## License

MIT License – see [LICENSE](LICENSE).
