# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import time

class MockBookingService:
    def __init__(self): 
        self.locked_slots = {}

    def lock_slot(self, user_id, slot_id):
        if slot_id not in ['S1', 'S2']: 
            return {'is_success': False, 'message': 'Invalid slot'}
        if slot_id in self.locked_slots: 
            return {'is_success': False, 'message': 'Slot taken'}
        self.locked_slots[slot_id] = {'user': user_id, 'expires_at': datetime.now() + timedelta(minutes=10)}
        return {'is_success': True, 'message': 'Locked'}

    def get_slot_status(self, slot_id):
        if slot_id in self.locked_slots: 
            return 'PENDING_PAYMENT'
        return 'AVAILABLE'

    def expire_slots(self, current_time=None):
        current_time = current_time or datetime.now()
        expired = [k for k, v in self.locked_slots.items() if current_time > v['expires_at']]
        for k in expired: 
            del self.locked_slots[k]

    def cancel_booking(self, user_id, slot_id):
        if slot_id in self.locked_slots and self.locked_slots[slot_id]['user'] == user_id:
            del self.locked_slots[slot_id]
            return True
        return False


class MockPaymentService:
    def __init__(self):
        self.processed = set()
        self.orders = {'O1': {'total': 1000, 'paid': 0, 'status': 'PENDING'}}

    def calculate_deposit(self, total, rate): 
        return total * rate

    def process_webhook(self, payload, signature, valid_signature):
        start = time.time()
        if signature != valid_signature: 
            return {'status_code': 403, 'message': 'Invalid Signature'}
        if 'amount' not in payload or 'order_id' not in payload: 
            return {'status_code': 400, 'message': 'Missing amount'}
        order_id, tx_id = payload['order_id'], payload.get('tx_id', 'TX_DEF')
        if tx_id in self.processed: 
            return {'status_code': 200, 'message': 'Idempotent - Already processed'}
        if payload['amount'] != self.orders.get(order_id, {}).get('total', -1): 
            return {'status_code': 400, 'message': 'Mismatch'}
        self.processed.add(tx_id)
        return {'status_code': 200, 'order_status': 'DEPOSITED', 'latency_ms': (time.time() - start)*1000}

    def calculate_refund(self, deposit, hours_before):
        if hours_before >= 24: 
            return deposit
        if hours_before >= 12: 
            return deposit * 0.5
        return 0


class MockPOS:
    def __init__(self, inventory):
        self.inventory = inventory
        self.cart = {}
        self.prices = {'water': 10000, 'bib': 5000}

    def add_item(self, item, qty):
        if qty <= 0 or item not in self.inventory or self.inventory[item] < qty: 
            return False
        self.inventory[item] -= qty
        self.cart[item] = self.cart.get(item, 0) + qty
        return True

    def remove_item(self, item, qty):
        if self.cart.get(item, 0) >= qty:
            self.cart[item] -= qty
            self.inventory[item] += qty
            return True
        return False

    def get_bill_total(self, overtime_fee=0): 
        if overtime_fee < 0: 
            return False
        return sum(self.prices.get(i, 0) * q for i, q in self.cart.items()) + overtime_fee