import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  NodeTypes,
  EdgeTypes,
  MarkerType,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './EnhancedWorkflowEditor.css';

// Custom Node Types
const PolicyNode = ({ data, selected }: { data: any; selected: boolean }) => (
  <div className={`policy-node ${selected ? 'selected' : ''}`}>
    <div className="policy-header">
      <span className="policy-icon">🛡️</span>
      <span className="policy-name">{data.label}</span>
    </div>
    <div className="policy-details">
      <div className="policy-type">{data.policyType}</div>
      <div className="policy-status">
        <span className={`status-indicator ${data.status}`}></span>
        {data.status}
      </div>
    </div>
  </div>
);

const AgentNode = ({ data, selected }: { data: any; selected: boolean }) => (
  <div className={`agent-node ${selected ? 'selected' : ''}`}>
    <div className="agent-header">
      <span className="agent-icon">🤖</span>
      <span className="agent-name">{data.label}</span>
    </div>
    <div className="agent-details">
      <div className="agent-model">{data.model}</div>
      <div className="agent-status">
        <span className={`status-indicator ${data.status}`}></span>
        {data.status}
      </div>
    </div>
  </div>
);

const HumanNode = ({ data, selected }: { data: any; selected: boolean }) => (
  <div className={`human-node ${selected ? 'selected' : ''}`}>
    <div className="human-header">
      <span className="human-icon">👤</span>
      <span className="human-name">{data.label}</span>
    </div>
    <div className="human-details">
      <div className="approval-key">{data.approvalKey}</div>
      <div className="human-status">
        <span className={`status-indicator ${data.status}`}></span>
        {data.status}
      </div>
    </div>
  </div>
);

const TaskNode = ({ data, selected }: { data: any; selected: boolean }) => (
  <div className={`task-node ${selected ? 'selected' : ''}`}>
    <div className="task-header">
      <span className="task-icon">⚙️</span>
      <span className="task-name">{data.label}</span>
    </div>
    <div className="task-details">
      <div className="task-type">{data.taskType}</div>
      <div className="task-status">
        <span className={`status-indicator ${data.status}`}></span>
        {data.status}
      </div>
    </div>
  </div>
);

// Custom Edge Types
const PolicyEdge = ({ data }: { data: any }) => (
  <div className="policy-edge">
    <div className="edge-label">{data.label}</div>
    <div className="edge-policies">
      {data.policies?.map((policy: string, index: number) => (
        <span key={index} className="policy-tag">{policy}</span>
      ))}
    </div>
  </div>
);

const nodeTypes: NodeTypes = {
  policy: PolicyNode,
  agent: AgentNode,
  human: HumanNode,
  task: TaskNode,
};

const edgeTypes: EdgeTypes = {
  policy: PolicyEdge,
};

interface WorkflowEditorProps {
  onSave?: (workflow: any) => void;
  initialWorkflow?: any;
  readOnly?: boolean;
}

const EnhancedWorkflowEditor: React.FC<WorkflowEditorProps> = ({
  onSave,
  initialWorkflow,
  readOnly = false,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isDirty, setIsDirty] = useState(false);

  // Initialize with sample data or provided workflow
  useEffect(() => {
    if (initialWorkflow) {
      setNodes(initialWorkflow.nodes || []);
      setEdges(initialWorkflow.edges || []);
    } else {
      setNodes([
        {
          id: '1',
          type: 'task',
          position: { x: 100, y: 100 },
          data: {
            label: 'Data Ingestion',
            taskType: 'ETL',
            status: 'ready',
          },
        },
        {
          id: '2',
          type: 'agent',
          position: { x: 300, y: 100 },
          data: {
            label: 'Analysis Agent',
            model: 'llama2-70b',
            status: 'ready',
          },
        },
        {
          id: '3',
          type: 'policy',
          position: { x: 500, y: 100 },
          data: {
            label: 'Risk Assessment',
            policyType: 'compliance',
            status: 'ready',
          },
        },
        {
          id: '4',
          type: 'human',
          position: { x: 700, y: 100 },
          data: {
            label: 'Human Review',
            approvalKey: 'approval',
            status: 'pending',
          },
        },
      ]);

      setEdges([
        {
          id: 'e1-2',
          source: '1',
          target: '2',
          type: 'policy',
          data: {
            label: 'process',
            policies: ['data_access'],
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 20,
            height: 20,
            color: '#ff0072',
          },
        },
        {
          id: 'e2-3',
          source: '2',
          target: '3',
          type: 'policy',
          data: {
            label: 'analyze',
            policies: ['risk_check'],
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 20,
            height: 20,
            color: '#ff0072',
          },
        },
        {
          id: 'e3-4',
          source: '3',
          target: '4',
          type: 'policy',
          data: {
            label: 'review',
            policies: ['human_approval'],
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 20,
            height: 20,
            color: '#ff0072',
          },
        },
      ]);
    }
  }, [initialWorkflow]);

  const onConnect = useCallback(
    (params: Connection | Edge) => {
      const newEdge = {
        ...params,
        type: 'policy',
        data: {
          label: 'new_edge',
          policies: ['default_policy'],
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
          color: '#ff0072',
        },
      };
      setEdges((eds) => addEdge(newEdge, eds));
      setIsDirty(true);
    },
    [setEdges],
  );

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const validateWorkflow = useCallback(() => {
    const errors: string[] = [];

    // Check for orphaned nodes
    const nodeIds = new Set(nodes.map(n => n.id));
    const connectedNodes = new Set([
      ...edges.map(e => e.source),
      ...edges.map(e => e.target),
    ]);

    nodes.forEach(node => {
      if (!connectedNodes.has(node.id) && nodes.length > 1) {
        errors.push(`Node "${node.data.label}" is not connected`);
      }
    });

    // Check for cycles
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const hasCycle = (nodeId: string): boolean => {
      if (recursionStack.has(nodeId)) return true;
      if (visited.has(nodeId)) return false;

      visited.add(nodeId);
      recursionStack.add(nodeId);

      const outgoingEdges = edges.filter(e => e.source === nodeId);
      for (const edge of outgoingEdges) {
        if (hasCycle(edge.target)) return true;
      }

      recursionStack.delete(nodeId);
      return false;
    };

    for (const node of nodes) {
      if (hasCycle(node.id)) {
        errors.push('Workflow contains cycles');
        break;
      }
    }

    // Check for required fields
    nodes.forEach(node => {
      if (!node.data.label) {
        errors.push(`Node ${node.id} is missing a label`);
      }
    });

    setValidationErrors(errors);
    return errors.length === 0;
  }, [nodes, edges]);

  const handleSave = useCallback(() => {
    if (validateWorkflow()) {
      const workflow = {
        nodes: nodes.map(node => ({
          id: node.id,
          type: node.type,
          position: node.position,
          data: node.data,
        })),
        edges: edges.map(edge => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: edge.type,
          data: edge.data,
        })),
      };
      onSave?.(workflow);
      setIsDirty(false);
    }
  }, [nodes, edges, validateWorkflow, onSave]);

  const addNode = useCallback((type: string) => {
    const newNode: Node = {
      id: `node_${Date.now()}`,
      type,
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      data: {
        label: `New ${type}`,
        status: 'ready',
        ...(type === 'agent' && { model: 'llama2-7b' }),
        ...(type === 'policy' && { policyType: 'compliance' }),
        ...(type === 'human' && { approvalKey: 'approval' }),
        ...(type === 'task' && { taskType: 'ETL' }),
      },
    };
    setNodes(nds => [...nds, newNode]);
    setIsDirty(true);
  }, [setNodes]);

  return (
    <div className="enhanced-workflow-editor">
      <div className="editor-toolbar">
        <div className="toolbar-section">
          <h3>Add Nodes</h3>
          <div className="node-buttons">
            <button onClick={() => addNode('task')} disabled={readOnly}>
              ⚙️ Task
            </button>
            <button onClick={() => addNode('agent')} disabled={readOnly}>
              🤖 Agent
            </button>
            <button onClick={() => addNode('policy')} disabled={readOnly}>
              🛡️ Policy
            </button>
            <button onClick={() => addNode('human')} disabled={readOnly}>
              👤 Human
            </button>
          </div>
        </div>

        <div className="toolbar-section">
          <h3>Actions</h3>
          <div className="action-buttons">
            <button onClick={validateWorkflow}>🔍 Validate</button>
            <button onClick={handleSave} disabled={!isDirty || readOnly}>
              💾 Save
            </button>
          </div>
        </div>

        {validationErrors.length > 0 && (
          <div className="validation-errors">
            <h4>Validation Errors:</h4>
            <ul>
              {validationErrors.map((error, index) => (
                <li key={index} className="error">{error}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="editor-content">
        <div className="flow-container">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Controls />
            <MiniMap
              nodeStrokeColor={(n) => {
                if (n.type === 'policy') return '#ff0072';
                if (n.type === 'agent') return '#0041d0';
                if (n.type === 'human') return '#ffa500';
                return '#333';
              }}
              nodeColor={(n) => {
                if (n.type === 'policy') return '#ff0072';
                if (n.type === 'agent') return '#0041d0';
                if (n.type === 'human') return '#ffa500';
                return '#333';
              }}
              nodeBorderRadius={2}
            />
            <Background variant="dots" gap={12} size={1} />
          </ReactFlow>
        </div>

        {selectedNode && (
          <div className="node-properties">
            <h3>Node Properties</h3>
            <div className="property-form">
              <div className="form-group">
                <label>Label:</label>
                <input
                  type="text"
                  value={selectedNode.data.label}
                  onChange={(e) => {
                    setNodes(nds =>
                      nds.map(n =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...n.data, label: e.target.value } }
                          : n
                      )
                    );
                    setIsDirty(true);
                  }}
                  disabled={readOnly}
                />
              </div>

              {selectedNode.type === 'agent' && (
                <div className="form-group">
                  <label>Model:</label>
                  <select
                    value={selectedNode.data.model}
                    onChange={(e) => {
                      setNodes(nds =>
                        nds.map(n =>
                          n.id === selectedNode.id
                            ? { ...n, data: { ...n.data, model: e.target.value } }
                            : n
                        )
                      );
                      setIsDirty(true);
                    }}
                    disabled={readOnly}
                  >
                    <option value="llama2-7b">Llama2 7B</option>
                    <option value="llama2-70b">Llama2 70B</option>
                    <option value="llama2-120b">Llama2 120B</option>
                  </select>
                </div>
              )}

              {selectedNode.type === 'policy' && (
                <div className="form-group">
                  <label>Policy Type:</label>
                  <select
                    value={selectedNode.data.policyType}
                    onChange={(e) => {
                      setNodes(nds =>
                        nds.map(n =>
                          n.id === selectedNode.id
                            ? { ...n, data: { ...n.data, policyType: e.target.value } }
                            : n
                        )
                      );
                      setIsDirty(true);
                    }}
                    disabled={readOnly}
                  >
                    <option value="compliance">Compliance</option>
                    <option value="security">Security</option>
                    <option value="data">Data</option>
                    <option value="cost">Cost</option>
                  </select>
                </div>
              )}

              {selectedNode.type === 'human' && (
                <div className="form-group">
                  <label>Approval Key:</label>
                  <input
                    type="text"
                    value={selectedNode.data.approvalKey}
                    onChange={(e) => {
                      setNodes(nds =>
                        nds.map(n =>
                          n.id === selectedNode.id
                            ? { ...n, data: { ...n.data, approvalKey: e.target.value } }
                            : n
                        )
                      );
                      setIsDirty(true);
                    }}
                    disabled={readOnly}
                  />
                </div>
              )}

              {selectedNode.type === 'task' && (
                <div className="form-group">
                  <label>Task Type:</label>
                  <select
                    value={selectedNode.data.taskType}
                    onChange={(e) => {
                      setNodes(nds =>
                        nds.map(n =>
                          n.id === selectedNode.id
                            ? { ...n, data: { ...n.data, taskType: e.target.value } }
                            : n
                        )
                      );
                      setIsDirty(true);
                    }}
                    disabled={readOnly}
                  >
                    <option value="ETL">ETL</option>
                    <option value="API">API</option>
                    <option value="Database">Database</option>
                    <option value="File">File</option>
                  </select>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EnhancedWorkflowEditor;
