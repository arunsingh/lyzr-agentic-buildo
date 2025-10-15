from __future__ import annotations
import os
import json
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

app = FastAPI(title="Audit Service")

class DecisionRecordIn(BaseModel):
    correlation_id: str
    workflow_id: str
    node_id: str
    node_name: str
    node_kind: str
    allowed: bool
    policies_applied: list[str]
    input_snapshot: dict
    output_snapshot: dict
    model_info: dict
    tool_calls: list[dict]
    cost: dict
    latency_ms: float | None = None
    timestamp: Optional[datetime] = None

# In-memory storage for demo (replace with proper DB in production)
_records: list[DecisionRecordIn] = []

class ParquetExporter:
    def __init__(self):
        self.s3_bucket = os.getenv("AOB_S3_BUCKET")
        self.s3_prefix = os.getenv("AOB_S3_PREFIX", "audit/decisions")
        self.local_path = os.getenv("AOB_LOCAL_AUDIT_PATH", "/tmp/audit")
        
    async def export_batch(self, records: list[DecisionRecordIn], batch_id: str):
        """Export a batch of DecisionRecords to Parquet format"""
        if not records:
            return
            
        # Convert to DataFrame
        df_data = []
        for record in records:
            df_data.append({
                "correlation_id": record.correlation_id,
                "workflow_id": record.workflow_id,
                "node_id": record.node_id,
                "node_name": record.node_name,
                "node_kind": record.node_kind,
                "allowed": record.allowed,
                "policies_applied": json.dumps(record.policies_applied),
                "input_snapshot": json.dumps(record.input_snapshot),
                "output_snapshot": json.dumps(record.output_snapshot),
                "model_info": json.dumps(record.model_info),
                "tool_calls": json.dumps(record.tool_calls),
                "cost": json.dumps(record.cost),
                "latency_ms": record.latency_ms,
                "timestamp": record.timestamp or datetime.utcnow(),
                "batch_id": batch_id
            })
        
        df = pd.DataFrame(df_data)
        
        # Convert to PyArrow Table
        table = pa.Table.from_pandas(df)
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"decisions_{batch_id}_{timestamp}.parquet"
        
        if self.s3_bucket:
            # Export to S3 (placeholder - implement with boto3)
            await self._export_to_s3(table, filename)
        else:
            # Export locally
            await self._export_local(table, filename)
    
    async def _export_local(self, table: pa.Table, filename: str):
        """Export to local filesystem"""
        os.makedirs(self.local_path, exist_ok=True)
        filepath = os.path.join(self.local_path, filename)
        pq.write_table(table, filepath)
        print(f"Exported {len(table)} records to {filepath}")
    
    async def _export_to_s3(self, table: pa.Table, filename: str):
        """Export to S3 (placeholder implementation)"""
        # TODO: Implement with boto3
        print(f"Would export {len(table)} records to s3://{self.s3_bucket}/{self.s3_prefix}/{filename}")

exporter = ParquetExporter()

@app.post("/decisions")
async def ingest(record: DecisionRecordIn, background_tasks: BackgroundTasks):
    if not record.timestamp:
        record.timestamp = datetime.utcnow()
    
    _records.append(record)
    
    # Trigger background export if we have enough records
    if len(_records) >= 100:  # Export every 100 records
        batch_id = f"batch_{len(_records)}"
        background_tasks.add_task(exporter.export_batch, _records.copy(), batch_id)
        _records.clear()  # Clear after scheduling export
    
    return {"ok": True, "total_records": len(_records)}

@app.get("/decisions")
async def list_records():
    return {"count": len(_records), "items": [r.dict() for r in _records]}

@app.post("/export")
async def trigger_export(background_tasks: BackgroundTasks):
    """Manually trigger export of current records"""
    if not _records:
        return {"message": "No records to export"}
    
    batch_id = f"manual_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    background_tasks.add_task(exporter.export_batch, _records.copy(), batch_id)
    
    exported_count = len(_records)
    _records.clear()
    
    return {"message": f"Export triggered for {exported_count} records", "batch_id": batch_id}

@app.get("/health")
async def health():
    return {"status": "healthy", "records_in_memory": len(_records)}

