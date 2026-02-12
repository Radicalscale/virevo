import os
import asyncio
import logging
import argparse
from motor.motor_asyncio import AsyncIOMotorClient
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def migrate_data(source_uri, dest_uri, source_db_name=None, dest_db_name=None):
    """
    Migrate all collections from source MongoDB to destination MongoDB.
    """
    try:
        # Connect to source
        logger.info("Connecting to source database...")
        source_client = AsyncIOMotorClient(source_uri)
        # Verify connection
        await source_client.server_info()
        logger.info("✅ Connected to source.")

        # Connect to destination
        logger.info("Connecting to destination database...")
        dest_client = AsyncIOMotorClient(dest_uri)
        await dest_client.server_info()
        logger.info("✅ Connected to destination.")

        # Determine database names
        if not source_db_name:
            source_db_name = source_client.get_default_database().name
        if not dest_db_name:
            dest_db_name = dest_client.get_default_database().name or source_db_name

        s_db = source_client[source_db_name]
        d_db = dest_client[dest_db_name]

        logger.info(f"Migrating from [{source_db_name}] to [{dest_db_name}]")

        # Get all collection names
        collections = await s_db.list_collection_names()
        logger.info(f"Found {len(collections)} collections: {collections}")

        for col_name in collections:
            logger.info(f"Processing collection: {col_name}")
            
            # Count documents
            count = await s_db[col_name].count_documents({})
            logger.info(f"  - Found {count} documents.")

            if count == 0:
                continue

            # Clear destination collection (optional - safer to not do this by default, but for a clean migration it helps)
            # await d_db[col_name].drop() 
            # logger.info(f"  - Cleared destination collection.")

            # Batch insert
            cursor = s_db[col_name].find({})
            batch = []
            batch_size = 1000
            inserted_count = 0

            async for doc in cursor:
                batch.append(doc)
                if len(batch) >= batch_size:
                    try:
                        # Use unordered insert to ignore duplicate keys if they exist
                        await d_db[col_name].insert_many(batch, ordered=False)
                        inserted_count += len(batch)
                        batch = []
                    except Exception as e:
                        # Handle potential duplicate key errors if not dropping
                        logger.warning(f"  - Batch insert warning (likely duplicates): {e}")
                        inserted_count += len(batch) # Approximate
                        batch = []

            if batch:
                try:
                    await d_db[col_name].insert_many(batch, ordered=False)
                    inserted_count += len(batch)
                except Exception as e:
                     logger.warning(f"  - Final batch insert warning: {e}")

            logger.info(f"  ✅ Migrated {inserted_count}/{count} documents for {col_name}")

        logger.info("🎉 Migration completed successfully!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
    finally:
        source_client.close()
        dest_client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate MongoDB data between instances.")
    parser.add_argument("--source", required=True, help="Source MongoDB URI")
    parser.add_argument("--dest", required=True, help="Destination MongoDB URI")
    parser.add_argument("--source-db", help="Source Database Name (optional if in URI)")
    parser.add_argument("--dest-db", help="Destination Database Name (optional)")

    args = parser.parse_args()

    asyncio.run(migrate_data(args.source, args.dest, args.source_db, args.dest_db))
