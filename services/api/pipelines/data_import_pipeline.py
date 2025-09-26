from services.api.pipelines.import_functions import monark_import
from services.api.pipelines.data_parsing_functions import parse_budget_data, parse_transaction_data
from config import Settings
import json
import os
from datetime import datetime
import asyncio
from .mongo_client import MongoDBClient


class DataImportPipeline:
    
    def __init__(self):
        self.pw = Settings.MONARK_PW.get_secret_value()
        self.user = Settings.MONARK_USER
        self.budget_data = None
        self.transaction_data = None
        self.mongo_client = MongoDBClient()

        print("MONARK_USER:", Settings.MONARK_USER)
        print("MONARK_DD_ID:", Settings.MONARK_DD_ID)
        print("MONARK_PW is set:", bool(Settings.MONARK_PW))
        
        print("MONGO_DB:", Settings.MONGO_DB)
        print("MONGO_URL is set:", bool(Settings.MONGO_URL))

    
    async def run_pipeline(self):

        print("Initiating data import from MonarchMoney...")
        self.imports = await monark_import(self.pw, self.user)

        print("Parsing Budget and Transaction Data...")
        self.budget_data = parse_budget_data(self.imports['budget'])
        self.transaction_data = parse_transaction_data(self.imports['transactions'])

        print("Initiating Data Export to MongoDB...")
        self._export_mongo()

    def _export_mongo(self):
        """Save budget and transaction data to MongoDB"""

        budget_docs = json.loads(self.budget_data)
        transaction_docs = json.loads(self.transaction_data)

        print("Exporting Budget Data to MongoDB...")
        self.mongo_client.export_budget_data(budget_docs)

        print("Exporting Transaction Data to MongoDB...")
        self.mongo_client.export_transaction_data(transaction_docs) 

        print("Closing MongoDB connection...")
        self.mongo_client.close_connection()


if __name__ == "__main__":
    
    async def main():
        print("🚀 Starting Data Import Pipeline...")
        
        pipeline = DataImportPipeline()
        await pipeline.run_pipeline()

        print("✅ Data Pipeline completed successfully!")

    asyncio.run(main())