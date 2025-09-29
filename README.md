# CLAUTH

**Claude + AWS SSO helper for Bedrock**

A Python CLI tool that simplifies setting up Claude Code with AWS Bedrock authentication through AWS SSO.

## Overview

CLAUTH streamlines the complex process of configuring AWS SSO, discovering Bedrock models, and launching Claude Code CLI with proper authentication. Instead of manually configuring AWS profiles, SSO sessions, and environment variables, CLAUTH provides an interactive setup wizard that handles everything automatically.

## Features

- **Automated AWS SSO Setup** - Creates and configures AWS profiles and SSO sessions
- **Model Discovery** - Automatically discovers available Bedrock inference profiles
- **Interactive Model Selection** - Choose default and fast models through user-friendly menus
- **Auto-launch Claude Code** - Seamlessly launches Claude Code CLI with proper configuration
- **Model Management** - List and manage available Bedrock models
- **Polished CLI UI** - Themed banners, cards, and progress spinners keep steps focused and easy to follow

## Prerequisites

Before using CLAUTH, ensure you have:

- **AWS CLI v2** - [Installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Claude Code CLI** - [Installation guide](https://docs.anthropic.com/en/docs/claude-code)
- **Python 3.10+**
- **Access to AWS Bedrock** with appropriate permissions

## Installation

### From PyPI

```bash
pip install clauth
```

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/khordoo/clauth.git
   cd clauth
   ```

2. Install using uv (recommended) or pip:
   ```bash
   # Using uv
   uv sync

   # Or using pip
   pip install -e .
   ```

3. Verify installation:
   ```bash
   clauth --help
   ```

## Usage

### Initial Setup

Run the setup wizard to configure everything automatically:

```bash
clauth init
```

This command will:
1. Configure AWS SSO profile and session
2. Open AWS SSO wizard for authentication
3. Discover available Bedrock models
4. Let you select default and fast models
5. Launch Claude Code CLI with proper environment

### Sample CLI Experience

![CLAUTH init wizard](assets/images/clauth-init.png)

### Command Options

```bash
clauth init [OPTIONS]
```

**AWS Profile Options:**
- `--profile, -p TEXT` - AWS profile name (default: clauth)
- `--region, -r TEXT` - Default AWS region (default: ap-southeast-2)

**AWS SSO Options:**
- `--session-name, -s TEXT` - SSO session name (default: clauth-session)
- `--sso-start-url TEXT` - IAM Identity Center start URL
- `--sso-region TEXT` - SSO region (default: ap-southeast-2)

**Behavior Options:**
- `--auto-start/--no-auto-start` - Launch Claude Code after setup (default: true)

### List Available Models

View all available Bedrock models:

```bash
clauth model list
```

Add `--show-arn` to see full model ARNs:

```bash
clauth model list --show-arn
```

### Quick Model Switching

Switch between available models without going through the full setup process:

```bash
# Interactive model switching
clauth model switch
```

**Options:**
```bash
clauth model switch [OPTIONS]

# Only change the default model
clauth model switch --default-only

# Only change the fast model
clauth model switch --fast-only

# Use specific profile/region
clauth model switch --profile myprofile --region us-west-2
```

The command will:
1. Show your current default and fast models
2. Discover available models from AWS Bedrock
3. Present an interactive menu to select new models
4. Update your configuration and confirm the changes

### Delete Configuration

To completely remove all `clauth` configurations, including the AWS profile and SSO tokens, use the `delete` command:

```bash
clauth delete
```

This command will permanently delete:
- The `clauth` AWS profile from `~/.aws/config`.
- The AWS credentials profile (if it exists).
- The AWS SSO token cache.
- The SSO session configuration.
- The entire `clauth` configuration directory.

To skip the confirmation prompt, use the `--yes` or `-y` flag:
```bash
clauth delete --yes
```

## Configuration

CLAUTH uses a persistent configuration system that saves your preferences between runs. Configuration is stored in TOML format at `~/.clauth/config.toml` (or `%APPDATA%/clauth/config.toml` on Windows).

### View Current Configuration

You can view the current configuration by running:

```bash
clauth config show
```

To see the path to the configuration file, use the `--path` flag:
```bash
clauth config show --path
```

### Configuration Sections

#### AWS Settings (`aws.*`)
- `aws.profile` - AWS profile name (default: `clauth`)
- `aws.region` - Default AWS region (default: `ap-southeast-2`)
- `aws.sso_start_url` - IAM Identity Center start URL
- `aws.sso_region` - SSO region (default: `ap-southeast-2`)
- `aws.session_name` - SSO session name (default: `clauth-session`)
- `aws.output_format` - AWS CLI output format (default: `json`)

#### Model Settings (`models.*`)
- `models.provider_filter` - Preferred model provider (default: `anthropic`)
- `models.default_model` - Default model ID (set automatically during init)
- `models.fast_model` - Fast/small model ID (set automatically during init)
- `models.default_model_arn` - Default model ARN (set automatically)
- `models.fast_model_arn` - Fast model ARN (set automatically)

#### CLI Settings (`cli.*`)
- `cli.claude_cli_name` - Claude CLI executable name (default: `claude`)
- `cli.auto_start` - Auto-launch Claude Code after setup (default: `true`)
- `cli.show_progress` - Show progress indicators (default: `true`)
- `cli.color_output` - Enable colored output (default: `true`)

### Environment Variable Overrides

Configuration can be overridden with environment variables:

```bash
# AWS settings
export CLAUTH_PROFILE=my-profile
export CLAUTH_REGION=us-east-1
export CLAUTH_SSO_START_URL=https://my-org.awsapps.com/start/
export CLAUTH_SSO_REGION=us-east-1
export CLAUTH_SESSION_NAME=my-session

# CLI settings
export CLAUTH_CLAUDE_CLI_NAME=claude-dev
export CLAUTH_AUTO_START=false

# Model settings
export CLAUTH_PROVIDER_FILTER=anthropic
export CLAUTH_DEFAULT_MODEL=claude-3-5-sonnet-20241022-v2:0
export CLAUTH_FAST_MODEL=claude-3-5-haiku-20241022-v1:0
```

### Environment Variables for Claude Code

After running `clauth init`, these environment variables are set for Claude Code:

- `AWS_PROFILE` - Selected AWS profile
- `AWS_REGION` - Selected AWS region
- `CLAUDE_CODE_USE_BEDROCK=1` - Enables Bedrock integration
- `ANTHROPIC_MODEL` - Default model ARN
- `ANTHROPIC_SMALL_FAST_MODEL` - Fast model ARN

## Project Structure

```
clauth/
├── src/clauth/
│   ├── __init__.py
│   ├── cli.py          # Main CLI interface with Typer
│   ├── aws_utils.py    # AWS/Bedrock integration utilities
│   └── models.py       # Model selection utilities
├── pyproject.toml      # Project configuration
└── README.md           # This file
```

## Dependencies

- **boto3** - AWS SDK for Python
- **typer** - CLI framework with rich features
- **inquirerpy** - Interactive command-line prompts
- **rich** - Rich text and beautiful formatting

## Development

### Setting up Development Environment

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install in development mode:
   ```bash
   pip install -e .
   ```

### Project Commands

The CLI is available as both `clauth` command and as a Python module:

```bash
# Via installed command
clauth init

# Via Python module
python -m clauth.cli init
```

## Troubleshooting

### Common Issues

**"Setup failed" errors:**
- Ensure AWS CLI v2 is installed and accessible
- Verify you have permissions to access AWS Bedrock
- Check your internet connection for SSO authentication

**"Credentials are missing or expired":**
- Run `clauth init` to re-authenticate
- Manually run `aws sso login --profile clauth` if needed

**"Claude not found on system":**
- Install Claude Code CLI from [official documentation](https://docs.anthropic.com/en/docs/claude-code)
- Ensure `claude` command is in your PATH

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.
