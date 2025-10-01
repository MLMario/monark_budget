import json
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import Settings
from services.api.app.exceptions import DatabaseConnectionError, DatabaseQueryError


class MongoDBClient:
    def __init__(self):
        """
        Initialize MongoDB client with connection error handling.

        Raises:
            DatabaseConnectionError: If connection to MongoDB fails
        """
        try:
            self.client = MongoClient(
                Settings.MONGO_URL.get_secret_value(),
                serverSelectionTimeoutMS=5000,  # 5 second timeout
            )
            # Test connection
            self.client.server_info()
            self.db = self.client[Settings.MONGO_DB]
            self.budgets_collection = self.db["budget"]
            self.transactions_collection = self.db["transactions"]
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            raise DatabaseConnectionError(f"Failed to connect to MongoDB: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseQueryError),
        reraise=True,
    )
    def export_budget_data(self, budget_data):
        """
        Export budget data to MongoDB with retry logic.

        Args:
            budget_data: Budget data to export

        Raises:
            DatabaseQueryError: On database operation failures after retries
        """
        try:
            # Full refresh - delete existing and insert new
            self.budgets_collection.delete_many({})
            self.budgets_collection.insert_many(budget_data)
        except OperationFailure as exc:
            raise DatabaseQueryError(f"Failed to export budget data: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseQueryError),
        reraise=True,
    )
    def export_transaction_data(self, transaction_data):
        """
        Export transaction data to MongoDB with retry logic.

        Args:
            transaction_data: Transaction data to export

        Raises:
            DatabaseQueryError: On database operation failures after retries
        """
        try:
            # Full refresh - delete existing and insert new
            self.transactions_collection.delete_many({})
            self.transactions_collection.insert_many(transaction_data)
        except OperationFailure as exc:
            raise DatabaseQueryError(f"Failed to export transaction data: {exc}") from exc

    def close_connection(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()


class AsyncMongoDBClient:

    def __init__(self):
        """
        Initialize async MongoDB client with connection error handling.

        Raises:
            DatabaseConnectionError: If connection to MongoDB fails
        """
        try:
            self.client = AsyncIOMotorClient(
                Settings.MONGO_URL.get_secret_value(),
                serverSelectionTimeoutMS=5000,  # 5 second timeout
            )
            self.db = self.client[Settings.MONGO_DB]
            self.budgets_collection = self.db["budget"]
            self.transactions_collection = self.db["transactions"]
        except Exception as exc:
            raise DatabaseConnectionError(f"Failed to initialize async MongoDB client: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseQueryError),
        reraise=True,
    )
    async def import_budget_data(self, filter_query: Optional[dict] = None):
        """
        Import budget data from MongoDB with retry logic.

        Args:
            filter_query: Optional MongoDB filter query

        Returns:
            JSON string of budget documents

        Raises:
            DatabaseQueryError: On database operation failures after retries
        """
        try:
            if filter_query is None:
                filter_query = {}

            cursor = self.budgets_collection.find(
                filter_query, {"_id": 0}
            )  # Exclude MongoDB _id field
            documents = await cursor.to_list(length=None)  # Get all documents

            return json.dumps(documents, default=str)
        except OperationFailure as exc:
            raise DatabaseQueryError(f"Failed to import budget data: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseQueryError),
        reraise=True,
    )
    async def import_transaction_data(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ):
        """
        Import transaction data from MongoDB with retry logic.

        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            JSON string of transaction documents

        Raises:
            DatabaseQueryError: On database operation failures after retries
        """
        try:
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
        except OperationFailure as exc:
            raise DatabaseQueryError(f"Failed to import transaction data: {exc}") from exc

    def close_connection(self):
        """Close async MongoDB connection."""
        if self.client:
            self.client.close()
