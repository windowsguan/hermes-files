# -*- coding: utf-8 -*-
"""
ItemCraftManager.py - Item Crafting & Combining System
Core responsibility: Handles item crafting, combining, and material consumption.
"""

import KBEngine
from common.KBEDebug import *
import json


class ItemCraftManager:
    """
    Crafting System:
    - Recipe definition: {resultTemplateID, materials: [(templateID, quantity), ...], cooldown}
    - Checks material availability in player inventory
    - Consumes materials and produces crafted item
    - Supports multi-step crafting chains

    Design principles:
    - Recipes loaded from DB (item_recipe table)
    - Material check is done against inventory without modifying until confirmed
    - Atomic operation: check → consume → produce
    """

    def __init__(self):
        self._recipes = {}
        self._cooldowns = {}  # ownerID -> (recipeID, endTime)

    def loadRecipes(self):
        """Load all crafting recipes from database."""
        result = KBEngine.DBManager.executeSQL("SELECT * FROM item_recipe")
        for row in result:
            rid = row['recipeID']
            self._recipes[rid] = {
                'name': row['name'],
                'resultTemplateID': row['resultTemplateID'],
                'resultQuantity': row.get('resultQuantity', 1),
                'materials': self._parseMaterials(row['materials']),
                'cooldown': row.get('cooldown', 0),
            }
        INFO_MSG(f'ItemCraftManager: Loaded {len(self._recipes)} recipes')

    def _parseMaterials(self, materialsJson):
        """Parse materials JSON string into list of (templateID, quantity)."""
        data = json.loads(materialsJson)
        return [(m['templateID'], m['quantity']) for m in data]

    def craft(self, ownerID, recipeID, inventoryManager):
        """
        Attempt to craft an item from a recipe.
        Returns (success, message).
        """
        recipe = self._recipes.get(recipeID)
        if not recipe:
            return (False, 'Unknown recipe')

        # Check cooldown
        if recipe['cooldown'] > 0:
            now = int(KBEngine.getCurrentTime())
            if ownerID in self._cooldowns:
                lastTime, lastRecipeID = self._cooldowns[ownerID]
                if lastRecipeID == recipeID and now - lastTime < recipe['cooldown']:
                    remaining = recipe['cooldown'] - (now - lastTime)
                    return (False, f'Crafting on cooldown ({remaining}s)')

        # Check materials
        invItems = inventoryManager.getInventory(ownerID)
        materialMap = {}
        for item in invItems:
            tid = item.templateID
            if tid not in materialMap:
                materialMap[tid] = 0
            materialMap[tid] += item.quantity

        for (templateID, requiredQty) in recipe['materials']:
            available = materialMap.get(templateID, 0)
            if available < requiredQty:
                return (False, f'Missing material: templateID={templateID}')

        # Consume materials (atomic operation)
        consumed = {}
        for (templateID, requiredQty) in recipe['materials']:
            for item in invItems:
                if item.templateID == templateID and item.quantity > 0:
                    consumeQty = min(requiredQty, item.quantity)
                    item.use(consumeQty)
                    if item.quantity == 0:
                        ItemPool.returnItem(item)
                    consumed[templateID] = consumed.get(templateID, 0) + consumeQty
                    requiredQty -= consumeQty
                    if requiredQty <= 0:
                        break
                    # Need to continue to next item of same templateID
                    continue

        # Produce result
        resultItem = ItemPool.allocate(
            ownerID, recipe['resultTemplateID'],
            recipe['resultQuantity'], 'inventory'
        )
        inventoryManager._inventory[resultItem.slotIndex] = resultItem

        # Set cooldown
        now = int(KBEngine.getCurrentTime())
        self._cooldowns[ownerID] = (now, recipeID)

        return (True, f'Crafted {recipe["name"]}')
