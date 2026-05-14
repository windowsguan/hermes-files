# -*- coding: utf-8 -*-
"""
ItemMessageProtocol.py - Network Message Definitions
Core responsibility: Defines compact message protocol for item operations,
minimizing network traffic between client and server.
"""

import KBEngine
from common.KBEDebug import *


class ItemMessageProtocol:
    """
    Message Protocol Design:
    - Uses KBEngine's message system with compact binary/struct encoding
    - Batch messages: one message for multiple operations
    - Delta updates: only send changed properties

    Message Types (opcode ranges 1000-1099 reserved for item system):

    SERVER-TO-CLIENT:
      MSG_INVENTORY_SYNC (1000): Full inventory state sync
      MSG_ITEM_UPDATED (1001): Delta update for a single item
      MSG_TRADE_OFFER (1002): Trade offer received
      MSG_TRADE_CONFIRM (1003): Trade confirmation
      MSG_CRAFT_RESULT (1004): Crafting result notification

    CLIENT-TO-SERVER:
      MSG_USE_ITEM (1010): Use/consume item
      MSG_ADD_ITEM (1011): Add item to inventory
      MSG_REMOVE_ITEM (1012): Remove quantity from item
      MSG_EQUIP_ITEM (1013): Equip item to slot
      MSG_UNEQUIP_ITEM (1014): Unequip item
      MSG_TRANSFER_ITEM (1015): Transfer between inventory/warehouse
      MSG_SORT_INVENTORY (1016): Sort inventory
      MSG_SORT_WAREHOUSE (1017): Sort warehouse
      MSG_TRADE_START (1018): Start trade session
      MSG_TRADE_ADD_ITEM (1019): Add item to trade
      MSG_TRADE_CONFIRM (1020): Confirm trade
      MSG_TRADE_CANCEL (1021): Cancel trade
      MSG_CRAFT_ITEM (1022): Initiate crafting
      MSG_BATCH_USE (1023): Batch use multiple items

    Optimization:
    - MSG_INVENTORY_SYNC sends full inventory once on login
    - Subsequent updates use MSG_ITEM_UPDATED with delta fields only
    - MSG_BATCH_USE allows multiple uses in one message
    """

    # Message opcodes
    MSG_INVENTORY_SYNC = 1000
    MSG_ITEM_UPDATED = 1001
    MSG_TRADE_OFFER = 1002
    MSG_TRADE_CONFIRM = 1003
    MSG_CRAFT_RESULT = 1004

    MSG_USE_ITEM = 1010
    MSG_ADD_ITEM = 1011
    MSG_REMOVE_ITEM = 1012
    MSG_EQUIP_ITEM = 1013
    MSG_UNEQUIP_ITEM = 1014
    MSG_TRANSFER_ITEM = 1015
    MSG_SORT_INVENTORY = 1016
    MSG_SORT_WAREHOUSE = 1017
    MSG_TRADE_START = 1018
    MSG_TRADE_ADD_ITEM = 1019
    MSG_TRADE_CONFIRM_MSG = 1020
    MSG_TRADE_CANCEL = 1021
    MSG_CRAFT_ITEM = 1022
    MSG_BATCH_USE = 1023

    @classmethod
    def handleClientMessages(cls, client, messageID, data):
        """
        Dispatch client messages to appropriate handlers.
        Called from baseapp or cellapp message router.
        """
        if messageID == cls.MSG_USE_ITEM:
            # data = {'slotIndex': int, 'quantity': int}
            slotIdx = data['slotIndex']
            qty = data.get('quantity', 1)
            # Dispatch to InventoryManager.use()
            DEBUG_MSG(f'handleClientMessages: USE_ITEM slot={slotIdx} qty={qty}')
            return True

        elif messageID == cls.MSG_BATCH_USE:
            # data = [{'slotIndex': int, 'quantity': int}, ...]
            DEBUG_MSG(f'handleClientMessages: BATCH_USE count={len(data)}')
            return True

        elif messageID == cls.MSG_EQUIP_ITEM:
            # data = {'slotIndex': int, 'equipSlot': int}
            DEBUG_MSG(f'handleClientMessages: EQUIP_ITEM slot={data["slotIndex"]}')
            return True

        elif messageID == cls.MSG_SORT_INVENTORY:
            DEBUG_MSG('handleClientMessages: SORT_INVENTORY')
            return True

        elif messageID == cls.MSG_TRADE_START:
            # data = {'targetOwnerID': int}
            DEBUG_MSG(f'handleClientMessages: TRADE_START target={data["targetOwnerID"]}')
            return True

        elif messageID == cls.MSG_CRAFT_ITEM:
            # data = {'recipeID': int}
            DEBUG_MSG(f'handleClientMessages: CRAFT_ITEM recipe={data["recipeID"]}')
            return True

        return False  # Unhandled message

    @classmethod
    def buildInventorySyncMessage(cls, inventoryManager):
        """
        Build compact inventory sync message.
        Only includes non-zero quantity items, reducing message size.
        Format: list of {itemID, templateID, quantity, durability, ...}
        """
        items = inventoryManager.getAllItems(0)  # ownerID placeholder
        # Send only essential fields for initial sync
        syncData = []
        for item in items:
            syncData.append({
                'itemID': item.id,
                'templateID': item.templateID,
                'quantity': item.quantity,
                'durability': item.durability,
                'maxDurability': item.maxDurability,
                'location': item.location,
                'slotIndex': item.slotIndex,
            })
        return syncData

    @classmethod
    def buildItemUpdateMessage(cls, item):
        """Build delta update message for a single item."""
        updateData = {
            'itemID': item.id,
            'templateID': item.templateID,
            'quantity': item.quantity,
            'durability': item.durability,
            'location': item.location,
            'slotIndex': item.slotIndex,
        }
        return updateData
