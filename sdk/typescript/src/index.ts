/**
 * Agentic Orchestration Builder - TypeScript SDK
 * 
 * A comprehensive TypeScript SDK for the AOB platform with streaming, retries, and HITL helpers.
 */

export enum AuthMethod {
  OIDC = 'oidc',
  API_KEY = 'api_key'
}

export interface AuthConfig {
  method: AuthMethod;
  token?: string;
  apiKey?: string;
  tenant?: string;
}

export enum WorkflowStatus {
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  PAUSED = 'paused'
}

export interface WorkflowEvent {
  type: string;
  payload: Record<string, any>;
  timestamp: number;
  correlationId: string;
  nodeId?: string;
}

export interface DecisionRecord {
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
  toolCalls: Record<string, any>[];
  cost: Record<string, any>;
  latencyMs?: number;
  timestamp?: string;
}

export interface ServiceInfo {
  _links: Record<string, { href: string; method?: string }>;
}

export interface WorkflowStartRequest {
  workflowId: string;
  text?: string;
  approval?: boolean;
  [key: string]: any;
}

export interface WorkflowStartResponse {
  correlationId: string;
  _links: Record<string, { href: string; method?: string }>;
}

export interface WorkflowEventsResponse {
  count: number;
  items: WorkflowEvent[];
  _links: Record<string, { href: string }>;
}

export class AOBClient {
  private baseUrl: string;
  private auth: AuthConfig;
  private abortController?: AbortController;

  constructor(baseUrl: string = 'http://localhost:8000', auth?: AuthConfig) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.auth = auth || { method: AuthMethod.API_KEY, apiKey: 'demo:local-dev-key' };
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    if (this.auth.method === AuthMethod.OIDC && this.auth.token) {
      headers['Authorization'] = `Bearer ${this.auth.token}`;
    } else if (this.auth.method === AuthMethod.API_KEY && this.auth.apiKey) {
      headers['X-API-Key'] = this.auth.apiKey;
    }

    return headers;
  }

  async getServiceInfo(): Promise<ServiceInfo> {
    const response = await fetch(`${this.baseUrl}/`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async compileWorkflow(yamlContent: string): Promise<{ status: string; workflowId: string }> {
    const response = await fetch(`${this.baseUrl}/workflows/compile`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ yaml: yamlContent })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async startWorkflow(workflowId: string, params: Record<string, any> = {}): Promise<WorkflowStartResponse> {
    const payload = { workflowId, ...params };
    
    const response = await fetch(`${this.baseUrl}/workflows/start`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async resumeWorkflow(workflowId: string, approval: boolean = true): Promise<WorkflowStartResponse> {
    const response = await fetch(`${this.baseUrl}/workflows/resume`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ workflowId, approval })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async getWorkflowEvents(correlationId: string): Promise<WorkflowEvent[]> {
    const response = await fetch(`${this.baseUrl}/workflows/${correlationId}/events`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: WorkflowEventsResponse = await response.json();
    return data.items;
  }

  async *streamWorkflowEvents(
    correlationId: string, 
    pollInterval: number = 1000
  ): AsyncGenerator<WorkflowEvent, void, unknown> {
    const seenEvents = new Set<string>();

    while (true) {
      try {
        const events = await this.getWorkflowEvents(correlationId);

        for (const event of events) {
          const eventKey = `${event.type}:${event.timestamp}:${event.correlationId}`;
          if (!seenEvents.has(eventKey)) {
            seenEvents.add(eventKey);
            yield event;
          }
        }

        await new Promise(resolve => setTimeout(resolve, pollInterval));
      } catch (error) {
        console.error('Error streaming events:', error);
        break;
      }
    }
  }

  async createSnapshot(correlationId: string): Promise<{ snapshotId: string }> {
    const response = await fetch(`${this.baseUrl}/workflows/${correlationId}/snapshots`, {
      method: 'POST',
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async listSnapshots(correlationId: string): Promise<{ snapshots: Array<{ id: string; timestamp: string }> }> {
    const response = await fetch(`${this.baseUrl}/workflows/${correlationId}/snapshots`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async replayWorkflow(correlationId: string, snapshotId: string): Promise<WorkflowStartResponse> {
    const response = await fetch(`${this.baseUrl}/workflows/${correlationId}/replay?snapshot_id=${snapshotId}`, {
      method: 'POST',
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async getAuditRecords(correlationId?: string): Promise<DecisionRecord[]> {
    const auditUrl = 'http://localhost:8001';
    const response = await fetch(`${auditUrl}/decisions`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data.items.filter((record: DecisionRecord) => 
      !correlationId || record.correlationId === correlationId
    );
  }

  destroy(): void {
    if (this.abortController) {
      this.abortController.abort();
    }
  }
}

export class HITLHelper {
  constructor(private client: AOBClient) {}

  async waitForApproval(correlationId: string, timeout: number = 300000): Promise<boolean> {
    const startTime = Date.now();

    for await (const event of this.client.streamWorkflowEvents(correlationId)) {
      if (event.type === 'human.approved') {
        return true;
      } else if (event.type === 'human.rejected') {
        return false;
      } else if (Date.now() - startTime > timeout) {
        throw new Error(`Approval timeout after ${timeout}ms`);
      }
    }

    return false;
  }

  async approveWorkflow(correlationId: string): Promise<WorkflowStartResponse> {
    return this.client.resumeWorkflow(correlationId, true);
  }

  async rejectWorkflow(correlationId: string): Promise<WorkflowStartResponse> {
    return this.client.resumeWorkflow(correlationId, false);
  }
}

export class RetryHelper {
  static async withRetry<T>(
    fn: () => Promise<T>,
    options: {
      maxAttempts?: number;
      baseDelay?: number;
      maxDelay?: number;
      backoffFactor?: number;
      jitter?: boolean;
    } = {}
  ): Promise<T> {
    const {
      maxAttempts = 3,
      baseDelay = 1000,
      maxDelay = 60000,
      backoffFactor = 2,
      jitter = true
    } = options;

    let lastError: Error;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;
        
        if (attempt === maxAttempts - 1) {
          throw lastError;
        }

        let delay = Math.min(baseDelay * Math.pow(backoffFactor, attempt), maxDelay);
        if (jitter) {
          delay *= (0.5 + 0.5 * Math.random());
        }

        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError!;
  }
}

// Convenience functions
export function createClient(options: {
  baseUrl?: string;
  oidcToken?: string;
  apiKey?: string;
  tenant?: string;
} = {}): AOBClient {
  const { baseUrl = 'http://localhost:8000', oidcToken, apiKey, tenant } = options;

  let auth: AuthConfig;
  if (oidcToken) {
    auth = { method: AuthMethod.OIDC, token: oidcToken, tenant };
  } else {
    auth = { method: AuthMethod.API_KEY, apiKey: apiKey || 'demo:local-dev-key' };
  }

  return new AOBClient(baseUrl, auth);
}

// Example usage
export async function exampleUsage(): Promise<void> {
  const client = createClient();

  try {
    // Start a workflow
    const result = await client.startWorkflow('example-workflow', { text: 'Hello AOB!' });
    const correlationId = result.correlationId;

    // Stream events
    for await (const event of client.streamWorkflowEvents(correlationId)) {
      console.log(`Event: ${event.type} -`, event.payload);

      if (event.type === 'workflow.completed') {
        break;
      }
    }

    // Get audit records
    const records = await client.getAuditRecords(correlationId);
    for (const record of records) {
      console.log(`Decision: ${record.nodeName} - Allowed: ${record.allowed}`);
    }
  } finally {
    client.destroy();
  }
}

// Export all types and classes
export * from './types';
