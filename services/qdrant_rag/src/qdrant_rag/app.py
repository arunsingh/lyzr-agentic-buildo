"""
Qdrant Vector Database Integration Service

High-performance vector database service for RAG capabilities with multimodal support.
"""

from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, SearchRequest, FilterSelector
)
from sentence_transformers import SentenceTransformer
import logging
import hashlib
import uuid

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Supported document types"""
    TEXT = "text"
    PDF = "pdf"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    CODE = "code"
    MARKDOWN = "markdown"
    JSON = "json"
    CSV = "csv"


class SearchType(Enum):
    """Search types"""
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    MULTIMODAL = "multimodal"


@dataclass
class Document:
    """Document representation"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embeddings: Optional[List[float]] = None
    document_type: DocumentType = DocumentType.TEXT
    tenant_id: str = ""
    collection_name: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class SearchResult:
    """Search result representation"""
    document: Document
    score: float
    explanation: Optional[str] = None
    search_type: SearchType = SearchType.VECTOR


@dataclass
class CollectionConfig:
    """Collection configuration"""
    name: str
    tenant_id: str
    vector_size: int = 384
    distance_metric: Distance = Distance.COSINE
    shard_number: int = 1
    replication_factor: int = 1
    on_disk_payload: bool = True


class QdrantRAGService:
    """Qdrant-based RAG service with multimodal support"""
    
    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        
        # Embedding models
        self.text_encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.multimodal_encoder = SentenceTransformer('clip-ViT-B-32')
        
        # Collection cache
        self.collections: Dict[str, CollectionConfig] = {}
        
        # Initialize default collections
        asyncio.create_task(self._initialize_collections())
    
    async def _initialize_collections(self):
        """Initialize default collections"""
        try:
            # Create default tenant collections
            await self.create_collection("default", "documents")
            await self.create_collection("default", "multimodal")
            logger.info("Default collections initialized")
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
    
    async def create_collection(self, tenant_id: str, collection_name: str, 
                              config: Optional[CollectionConfig] = None) -> str:
        """Create a new collection for tenant"""
        collection_id = f"{tenant_id}_{collection_name}"
        
        if config is None:
            config = CollectionConfig(
                name=collection_name,
                tenant_id=tenant_id,
                vector_size=384,  # all-MiniLM-L6-v2 size
                distance_metric=Distance.COSINE
            )
        
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            existing_names = [col.name for col in collections.collections]
            
            if collection_id not in existing_names:
                self.client.create_collection(
                    collection_name=collection_id,
                    vectors_config=VectorParams(
                        size=config.vector_size,
                        distance=config.distance_metric
                    ),
                    shard_number=config.shard_number,
                    replication_factor=config.replication_factor,
                    on_disk_payload=config.on_disk_payload
                )
                
                logger.info(f"Created collection: {collection_id}")
            
            self.collections[collection_id] = config
            return collection_id
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_id}: {e}")
            raise
    
    async def ingest_document(self, document: Document) -> Document:
        """Ingest document with embeddings"""
        collection_id = f"{document.tenant_id}_{document.collection_name}"
        
        if collection_id not in self.collections:
            await self.create_collection(document.tenant_id, document.collection_name)
        
        try:
            # Generate embeddings based on document type
            if document.document_type in [DocumentType.TEXT, DocumentType.MARKDOWN, DocumentType.CODE]:
                embeddings = self.text_encoder.encode(document.content).tolist()
            elif document.document_type in [DocumentType.IMAGE]:
                # For images, we'd need to process the image first
                # This is a placeholder - would integrate with image processing
                embeddings = self.multimodal_encoder.encode([document.content]).tolist()[0]
            else:
                embeddings = self.text_encoder.encode(document.content).tolist()
            
            document.embeddings = embeddings
            
            # Prepare metadata
            payload = {
                "content": document.content,
                "metadata": document.metadata,
                "document_type": document.document_type.value,
                "tenant_id": document.tenant_id,
                "collection_name": document.collection_name,
                "created_at": document.created_at or str(time.time()),
                "updated_at": str(time.time())
            }
            
            # Create point
            point = PointStruct(
                id=document.id,
                vector=embeddings,
                payload=payload
            )
            
            # Upsert to Qdrant
            self.client.upsert(
                collection_name=collection_id,
                points=[point]
            )
            
            logger.info(f"Ingested document {document.id} into {collection_id}")
            return document
            
        except Exception as e:
            logger.error(f"Failed to ingest document {document.id}: {e}")
            raise
    
    async def search(self, tenant_id: str, collection_name: str, query: str,
                    search_type: SearchType = SearchType.VECTOR,
                    limit: int = 10, filters: Optional[Dict] = None,
                    score_threshold: float = 0.0) -> List[SearchResult]:
        """Search documents in collection"""
        collection_id = f"{tenant_id}_{collection_name}"
        
        if collection_id not in self.collections:
            raise ValueError(f"Collection {collection_id} not found")
        
        try:
            if search_type == SearchType.VECTOR:
                return await self._vector_search(collection_id, query, limit, filters, score_threshold)
            elif search_type == SearchType.KEYWORD:
                return await self._keyword_search(collection_id, query, limit, filters)
            elif search_type == SearchType.HYBRID:
                return await self._hybrid_search(collection_id, query, limit, filters, score_threshold)
            else:
                raise ValueError(f"Unsupported search type: {search_type}")
                
        except Exception as e:
            logger.error(f"Search failed for {collection_id}: {e}")
            raise
    
    async def _vector_search(self, collection_id: str, query: str, limit: int,
                           filters: Optional[Dict], score_threshold: float) -> List[SearchResult]:
        """Vector similarity search"""
        # Generate query embeddings
        query_embeddings = self.text_encoder.encode(query).tolist()
        
        # Build filter
        qdrant_filter = None
        if filters:
            qdrant_filter = self._build_qdrant_filter(filters)
        
        # Search in Qdrant
        search_results = self.client.search(
            collection_name=collection_id,
            query_vector=query_embeddings,
            limit=limit,
            query_filter=qdrant_filter,
            score_threshold=score_threshold,
            with_payload=True
        )
        
        results = []
        for result in search_results:
            document = Document(
                id=result.id,
                content=result.payload["content"],
                metadata=result.payload["metadata"],
                document_type=DocumentType(result.payload["document_type"]),
                tenant_id=result.payload["tenant_id"],
                collection_name=result.payload["collection_name"],
                created_at=result.payload.get("created_at"),
                updated_at=result.payload.get("updated_at")
            )
            
            results.append(SearchResult(
                document=document,
                score=result.score,
                search_type=SearchType.VECTOR
            ))
        
        return results
    
    async def _keyword_search(self, collection_id: str, query: str, limit: int,
                            filters: Optional[Dict]) -> List[SearchResult]:
        """Keyword search (placeholder - would integrate with Elasticsearch)"""
        # This is a placeholder implementation
        # In production, this would integrate with Elasticsearch or Postgres full-text search
        logger.warning("Keyword search not implemented - using vector search fallback")
        return await self._vector_search(collection_id, query, limit, filters, 0.0)
    
    async def _hybrid_search(self, collection_id: str, query: str, limit: int,
                           filters: Optional[Dict], score_threshold: float,
                           vector_weight: float = 0.7, keyword_weight: float = 0.3) -> List[SearchResult]:
        """Hybrid vector + keyword search"""
        # Get vector results
        vector_results = await self._vector_search(collection_id, query, limit * 2, filters, score_threshold)
        
        # Get keyword results (placeholder)
        keyword_results = await self._keyword_search(collection_id, query, limit * 2, filters)
        
        # Combine and rerank results
        combined_results = self._combine_search_results(
            vector_results, keyword_results, vector_weight, keyword_weight
        )
        
        return combined_results[:limit]
    
    def _combine_search_results(self, vector_results: List[SearchResult],
                               keyword_results: List[SearchResult],
                               vector_weight: float, keyword_weight: float) -> List[SearchResult]:
        """Combine and rerank search results"""
        combined = {}
        
        # Add vector results
        for result in vector_results:
            doc_id = result.document.id
            combined[doc_id] = result
            combined[doc_id].score *= vector_weight
        
        # Add keyword results
        for result in keyword_results:
            doc_id = result.document.id
            if doc_id in combined:
                combined[doc_id].score += result.score * keyword_weight
            else:
                combined[doc_id] = result
                combined[doc_id].score *= keyword_weight
        
        # Sort by combined score
        return sorted(combined.values(), key=lambda x: x.score, reverse=True)
    
    def _build_qdrant_filter(self, filters: Dict) -> Filter:
        """Build Qdrant filter from filters dict"""
        conditions = []
        
        for key, value in filters.items():
            if isinstance(value, list):
                # Handle list values (e.g., document_type in ["text", "pdf"])
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            else:
                # Handle single values
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
        
        return Filter(must=conditions)
    
    async def get_collection_stats(self, tenant_id: str, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""
        collection_id = f"{tenant_id}_{collection_name}"
        
        try:
            info = self.client.get_collection(collection_id)
            
            return {
                "collection_id": collection_id,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "optimizer_status": info.optimizer_status,
                "payload_schema": info.payload_schema
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats for {collection_id}: {e}")
            raise
    
    async def delete_document(self, tenant_id: str, collection_name: str, document_id: str) -> bool:
        """Delete document from collection"""
        collection_id = f"{tenant_id}_{collection_name}"
        
        try:
            self.client.delete(
                collection_name=collection_id,
                points_selector=[document_id]
            )
            
            logger.info(f"Deleted document {document_id} from {collection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    async def update_document(self, document: Document) -> Document:
        """Update document in collection"""
        # Update is same as upsert in Qdrant
        return await self.ingest_document(document)
    
    async def list_collections(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List collections, optionally filtered by tenant"""
        try:
            collections = self.client.get_collections()
            
            result = []
            for collection in collections.collections:
                collection_info = {
                    "name": collection.name,
                    "tenant_id": "",
                    "collection_name": "",
                    "status": "active"
                }
                
                # Parse tenant_id and collection_name from collection name
                if "_" in collection.name:
                    parts = collection.name.split("_", 1)
                    collection_info["tenant_id"] = parts[0]
                    collection_info["collection_name"] = parts[1]
                
                # Filter by tenant if specified
                if tenant_id is None or collection_info["tenant_id"] == tenant_id:
                    result.append(collection_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for Qdrant service"""
        try:
            # Check if Qdrant is accessible
            collections = self.client.get_collections()
            
            return {
                "status": "healthy",
                "qdrant_host": self.qdrant_host,
                "qdrant_port": self.qdrant_port,
                "collections_count": len(collections.collections),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }


# Global instance
qdrant_rag_service = QdrantRAGService()


# FastAPI integration
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Qdrant RAG Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DocumentIn(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}
    document_type: str = "text"
    tenant_id: str = "default"
    collection_name: str = "documents"


class SearchRequest(BaseModel):
    query: str
    search_type: str = "vector"
    limit: int = 10
    filters: Optional[Dict] = None
    score_threshold: float = 0.0


@app.post("/collections/{tenant_id}/{collection_name}")
async def create_collection_endpoint(tenant_id: str, collection_name: str):
    """Create new collection for tenant"""
    try:
        collection_id = await qdrant_rag_service.create_collection(tenant_id, collection_name)
        return {"collection_id": collection_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/{tenant_id}/{collection_name}")
async def ingest_document_endpoint(tenant_id: str, collection_name: str, document: DocumentIn):
    """Ingest document into collection"""
    try:
        doc = Document(
            id=str(uuid.uuid4()),
            content=document.content,
            metadata=document.metadata,
            document_type=DocumentType(document.document_type),
            tenant_id=tenant_id,
            collection_name=collection_name
        )
        
        result = await qdrant_rag_service.ingest_document(doc)
        return {"document_id": result.id, "status": "ingested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/{tenant_id}/{collection_name}")
async def search_documents_endpoint(
    tenant_id: str,
    collection_name: str,
    query: str,
    search_type: str = "vector",
    limit: int = 10,
    filters: Optional[Dict] = None,
    score_threshold: float = 0.0
):
    """Search documents in collection"""
    try:
        results = await qdrant_rag_service.search(
            tenant_id, collection_name, query,
            SearchType(search_type), limit, filters, score_threshold
        )
        
        return {
            "results": [
                {
                    "document": {
                        "id": r.document.id,
                        "content": r.document.content,
                        "metadata": r.document.metadata,
                        "document_type": r.document.document_type.value
                    },
                    "score": r.score,
                    "search_type": r.search_type.value
                }
                for r in results
            ],
            "query": query,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{tenant_id}/{collection_name}/stats")
async def get_collection_stats_endpoint(tenant_id: str, collection_name: str):
    """Get collection statistics"""
    try:
        stats = await qdrant_rag_service.get_collection_stats(tenant_id, collection_name)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{tenant_id}/{collection_name}/{document_id}")
async def delete_document_endpoint(tenant_id: str, collection_name: str, document_id: str):
    """Delete document from collection"""
    try:
        success = await qdrant_rag_service.delete_document(tenant_id, collection_name, document_id)
        return {"status": "deleted" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections")
async def list_collections_endpoint(tenant_id: Optional[str] = None):
    """List collections"""
    try:
        collections = await qdrant_rag_service.list_collections(tenant_id)
        return {"collections": collections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check_endpoint():
    """Health check endpoint"""
    return await qdrant_rag_service.health_check()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
