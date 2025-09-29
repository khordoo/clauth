# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

"""
CLAUTH Commands Package.

This package contains all CLAUTH CLI commands organized as separate modules
for better maintainability and modularity.
"""

from .models import model_app
from . import delete as delete_module
from .config import config_app
from .init import init_command

# Backwards-compatible alias for the delete function
delete = delete_module.delete

__all__ = ["model_app", "delete", "config_app", "init_command", "delete_module"]
