from pymongo import MongoClient
from config import Settings


class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(Settings.MONGO_URL)
        self.db = self.client[Settings.MONGO_DB]
        self.budgets_collection = self.db['budget']
        self.transactions_collection = self.db['transactions']
    
    def export_budget_data(self, budget_data):
        # Full refresh - delete existing and insert new
        self.budgets_collection.delete_many({})
        self.budgets_collection.insert_many(budget_data)
    
    def export_transaction_data(self, transaction_data):
        # Full refresh - delete existing and insert new
        self.transactions_collection.delete_many({})
        self.transactions_collection.insert_many(transaction_data)
    
    def close_connection(self):
        self.client.close()
