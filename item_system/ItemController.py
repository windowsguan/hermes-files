# -*- coding: utf-8 -*-
"""
ItemController.py - Central Item System Controller
Core responsibility: Orchestrates all item subsystems, provides unified
API for other game systems to interact with items.
"""

import KBEngine
from common.KBEDebug import *


class ItemController:
    """
    Central controller for the item system.
    - Initializes all subsystem managers
    - Coordinates inventory, warehouse, crafting, trading
    - Handles player login/logout item sync
    - Manages periodic database synchronization

    Usage:
        controller = ItemController()
        controller.onPlayerLogin(playerEntity)   # Load items from DB
        controller.onPlayerLogout(playerEntity)  # Flush to DB
    """

    def __init__(self):
        self.inventoryMgr = __import__('item_system.InventoryManager').InventoryManager()
        self.itemPool = __import__('item_system.ItemPool').ItemPool()
        self.templateMgr = __import__('item_system.ItemTemplate').ItemTemplate
        self.craftMgr = __import__('item_system.ItemCraftManager').ItemCraftManager()
        self.tradeMgr = __import__('item_system.ItemTradeManager').ItemTradeManager()
        self.dbSync = __import__('item_system.ItemDatabaseSync').ItemDatabaseSync()
        self.msgProtocol = __import__('item_system.ItemMessageProtocol').ItemMessageProtocol

        # Per-player inventory manager cache
        self._inventoryManagers = {}  # ownerID -> InventoryManager

    def init(self):
        """Initialize item system: load templates, recipes, start DB sync timer."""
        # Load item templates
        self.templateMgr.loadAllTemplates()

        # Load crafting recipes
        self.craftMgr.loadRecipes()

        # Start periodic DB sync
        self.dbSync.start()

        INFO_MSG('ItemController: Item system initialized')

    def onPlayerLogin(self, playerEntity):
        """
        Called when a player logs in.
        Load player's items from database into memory.
        """
        ownerID = playerEntity.id
        invMgr = __import__('item_system.InventoryManager').InventoryManager()
        self._inventoryManagers[ownerID] = invMgr

        # Load items from DB
        result = KBEngine.DBManager.executeSQL(
            f"SELECT * FROM player_item WHERE ownerID = {ownerID}"
        )

        for row in result:
            item = self.itemPool.allocate(
                ownerID, row['templateID'],
                row['quantity'], row['location'], row['slotIndex']
            )
            item.name = row['name']
            item.durability = row.get('durability', 0)
            item.maxDurability = row.get('maxDurability', 0)
            item.bound = row.get('bound', False)
            item.createTime = row.get('createTime', 0)
            item.expireTime = row.get('expireTime', 0)
            item.isDirty = False  # Fresh from DB, not dirty

            # Place in correct manager dict
            if item.location == 'inventory':
                invMgr._inventory[item.slotIndex] = item
            elif item.location == 'warehouse':
                invMgr._warehouse[item.slotIndex] = item
            elif item.location == 'equipped':
                invMgr._equipped[item.slotIndex] = item

        # Send full inventory sync to client
        syncData = self.msgProtocol.buildInventorySyncMessage(invMgr)
        # In production: send to client via playerEntity.messageSend()
        playerEntity.messageSend(self.msgProtocol.MSG_INVENTORY_SYNC, syncData)

        DEBUG_MSG(f'ItemController: Loaded {len(result)} items for ownerID={ownerID}')
        return syncData

    def onPlayerLogout(self, playerEntity):
        """Called when a player logs out. Flush all dirty items to DB."""
        ownerID = playerEntity.id
        invMgr = self._inventoryManagers.get(ownerID)
        if invMgr:
            self.dbSync.syncOwner(ownerID, invMgr)
            # Also flush any remaining queue items for this player
            self.dbSync.forceSync()
            DEBUG_MSG(f'ItemController: Flushed items for ownerID={ownerID}')

    def handleClientMessage(self, playerEntity, messageID, data):
        """Route client messages to appropriate handler."""
        ownerID = playerEntity.id
        invMgr = self._inventoryManagers.get(ownerID)
        if not invMgr:
            return False

        protocol = self.msgProtocol

        if messageID == protocol.MSG_USE_ITEM:
            slotIdx = data['slotIndex']
            qty = data.get('quantity', 1)
            item = invMgr._inventory.get(slotIdx)
            if item:
                invMgr.removeItem(ownerID, slotIdx, qty)
                self.dbSync.markDirty(item)
        elif messageID == protocol.MSG_BATCH_USE:
            for entry in data:
                slotIdx = entry['slotIndex']
                qty = entry.get('quantity', 1)
                item = invMgr._inventory.get(slotIdx)
                if item:
                    invMgr.removeItem(ownerID, slotIdx, qty)
                    self.dbSync.markDirty(item)
        elif messageID == protocol.MSG_EQUIP_ITEM:
            slotIdx = data['slotIndex']
            equipSlot = data['equipSlot']
            (item, success, msg) = invMgr.equip(ownerID, slotIdx, equipSlot)
            if success:
                self.dbSync.markDirty(item)
        elif messageID == protocol.MSG_UNEQUIP_ITEM:
            equipSlot = data['equipSlot']
            (item, success, msg) = invMgr.unequip(ownerID, equipSlot)
            if success:
                self.dbSync.markDirty(item)
        elif messageID == protocol.MSG_TRANSFER_ITEM:
            fromSlot = data['fromSlot']
            qty = data.get('quantity', 1)
            direction = data.get('direction', 'to_warehouse')
            if direction == 'to_warehouse':
                invMgr.transferToWarehouse(ownerID, fromSlot, qty)
            else:
                invMgr.transferToInventory(ownerID, fromSlot, qty)
        elif messageID == protocol.MSG_SORT_INVENTORY:
            invMgr.sortInventory(ownerID)
        elif messageID == protocol.MSG_SORT_WAREHOUSE:
            invMgr.sortWarehouse(ownerID)
        elif messageID == protocol.MSG_CRAFT_ITEM:
            recipeID = data['recipeID']
            (success, msg) = self.craftMgr.craft(ownerID, recipeID, invMgr)
            if success:
                # Send craft result to client
                playerEntity.messageSend(protocol.MSG_CRAFT_RESULT, {'message': msg, 'success': True})
            else:
                playerEntity.messageSend(protocol.MSG_CRAFT_RESULT, {'message': msg, 'success': False})

        return True

    def shutdown(self):
        """Shutdown hook: sync all dirty items."""
        self.dbSync.shutdownSync(list(self._inventoryManagers.values()))
        INFO_MSG('ItemController: Shutdown complete')
