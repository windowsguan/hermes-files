# -*- coding: utf-8 -*-
"""
ItemTemplate.py - Item Template Manager
Core responsibility: Load item configuration from database/cache, provide item template lookup.
Uses KBEngine's dbmgr for template queries and in-memory dict for caching.
"""

import KBEngine
from common.KBEDebug import *
import json

class ItemTemplateManager:
    """
    Manages item templates (static configuration).
    - Loads templates from MySQL via dbmgr
    - Caches templates in a dict keyed by templateID
    - Supports bulk load and single lookup
    """

    def __init__(self):
        self._templates = {}
        self._dirty = False

    def loadAllTemplates(self):
        """
        Load all item templates from database (item_template table).
        Called once at server startup.
        """
        DEBUG_MSG('ItemTemplateManager: Loading all item templates...')
        # Query: SELECT * FROM item_template
        result = KBEngine.DBManager.executeSQL("SELECT * FROM item_template")
        for row in result:
            tid = row['templateID']
            self._templates[tid] = {
                'name': row['name'],
                'type': row['type'],
                'maxStack': row.get('maxStack', 1),
                'maxDurability': row.get('maxDurability', 0),
                'bound': row.get('bound', False),
                'attributes': json.loads(row['attributes']) if row.get('attributes') else {},
            }
        INFO_MSG(f'ItemTemplateManager: Loaded {len(self._templates)} templates')
        self._dirty = False

    def getTemplate(self, templateID):
        """Get template by ID. Returns None if not found."""
        tmpl = self._templates.get(templateID)
        if tmpl is None:
            DEBUG_MSG(f'ItemTemplateManager: Template {templateID} not found in cache')
            # Try to load from DB
            row = KBEngine.DBManager.executeSQL(
                f"SELECT * FROM item_template WHERE templateID = {templateID}"
            )
            if row:
                if isinstance(row, list):
                    row = row[0]
                tmpl = {
                    'name': row['name'],
                    'type': row['type'],
                    'maxStack': row.get('maxStack', 1),
                    'maxDurability': row.get('maxDurability', 0),
                    'bound': row.get('bound', False),
                    'attributes': json.loads(row['attributes']) if row.get('attributes') else {},
                }
                self._templates[templateID] = tmpl
        return tmpl

    def addTemplate(self, templateID, data):
        self._templates[templateID] = data
        self._dirty = True

    def saveNewTemplates(self):
        """Save new/modified templates back to database."""
        if not self._dirty:
            return
        for tid, data in self._templates.items():
            KBEngine.DBManager.executeSQL(
                f"INSERT INTO item_template (templateID, name, type, maxStack, maxDurability, bound, attributes) "
                f"VALUES ({tid}, '{data['name']}', '{data['type']}', {data['maxStack']}, "
                f"{data['maxDurability']}, {data['bound']}, '{json.dumps(data['attributes'])}' "
                f"ON DUPLICATE KEY UPDATE name='{data['name']}'"
            )
        self._dirty = False


# Singleton instance
ItemTemplate = ItemTemplateManager()
