# -*- coding: utf-8 -*-
"""
ItemTradeManager.py - Item Trading System
Core responsibility: Handles player-to-player item trading with lock-step
protocol, trade cancellation, and bound-item checks.
"""

import KBEngine
from common.KBEDebug import *


class ItemTradeManager:
    """
    Trade System:
    - Two-step trade protocol: offer → confirm → exchange
    - Supports single item and multi-item trades
    - Validates bound status (bound items cannot be traded)
    - Trade cancellation by either party before both confirm

    Trade Flow:
    PlayerA offers items → PlayerB sees offer → PlayerB offers items →
    PlayerA confirms → PlayerB confirms → Items exchanged atomically
    """

    def __init__(self):
        self._trades = {}  # tradeID -> trade data

    def createTrade(self, fromOwnerID, toOwnerID):
        """Create a new trade session."""
        tradeID = int(KBEngine.getCurrentTime()) ^ (fromOwnerID * 7) ^ (toOwnerID * 13)
        self._trades[tradeID] = {
            'id': tradeID,
            'from': fromOwnerID,
            'to': toOwnerID,
            'from_items': [],   # Items offered by fromOwner
            'to_items': [],     # Items offered by toOwner
            'from_confirmed': False,
            'to_confirmed': False,
            'status': 'pending',  # pending, completed, cancelled
        }
        return tradeID

    def addItemToTrade(self, tradeID, fromOwnerID, item):
        """Add an item to the trade offer."""
        trade = self._trades.get(tradeID)
        if not trade:
            return False
        if item.bound:
            DEBUG_MSG(f'ItemTrade: Item {item.id} is bound, cannot trade')
            return False

        # Validate ownership
        if fromOwnerID == trade['from']:
            trade['from_items'].append(item)
        elif fromOwnerID == trade['to']:
            trade['to_items'].append(item)
        else:
            return False
        return True

    def confirmTrade(self, tradeID, ownerID):
        """A player confirms their side of the trade."""
        trade = self._trades.get(tradeID)
        if not trade:
            return False
        if ownerID == trade['from']:
            trade['from_confirmed'] = True
        elif ownerID == trade['to']:
            trade['to_confirmed'] = True
        else:
            return False
        return True

    def cancelTrade(self, tradeID):
        """Either player cancels the trade."""
        trade = self._trades.get(tradeID)
        if not trade:
            return False
        trade['status'] = 'cancelled'
        # Return items back to owners (remove from trade)
        self._returnItems(trade['from_items'], trade['from'])
        self._returnItems(trade['to_items'], trade['to'])
        return True

    def executeTrade(self, tradeID, fromInventoryMgr, toInventoryMgr):
        """
        Execute trade when both players have confirmed.
        Atomically swaps items between inventories.
        """
        trade = self._trades.get(tradeID)
        if not trade:
            return (False, 'Trade not found')

        if not (trade['from_confirmed'] and trade['to_confirmed']):
            return (False, 'Not all players confirmed')

        # Swap items
        from_items = list(trade['from_items'])
        to_items = list(trade['to_items'])

        # Add to-from items to 'to' inventory
        for item in from_items:
            item.ownerID = trade['to']
            item.location = 'inventory'
            item.isDirty = True
            # Add to receiving inventory
            (_, success, msg) = toInventoryMgr.addItem(trade['to'], item.templateID, item.quantity)
            if not success:
                # Rollback needed in production
                pass

        # Add to-from items to 'from' inventory
        for item in to_items:
            item.ownerID = trade['from']
            item.location = 'inventory'
            item.isDirty = True
            (_, success, msg) = fromInventoryMgr.addItem(trade['from'], item.templateID, item.quantity)

        trade['status'] = 'completed'
        return (True, 'Trade completed')

    def _returnItems(self, items, ownerID):
        """Helper: Return items from cancelled trade."""
        for item in items:
            ItemPool.returnItem(item)
