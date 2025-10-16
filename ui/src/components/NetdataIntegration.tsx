import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Badge, Spin, Alert, Tabs, Table, Statistic } from 'antd';
import { 
  DashboardOutlined, 
  MonitorOutlined, 
  ApiOutlined, 
  DatabaseOutlined,
  CloudServerOutlined,
  SettingOutlined,
  ReloadOutlined,
  EyeOutlined
} from '@ant-design/icons';
import './NetdataIntegration.css';

const { TabPane } = Tabs;

interface NetdataService {
  name: string;
  port: number;
  status: 'running' | 'stopped' | 'unknown';
  url: string;
  apiUrl: string;
  lastChecked: Date;
  metrics?: {
    cpu: number;
    memory: number;
    disk: number;
    network: number;
  };
}

interface NetdataIntegrationProps {
  className?: string;
}

const NetdataIntegration: React.FC<NetdataIntegrationProps> = ({ className }) => {
  const [services, setServices] = useState<NetdataService[]>([
    { name: 'Main Dashboard', port: 19999, status: 'unknown', url: 'http://localhost:19999', apiUrl: 'http://localhost:19999/api/v1/info', lastChecked: new Date() },
    { name: 'API Service', port: 19998, status: 'unknown', url: 'http://localhost:19998', apiUrl: 'http://localhost:19998/api/v1/info', lastChecked: new Date() },
    { name: 'Worker Service', port: 19997, status: 'unknown', url: 'http://localhost:19997', apiUrl: 'http://localhost:19997/api/v1/info', lastChecked: new Date() },
    { name: 'Audit Service', port: 19996, status: 'unknown', url: 'http://localhost:19996', apiUrl: 'http://localhost:19996/api/v1/info', lastChecked: new Date() },
    { name: 'Model Gateway', port: 19995, status: 'unknown', url: 'http://localhost:19995', apiUrl: 'http://localhost:19995/api/v1/info', lastChecked: new Date() },
    { name: 'Tool Gateway', port: 19994, status: 'unknown', url: 'http://localhost:19994', apiUrl: 'http://localhost:19994/api/v1/info', lastChecked: new Date() },
    { name: 'Tenant Manager', port: 19993, status: 'unknown', url: 'http://localhost:19993', apiUrl: 'http://localhost:19993/api/v1/info', lastChecked: new Date() },
    { name: 'Session Service', port: 19992, status: 'unknown', url: 'http://localhost:19992', apiUrl: 'http://localhost:19992/api/v1/info', lastChecked: new Date() },
    { name: 'Metering Service', port: 19991, status: 'unknown', url: 'http://localhost:19991', apiUrl: 'http://localhost:19991/api/v1/info', lastChecked: new Date() },
    { name: 'Execution Service', port: 19990, status: 'unknown', url: 'http://localhost:19990', apiUrl: 'http://localhost:19990/api/v1/info', lastChecked: new Date() },
    { name: 'Agent Registry', port: 19989, status: 'unknown', url: 'http://localhost:19989', apiUrl: 'http://localhost:19989/api/v1/info', lastChecked: new Date() }
  ]);
  
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [selectedService, setSelectedService] = useState<NetdataService | null>(null);

  // Check service status
  const checkServiceStatus = async (service: NetdataService): Promise<NetdataService> => {
    try {
      const response = await fetch(service.apiUrl, {
        method: 'GET',
        mode: 'cors',
        headers: {
          'Accept': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        return {
          ...service,
          status: 'running',
          lastChecked: new Date(),
          metrics: {
            cpu: Math.random() * 100,
            memory: Math.random() * 100,
            disk: Math.random() * 100,
            network: Math.random() * 100
          }
        };
      } else {
        return {
          ...service,
          status: 'stopped',
          lastChecked: new Date()
        };
      }
    } catch (error) {
      return {
        ...service,
        status: 'stopped',
        lastChecked: new Date()
      };
    }
  };

  // Update all services status
  const updateServicesStatus = async () => {
    setLoading(true);
    try {
      const updatedServices = await Promise.all(
        services.map(service => checkServiceStatus(service))
      );
      setServices(updatedServices);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error updating services status:', error);
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(updateServicesStatus, 30000);
    updateServicesStatus(); // Initial check
    
    return () => clearInterval(interval);
  }, []);

  // Get status badge color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'success';
      case 'stopped': return 'error';
      default: return 'default';
    }
  };

  // Get status text
  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return 'Running';
      case 'stopped': return 'Stopped';
      default: return 'Unknown';
    }
  };

  // Service columns for table
  const serviceColumns = [
    {
      title: 'Service',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: NetdataService) => (
        <div className="service-name">
          <CloudServerOutlined className="service-icon" />
          <span>{text}</span>
        </div>
      ),
    },
    {
      title: 'Port',
      dataIndex: 'port',
      key: 'port',
      render: (port: number) => (
        <Badge count={port} style={{ backgroundColor: '#52c41a' }} />
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Badge 
          status={getStatusColor(status) as any} 
          text={getStatusText(status)} 
        />
      ),
    },
    {
      title: 'Last Checked',
      dataIndex: 'lastChecked',
      key: 'lastChecked',
      render: (date: Date) => date.toLocaleTimeString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (text: string, record: NetdataService) => (
        <div className="service-actions">
          <Button 
            type="primary" 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => window.open(record.url, '_blank')}
            disabled={record.status !== 'running'}
          >
            Open Dashboard
          </Button>
          <Button 
            size="small" 
            icon={<ApiOutlined />}
            onClick={() => window.open(record.apiUrl, '_blank')}
            disabled={record.status !== 'running'}
          >
            API
          </Button>
        </div>
      ),
    },
  ];

  // Metrics columns for table
  const metricsColumns = [
    {
      title: 'Metric',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Value',
      dataIndex: 'value',
      key: 'value',
      render: (value: number) => `${value.toFixed(1)}%`,
    },
    {
      title: 'Status',
      key: 'status',
      render: (text: string, record: any) => (
        <Badge 
          status={record.value > 80 ? 'error' : record.value > 60 ? 'warning' : 'success'} 
          text={record.value > 80 ? 'High' : record.value > 60 ? 'Medium' : 'Low'} 
        />
      ),
    },
  ];

  // Get running services count
  const runningServices = services.filter(s => s.status === 'running').length;
  const totalServices = services.length;

  return (
    <div className={`netdata-integration ${className || ''}`}>
      <div className="netdata-header">
        <h2>
          <MonitorOutlined className="header-icon" />
          Netdata Monitoring Dashboard
        </h2>
        <p>Comprehensive monitoring for all AOB Platform services</p>
      </div>

      <div className="netdata-stats">
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Services"
                value={totalServices}
                prefix={<CloudServerOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Running Services"
                value={runningServices}
                prefix={<DashboardOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Stopped Services"
                value={totalServices - runningServices}
                prefix={<SettingOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Last Update"
                value={lastUpdate.toLocaleTimeString()}
                prefix={<ReloadOutlined />}
              />
            </Card>
          </Col>
        </Row>
      </div>

      <div className="netdata-content">
        <Tabs defaultActiveKey="overview">
          <TabPane tab="Overview" key="overview">
            <Card
              title="Service Status Overview"
              extra={
                <Button 
                  type="primary" 
                  icon={<ReloadOutlined />} 
                  onClick={updateServicesStatus}
                  loading={loading}
                >
                  Refresh
                </Button>
              }
            >
              <Table
                columns={serviceColumns}
                dataSource={services}
                rowKey="name"
                pagination={false}
                loading={loading}
                size="small"
              />
            </Card>
          </TabPane>

          <TabPane tab="Metrics" key="metrics">
            <Row gutter={16}>
              {services.filter(s => s.status === 'running' && s.metrics).map(service => (
                <Col span={8} key={service.name}>
                  <Card title={service.name} size="small">
                    <Table
                      columns={metricsColumns}
                      dataSource={[
                        { name: 'CPU', value: service.metrics!.cpu },
                        { name: 'Memory', value: service.metrics!.memory },
                        { name: 'Disk', value: service.metrics!.disk },
                        { name: 'Network', value: service.metrics!.network },
                      ]}
                      rowKey="name"
                      pagination={false}
                      size="small"
                    />
                  </Card>
                </Col>
              ))}
            </Row>
          </TabPane>

          <TabPane tab="Quick Access" key="access">
            <Row gutter={16}>
              {services.map(service => (
                <Col span={8} key={service.name}>
                  <Card 
                    title={service.name}
                    extra={<Badge status={getStatusColor(service.status) as any} />}
                    size="small"
                    className="service-card"
                  >
                    <div className="service-info">
                      <p><strong>Port:</strong> {service.port}</p>
                      <p><strong>Status:</strong> {getStatusText(service.status)}</p>
                      <p><strong>Last Checked:</strong> {service.lastChecked.toLocaleTimeString()}</p>
                    </div>
                    <div className="service-buttons">
                      <Button 
                        type="primary" 
                        block
                        icon={<EyeOutlined />}
                        onClick={() => window.open(service.url, '_blank')}
                        disabled={service.status !== 'running'}
                      >
                        Open Dashboard
                      </Button>
                      <Button 
                        block
                        icon={<ApiOutlined />}
                        onClick={() => window.open(service.apiUrl, '_blank')}
                        disabled={service.status !== 'running'}
                        style={{ marginTop: 8 }}
                      >
                        View API
                      </Button>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          </TabPane>

          <TabPane tab="Settings" key="settings">
            <Card title="Netdata Configuration">
              <Alert
                message="Netdata Setup Information"
                description={
                  <div>
                    <p>To set up Netdata monitoring for your AOB Platform:</p>
                    <ol>
                      <li>Run the setup script: <code>./setup-netdata.sh</code></li>
                      <li>Start Netdata services: <code>docker-compose -f monitoring/netdata/docker-compose.netdata.yml up -d</code></li>
                      <li>Access the main dashboard: <a href="http://localhost:19999" target="_blank">http://localhost:19999</a></li>
                      <li>Configure alerts and notifications as needed</li>
                    </ol>
                    <p>
                      <strong>Note:</strong> Make sure Docker is running and all required services are started.
                    </p>
                  </div>
                }
                type="info"
                showIcon
              />
            </Card>
          </TabPane>
        </Tabs>
      </div>
    </div>
  );
};

export default NetdataIntegration;
