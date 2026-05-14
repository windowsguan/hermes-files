# -*- coding: utf-8 -*-
"""
ItemSystem_kbemain.py - KBEngine Integration Entry Point
Core responsibility: Hook into KBEngine lifecycle to initialize and manage
the item system. Called from baseapp's kbemain.py.
"""

import KBEngine
from common.KBEDebug import *

# Import and initialize ItemController
ItemController = None


def onInit(isReload):
    """KBEngine: Initialize item system on server startup."""
    global ItemController
    ItemController = __import__('item_system.ItemController').ItemController()
    ItemController.init()
    INFO_MSG('kbemain: Item system ready')


def onBaseAppReady(isBootstrap):
    """KBEngine: BaseApp ready hook."""
    if isBootstrap and ItemController:
        ItemController.init()


def onReadyForLogin(isBootstrap):
    """KBEngine: Check if ready for player login."""
    return 1.0


def onReadyForShutDown():
    """KBEngine: Prepare for shutdown - sync all items."""
    if ItemController:
        ItemController.shutdown()
    return True


def onBaseAppShutDown(state):
    """KBEngine: Final flush before shutdown."""
    if state == 1 and ItemController:
        ItemController.shutdown()
    DEBUG_MSG(f'kbemain: onBaseAppShutDown state={state}')


def onInit_reload(isReload):
    """KBEngine: Handle script reload."""
    if isReload and ItemController:
        ItemController.init()
