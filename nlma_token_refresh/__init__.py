# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Xing Li
def classFactory(iface):
    from .plugin import Plugin
    return Plugin(iface)
