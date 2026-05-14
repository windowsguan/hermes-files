#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_item_system.py - Comprehensive Unit Tests for KBEngine Item System

Covers: ItemTemplate, ItemPool, ItemEntity, InventoryManager,
         ItemDatabaseSync, ItemCraftManager, ItemTradeManager, ItemMessageProtocol

Run: python3 test_item_system.py
"""

import unittest
import json
import sys
import os

# ── Mock KBEngine ──

class MockKBEngine:
    """Minimal mock of KBEngine for unit testing."""

    class MockProxy:
        """Mock Proxy base class."""
        def __init__(self):
            self.id = getattr(self, '_mock_id', 0)

    class MockDBManager:
        """Mock DBManager with in-memory SQL execution."""
        def __init__(self):
            self._sql_log = []
            self._all_templates = [
                {'templateID': 1001, 'name': 'Iron Sword', 'type': 'weapon',
                 'maxStack': 1, 'maxDurability': 100, 'bound': False,
                 'attributes': json.dumps({'atk': 25, 'def': 0})},
                {'templateID': 1002, 'name': 'Health Potion', 'type': 'consumable',
                 'maxStack': 20, 'maxDurability': 0, 'bound': False,
                 'attributes': json.dumps({'heal': 50})},
                {'templateID': 1003, 'name': 'Leather Armor', 'type': 'armor',
                 'maxStack': 1, 'maxDurability': 80, 'bound': True,
                 'attributes': json.dumps({'def': 15})},
            ]

        def _get_all_templates(self):
            return self._all_templates

        def executeSQL(self, sql):
            self._sql_log.append(sql)
            # Dispatch based on SQL pattern (specific before general)
            if 'SELECT * FROM item_template WHERE' in sql:
                tid = int(sql.split('=')[-1].strip())
                for row in self._get_all_templates():
                    if row['templateID'] == tid:
                        return row
                return None
            elif 'SELECT * FROM item_template' in sql:
                return self._get_all_templates()
            elif 'SELECT * FROM item_recipe' in sql:
                return [
                    {'recipeID': 5001, 'name': 'Iron Sword from Ore',
                     'resultTemplateID': 1001, 'resultQuantity': 1,
                     'materials': json.dumps([{'templateID': 2001, 'quantity': 5}]),
                     'cooldown': 30},
                    {'recipeID': 5002, 'name': 'Health Potion from Herb',
                     'resultTemplateID': 1002, 'resultQuantity': 3,
                     'materials': json.dumps([{'templateID': 2002, 'quantity': 2}]),
                     'cooldown': 10},
                ]
            elif 'SELECT * FROM player_item' in sql:
                return [
                    {'itemID': 9001, 'templateID': 1002, 'name': 'Health Potion',
                     'quantity': 15, 'maxStack': 20, 'durability': 0, 'maxDurability': 0,
                     'bound': False, 'ownerID': 100, 'location': 'inventory', 'slotIndex': 1,
                     'attributes': json.dumps({'heal': 50}), 'createTime': 1700000000, 'expireTime': 0},
                    {'itemID': 9002, 'templateID': 1003, 'name': 'Leather Armor',
                     'quantity': 1, 'maxStack': 1, 'durability': 60, 'maxDurability': 80,
                     'bound': True, 'ownerID': 100, 'location': 'equipped', 'slotIndex': 3,
                     'attributes': json.dumps({'def': 15}), 'createTime': 1700000100, 'expireTime': 0},
                ]
            elif 'SELECT * FROM player_item WHERE ownerID' in sql:
                owner = int(sql.split('=')[-1].strip())
                all = self.executeSQL('SELECT * FROM player_item')
                return [r for r in all if r.get('ownerID') == owner]
            else:
                return None

        def get_sql_log(self):
            return self._sql_log

    # Class-level members
    Proxy = MockProxy
    DBManager = MockDBManager()
    _current_time = 1700000000
    _timer_callbacks = []
    _created_entities = []
    _publish_count = 0

    LOG_TYPE_DBG = 0
    LOG_TYPE_INFO = 1
    LOG_TYPE_WARN = 2
    LOG_TYPE_ERR = 3

    @classmethod
    def publish(cls):
        """Mock of KBEngine.publish() - returns 0 (success)."""
        cls._publish_count += 1
        return 0

    @classmethod
    def scriptLogType(cls, logType):
        """Mock of KBEngine.scriptLogType() - no-op."""
        pass

    @classmethod
    def getCurrentTime(cls):
        return cls._current_time

    @classmethod
    def createEntity(cls, entityType):
        entity = cls.Proxy()
        entity.id = len(cls._created_entities) + 1
        entity.entityType = entityType
        cls._created_entities.append(entity)
        return entity

    @classmethod
    def addTimer(cls, delay, period, callback):
        cls._timer_callbacks.append((delay, period, callback))
        return len(cls._timer_callbacks)


# Patch sys.modules so __import__ resolves to mock
sys.modules['KBEngine'] = MockKBEngine

# Add scripts directory to sys.path so 'from common.KBEDebug import *' works
_scripts_path = '/home/gxl/kbengine/kbe/res/sdk_templates/server/python_assets/scripts'
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)

def __import__(module_path):
    """Simulate KBEngine's __import__ helper."""
    # Cache: return cached module if already loaded
    if module_path in sys.modules:
        return sys.modules[module_path]

    parts = module_path.split('.')
    mod_name = parts[-1]
    mod_path = os.path.join(
        '/home/gxl/kbengine/kbe/res/sdk_templates/server/python_assets/scripts/item_system',
        f'{mod_name}.py'
    )
    import importlib.util
    spec = importlib.util.spec_from_file_location(f'item_system.{mod_name}', mod_path)
    module = importlib.util.module_from_spec(spec)
    with open(mod_path, 'r', encoding='utf-8') as f:
        code = compile(f.read(), mod_path, 'exec')
        exec(code, module.__dict__)
    sys.modules[module_path] = module
    return module


# ── Test Fixtures ──

class TestBase(unittest.TestCase):
    """Base class with shared setup for all item system tests."""

    @classmethod
    def setUpClass(cls):
        # Reset MockKBEngine state before each class
        MockKBEngine._created_entities = []
        MockKBEngine._timer_callbacks = []
        MockKBEngine.DBManager._sql_log = []
        MockKBEngine._current_time = 1700000000

    def setUp(self):
        self.ownerID = 100


# ── Test Classes ──

class TestItemTemplate(TestBase):
    """Tests for ItemTemplate.py"""

    def setUp(self):
        super().setUp()
        self.tmpl_mgr = __import__('item_system.ItemTemplate').ItemTemplateManager()

    def test_loadAllTemplates(self):
        self.tmpl_mgr.loadAllTemplates()
        self.assertEqual(len(self.tmpl_mgr._templates), 3)
        self.assertIn(1001, self.tmpl_mgr._templates)
        self.assertIn(1002, self.tmpl_mgr._templates)

    def test_getTemplate_cache_hit(self):
        self.tmpl_mgr.loadAllTemplates()
        tmpl = self.tmpl_mgr.getTemplate(1001)
        self.assertEqual(tmpl['name'], 'Iron Sword')
        # Verify no DB query for cached template
        log_len_before = len(MockKBEngine.DBManager.get_sql_log())
        self.tmpl_mgr.getTemplate(1001)  # Should be cache hit
        log_len_after = len(MockKBEngine.DBManager.get_sql_log())
        self.assertEqual(log_len_before, log_len_after, "No extra DB query for cached template")

    def test_getTemplate_cache_miss(self):
        self.tmpl_mgr.loadAllTemplates()
        # Request templateID=9999 which doesn't exist in the 3 templates
        tmpl = self.tmpl_mgr.getTemplate(9999)
        self.assertIsNone(tmpl)

    def test_addTemplate(self):
        self.tmpl_mgr.loadAllTemplates()
        self.tmpl_mgr.addTemplate(9999, {
            'name': 'Test Item', 'type': 'misc', 'maxStack': 5,
            'maxDurability': 0, 'bound': False, 'attributes': {}
        })
        self.assertTrue(self.tmpl_mgr._dirty)
        self.assertIn(9999, self.tmpl_mgr._templates)


class TestItemEntity(TestBase):
    """Tests for ItemEntity.py"""

    def setUp(self):
        super().setUp()
        MockKBEngine._created_entities = []
        # Create item via KBEngine mock
        self.item = MockKBEngine.createEntity('Item')
        # Simulate template load
        tmpl = __import__('item_system.ItemTemplate').ItemTemplateManager()
        tmpl.loadAllTemplates()

    def test_use(self):
        self.item.templateID = 1002  # Health Potion
        self.item.quantity = 10
        self.item.maxDurability = 0
        self.assertTrue(self.item.use(3))
        self.assertEqual(self.item.quantity, 7)
        self.assertTrue(self.item.isDirty)

    def test_use_empty_returns_to_pool(self):
        self.item.templateID = 1002
        self.item.quantity = 3
        self.item.maxDurability = 0
        # Use exactly remaining quantity
        self.assertTrue(self.item.use(3))
        self.assertEqual(self.item.quantity, 0)

    def test_add_stacking(self):
        self.item.templateID = 1002  # maxStack=20
        self.item.quantity = 15
        self.item.maxStack = 20
        self.assertTrue(self.item.add(5))
        self.assertEqual(self.item.quantity, 20)

    def test_add_over_stack_limit(self):
        self.item.templateID = 1002
        self.item.quantity = 18
        self.item.maxStack = 20
        self.assertTrue(self.item.add(5))  # Only 2 can be added
        self.assertEqual(self.item.quantity, 20)

    def test_equip(self):
        self.item.location = 'inventory'
        self.item.equip(3)
        self.assertEqual(self.item.location, 'equipped')
        self.assertEqual(self.item.slotIndex, 3)
        self.assertTrue(self.item.isDirty)

    def test_unequip(self):
        self.item.location = 'equipped'
        self.item.slotIndex = 3
        self.item.unequip()
        self.assertEqual(self.item.location, 'inventory')
        self.assertEqual(self.item.slotIndex, -1)

    def test_damage(self):
        self.item.durability = 50
        self.item.maxDurability = 100
        self.item.damage(20)
        self.assertEqual(self.item.durability, 30)
        self.assertTrue(self.item.isDirty)

    def test_damage_deplete(self):
        self.item.durability = 5
        self.item.maxDurability = 100
        self.item.damage(10)  # Damage exceeds durability
        self.assertEqual(self.item.durability, 0)


class TestItemPool(TestBase):
    """Tests for ItemPool.py"""

    def setUp(self):
        super().setUp()
        MockKBEngine._created_entities = []
        tmpl = __import__('item_system.ItemTemplate').ItemTemplateManager()
        tmpl.loadAllTemplates()
        self.pool = __import__('item_system.ItemPool').ItemPool()

    def test_allocate(self):
        item = self.pool.allocate(self.ownerID, 1002, 5)
        self.assertEqual(item.templateID, 1002)
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.location, 'inventory')
        self.assertIn(item, self.pool.getInventory(self.ownerID))

    def test_return_item(self):
        item = self.pool.allocate(self.ownerID, 1002, 5)
        self.pool.returnItem(item)
        self.assertEqual(len(self.pool._inactive), 1)
        self.assertEqual(self.pool.available, 1)

    def test_allocate_recycled(self):
        item1 = self.pool.allocate(self.ownerID, 1002, 3)
        self.pool.returnItem(item1)
        item2 = self.pool.allocate(self.ownerID, 1002, 5)
        # item2 should be the recycled item1
        self.assertEqual(item2.id, item1.id)

    def test_recycle_threshold(self):
        for i in range(160):
            item = self.pool.allocate(self.ownerID, 1002, 1)
            self.pool.returnItem(item)
        # 150 in pool (threshold=150), 10 items should have been recycled
        self.assertLessEqual(len(self.pool._inactive), 150)


class TestInventoryManager(TestBase):
    """Tests for InventoryManager.py"""

    def setUp(self):
        super().setUp()
        tmpl = __import__('item_system.ItemTemplate').ItemTemplateManager()
        tmpl.loadAllTemplates()
        self.pool = __import__('item_system.ItemPool').ItemPool()
        self.invMgr = __import__('item_system.InventoryManager').InventoryManager()

    def test_add_item(self):
        (item, success, msg) = self.invMgr.addItem(self.ownerID, 1002, 10)
        self.assertTrue(success)
        self.assertEqual(item.quantity, 10)
        self.assertIn(1, self.invMgr._inventory)

    def test_add_item_stacking(self):
        self.invMgr.addItem(self.ownerID, 1002, 5)
        (item, success, msg) = self.invMgr.addItem(self.ownerID, 1002, 3)
        self.assertTrue(success)
        self.assertEqual(item.quantity, 8)

    def test_remove_item(self):
        self.invMgr.addItem(self.ownerID, 1002, 10)
        self.assertTrue(self.invMgr.removeItem(self.ownerID, 1, 3))
        item = self.invMgr._inventory.get(1)
        self.assertEqual(item.quantity, 7)

    def test_remove_item_deletes_slot(self):
        self.invMgr.addItem(self.ownerID, 1002, 3)
        self.assertTrue(self.invMgr.removeItem(self.ownerID, 1, 3))
        self.assertNotIn(1, self.invMgr._inventory)

    def test_equip(self):
        self.invMgr.addItem(self.ownerID, 1001, 1)  # Iron Sword (equippable)
        (item, success, msg) = self.invMgr.equip(self.ownerID, 1, 3)
        self.assertTrue(success)
        self.assertEqual(item.location, 'equipped')
        self.assertIn(3, self.invMgr._equipped)
        self.assertNotIn(1, self.invMgr._inventory)

    def test_unequip(self):
        self.invMgr.addItem(self.ownerID, 1001, 1)
        self.invMgr.equip(self.ownerID, 1, 3)
        (item, success, msg) = self.invMgr.unequip(self.ownerID, 3)
        self.assertTrue(success)
        self.assertEqual(item.location, 'inventory')
        self.assertIn(item.slotIndex, self.invMgr._inventory)

    def test_transfer_to_warehouse(self):
        self.invMgr.addItem(self.ownerID, 1002, 10)
        self.assertTrue(self.invMgr.transferToWarehouse(self.ownerID, 1, 5))
        self.assertEqual(self.invMgr._warehouse[1]['quantity'], 5)

    def test_transfer_to_inventory(self):
        self.invMgr._warehouse[1] = self.pool.allocate(self.ownerID, 1002, 10, 'warehouse', 1)
        self.invMgr._warehouse[1].quantity = 10
        self.assertTrue(self.invMgr.transferToInventory(self.ownerID, 1, 5))
        self.assertEqual(self.invMgr._inventory[1]['quantity'], 5)

    def test_sort_inventory(self):
        self.invMgr.addItem(self.ownerID, 1002, 5)  # slot 1
        self.invMgr.addItem(self.ownerID, 1001, 1)  # slot 2
        self.invMgr.sortInventory(self.ownerID)
        # After sort by templateID: 1001 (Iron Sword) comes before 1002
        items = list(self.invMgr._inventory.items())
        self.assertEqual(items[0][1].templateID, 1001)
        self.assertEqual(items[1][1].templateID, 1002)

    def test_inventory_full(self):
        for i in range(40):
            self.invMgr.addItem(self.ownerID, 1002, 1)
        (_, success, msg) = self.invMgr.addItem(self.ownerID, 1002, 1)
        self.assertFalse(success)
        self.assertEqual(msg, 'Inventory full')


class TestItemDatabaseSync(TestBase):
    """Tests for ItemDatabaseSync.py"""

    def setUp(self):
        super().setUp()
        MockKBEngine._timer_callbacks = []
        MockKBEngine.DBManager._sql_log = []
        self.sync = __import__('item_system.ItemDatabaseSync').ItemDatabaseSync()

    def test_mark_dirty(self):
        item = MockKBEngine.createEntity('Item')
        item.isDirty = False
        self.sync.markDirty(item)
        self.assertTrue(item.isDirty)
        self.assertIn(item, self.sync._syncQueue)

    def test_mark_clean(self):
        item = MockKBEngine.createEntity('Item')
        item.isDirty = True
        self.sync.markClean(item)
        self.assertFalse(item.isDirty)

    def test_force_sync(self):
        item1 = MockKBEngine.createEntity('Item')
        item1.id = 9001; item1.templateID = 1002; item1.name = 'Health Potion'
        item1.quantity = 10; item1.maxStack = 20; item1.durability = 0
        item1.maxDurability = 0; item1.bound = False; item1.ownerID = 100
        item1.location = 'inventory'; item1.slotIndex = 1
        item1.attributes = '{}'; item1.createTime = 1700000000; item1.expireTime = 0
        item1.isDirty = True
        self.sync._syncQueue.append(item1)
        self.sync.forceSync()
        self.assertEqual(len(self.sync._syncQueue), 0)
        self.assertFalse(item1.isDirty)
        log = MockKBEngine.DBManager.get_sql_log()
        self.assertGreater(len(log), 0)


class TestItemCraftManager(TestBase):
    """Tests for ItemCraftManager.py"""

    def setUp(self):
        super().setUp()
        MockKBEngine._created_entities = []
        tmpl = __import__('item_system.ItemTemplate').ItemTemplateManager()
        tmpl.loadAllTemplates()
        self.pool = __import__('item_system.ItemPool').ItemPool()
        self.invMgr = __import__('item_system.InventoryManager').InventoryManager()
        self.craftMgr = __import__('item_system.ItemCraftManager').ItemCraftManager()
        self.craftMgr.loadRecipes()

    def test_craft_success(self):
        # Pre-populate inventory with material
        self.invMgr.addItem(self.ownerID, 2001, 10)  # Iron Ore (material for recipe 5001)
        MockKBEngine._current_time = 1700000000
        (success, msg) = self.craftMgr.craft(self.ownerID, 5001, self.invMgr)
        self.assertTrue(success)

    def test_craft_missing_material(self):
        # No material in inventory
        MockKBEngine._current_time = 1700000000
        (success, msg) = self.craftMgr.craft(self.ownerID, 5001, self.invMgr)
        self.assertFalse(success)

    def test_craft_cooldown(self):
        self.invMgr.addItem(self.ownerID, 2001, 20)
        MockKBEngine._current_time = 1700000000
        self.craftMgr.craft(self.ownerID, 5001, self.invMgr)
        # Still within cooldown (30s)
        MockKBEngine._current_time = 1700000010
        (success, msg) = self.craftMgr.craft(self.ownerID, 5001, self.invMgr)
        self.assertFalse(success)


class TestItemTradeManager(TestBase):
    """Tests for ItemTradeManager.py"""

    def setUp(self):
        super().setUp()
        self.tradeMgr = __import__('item_system.ItemTradeManager').ItemTradeManager()

    def test_create_trade(self):
        tradeID = self.tradeMgr.createTrade(100, 200)
        trade = self.tradeMgr._trades[tradeID]
        self.assertEqual(trade['from'], 100)
        self.assertEqual(trade['to'], 200)
        self.assertEqual(trade['status'], 'pending')

    def test_add_bound_item_rejected(self):
        tradeID = self.tradeMgr.createTrade(100, 200)
        item = MockKBEngine.createEntity('Item')
        item.id = 9003; item.bound = True
        self.assertFalse(self.tradeMgr.addItemToTrade(tradeID, 100, item))

    def test_add_unbound_item_accepted(self):
        tradeID = self.tradeMgr.createTrade(100, 200)
        item = MockKBEngine.createEntity('Item')
        item.id = 9004; item.bound = False
        self.assertTrue(self.tradeMgr.addItemToTrade(tradeID, 100, item))

    def test_confirm_and_cancel(self):
        tradeID = self.tradeMgr.createTrade(100, 200)
        self.assertTrue(self.tradeMgr.confirmTrade(tradeID, 100))
        self.assertTrue(self.tradeMgr.cancelTrade(tradeID))
        trade = self.tradeMgr._trades[tradeID]
        self.assertEqual(trade['status'], 'cancelled')

    def test_execute_trade(self):
        tradeID = self.tradeMgr.createTrade(100, 200)
        itemA = MockKBEngine.createEntity('Item')
        itemA.id = 9005; itemA.bound = False; itemA.templateID = 1002; itemA.quantity = 5
        itemB = MockKBEngine.createEntity('Item')
        itemB.id = 9006; itemB.bound = False; itemB.templateID = 1001; itemB.quantity = 1
        self.tradeMgr.addItemToTrade(tradeID, 100, itemA)
        self.tradeMgr.addItemToTrade(tradeID, 200, itemB)
        self.tradeMgr.confirmTrade(tradeID, 100)
        self.tradeMgr.confirmTrade(tradeID, 200)

        fromMgr = __import__('item_system.InventoryManager').InventoryManager()
        toMgr = __import__('item_system.InventoryManager').InventoryManager()
        (success, msg) = self.tradeMgr.executeTrade(tradeID, fromMgr, toMgr)
        self.assertTrue(success)
        trade = self.tradeMgr._trades[tradeID]
        self.assertEqual(trade['status'], 'completed')


class TestItemMessageProtocol(TestBase):
    """Tests for ItemMessageProtocol.py"""

    def setUp(self):
        super().setUp()
        self.protocol = __import__('item_system.ItemMessageProtocol').ItemMessageProtocol

    def test_msg_opcodes(self):
        self.assertEqual(self.protocol.MSG_INVENTORY_SYNC, 1000)
        self.assertEqual(self.protocol.MSG_USE_ITEM, 1010)
        self.assertEqual(self.protocol.MSG_BATCH_USE, 1023)

    def test_build_inventory_sync_message(self):
        tmpl = __import__('item_system.ItemTemplate').ItemTemplateManager()
        tmpl.loadAllTemplates()
        pool = __import__('item_system.ItemPool').ItemPool()
        invMgr = __import__('item_system.InventoryManager').InventoryManager()
        invMgr.addItem(self.ownerID, 1002, 10)
        invMgr.addItem(self.ownerID, 1001, 1)

        syncData = self.protocol.buildInventorySyncMessage(invMgr)
        self.assertIsInstance(syncData, list)
        self.assertEqual(len(syncData), 2)
        # Verify structure
        for entry in syncData:
            self.assertIn('itemID', entry)
            self.assertIn('templateID', entry)
            self.assertIn('quantity', entry)
            self.assertIn('location', entry)

    def test_build_item_update_message(self):
        item = MockKBEngine.createEntity('Item')
        item.id = 9007; item.templateID = 1002; item.quantity = 5
        item.durability = 0; item.maxDurability = 0
        item.location = 'inventory'; item.slotIndex = 1

        updateData = self.protocol.buildItemUpdateMessage(item)
        self.assertEqual(updateData['itemID'], 9007)
        self.assertEqual(updateData['quantity'], 5)
        self.assertEqual(updateData['location'], 'inventory')


if __name__ == '__main__':
    unittest.main(verbosity=2)
