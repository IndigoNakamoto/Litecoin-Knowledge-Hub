from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from backend.data_models import DataSource, DataSourceUpdate # Import DataSourceUpdate
from datetime import datetime
from bson import ObjectId # For MongoDB _id handling
from pymongo import MongoClient # For direct MongoDB interaction
from pymongo.collection import Collection
import os

router = APIRouter()

def document_to_data_source(doc: dict) -> DataSource:
    """Converts a MongoDB document to a DataSource model."""
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"] # Explicitly remove _id to avoid validation issues
    return DataSource(**doc)

def get_mongo_client():
    """Returns a MongoDB client instance."""
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    return MongoClient(mongo_uri)

def get_database(client: MongoClient = Depends(get_mongo_client)):
    """Returns the MongoDB database instance."""
    db_name = os.getenv("MONGO_DB_NAME", "litecoin_rag_chat")
    return client[db_name]

def get_data_sources_collection(db: Collection = Depends(get_database)):
    """Returns the data_sources collection."""
    return db.data_sources

def get_litecoin_docs_collection(db: Collection = Depends(get_database)):
    """Returns the litecoin_docs collection."""
    return db.litecoin_docs

@router.post("/", response_model=DataSource, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    source: DataSource,
    data_sources_collection: Collection = Depends(get_data_sources_collection)
):
    """
    Creates a new data source record and triggers its ingestion.
    """
    source_dict = source.model_dump(exclude_unset=True) # No by_alias needed anymore
    source_dict["created_at"] = datetime.utcnow()
    source_dict["updated_at"] = datetime.utcnow()
    
    # Ensure URI is unique
    if data_sources_collection.find_one({"uri": source.uri}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data source with this URI already exists.")

    result = data_sources_collection.insert_one(source_dict)
    
    # Retrieve the inserted document to get the actual _id and return it as DataSource
    inserted_doc = data_sources_collection.find_one({"_id": result.inserted_id})
    
    # TODO: Trigger ingestion process here (e.g., call a background task or a dedicated ingestion service)
    # For now, we'll just update the status to 'ingesting'
    data_sources_collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"status": "ingesting"}}
    )
    inserted_doc["status"] = "ingesting" # Update status in the dict before converting

    return document_to_data_source(inserted_doc)

@router.get("/", response_model=List[DataSource])
async def get_all_data_sources(
    data_sources_collection: Collection = Depends(get_data_sources_collection)
):
    """
    Retrieves all data source records.
    """
    sources = []
    for source_doc in data_sources_collection.find():
        sources.append(document_to_data_source(source_doc))
    return sources

@router.get("/{source_id}", response_model=DataSource)
async def get_data_source(
    source_id: str,
    data_sources_collection: Collection = Depends(get_data_sources_collection)
):
    """
    Retrieves a single data source record by its ID.
    """
    if not ObjectId.is_valid(source_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source ID format.")
    
    source_doc = data_sources_collection.find_one({"_id": ObjectId(source_id)})
    if source_doc:
        return document_to_data_source(source_doc)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

@router.put("/{source_id}", response_model=DataSource)
async def update_data_source(
    source_id: str,
    source_update: DataSourceUpdate, # Change parameter name and type
    data_sources_collection: Collection = Depends(get_data_sources_collection),
    litecoin_docs_collection: Collection = Depends(get_litecoin_docs_collection)
):
    """
    Updates an existing data source record and triggers re-ingestion if content likely changed.
    """
    if not ObjectId.is_valid(source_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source ID format.")

    existing_source_doc = data_sources_collection.find_one({"_id": ObjectId(source_id)})
    if not existing_source_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    # Convert existing_source_doc to DataSource model to easily access fields
    existing_source = document_to_data_source(existing_source_doc)

    # Get only the fields that are actually provided in the update request
    update_data = source_update.model_dump(exclude_unset=True)
    print(f"DEBUG: Incoming source_update: {source_update}")
    print(f"DEBUG: Update data for MongoDB: {update_data}")
    update_data["updated_at"] = datetime.utcnow()

    # Check if URI changed, which implies content change and requires re-ingestion
    uri_changed = False
    if "uri" in update_data and update_data["uri"] != existing_source.uri: # Compare with existing_source.uri
        uri_changed = True
        # If URI changes, delete old embeddings first
        litecoin_docs_collection.delete_many({"source_uri": existing_source.uri}) # Use existing_source.uri
        update_data["status"] = "ingesting" # Set status to ingesting for new URI

    result = data_sources_collection.update_one(
        {"_id": ObjectId(source_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Data source not modified.")

    updated_source_doc = data_sources_collection.find_one({"_id": ObjectId(source_id)})
    
    return document_to_data_source(updated_source_doc)

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    source_id: str,
    data_sources_collection: Collection = Depends(get_data_sources_collection),
    litecoin_docs_collection: Collection = Depends(get_litecoin_docs_collection)
):
    """
    Deletes a data source record and all its associated document chunks from the vector store.
    """
    if not ObjectId.is_valid(source_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source ID format.")

    source_to_delete = data_sources_collection.find_one({"_id": ObjectId(source_id)})
    if not source_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    # Get the URI of the source to delete its associated embeddings
    source_uri = source_to_delete.get("uri")

    # Delete the data source record
    delete_result = data_sources_collection.delete_one({"_id": ObjectId(source_id)})

    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    # Delete all associated document chunks from the litecoin_docs collection
    # Assuming 'source_uri' is the metadata field that stores the URI of the original source
    if source_uri:
        litecoin_docs_collection.delete_many({"source_uri": source_uri})
        # TODO: Log the number of deleted documents from litecoin_docs_collection

    return {"message": "Data source and associated embeddings deleted successfully."}

@router.post("/", response_model=DataSource, status_code=status.HTTP_201_CREATED)
async def create_data_source(source: DataSource):
    """
    Creates a new data source record and triggers its ingestion.
    """
    source_dict = source.model_dump(by_alias=True, exclude_unset=True)
    source_dict["created_at"] = datetime.utcnow()
    source_dict["updated_at"] = datetime.utcnow()
    
    # Ensure URI is unique
    if data_sources_collection.find_one({"uri": source.uri}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data source with this URI already exists.")

    result = data_sources_collection.insert_one(source_dict)
    source.id = str(result.inserted_id)
    
    # TODO: Trigger ingestion process here (e.g., call a background task or a dedicated ingestion service)
    # For now, we'll just update the status to 'ingesting'
    data_sources_collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"status": "ingesting"}}
    )
    source.status = "ingesting"

    return source

@router.get("/", response_model=List[DataSource])
async def get_all_data_sources():
    """
    Retrieves all data source records.
    """
    sources = []
    for source in data_sources_collection.find():
        source["id"] = str(source["_id"])
        sources.append(DataSource(**source))
    return sources

@router.get("/{source_id}", response_model=DataSource)
async def get_data_source(source_id: str):
    """
    Retrieves a single data source record by its ID.
    """
    if not ObjectId.is_valid(source_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source ID format.")
    
    source = data_sources_collection.find_one({"_id": ObjectId(source_id)})
    if source:
        source["id"] = str(source["_id"])
        return DataSource(**source)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

@router.put("/{source_id}", response_model=DataSource)
async def update_data_source(source_id: str, source: DataSource):
    """
    Updates an existing data source record and triggers re-ingestion if content likely changed.
    """
    if not ObjectId.is_valid(source_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source ID format.")

    existing_source = data_sources_collection.find_one({"_id": ObjectId(source_id)})
    if not existing_source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    update_data = source.model_dump(by_alias=True, exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    # Check if URI changed, which implies content change and requires re-ingestion
    uri_changed = False
    if "uri" in update_data and update_data["uri"] != existing_source.get("uri"):
        uri_changed = True
        # If URI changes, delete old embeddings first
        litecoin_docs_collection.delete_many({"source_uri": existing_source.get("uri")})
        update_data["status"] = "ingesting" # Set status to ingesting for new URI

    result = data_sources_collection.update_one(
        {"_id": ObjectId(source_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Data source not modified.")

    updated_source = data_sources_collection.find_one({"_id": ObjectId(source_id)})
    updated_source["id"] = str(updated_source["_id"])
    
    # TODO: If uri_changed or a specific re-ingestion flag is set, trigger ingestion here.
    # For now, status is updated above.

    return DataSource(**updated_source)

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(source_id: str):
    """
    Deletes a data source record and all its associated document chunks from the vector store.
    """
    if not ObjectId.is_valid(source_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source ID format.")

    source_to_delete = data_sources_collection.find_one({"_id": ObjectId(source_id)})
    if not source_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    # Get the URI of the source to delete its associated embeddings
    source_uri = source_to_delete.get("uri")

    # Delete the data source record
    delete_result = data_sources_collection.delete_one({"_id": ObjectId(source_id)})

    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")

    # Delete all associated document chunks from the litecoin_docs collection
    # Assuming 'source_uri' is the metadata field that stores the URI of the original source
    if source_uri:
        litecoin_docs_collection.delete_many({"source_uri": source_uri})
        # TODO: Log the number of deleted documents from litecoin_docs_collection

    return {"message": "Data source and associated embeddings deleted successfully."}
