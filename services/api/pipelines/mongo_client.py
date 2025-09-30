import json
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from config import Settings


class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(Settings.MONGO_URL.get_secret_value())
        self.db = self.client[Settings.MONGO_DB]
        self.budgets_collection = self.db["budget"]
        self.transactions_collection = self.db["transactions"]

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


class AsyncMongoDBClient:

    def __init__(self):
        self.client = AsyncIOMotorClient(Settings.MONGO_URL.get_secret_value())
        self.db = self.client[Settings.MONGO_DB]
        self.budgets_collection = self.db["budget"]
        self.transactions_collection = self.db["transactions"]

    async def import_budget_data(self, filter_query: Optional[dict] = None):

        if filter_query is None:
            filter_query = {}

        cursor = self.budgets_collection.find(
            filter_query, {"_id": 0}
        )  # Exclude MongoDB _id field
        documents = await cursor.to_list(length=None)  # Get all documents

        return json.dumps(documents, default=str)

    async def import_transaction_data(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ):

        filter_query = {}

        # Build date filter if dates are provided
        if start_date or end_date:
            date_filter = {}

            if start_date:
                date_filter["$gte"] = f"{start_date}T00:00:00.000Z"

            if end_date:
                date_filter["$lte"] = f"{end_date}T23:59:59.999Z"

            filter_query["createdAt"] = date_filter

        cursor = self.transactions_collection.find(
            filter_query, {"_id": 0}
        )  # Exclude MongoDB _id field
        documents = await cursor.to_list(length=None)  # Get all documents

        return json.dumps(documents, default=str)

    def close_connection(self):
        self.client.close()
