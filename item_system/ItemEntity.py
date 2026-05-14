# -*- coding: utf-8 -*-
"""
ItemEntity.py - Item Entity (KBEngine Proxy)
Core responsibility: Represents a single item instance with all its properties.
"""

import KBEngine
from common.KBEDebug import *


class Item(KBEngine.Proxy):
    """
    Item Entity - KBEngine Proxy
    Properties (from types.xml):
      itemID, templateID, name, quantity, maxStack, durability, maxDurability,
      bound, ownerID, ownerName, location, slotIndex, attributes, createTime,
      expireTime, isDirty

    Lifecycle:
      - Created via ItemPool.allocate()
      - Marked dirty when modified
      - Returned to pool when quantity becomes 0
    """

    def __init__(self):
        KBEngine.Proxy.__init__(self)
        # Default property initialization
        self.itemID = 0
        self.templateID = 0
        self.name = ''
        self.quantity = 0
        self.maxStack = 1
        self.durability = 0
        self.maxDurability = 0
        self.bound = False
        self.ownerID = 0
        self.ownerName = ''
        self.location = ''    # 'inventory', 'warehouse', 'equipped'
        self.slotIndex = -1
        self.attributes = '{}'
        self.createTime = 0
        self.expireTime = 0
        self.isDirty = False

    # ── KBEngine lifecycle hooks ──

    def onCreated(self):
        """Called when item entity is first created."""
        DEBUG_MSG(f'Item[{self.id}]: onCreated')

    def onAddProps(self, addedProps):
        """Called when properties are updated from client or engine."""
        self.isDirty = True

    def onBeforeSerialize(self):
        """Before entity is serialized to database."""
        pass

    def onAfterUnserialize(self):
        """After entity is deserialized from database."""
        DEBUG_MSG(f'Item[{self.id}]: loaded from DB')

    def onDestroy(self):
        """Called before entity destruction - return item to pool."""
        DEBUG_MSG(f'Item[{self.id}]: destroyed')

    # ── Item operations ──

    def use(self, count=1):
        """
        Use/consume items from this stack.
        Returns True on success, False if insufficient quantity.
        """
        if self.quantity < count:
            return False
        self.quantity -= count
        self.isDirty = True
        # Apply durability cost for tools/weapons
        if self.maxDurability > 0:
            self.durability = max(0, self.durability - count)
        if self.quantity == 0:
            self.isDirty = True
            self._returnToPool()
            return True
        return True

    def add(self, count=1):
        """Add quantity to this item stack."""
        tmpl = ItemTemplate.getTemplate(self.templateID)
        maxStack = tmpl['maxStack'] if tmpl else self.maxStack
        canAdd = min(count, maxStack - self.quantity)
        self.quantity += canAdd
        self.isDirty = True
        return canAdd == count

    def equip(self, slot):
        """Equip this item to a specific slot."""
        self.location = 'equipped'
        self.slotIndex = slot
        self.isDirty = True
        DEBUG_MSG(f'Item[{self.id}]: equipped to slot {slot}')

    def unequip(self):
        """Unequip item, move back to inventory."""
        self.location = 'inventory'
        self.slotIndex = -1
        self.isDirty = True

    def damage(self, amount=1):
        """Consume durability."""
        self.durability = max(0, self.durability - amount)
        self.isDirty = True
        if self.durability == 0:
            DEBUG_MSG(f'Item[{self.id}]: durability depleted!')

    def _returnToPool(self):
        """Return this item instance to the ItemPool."""
        ItemPool.returnItem(self)


# Singleton - template manager reference
ItemTemplate = __import__('item_system.ItemTemplate').ItemTemplate
