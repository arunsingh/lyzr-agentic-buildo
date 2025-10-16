import React, { useState, useEffect, useCallback } from 'react';
import { AOBClient, WorkflowEvent, DecisionRecord } from '@aob/sdk';

interface SessionViewerProps {
  correlationId: string;
  client: AOBClient;
}

interface EventTimelineProps {
  events: WorkflowEvent[];
}

const EventTimeline: React.FC<EventTimelineProps> = ({ events }) => {
  const getEventIcon = (type: string) => {
    switch (type) {
      case 'task.completed':
        return '📋';
      case 'agent.completed':
        return '🤖';
      case 'human.approved':
        return '✅';
      case 'human.rejected':
        return '❌';
      case 'workflow.completed':
        return '🎉';
      case 'workflow.failed':
        return '💥';
      default:
        return '📝';
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case 'task.completed':
        return 'bg-gray-100 border-gray-300';
      case 'agent.completed':
        return 'bg-blue-100 border-blue-300';
      case 'human.approved':
        return 'bg-green-100 border-green-300';
      case 'human.rejected':
        return 'bg-red-100 border-red-300';
      case 'workflow.completed':
        return 'bg-green-100 border-green-300';
      case 'workflow.failed':
        return 'bg-red-100 border-red-300';
      default:
        return 'bg-gray-100 border-gray-300';
    }
  };

  return (
    <div className="space-y-4">
      {events.map((event, index) => (
        <div
          key={`${event.type}-${event.timestamp}-${index}`}
          className={`p-4 rounded-lg border-l-4 ${getEventColor(event.type)}`}
        >
          <div className="flex items-start space-x-3">
            <div className="text-2xl">{getEventIcon(event.type)}</div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h4 className="text-lg font-semibold capitalize">
                  {event.type.replace('.', ' ')}
                </h4>
                <span className="text-sm text-gray-500">
                  {new Date(event.timestamp * 1000).toLocaleTimeString()}
                </span>
              </div>
              {event.nodeId && (
                <p className="text-sm text-gray-600 mt-1">
                  Node: {event.nodeId}
                </p>
              )}
              {event.payload && Object.keys(event.payload).length > 0 && (
                <details className="mt-2">
                  <summary className="text-sm text-gray-600 cursor-pointer">
                    View Details
                  </summary>
                  <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-auto">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

interface AuditTrailProps {
  records: DecisionRecord[];
}

const AuditTrail: React.FC<AuditTrailProps> = ({ records }) => {
  return (
    <div className="space-y-4">
      {records.map((record, index) => (
        <div
          key={`${record.correlationId}-${record.nodeId}-${index}`}
          className={`p-4 rounded-lg border ${
            record.allowed ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <span className="text-lg">
                  {record.allowed ? '✅' : '❌'}
                </span>
                <h4 className="text-lg font-semibold">{record.nodeName}</h4>
                <span className="text-sm text-gray-500">({record.nodeKind})</span>
              </div>
              <p className="text-sm text-gray-600 mt-1">
                Policies: {record.policiesApplied.join(', ')}
              </p>
              {record.latencyMs && (
                <p className="text-sm text-gray-500">
                  Latency: {record.latencyMs.toFixed(2)}ms
                </p>
              )}
              {record.cost && record.cost.cost_usd > 0 && (
                <p className="text-sm text-gray-500">
                  Cost: ${record.cost.cost_usd.toFixed(4)}
                </p>
              )}
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500">
                {record.timestamp && new Date(record.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
          
          {record.modelInfo && Object.keys(record.modelInfo).length > 0 && (
            <details className="mt-2">
              <summary className="text-sm text-gray-600 cursor-pointer">
                Model Info
              </summary>
              <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-auto">
                {JSON.stringify(record.modelInfo, null, 2)}
              </pre>
            </details>
          )}
          
          {record.toolCalls && record.toolCalls.length > 0 && (
            <details className="mt-2">
              <summary className="text-sm text-gray-600 cursor-pointer">
                Tool Calls ({record.toolCalls.length})
              </summary>
              <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-auto">
                {JSON.stringify(record.toolCalls, null, 2)}
              </pre>
            </details>
          )}
        </div>
      ))}
    </div>
  );
};

export const SessionViewer: React.FC<SessionViewerProps> = ({
  correlationId,
  client,
}) => {
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [auditRecords, setAuditRecords] = useState<DecisionRecord[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeTab, setActiveTab] = useState<'events' | 'audit'>('events');
  const [error, setError] = useState<string | null>(null);

  const loadInitialData = useCallback(async () => {
    try {
      const [eventsData, auditData] = await Promise.all([
        client.getWorkflowEvents(correlationId),
        client.getAuditRecords(correlationId),
      ]);
      setEvents(eventsData);
      setAuditRecords(auditData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    }
  }, [client, correlationId]);

  const startStreaming = useCallback(async () => {
    setIsStreaming(true);
    setError(null);

    try {
      for await (const event of client.streamWorkflowEvents(correlationId)) {
        setEvents((prev) => [...prev, event]);
        
        // Refresh audit records periodically
        if (event.type.includes('completed') || event.type.includes('approved')) {
          const auditData = await client.getAuditRecords(correlationId);
          setAuditRecords(auditData);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Streaming failed');
    } finally {
      setIsStreaming(false);
    }
  }, [client, correlationId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const handleRefresh = useCallback(() => {
    loadInitialData();
  }, [loadInitialData]);

  const handleCreateSnapshot = useCallback(async () => {
    try {
      await client.createSnapshot(correlationId);
      alert('Snapshot created successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create snapshot');
    }
  }, [client, correlationId]);

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <h3 className="text-lg font-semibold text-red-800">Error</h3>
        <p className="text-red-600">{error}</p>
        <button
          onClick={handleRefresh}
          className="mt-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-gray-100 p-4 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Session: {correlationId}</h2>
            <p className="text-sm text-gray-600">
              {events.length} events, {auditRecords.length} audit records
            </p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
            >
              Refresh
            </button>
            <button
              onClick={handleCreateSnapshot}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Create Snapshot
            </button>
            <button
              onClick={startStreaming}
              disabled={isStreaming}
              className={`px-4 py-2 rounded ${
                isStreaming
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-green-500 hover:bg-green-600'
              } text-white`}
            >
              {isStreaming ? 'Streaming...' : 'Start Streaming'}
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-gray-50 border-b">
        <div className="flex">
          <button
            onClick={() => setActiveTab('events')}
            className={`px-4 py-2 ${
              activeTab === 'events'
                ? 'bg-white border-b-2 border-blue-500'
                : 'hover:bg-gray-100'
            }`}
          >
            Events Timeline
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-4 py-2 ${
              activeTab === 'audit'
                ? 'bg-white border-b-2 border-blue-500'
                : 'hover:bg-gray-100'
            }`}
          >
            Audit Trail
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'events' && <EventTimeline events={events} />}
        {activeTab === 'audit' && <AuditTrail records={auditRecords} />}
      </div>
    </div>
  );
};

export default SessionViewer;
