# -*- coding: utf-8 -*-
"""
ItemPool.py - Item Object Pool
Core responsibility: Manages a pool of Item entities to avoid frequent
creation and destruction, reducing GC pressure and database overhead.
"""

import KBEngine
from common.KBEDebug import *


class ItemPool(KBEngine.Proxy):
    """
    Object Pool for Item entities.
    - Maintains a list of inactive (recycled) item entities
    - allocate(): pop from inactive list or create new
    - returnItem(): push back to inactive list
    - recycleThreshold: when pool exceeds this, oldest inactive items are destroyed
    """

    def __init__(self):
        KBEngine.Proxy.__init__(self)
        self.capacity = 200       # Max items in pool
        self.available = 0        # Currently unused slots
        self.recycleThreshold = 150

        self._inactive = []       # List of recycled Item entities
        self._active = {}        # activeItems: ownerID -> list of Item entities

    def allocate(self, ownerID, templateID, quantity=1, location='inventory', slotIndex=-1):
        """
        Allocate an item from the pool or create a new one.
        Returns the Item entity (new or recycled).
        """
        item = None

        # Try to get from inactive list
        if self._inactive:
            item = self._inactive.pop()

        if item is None:
            # Create new Item entity via KBEngine
            item = KBEngine.createEntity('Item')

        # Initialize properties
        tmpl = ItemTemplate.getTemplate(templateID)
        item.templateID = templateID
        item.name = tmpl['name'] if tmpl else f'Item_{templateID}'
        item.quantity = quantity
        item.maxStack = tmpl['maxStack'] if tmpl else 1
        item.durability = tmpl['maxDurability'] if tmpl else 0
        item.maxDurability = tmpl['maxDurability'] if tmpl else 0
        item.bound = tmpl['bound'] if tmpl else False
        item.ownerID = ownerID
        item.ownerName = ''
        item.location = location
        item.slotIndex = slotIndex
        item.createTime = int(KBEngine.getCurrentTime())
        item.expireTime = 0
        item.isDirty = True

        # Track in active dict
        if ownerID not in self._active:
            self._active[ownerID] = []
        self._active[ownerID].append(item)
        self.available = len(self._inactive)

        DEBUG_MSG(f'ItemPool: allocated Item[{item.id}] (templateID={templateID})')
        return item

    def returnItem(self, item):
        """Return an item to the inactive pool."""
        # Remove from active list
        if item.ownerID in self._active:
            if item in self._active[item.ownerID]:
                self._active[item.ownerID].remove(item)

        # Reset item properties for reuse
        item.quantity = 0
        self._inactive.append(item)
        self.available = len(self._inactive)

        # Recycle if pool is too large
        if len(self._inactive) > self.recycleThreshold:
            recycled = self._inactive.pop(0)  # Remove oldest
            recycled.destroy()
            DEBUG_MSG(f'ItemPool: recycled oldest item')

    def getActiveItems(self, ownerID):
        """Get all active items for an owner."""
        return self._active.get(ownerID, [])

    def getItemsByLocation(self, ownerID, location):
        """Filter active items by location (inventory/warehouse/equipped)."""
        items = self._active.get(ownerID, [])
        return [it for it in items if it.location == location]

    def getInventory(self, ownerID):
        """Get inventory items."""
        return self.getItemsByLocation(ownerID, 'inventory')

    def getWarehouse(self, ownerID):
        """Get warehouse items."""
        return self.getItemsByLocation(ownerID, 'warehouse')

    def getEquipped(self, ownerID):
        """Get equipped items."""
        return self.getItemsByLocation(ownerID, 'equipped')


# Import ItemTemplate
ItemTemplateManager = __import__('item_system.ItemTemplate').ItemTemplateManager
