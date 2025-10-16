import React, { useState, useCallback, useRef, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  NodeTypes,
  EdgeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';

// Custom node types
const TaskNode = ({ data }: { data: any }) => (
  <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-stone-400">
    <div className="flex">
      <div className="rounded-full w-12 h-12 flex justify-center items-center bg-gray-100">
        📋
      </div>
      <div className="ml-2">
        <div className="text-lg font-bold">{data.label}</div>
        <div className="text-gray-500">{data.type}</div>
      </div>
    </div>
  </div>
);

const AgentNode = ({ data }: { data: any }) => (
  <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-blue-400">
    <div className="flex">
      <div className="rounded-full w-12 h-12 flex justify-center items-center bg-blue-100">
        🤖
      </div>
      <div className="ml-2">
        <div className="text-lg font-bold">{data.label}</div>
        <div className="text-gray-500">{data.type}</div>
      </div>
    </div>
  </div>
);

const HumanNode = ({ data }: { data: any }) => (
  <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-green-400">
    <div className="flex">
      <div className="rounded-full w-12 h-12 flex justify-center items-center bg-green-100">
        👤
      </div>
      <div className="ml-2">
        <div className="text-lg font-bold">{data.label}</div>
        <div className="text-gray-500">{data.type}</div>
      </div>
    </div>
  </div>
);

const nodeTypes: NodeTypes = {
  task: TaskNode,
  agent: AgentNode,
  human: HumanNode,
};

const initialNodes: Node[] = [
  {
    id: '1',
    type: 'task',
    position: { x: 250, y: 25 },
    data: { label: 'Input Processing', type: 'Task' },
  },
  {
    id: '2',
    type: 'agent',
    position: { x: 100, y: 125 },
    data: { label: 'AI Analysis', type: 'Agent' },
  },
  {
    id: '3',
    type: 'human',
    position: { x: 400, y: 125 },
    data: { label: 'Human Review', type: 'Human' },
  },
  {
    id: '4',
    type: 'task',
    position: { x: 250, y: 225 },
    data: { label: 'Output Generation', type: 'Task' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e1-3', source: '1', target: '3', animated: true },
  { id: 'e2-4', source: '2', target: '4', animated: true },
  { id: 'e3-4', source: '3', target: '4', animated: true },
];

interface WorkflowEditorProps {
  onSave?: (workflow: { nodes: Node[]; edges: Edge[] }) => void;
  initialWorkflow?: { nodes: Node[]; edges: Edge[] };
}

export const WorkflowEditor: React.FC<WorkflowEditorProps> = ({
  onSave,
  initialWorkflow,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    initialWorkflow?.nodes || initialNodes
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialWorkflow?.edges || initialEdges
  );
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [workflowName, setWorkflowName] = useState('My Workflow');

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave({ nodes, edges });
    }
  }, [nodes, edges, onSave]);

  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const updateNodeData = useCallback((nodeId: string, newData: any) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...newData } } : node
      )
    );
  }, [setNodes]);

  const addNode = useCallback((type: string) => {
    const newNode: Node = {
      id: `${Date.now()}`,
      type,
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      data: { label: `New ${type}`, type: type.charAt(0).toUpperCase() + type.slice(1) },
    };
    setNodes((nds) => [...nds, newNode]);
  }, [setNodes]);

  return (
    <div className="h-screen flex flex-col">
      {/* Toolbar */}
      <div className="bg-gray-100 p-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <input
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              className="px-3 py-2 border rounded-md"
              placeholder="Workflow Name"
            />
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              Save Workflow
            </button>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => addNode('task')}
              className="px-3 py-2 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              + Task
            </button>
            <button
              onClick={() => addNode('agent')}
              className="px-3 py-2 bg-blue-200 rounded-md hover:bg-blue-300"
            >
              + Agent
            </button>
            <button
              onClick={() => addNode('human')}
              className="px-3 py-2 bg-green-200 rounded-md hover:bg-green-300"
            >
              + Human
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-1">
        {/* Main Editor */}
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Controls />
            <MiniMap />
            <Background variant="dots" gap={12} size={1} />
          </ReactFlow>
        </div>

        {/* Properties Panel */}
        {selectedNode && (
          <div className="w-80 bg-gray-50 border-l p-4">
            <h3 className="text-lg font-semibold mb-4">Node Properties</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Label
                </label>
                <input
                  type="text"
                  value={selectedNode.data.label}
                  onChange={(e) =>
                    updateNodeData(selectedNode.id, { label: e.target.value })
                  }
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Type
                </label>
                <select
                  value={selectedNode.type}
                  onChange={(e) => {
                    const newNode = { ...selectedNode, type: e.target.value };
                    setNodes((nds) =>
                      nds.map((node) => (node.id === selectedNode.id ? newNode : node))
                    );
                    setSelectedNode(newNode);
                  }}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="task">Task</option>
                  <option value="agent">Agent</option>
                  <option value="human">Human</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <textarea
                  value={selectedNode.data.description || ''}
                  onChange={(e) =>
                    updateNodeData(selectedNode.id, { description: e.target.value })
                  }
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={3}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkflowEditor;
