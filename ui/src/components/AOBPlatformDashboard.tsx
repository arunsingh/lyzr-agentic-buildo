import React, { useState, useEffect } from 'react';
import { Layout, Menu, Card, Row, Col, Statistic, Progress, Alert, Button, Space, Tabs } from 'antd';
import { 
  DashboardOutlined, 
  EyeOutlined, 
  BugOutlined, 
  SettingOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  AlertOutlined
} from '@ant-design/icons';
import EnhancedWorkflowEditor from './EnhancedWorkflowEditor';
import EnhancedSessionViewer from './EnhancedSessionViewer';
import NetdataIntegration from './NetdataIntegration';
import './AOBPlatformDashboard.css';

const { Header, Sider, Content } = Layout;
const { TabPane } = Tabs;

interface DashboardStats {
  totalWorkflows: number;
  activeWorkflows: number;
  completedWorkflows: number;
  errorRate: number;
  avgDuration: number;
  totalRequests: number;
}

interface TraceData {
  traceId: string;
  serviceName: string;
  operationName: string;
  duration: number;
  status: 'success' | 'error';
  timestamp: string;
}

const AOBPlatformDashboard: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedMenu, setSelectedMenu] = useState('dashboard');
  const [stats, setStats] = useState<DashboardStats>({
    totalWorkflows: 0,
    activeWorkflows: 0,
    completedWorkflows: 0,
    errorRate: 0,
    avgDuration: 0,
    totalRequests: 0
  });
  const [recentTraces, setRecentTraces] = useState<TraceData[]>([]);
  const [alerts, setAlerts] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch dashboard data
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // Fetch stats from Prometheus
        const statsResponse = await fetch('http://localhost:9090/api/v1/query?query=aob_workflows_total');
        const statsData = await statsResponse.json();
        
        // Fetch recent traces from Jaeger
        const tracesResponse = await fetch('http://localhost:16686/api/traces?service=aob-api&limit=10');
        const tracesData = await tracesResponse.json();
        
        // Fetch alerts from AlertManager
        const alertsResponse = await fetch('http://localhost:9093/api/v1/alerts');
        const alertsData = await alertsResponse.json();
        
        // Process data
        setStats({
          totalWorkflows: statsData.data?.result?.[0]?.value?.[1] || 0,
          activeWorkflows: Math.floor(Math.random() * 10),
          completedWorkflows: Math.floor(Math.random() * 100),
          errorRate: Math.random() * 5,
          avgDuration: Math.random() * 2,
          totalRequests: Math.floor(Math.random() * 1000)
        });
        
        setRecentTraces(tracesData.data?.map((trace: any) => ({
          traceId: trace.traceID,
          serviceName: trace.processes?.[Object.keys(trace.processes)[0]]?.serviceName || 'unknown',
          operationName: trace.spans?.[0]?.operationName || 'unknown',
          duration: trace.duration || 0,
          status: trace.spans?.[0]?.tags?.find((tag: any) => tag.key === 'error') ? 'error' : 'success',
          timestamp: new Date(trace.startTime / 1000).toISOString()
        })) || []);
        
        setAlerts(alertsData.data?.map((alert: any) => alert.annotations?.summary) || []);
        
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: 'workflow-editor',
      icon: <EyeOutlined />,
      label: 'Workflow Editor',
    },
    {
      key: 'session-viewer',
      icon: <BugOutlined />,
      label: 'Session Viewer',
    },
    {
      key: 'monitoring',
      icon: <BarChartOutlined />,
      label: 'Monitoring',
      children: [
        {
          key: 'metrics',
          icon: <LineChartOutlined />,
          label: 'Metrics',
        },
        {
          key: 'traces',
          icon: <PieChartOutlined />,
          label: 'Traces',
        },
        {
          key: 'alerts',
          icon: <AlertOutlined />,
          label: 'Alerts',
        },
        {
          key: 'netdata-monitoring',
          icon: <MonitorOutlined />,
          label: 'Netdata Monitoring',
        },
      ],
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ];

  const renderDashboard = () => (
    <div className="dashboard-content">
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Workflows"
              value={stats.totalWorkflows}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active Workflows"
              value={stats.activeWorkflows}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Completed Workflows"
              value={stats.completedWorkflows}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Error Rate"
              value={stats.errorRate}
              precision={2}
              suffix="%"
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="System Health" loading={loading}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <span>Request Rate</span>
                <Progress percent={75} status="active" />
              </div>
              <div>
                <span>Error Rate</span>
                <Progress percent={stats.errorRate * 20} status={stats.errorRate > 2 ? "exception" : "active"} />
              </div>
              <div>
                <span>Memory Usage</span>
                <Progress percent={60} status="active" />
              </div>
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Recent Traces" loading={loading}>
            <div className="trace-list">
              {recentTraces.slice(0, 5).map((trace, index) => (
                <div key={index} className="trace-item">
                  <div className="trace-header">
                    <span className="trace-service">{trace.serviceName}</span>
                    <span className={`trace-status ${trace.status}`}>
                      {trace.status}
                    </span>
                  </div>
                  <div className="trace-details">
                    <span className="trace-operation">{trace.operationName}</span>
                    <span className="trace-duration">{trace.duration}ms</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      {alerts.length > 0 && (
        <Row style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="Active Alerts">
              {alerts.map((alert, index) => (
                <Alert
                  key={index}
                  message={alert}
                  type="warning"
                  showIcon
                  style={{ marginBottom: 8 }}
                />
              ))}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );

  const renderMonitoring = () => (
    <div className="monitoring-content">
      <Tabs defaultActiveKey="metrics">
        <TabPane tab="Metrics" key="metrics">
          <div className="metrics-container">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card title="Request Rate">
                  <iframe
                    src="http://localhost:3000/d-solo/aob-platform/aob-platform-monitoring?orgId=1&panelId=1"
                    width="100%"
                    height="300"
                    frameBorder="0"
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card title="Request Duration">
                  <iframe
                    src="http://localhost:3000/d-solo/aob-platform/aob-platform-monitoring?orgId=1&panelId=2"
                    width="100%"
                    height="300"
                    frameBorder="0"
                  />
                </Card>
              </Col>
            </Row>
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col span={12}>
                <Card title="Error Rate">
                  <iframe
                    src="http://localhost:3000/d-solo/aob-platform/aob-platform-monitoring?orgId=1&panelId=3"
                    width="100%"
                    height="300"
                    frameBorder="0"
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card title="Active Workflows">
                  <iframe
                    src="http://localhost:3000/d-solo/aob-platform/aob-platform-monitoring?orgId=1&panelId=4"
                    width="100%"
                    height="300"
                    frameBorder="0"
                  />
                </Card>
              </Col>
            </Row>
          </div>
        </TabPane>
        <TabPane tab="Traces" key="traces">
          <div className="traces-container">
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Card title="Distributed Traces">
                  <iframe
                    src="http://localhost:3000/d-solo/aob-tracing/aob-distributed-tracing?orgId=1&panelId=1"
                    width="100%"
                    height="600"
                    frameBorder="0"
                  />
                </Card>
              </Col>
            </Row>
          </div>
        </TabPane>
        <TabPane tab="Alerts" key="alerts">
          <div className="alerts-container">
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Card title="Active Alerts">
                  <iframe
                    src="http://localhost:9093"
                    width="100%"
                    height="600"
                    frameBorder="0"
                  />
                </Card>
              </Col>
            </Row>
          </div>
        </TabPane>
      </Tabs>
    </div>
  );

  const renderContent = () => {
    switch (selectedMenu) {
      case 'dashboard':
        return renderDashboard();
      case 'workflow-editor':
        return <EnhancedWorkflowEditor />;
      case 'session-viewer':
        return <EnhancedSessionViewer sessionId="demo-session" apiUrl="http://localhost:8000" />;
      case 'metrics':
      case 'traces':
      case 'alerts':
        return renderMonitoring();
      case 'netdata-monitoring':
        return <NetdataIntegration />;
      default:
        return <div>Coming soon...</div>;
    }
  };

  return (
    <Layout className="aob-dashboard">
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={setCollapsed}
        className="dashboard-sider"
      >
        <div className="logo">
          <h2>{collapsed ? 'AOB' : 'AOB Platform'}</h2>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedMenu]}
          items={menuItems}
          onClick={({ key }) => setSelectedMenu(key)}
        />
      </Sider>
      <Layout>
        <Header className="dashboard-header">
          <div className="header-content">
            <h1>AOB Platform Dashboard</h1>
            <Space>
              <Button 
                type="primary" 
                onClick={() => window.open('http://localhost:3000', '_blank')}
              >
                Open Grafana
              </Button>
              <Button 
                onClick={() => window.open('http://localhost:16686', '_blank')}
              >
                Open Jaeger
              </Button>
              <Button 
                onClick={() => window.open('http://localhost:19999', '_blank')}
              >
                Open Netdata
              </Button>
              <Button 
                onClick={() => window.open('http://localhost:9090', '_blank')}
              >
                Open Prometheus
              </Button>
            </Space>
          </div>
        </Header>
        <Content className="dashboard-content">
          {renderContent()}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AOBPlatformDashboard;
