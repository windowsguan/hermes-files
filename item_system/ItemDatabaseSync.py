# -*- coding: utf-8 -*-
"""
ItemDatabaseSync.py - Database Synchronization Controller
Core responsibility: Batch-write dirty item data to MySQL. Uses delayed
batching strategy to minimize database round-trips.
"""

import KBEngine
from common.KBEDebug import *
import json


class ItemDatabaseSync:
    """
    Database sync controller with these strategies:
    1. Dirty-flag marking: Items mark themselves dirty on modification
    2. Timer-based batching: Sync every N seconds with all dirty items
    3. Bulk INSERT/UPDATE: Use a single SQL statement per sync cycle
    4. Periodic full-sync on player disconnect / server shutdown

    DB Schema (reference):
      CREATE TABLE player_item (
        itemID       BIGINT UNSIGNED NOT NULL,
        templateID   INT UNSIGNED NOT NULL,
        name         VARCHAR(128),
        quantity     INT UNSIGNED,
        maxStack     INT UNSIGNED,
        durability   INT UNSIGNED,
        maxDurability INT UNSIGNED,
        bound        TINYINT(1),
        ownerID      BIGINT UNSIGNED,
        location     VARCHAR(32),
        slotIndex    INT,
        attributes   JSON,
        createTime   BIGINT UNSIGNED,
        expireTime   BIGINT UNSIGNED,
        PRIMARY KEY (itemID),
        INDEX idx_owner (ownerID),
        INDEX idx_template (templateID)
      );
    """

    SYNC_INTERVAL = 10   # seconds between batch syncs
    MAX_BATCH_SIZE = 50   # max items per batch write

    def __init__(self):
        self._timerID = None
        self._syncQueue = []

    def start(self):
        """Start the periodic sync timer."""
        self._timerID = KBEngine.addTimer(
            self.SYNC_INTERVAL, self.SYNC_INTERVAL,
            self._onSyncTimer
        )
        INFO_MSG(f'ItemDatabaseSync: Sync timer started (interval={self.SYNC_INTERVAL}s)')

    def markDirty(self, item):
        """Mark item as dirty and add to sync queue."""
        if not item.isDirty:
            item.isDirty = True
            self._syncQueue.append(item)

    def markClean(self, item):
        """Clear dirty flag after successful write."""
        item.isDirty = False

    def _onSyncTimer(self, timerID):
        """Timer callback: batch write dirty items to database."""
        if not self._syncQueue:
            return

        batch = self._syncQueue[:self.MAX_BATCH_SIZE]
        self._syncQueue = self._syncQueue[self.MAX_BATCH_SIZE:]

        self._batchWrite(batch)

    def _batchWrite(self, items):
        """Write a batch of dirty items to the database."""
        if not items:
            return

        # Build batch SQL
        values = []
        for item in items:
            attrs = json.dumps(item.attributes) if hasattr(item, 'attributes') else '{}'
            values.append(
                f"({item.id}, {item.templateID}, '{item.name}', {item.quantity}, "
                f"{item.maxStack}, {item.durability}, {item.maxDurability}, "
                f"{item.bound}, {item.ownerID}, '{item.location}', "
                f"{item.slotIndex}, '{attrs}', {item.createTime}, {item.expireTime})"
            )

        sql = (
            f"INSERT INTO player_item "
            f"(itemID, templateID, name, quantity, maxStack, durability, maxDurability, "
            f"bound, ownerID, location, slotIndex, attributes, createTime, expireTime) "
            f"VALUES {','.join(values)} "
            f"ON DUPLICATE KEY UPDATE "
            f"templateID=VALUES(templateID), name=VALUES(name), quantity=VALUES(quantity), "
            f"maxStack=VALUES(maxStack), durability=VALUES(durability), "
            f"maxDurability=VALUES(maxDurability), bound=VALUES(bound), "
            f"location=VALUES(location), slotIndex=VALUES(slotIndex), "
            f"attributes=VALUES(attributes), createTime=VALUES(createTime), "
            f"expireTime=VALUES(expireTime)"
        )

        KBEngine.DBManager.executeSQL(sql)

        # Clear dirty flags
        for item in items:
            self.markClean(item)

        DEBUG_MSG(f'ItemDatabaseSync: Batch wrote {len(items)} items to DB')

    def forceSync(self):
        """Force immediate sync of all dirty items (used on player disconnect)."""
        self._batchWrite(self._syncQueue)
        self._syncQueue.clear()

    def syncOwner(self, ownerID, inventoryManager):
        """Sync all items for a specific owner."""
        items = inventoryManager.getAllItems(ownerID)
        dirtyItems = [it for it in items if it.isDirty]
        if dirtyItems:
            self._batchWrite(dirtyItems)

    def shutdownSync(self, allInventoryManagers):
        """Sync all dirty items before server shutdown."""
        allItems = []
        for mgr in allInventoryManagers:
            allItems.extend(mgr.getAllItems(0))  # ownerID placeholder
        if allItems:
            # Flush remaining queue first
            self._batchWrite(self._syncQueue)
            self._syncQueue.clear()
            # Then sync all dirty items
            dirtyItems = [it for it in allItems if it.isDirty]
            if dirtyItems:
                self._batchWrite(dirtyItems)
            INFO_MSG('ItemDatabaseSync: All items synced on shutdown')
