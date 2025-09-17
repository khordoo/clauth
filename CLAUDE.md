# CLAUTH - Claude Code Integration

This document provides information about integrating CLAUTH with Claude Code for AWS Bedrock usage.

## Overview

CLAUTH is designed to streamline the setup process for using Claude Code with AWS Bedrock. It handles the complex configuration of AWS SSO, model discovery, and environment setup automatically.

## How CLAUTH Works with Claude Code

### 1. Environment Configuration

CLAUTH sets up the following environment variables that Claude Code requires for Bedrock integration:

```bash
AWS_PROFILE=clauth                    # AWS profile with Bedrock access
AWS_REGION=ap-southeast-2             # Default AWS region
CLAUDE_CODE_USE_BEDROCK=1             # Enables Bedrock mode in Claude Code
ANTHROPIC_MODEL=<selected-model-arn>  # Default model ARN
ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION=<fast-model-arn>  # Fast model ARN
```

### 2. Model Selection Process

During `clauth init`, users select:
- **Default model**: Primary model for general tasks
- **Small/fast model**: Optimized model for quick operations

Available models are discovered dynamically from your AWS Bedrock access.

### 3. Authentication Flow

1. CLAUTH configures AWS SSO profile (`clauth` by default)
2. Opens AWS SSO browser flow for authentication
3. Verifies credentials with `aws sts get-caller-identity`
4. Discovers available Bedrock inference profiles
5. Launches Claude Code with proper environment

## Commands for Claude Code Users

### Quick Setup
```bash
# One-command setup - will launch Claude Code automatically
clauth init

# Setup without auto-launching Claude Code
clauth init --no-auto-start
```

### Model Management
```bash
# List available models
clauth list-models

# List models with full ARNs
clauth list-models --show-arn
```

### Manual Claude Code Launch

If you need to launch Claude Code manually after setup:

```bash
# Ensure your profile is authenticated
aws sso login --profile clauth

# Set environment variables (these are set automatically by clauth init)
export AWS_PROFILE=clauth
export AWS_REGION=ap-southeast-2
export CLAUDE_CODE_USE_BEDROCK=1
export ANTHROPIC_MODEL=<your-selected-model-arn>
export ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION=<your-selected-fast-model-arn>

# Launch Claude Code
claude
```

## Custom Configuration

### Using Different AWS Profile

```bash
clauth init --profile my-bedrock-profile
```

### Using Different Region

```bash
clauth init --region us-east-1 --sso-region us-east-1
```

### Custom SSO Configuration

```bash
clauth init \
  --sso-start-url https://your-org.awsapps.com/start/ \
  --sso-region us-west-2 \
  --session-name my-claude-session
```

## Configuration Management

CLAUTH provides configuration management commands to view, modify, and manage your settings.

### Viewing Configuration

```bash
# Show current configuration settings
clauth config show

# Show configuration with file location
clauth config show --path

# Show configuration for a specific profile
clauth config show --profile myteam --path
```

### Modifying Configuration

```bash
# Set individual configuration values
clauth config set aws.region us-west-2
clauth config set models.provider_filter anthropic
clauth config set cli.auto_start false

# Reset configuration to defaults
clauth config reset

# Reset specific profile configuration
clauth config reset --profile myteam
```

### Profile Management

```bash
# List available configuration profiles
clauth config profiles
```

Configuration files are stored in platform-appropriate locations:
- **Windows**: `%APPDATA%\clauth\config.toml`
- **Unix/Linux**: `~/.config/clauth/config.toml`
- **Profiles**: Stored in `profiles/` subdirectory

## Integration Benefits

### For Individual Users
- **One-command setup**: No need to manually configure AWS profiles, SSO, or environment variables
- **Model discovery**: Automatically finds available models in your AWS account
- **Interactive selection**: User-friendly model selection with preview
- **Automatic launch**: Seamlessly transitions from setup to Claude Code usage

### For Teams
- **Consistent setup**: Standardized configuration across team members
- **Customizable defaults**: Teams can modify default SSO URLs and regions
- **Easy onboarding**: New team members can get started with a single command

## Troubleshooting Claude Code Integration

### Authentication Issues
```bash
# Check if authenticated
aws sts get-caller-identity --profile clauth

# Re-authenticate if needed
aws sso login --profile clauth

# Or re-run full setup
clauth init
```

### Model Access Issues
```bash
# List available models to verify access
clauth list-models

# Check Bedrock permissions
aws bedrock list-inference-profiles --profile clauth --region ap-southeast-2
```

### Environment Variable Issues
If Claude Code doesn't detect Bedrock mode:

1. Verify environment variables are set:
   ```bash
   echo $CLAUDE_CODE_USE_BEDROCK
   echo $ANTHROPIC_MODEL
   ```

2. Re-run setup:
   ```bash
   clauth init
   ```

## Advanced Usage

### Programmatic Integration

CLAUTH modules can be imported for custom integrations:

```python
from clauth.aws_utils import user_is_authenticated, list_bedrock_profiles

# Check authentication
if user_is_authenticated(profile="clauth"):
    print("User is authenticated")

# List available models
model_ids, model_arns = list_bedrock_profiles(
    profile="clauth",
    region="ap-southeast-2"
)
```

### Custom Model Selection

```python
from clauth.models import model_picker

# Get Anthropic models only
anthropic_models = model_picker(
    profile="clauth",
    region="ap-southeast-2",
    provider="anthropic"
)
```

## Development and Testing

When developing CLAUTH or testing Claude Code integration:

```bash
# Install in development mode
pip install -e .

# Test authentication
python -c "from clauth.aws_utils import user_is_authenticated; print(user_is_authenticated('clauth'))"

# Test model listing
python -c "from clauth.aws_utils import list_bedrock_profiles; print(list_bedrock_profiles('clauth', 'ap-southeast-2'))"
```

## Best Practices

1. **Use consistent profiles**: Stick with the default `clauth` profile unless you have specific requirements
2. **Regular re-authentication**: AWS SSO tokens expire; re-run `clauth init` when needed
3. **Model selection**: Choose appropriate default vs fast models based on your usage patterns
4. **Team coordination**: Coordinate SSO URLs and regions across your team

## Support

For issues related to:
- **CLAUTH setup**: Check the main README.md troubleshooting section
- **Claude Code usage**: Refer to [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code)
- **AWS Bedrock access**: Contact your AWS administrator