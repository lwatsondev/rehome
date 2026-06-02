# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

import secrets
import string


def random_string(length: int, extra_chars: str = "") -> str:
    return "".join(
        secrets.choice(string.ascii_letters + string.digits + extra_chars)
        for _ in range(length)
    )
