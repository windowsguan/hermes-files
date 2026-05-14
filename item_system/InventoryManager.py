# -*- coding: utf-8 -*-
"""
InventoryManager.py - Player Inventory & Warehouse Management
Core responsibility: Manages inventory slots, warehouse slots, item stacking,
equipping, and dirty-marking for database sync.
"""

import KBEngine
from common.KBEDebug import *
ItemPool = __import__('item_system.ItemPool').ItemPool


class InventoryManager:
    """
    Manages player's inventory (max slots) and warehouse (max slots).
    - Inventory: quick access items, equippable gear
    - Warehouse: long-term storage, non-equippable
    - Stack merging/splitting logic
    - Dirty-flag based delayed database writes
    """

    INVENTORY_MAX_SLOTS = 40
    WAREHOUSE_MAX_SLOTS = 100

    def __init__(self):
        self._inventory = {}   # slotIndex -> Item entity
        self._warehouse = {}   # slotIndex -> Item entity
        self._equipped = {}   # slotIndex -> Item entity
        self._dirtySlots = set()

    # ── Inventory Operations ──

    def addItem(self, ownerID, templateID, quantity=1):
        """
        Add item to inventory. Handles stacking automatically.
        Returns (item, success, message).
        """
        # Try to stack with existing item
        for idx, item in self._inventory.items():
            if item.templateID == templateID and item.quantity < item.maxStack:
                space = item.maxStack - item.quantity
                added = min(quantity, space)
                item.add(added)
                self._dirtySlots.add(idx)
                return (item, added == quantity, '')

        # Find free slot
        freeSlot = self._findFreeSlot(self._inventory, self.INVENTORY_MAX_SLOTS)
        if freeSlot is None:
            return (None, False, 'Inventory full')

        item = ItemPool.allocate(ownerID, templateID, quantity, 'inventory', freeSlot)
        self._inventory[freeSlot] = item
        self._dirtySlots.add(freeSlot)
        return (item, True, '')

    def removeItem(self, ownerID, slotIndex, quantity=1):
        """Remove quantity from item at slotIndex. Returns True on success."""
        item = self._inventory.get(slotIndex)
        if not item:
            return False
        if item.use(quantity):
            if item.quantity == 0:
                del self._inventory[slotIndex]
            self._dirtySlots.add(slotIndex)
            return True
        return False

    # ── Warehouse Operations ──

    def addToWarehouse(self, ownerID, templateID, quantity=1):
        """Move or create item in warehouse."""
        # Try stacking in warehouse
        for idx, item in self._warehouse.items():
            if item.templateID == templateID and item.quantity < item.maxStack:
                space = item.maxStack - item.quantity
                added = min(quantity, space)
                item.add(added)
                self._dirtySlots.add(idx)
                return (item, added == quantity, '')

        freeSlot = self._findFreeSlot(self._warehouse, self.WAREHOUSE_MAX_SLOTS)
        if freeSlot is None:
            return (None, False, 'Warehouse full')

        item = ItemPool.allocate(ownerID, templateID, quantity, 'warehouse', freeSlot)
        self._warehouse[freeSlot] = item
        self._dirtySlots.add(freeSlot)
        return (item, True, '')

    def removeFromWarehouse(self, ownerID, slotIndex, quantity=1):
        """Remove quantity from warehouse item. Returns True on success."""
        item = self._warehouse.get(slotIndex)
        if not item:
            return False
        if item.use(quantity):
            if item.quantity == 0:
                del self._warehouse[slotIndex]
            self._dirtySlots.add(slotIndex)
            return True
        return False

    # ── Equip / Unequip ──

    def equip(self, ownerID, slotIndex, equipSlot):
        """Equip item from inventory to an equip slot."""
        item = self._inventory.get(slotIndex)
        if not item:
            return (None, False, 'Item not found')

        # Check if item can be equipped (has durability = equippable gear)
        if item.maxDurability == 0:
            return (item, False, 'Item is not equippable')

        item.equip(equipSlot)
        self._equipped[equipSlot] = item
        self._dirtySlots.add(slotIndex)
        # Remove from inventory slot
        del self._inventory[slotIndex]
        return (item, True, '')

    def unequip(self, ownerID, equipSlot):
        """Unequip item, return to inventory."""
        item = self._equipped.get(equipSlot)
        if not item:
            return (None, False, 'No item equipped')

        # Find free inventory slot
        freeSlot = self._findFreeSlot(self._inventory, self.INVENTORY_MAX_SLOTS)
        if freeSlot is None:
            return (item, False, 'No free inventory slot')

        item.unequip()
        item.slotIndex = freeSlot
        self._inventory[freeSlot] = item
        del self._equipped[equipSlot]
        self._dirtySlots.add(freeSlot)
        return (item, True, '')

    # ── Transfer between inventory and warehouse ──

    def transferToWarehouse(self, ownerID, fromSlot, quantity=1):
        """Transfer item from inventory to warehouse."""
        item = self._inventory.get(fromSlot)
        if not item:
            return False

        # Determine transfer quantity (respect stack limits)
        transferQty = min(quantity, item.quantity)
        (warehouseItem, success, msg) = self.addToWarehouse(ownerID, item.templateID, transferQty)
        if success:
            # Remove from inventory
            item.use(transferQty)
            if item.quantity == 0:
                del self._inventory[fromSlot]
            self._dirtySlots.add(fromSlot)
        return success

    def transferToInventory(self, ownerID, fromSlot, quantity=1):
        """Transfer item from warehouse to inventory."""
        item = self._warehouse.get(fromSlot)
        if not item:
            return False

        transferQty = min(quantity, item.quantity)
        (invItem, success, msg) = self.addItem(ownerID, item.templateID, transferQty)
        if success:
            item.use(transferQty)
            if item.quantity == 0:
                del self._warehouse[fromSlot]
            self._dirtySlots.add(fromSlot)
        return success

    # ── Sorting ──

    def sortInventory(self, ownerID):
        """Sort inventory by templateID (or custom criteria)."""
        items = list(self._inventory.items())
        items.sort(key=lambda x: x[1].templateID)
        self._inventory.clear()
        for i, (oldSlot, item) in enumerate(items):
            item.slotIndex = i + 1
            self._inventory[i + 1] = item
            self._dirtySlots.add(i + 1)

    def sortWarehouse(self, ownerID):
        """Sort warehouse by templateID."""
        items = list(self._warehouse.items())
        items.sort(key=lambda x: x[1].templateID)
        self._warehouse.clear()
        for i, (oldSlot, item) in enumerate(items):
            item.slotIndex = i + 1
            self._warehouse[i + 1] = item
            self._dirtySlots.add(i + 1)

    # ── Dirty Slot Sync ──

    def getDirtySlots(self):
        """Return set of dirty slot indices."""
        return self._dirtySlots.copy()

    def clearDirtySlots(self):
        """Clear dirty flags after successful DB sync."""
        self._dirtySlots.clear()

    # ── Private Helpers ──

    def _findFreeSlot(self, slotDict, maxSlots):
        """Find the first free slot index (1-based)."""
        usedSlots = set(slotDict.keys())
        for i in range(1, maxSlots + 1):
            if i not in usedSlots:
                return i
        return None

    def getAllItems(self, ownerID):
        """Get all items across inventory, warehouse, and equipped."""
        allItems = list(self._inventory.values())
        allItems.extend(self._warehouse.values())
        allItems.extend(self._equipped.values())
        return allItems
