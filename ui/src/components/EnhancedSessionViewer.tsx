import React, { useState, useEffect, useCallback } from 'react';
import { Timeline, Card, Badge, Button, Tabs, Alert, Progress, Tooltip } from 'antd';
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  ReloadOutlined, 
  EyeOutlined,
  BugOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import './EnhancedSessionViewer.css';

interface TraceSpan {
  spanId: string;
  traceId: string;
  parentSpanId?: string;
  operationName: string;
  startTime: number;
  duration: number;
  tags: Record<string, any>;
  logs: Array<{
    timestamp: number;
    fields: Record<string, any>;
  }>;
  status: 'success' | 'error' | 'warning';
  serviceName: string;
}

interface WorkflowEvent {
  id: string;
  timestamp: string;
  type: string;
  nodeId: string;
  nodeName: string;
  status: 'pending' | 'running' | 'completed' | 'error' | 'skipped';
  details: string;
  duration?: number;
  traceId?: string;
  spanId?: string;
  metadata: Record<string, any>;
}

interface DecisionRecord {
  correlationId: string;
  workflowId: string;
  nodeId: string;
  nodeName: string;
  nodeKind: string;
  allowed: boolean;
  policiesApplied: string[];
  inputSnapshot: Record<string, any>;
  outputSnapshot: Record<string, any>;
  modelInfo: Record<string, any>;
  toolCalls: Array<Record<string, any>>;
  cost: Record<string, any>;
  latencyMs: number;
  timestamp: string;
}

interface SessionViewerProps {
  sessionId: string;
  apiUrl: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const EnhancedSessionViewer: React.FC<SessionViewerProps> = ({
  sessionId,
  apiUrl,
  autoRefresh = true,
  refreshInterval = 2000,
}) => {
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [traces, setTraces] = useState<TraceSpan[]>([]);
  const [decisionRecords, setDecisionRecords] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('timeline');
  const [selectedEvent, setSelectedEvent] = useState<WorkflowEvent | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);

  // Fetch session data
  const fetchSessionData = useCallback(async () => {
    try {
      setLoading(true);
      const [eventsResponse, tracesResponse, decisionsResponse] = await Promise.all([
        fetch(`${apiUrl}/workflows/${sessionId}/events`),
        fetch(`${apiUrl}/workflows/${sessionId}/traces`),
        fetch(`${apiUrl}/workflows/${sessionId}/decisions`),
      ]);

      if (!eventsResponse.ok) throw new Error(`Events API error: ${eventsResponse.status}`);
      if (!tracesResponse.ok) throw new Error(`Traces API error: ${tracesResponse.status}`);
      if (!decisionsResponse.ok) throw new Error(`Decisions API error: ${decisionsResponse.status}`);

      const [eventsData, tracesData, decisionsData] = await Promise.all([
        eventsResponse.json(),
        tracesResponse.json(),
        decisionsResponse.json(),
      ]);

      setEvents(eventsData.events || []);
      setTraces(tracesData.spans || []);
      setDecisionRecords(decisionsData.decisions || []);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId, apiUrl]);

  // Auto-refresh effect
  useEffect(() => {
    fetchSessionData();
    
    if (autoRefresh) {
      const interval = setInterval(fetchSessionData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchSessionData, autoRefresh, refreshInterval]);

  // Playback simulation
  useEffect(() => {
    if (isPlaying && events.length > 0) {
      const interval = setInterval(() => {
        setEvents(prevEvents => {
          const nextEvent = prevEvents.find(e => e.status === 'pending');
          if (nextEvent) {
            return prevEvents.map(e => 
              e.id === nextEvent.id 
                ? { ...e, status: 'running' as const }
                : e
            );
          }
          return prevEvents;
        });
      }, 1000 / playbackSpeed);

      return () => clearInterval(interval);
    }
  }, [isPlaying, events.length, playbackSpeed]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'running':
        return <PlayCircleOutlined style={{ color: '#1890ff' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'skipped':
        return <PauseCircleOutlined style={{ color: '#8c8c8c' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#52c41a';
      case 'running': return '#1890ff';
      case 'error': return '#ff4d4f';
      case 'pending': return '#faad14';
      case 'skipped': return '#8c8c8c';
      default: return '#8c8c8c';
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const getProgressPercentage = () => {
    const completed = events.filter(e => e.status === 'completed').length;
    return events.length > 0 ? (completed / events.length) * 100 : 0;
  };

  const getTraceTree = () => {
    const spanMap = new Map<string, TraceSpan & { children: TraceSpan[] }>();
    
    // Create span map with children
    traces.forEach(span => {
      spanMap.set(span.spanId, { ...span, children: [] });
    });

    // Build tree structure
    const rootSpans: (TraceSpan & { children: TraceSpan[] })[] = [];
    traces.forEach(span => {
      const spanWithChildren = spanMap.get(span.spanId)!;
      if (span.parentSpanId && spanMap.has(span.parentSpanId)) {
        spanMap.get(span.parentSpanId)!.children.push(spanWithChildren);
      } else {
        rootSpans.push(spanWithChildren);
      }
    });

    return rootSpans;
  };

  const renderTimelineItem = (event: WorkflowEvent) => (
    <Timeline.Item
      key={event.id}
      dot={getStatusIcon(event.status)}
      color={getStatusColor(event.status)}
    >
      <Card
        size="small"
        className={`event-card ${event.status}`}
        onClick={() => setSelectedEvent(event)}
        hoverable
      >
        <div className="event-header">
          <div className="event-title">
            <Badge status={event.status as any} text={event.nodeName} />
            <span className="event-type">{event.type}</span>
          </div>
          <div className="event-meta">
            <span className="event-time">{new Date(event.timestamp).toLocaleTimeString()}</span>
            {event.duration && (
              <span className="event-duration">{formatDuration(event.duration)}</span>
            )}
          </div>
        </div>
        <div className="event-details">
          <p>{event.details}</p>
          {event.traceId && (
            <div className="trace-info">
              <Badge count={event.traceId.slice(-8)} style={{ backgroundColor: '#1890ff' }} />
            </div>
          )}
        </div>
      </Card>
    </Timeline.Item>
  );

  const renderTraceTree = (spans: (TraceSpan & { children: TraceSpan[] })[], level = 0) => (
    <div className="trace-tree">
      {spans.map(span => (
        <div key={span.spanId} className="trace-node" style={{ marginLeft: level * 20 }}>
          <div className="trace-header">
            <span className="trace-operation">{span.operationName}</span>
            <span className="trace-service">{span.serviceName}</span>
            <span className="trace-duration">{formatDuration(span.duration)}</span>
            <Badge 
              status={span.status === 'success' ? 'success' : 'error'} 
              text={span.status}
            />
          </div>
          <div className="trace-tags">
            {Object.entries(span.tags).map(([key, value]) => (
              <Badge key={key} count={`${key}: ${value}`} style={{ backgroundColor: '#f0f0f0', color: '#000' }} />
            ))}
          </div>
          {span.children.length > 0 && renderTraceTree(span.children, level + 1)}
        </div>
      ))}
    </div>
  );

  const renderDecisionRecords = () => (
    <div className="decision-records">
      {decisionRecords.map(record => (
        <Card key={record.correlationId} size="small" className="decision-card">
          <div className="decision-header">
            <span className="decision-node">{record.nodeName}</span>
            <Badge 
              status={record.allowed ? 'success' : 'error'} 
              text={record.allowed ? 'Allowed' : 'Denied'}
            />
            <span className="decision-latency">{formatDuration(record.latencyMs)}</span>
          </div>
          <div className="decision-policies">
            <strong>Policies:</strong>
            {record.policiesApplied.map(policy => (
              <Badge key={policy} count={policy} style={{ backgroundColor: '#1890ff' }} />
            ))}
          </div>
          <div className="decision-cost">
            <strong>Cost:</strong> {JSON.stringify(record.cost)}
          </div>
          {record.modelInfo && (
            <div className="decision-model">
              <strong>Model:</strong> {JSON.stringify(record.modelInfo)}
            </div>
          )}
        </Card>
      ))}
    </div>
  );

  if (loading) {
    return (
      <div className="session-viewer-loading">
        <Progress type="circle" percent={75} />
        <p>Loading session data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Error Loading Session"
        description={error}
        type="error"
        showIcon
        action={
          <Button size="small" onClick={fetchSessionData}>
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div className="enhanced-session-viewer">
      <div className="session-header">
        <div className="session-info">
          <h2>Session: {sessionId}</h2>
          <div className="session-stats">
            <Badge count={`${events.filter(e => e.status === 'completed').length}/${events.length} completed`} />
            <Badge count={`${traces.length} spans`} />
            <Badge count={`${decisionRecords.length} decisions`} />
          </div>
        </div>
        <div className="session-controls">
          <Button
            type={isPlaying ? 'default' : 'primary'}
            icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => setIsPlaying(!isPlaying)}
          >
            {isPlaying ? 'Pause' : 'Play'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchSessionData}>
            Refresh
          </Button>
          <Tooltip title="Auto-refresh">
            <Button
              type={autoRefresh ? 'primary' : 'default'}
              icon={<EyeOutlined />}
              onClick={() => {/* Toggle auto-refresh */}}
            />
          </Tooltip>
        </div>
      </div>

      <div className="session-progress">
        <Progress 
          percent={getProgressPercentage()} 
          status={getProgressPercentage() === 100 ? 'success' : 'active'}
          showInfo={false}
        />
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="Timeline" key="timeline">
          <Timeline mode="left">
            {events.map(renderTimelineItem)}
          </Timeline>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Distributed Traces" key="traces">
          <div className="traces-container">
            <h3>Trace Tree</h3>
            {renderTraceTree(getTraceTree())}
          </div>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Decision Records" key="decisions">
          <div className="decisions-container">
            <h3>Policy Decisions</h3>
            {renderDecisionRecords()}
          </div>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Debug" key="debug">
          <div className="debug-container">
            <h3>Debug Information</h3>
            <pre>{JSON.stringify({ events, traces, decisionRecords }, null, 2)}</pre>
          </div>
        </Tabs.TabPane>
      </Tabs>

      {selectedEvent && (
        <div className="event-details-modal">
          <Card title={`Event: ${selectedEvent.nodeName}`} extra={
            <Button onClick={() => setSelectedEvent(null)}>Close</Button>
          }>
            <div className="event-detail-content">
              <p><strong>Type:</strong> {selectedEvent.type}</p>
              <p><strong>Status:</strong> {selectedEvent.status}</p>
              <p><strong>Timestamp:</strong> {selectedEvent.timestamp}</p>
              {selectedEvent.duration && (
                <p><strong>Duration:</strong> {formatDuration(selectedEvent.duration)}</p>
              )}
              <p><strong>Details:</strong> {selectedEvent.details}</p>
              <div className="event-metadata">
                <strong>Metadata:</strong>
                <pre>{JSON.stringify(selectedEvent.metadata, null, 2)}</pre>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default EnhancedSessionViewer;
