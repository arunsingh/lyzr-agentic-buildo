"""
RAG Integration Service

Integrates RAG capabilities with the existing AOB platform, providing semantic search
and knowledge retrieval for agentic workflows.
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
from sentence_transformers import SentenceTransformer
import logging
import uuid

logger = logging.getLogger(__name__)


class RAGNodeType(Enum):
    """RAG node types for workflows"""
    RETRIEVE = "retrieve"
    GENERATE = "generate"
    RERANK = "rerank"
    SUMMARIZE = "summarize"
    QUESTION_ANSWER = "question_answer"


@dataclass
class RAGContext:
    """RAG context for workflow nodes"""
    query: str
    documents: List[Dict[str, Any]]
    max_documents: int = 5
    similarity_threshold: float = 0.7
    rerank: bool = True
    metadata_filters: Optional[Dict[str, Any]] = None


@dataclass
class RAGResult:
    """RAG operation result"""
    success: bool
    documents: List[Dict[str, Any]]
    query: str
    node_type: RAGNodeType
    latency_ms: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RAGIntegrationService:
    """RAG integration service for AOB platform"""
    
    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        
        # Embedding model
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Model gateway endpoint
        self.model_gateway_url = "http://localhost:8087"
        
    async def execute_rag_node(self, node_type: RAGNodeType, context: RAGContext, 
                              tenant_id: str = "default", collection_name: str = "documents") -> RAGResult:
        """Execute RAG operation for workflow node"""
        start_time = time.time()
        
        try:
            if node_type == RAGNodeType.RETRIEVE:
                result = await self._retrieve_documents(context, tenant_id, collection_name)
            elif node_type == RAGNodeType.GENERATE:
                result = await self._generate_with_context(context, tenant_id, collection_name)
            elif node_type == RAGNodeType.RERANK:
                result = await self._rerank_documents(context)
            elif node_type == RAGNodeType.SUMMARIZE:
                result = await self._summarize_documents(context)
            elif node_type == RAGNodeType.QUESTION_ANSWER:
                result = await self._question_answer(context, tenant_id, collection_name)
            else:
                raise ValueError(f"Unsupported RAG node type: {node_type}")
            
            latency_ms = (time.time() - start_time) * 1000
            
            return RAGResult(
                success=True,
                documents=result.get("documents", []),
                query=context.query,
                node_type=node_type,
                latency_ms=latency_ms,
                metadata=result.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"RAG operation failed for {node_type}: {e}")
            return RAGResult(
                success=False,
                documents=[],
                query=context.query,
                node_type=node_type,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def _retrieve_documents(self, context: RAGContext, tenant_id: str, 
                                 collection_name: str) -> Dict[str, Any]:
        """Retrieve relevant documents using semantic search"""
        collection_id = f"{tenant_id}_{collection_name}"
        
        # Generate query embeddings
        query_embeddings = self.encoder.encode(context.query).tolist()
        
        # Build filter
        qdrant_filter = None
        if context.metadata_filters:
            qdrant_filter = self._build_qdrant_filter(context.metadata_filters)
        
        # Search in Qdrant
        search_results = self.client.search(
            collection_name=collection_id,
            query_vector=query_embeddings,
            limit=context.max_documents,
            query_filter=qdrant_filter,
            score_threshold=context.similarity_threshold,
            with_payload=True
        )
        
        documents = []
        for result in search_results:
            documents.append({
                "id": result.id,
                "content": result.payload["content"],
                "metadata": result.payload["metadata"],
                "score": result.score,
                "document_type": result.payload.get("document_type", "text")
            })
        
        return {
            "documents": documents,
            "metadata": {
                "total_found": len(documents),
                "collection": collection_id,
                "similarity_threshold": context.similarity_threshold
            }
        }
    
    async def _generate_with_context(self, context: RAGContext, tenant_id: str, 
                                   collection_name: str) -> Dict[str, Any]:
        """Generate text using retrieved context"""
        # First retrieve documents
        retrieve_result = await self._retrieve_documents(context, tenant_id, collection_name)
        documents = retrieve_result["documents"]
        
        if not documents:
            return {
                "documents": [],
                "metadata": {"error": "No relevant documents found"}
            }
        
        # Prepare context for generation
        context_text = "\n\n".join([
            f"Document {i+1}:\n{doc['content']}" 
            for i, doc in enumerate(documents)
        ])
        
        # Generate prompt
        prompt = f"""Based on the following context, please provide a comprehensive response to: {context.query}

Context:
{context_text}

Response:"""
        
        # Call model gateway
        try:
            response = await self.http_client.post(
                f"{self.model_gateway_url}/infer",
                json={
                    "prompt": prompt,
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                model_result = response.json()
                generated_text = model_result["text"]
                
                return {
                    "documents": [{
                        "id": str(uuid.uuid4()),
                        "content": generated_text,
                        "metadata": {
                            "generated": True,
                            "source_documents": len(documents),
                            "model_used": model_result.get("model_used", "unknown")
                        },
                        "score": 1.0,
                        "document_type": "generated"
                    }],
                    "metadata": {
                        "source_documents": documents,
                        "generation_model": model_result.get("model_used"),
                        "tokens_used": model_result.get("tokens_used", 0)
                    }
                }
            else:
                raise Exception(f"Model gateway error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                "documents": [],
                "metadata": {"error": f"Generation failed: {str(e)}"}
            }
    
    async def _rerank_documents(self, context: RAGContext) -> Dict[str, Any]:
        """Rerank documents using cross-encoder"""
        if not context.documents:
            return {"documents": [], "metadata": {"error": "No documents to rerank"}}
        
        # Simple reranking based on content length and metadata
        # In production, this would use a cross-encoder model
        reranked_docs = sorted(
            context.documents,
            key=lambda x: (
                x.get("score", 0) * 0.7 +  # Original similarity score
                min(len(x.get("content", "")) / 1000, 1.0) * 0.3  # Content length bonus
            ),
            reverse=True
        )
        
        return {
            "documents": reranked_docs,
            "metadata": {
                "reranked": True,
                "original_count": len(context.documents),
                "reranked_count": len(reranked_docs)
            }
        }
    
    async def _summarize_documents(self, context: RAGContext) -> Dict[str, Any]:
        """Summarize retrieved documents"""
        if not context.documents:
            return {"documents": [], "metadata": {"error": "No documents to summarize"}}
        
        # Combine document content
        combined_content = "\n\n".join([
            f"Document {i+1}:\n{doc.get('content', '')}" 
            for i, doc in enumerate(context.documents)
        ])
        
        # Generate summary prompt
        prompt = f"""Please provide a concise summary of the following documents:

{combined_content}

Summary:"""
        
        # Call model gateway for summarization
        try:
            response = await self.http_client.post(
                f"{self.model_gateway_url}/infer",
                json={
                    "prompt": prompt,
                    "max_tokens": 500,
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                model_result = response.json()
                summary = model_result["text"]
                
                return {
                    "documents": [{
                        "id": str(uuid.uuid4()),
                        "content": summary,
                        "metadata": {
                            "summary": True,
                            "source_documents": len(context.documents),
                            "model_used": model_result.get("model_used", "unknown")
                        },
                        "score": 1.0,
                        "document_type": "summary"
                    }],
                    "metadata": {
                        "source_documents": context.documents,
                        "summary_model": model_result.get("model_used"),
                        "tokens_used": model_result.get("tokens_used", 0)
                    }
                }
            else:
                raise Exception(f"Model gateway error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return {
                "documents": [],
                "metadata": {"error": f"Summarization failed: {str(e)}"}
            }
    
    async def _question_answer(self, context: RAGContext, tenant_id: str, 
                             collection_name: str) -> Dict[str, Any]:
        """Answer questions using retrieved context"""
        # First retrieve relevant documents
        retrieve_result = await self._retrieve_documents(context, tenant_id, collection_name)
        documents = retrieve_result["documents"]
        
        if not documents:
            return {
                "documents": [],
                "metadata": {"error": "No relevant documents found for question"}
            }
        
        # Prepare context for Q&A
        context_text = "\n\n".join([
            f"Document {i+1}:\n{doc['content']}" 
            for i, doc in enumerate(documents)
        ])
        
        # Generate Q&A prompt
        prompt = f"""Based on the following context, please answer the question: {context.query}

Context:
{context_text}

Answer:"""
        
        # Call model gateway
        try:
            response = await self.http_client.post(
                f"{self.model_gateway_url}/infer",
                json={
                    "prompt": prompt,
                    "max_tokens": 800,
                    "temperature": 0.5
                }
            )
            
            if response.status_code == 200:
                model_result = response.json()
                answer = model_result["text"]
                
                return {
                    "documents": [{
                        "id": str(uuid.uuid4()),
                        "content": answer,
                        "metadata": {
                            "answer": True,
                            "question": context.query,
                            "source_documents": len(documents),
                            "model_used": model_result.get("model_used", "unknown")
                        },
                        "score": 1.0,
                        "document_type": "answer"
                    }],
                    "metadata": {
                        "question": context.query,
                        "source_documents": documents,
                        "answer_model": model_result.get("model_used"),
                        "tokens_used": model_result.get("tokens_used", 0)
                    }
                }
            else:
                raise Exception(f"Model gateway error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Q&A failed: {e}")
            return {
                "documents": [],
                "metadata": {"error": f"Q&A failed: {str(e)}"}
            }
    
    def _build_qdrant_filter(self, filters: Dict) -> Any:
        """Build Qdrant filter from filters dict"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        conditions = []
        
        for key, value in filters.items():
            if isinstance(value, list):
                # Handle list values
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
    
    async def ingest_workflow_documents(self, tenant_id: str, collection_name: str, 
                                      documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest documents for workflow use"""
        collection_id = f"{tenant_id}_{collection_name}"
        
        # Ensure collection exists
        try:
            collections = self.client.get_collections()
            existing_names = [col.name for col in collections.collections]
            
            if collection_id not in existing_names:
                from qdrant_client.models import VectorParams, Distance
                self.client.create_collection(
                    collection_name=collection_id,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 size
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            logger.error(f"Failed to create collection {collection_id}: {e}")
            raise
        
        # Ingest documents
        ingested_count = 0
        for doc in documents:
            try:
                # Generate embeddings
                embeddings = self.encoder.encode(doc["content"]).tolist()
                
                # Create point
                from qdrant_client.models import PointStruct
                point = PointStruct(
                    id=doc.get("id", str(uuid.uuid4())),
                    vector=embeddings,
                    payload={
                        "content": doc["content"],
                        "metadata": doc.get("metadata", {}),
                        "document_type": doc.get("document_type", "text"),
                        "tenant_id": tenant_id,
                        "collection_name": collection_name,
                        "created_at": str(time.time())
                    }
                )
                
                # Upsert to Qdrant
                self.client.upsert(
                    collection_name=collection_id,
                    points=[point]
                )
                
                ingested_count += 1
                
            except Exception as e:
                logger.error(f"Failed to ingest document {doc.get('id', 'unknown')}: {e}")
        
        return {
            "ingested_count": ingested_count,
            "total_count": len(documents),
            "collection_id": collection_id
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for RAG integration service"""
        try:
            # Check Qdrant connection
            collections = self.client.get_collections()
            
            # Check model gateway
            model_response = await self.http_client.get(f"{self.model_gateway_url}/health")
            model_healthy = model_response.status_code == 200
            
            return {
                "status": "healthy",
                "qdrant_connected": True,
                "qdrant_collections": len(collections.collections),
                "model_gateway_healthy": model_healthy,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"RAG integration health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }


# Global instance
rag_integration_service = RAGIntegrationService()


# FastAPI integration
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="RAG Integration Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RAGContextIn(BaseModel):
    query: str
    documents: List[Dict[str, Any]] = []
    max_documents: int = 5
    similarity_threshold: float = 0.7
    rerank: bool = True
    metadata_filters: Optional[Dict[str, Any]] = None


class DocumentIn(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}
    document_type: str = "text"


@app.post("/rag/{node_type}")
async def execute_rag_node_endpoint(
    node_type: str,
    context: RAGContextIn,
    tenant_id: str = "default",
    collection_name: str = "documents"
):
    """Execute RAG operation for workflow node"""
    try:
        rag_context = RAGContext(
            query=context.query,
            documents=context.documents,
            max_documents=context.max_documents,
            similarity_threshold=context.similarity_threshold,
            rerank=context.rerank,
            metadata_filters=context.metadata_filters
        )
        
        result = await rag_integration_service.execute_rag_node(
            RAGNodeType(node_type), rag_context, tenant_id, collection_name
        )
        
        return {
            "success": result.success,
            "documents": result.documents,
            "query": result.query,
            "node_type": result.node_type.value,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "metadata": result.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/{tenant_id}/{collection_name}/ingest")
async def ingest_documents_endpoint(
    tenant_id: str,
    collection_name: str,
    documents: List[DocumentIn]
):
    """Ingest documents for workflow use"""
    try:
        doc_list = [
            {
                "content": doc.content,
                "metadata": doc.metadata,
                "document_type": doc.document_type
            }
            for doc in documents
        ]
        
        result = await rag_integration_service.ingest_workflow_documents(
            tenant_id, collection_name, doc_list
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check_endpoint():
    """Health check endpoint"""
    return await rag_integration_service.health_check()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)
