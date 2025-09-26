# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

"""
CLAUTH - Claude + AWS SSO helper for Bedrock.

A Python CLI tool that simplifies setting up Claude Code with AWS Bedrock
authentication through AWS SSO. Provides automated AWS profile configuration,
model discovery, and Claude Code CLI launching.
"""
from importlib.metadata import version, PackageNotFoundError

_DIST_NAME = "clauth"

try:
    __version__ = version(_DIST_NAME)
except PackageNotFoundError:
    __version__ = "0.0.0"
