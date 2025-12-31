"""
config.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Utility functions for Fourdrinier.

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import re
import secrets


async def generate_id() -> str:
    """
    Generate a unique 8-character ID.
    """
    return secrets.token_hex(4)


def sanitize_directory_name(name: str) -> str:
    """
    Sanitize server name for use in filesystem paths.
    Replaces filesystem-unsafe characters with underscores.

    Args:
        name: Server name from database

    Returns:
        Sanitized name safe for directory creation
    """
    # Replace invalid chars: < > : " / \ | ? *
    return re.sub(r'[<>:"/\\|?*]', '_', name)
