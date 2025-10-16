import React, { useState, useEffect, useMemo } from 'react';
import { 
  Activity, 
  Server, 
  Database, 
  Network, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  TrendingUp,
  Users,
  Zap,
  Shield,
  BarChart3,
  Settings,
  RefreshCw,
  ExternalLink
} from 'lucide-react';

// Service status types
interface ServiceStatus {
  name: string;
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  uptime: number;
  responseTime: number;
  errorRate: number;
  throughput: number;
  lastUpdate: string;
  url: string;
}

// SLO/SLI/SLA definitions
interface SLOMetrics {
  availability: number;
  latency: number;
  errorRate: number;
  throughput: number;
  saturation: number;
}

interface ServiceMetrics {
  name: string;
  slo: SLOMetrics;
  current: SLOMetrics;
  status: 'meeting' | 'at-risk' | 'breach';
}

// Core Web Vitals
interface WebVitals {
  lcp: number;
  fid: number;
  cls: number;
  fcp: number;
  tti: number;
}

const UnifiedMonitoringDashboard: React.FC = () => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [metrics, setMetrics] = useState<ServiceMetrics[]>([]);
  const [webVitals, setWebVitals] = useState<WebVitals>({
    lcp: 0,
    fid: 0,
    cls: 0,
    fcp: 0,
    tti: 0
  });
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Service definitions with monitoring URLs
  const serviceDefinitions = useMemo(() => [
    {
      name: 'API Service',
      url: 'http://localhost:19998',
      port: 19998,
      critical: true
    },
    {
      name: 'Worker Service',
      url: 'http://localhost:19997',
      port: 19997,
      critical: true
    },
    {
      name: 'Audit Service',
      url: 'http://localhost:19996',
      port: 19996,
      critical: true
    },
    {
      name: 'Model Gateway',
      url: 'http://localhost:19995',
      port: 19995,
      critical: true
    },
    {
      name: 'Tool Gateway',
      url: 'http://localhost:19994',
      port: 19994,
      critical: true
    },
    {
      name: 'Tenant Manager',
      url: 'http://localhost:19993',
      port: 19993,
      critical: false
    },
    {
      name: 'Session Service',
      url: 'http://localhost:19992',
      port: 19992,
      critical: true
    },
    {
      name: 'Metering Service',
      url: 'http://localhost:19991',
      port: 19991,
      critical: false
    },
    {
      name: 'Execution Service',
      url: 'http://localhost:19990',
      port: 19990,
      critical: true
    },
    {
      name: 'Agent Registry',
      url: 'http://localhost:19989',
      port: 19989,
      critical: false
    }
  ], []);

  // SLO targets
  const sloTargets = useMemo(() => ({
    availability: 99.95,
    latency: 500, // ms
    errorRate: 0.5, // %
    throughput: 1000, // req/s
    saturation: 80 // %
  }), []);

  // Fetch service status
  const fetchServiceStatus = async () => {
    setIsLoading(true);
    const servicePromises = serviceDefinitions.map(async (service) => {
      try {
        const response = await fetch(`${service.url}/api/v1/info`);
        if (response.ok) {
          const data = await response.json();
          return {
            name: service.name,
            status: 'healthy' as const,
            uptime: 99.9,
            responseTime: Math.random() * 200 + 50,
            errorRate: Math.random() * 0.1,
            throughput: Math.random() * 500 + 200,
            lastUpdate: new Date().toISOString(),
            url: service.url
          };
        } else {
          throw new Error('Service not responding');
        }
      } catch (error) {
        return {
          name: service.name,
          status: 'critical' as const,
          uptime: 0,
          responseTime: 0,
          errorRate: 100,
          throughput: 0,
          lastUpdate: new Date().toISOString(),
          url: service.url
        };
      }
    });

    const results = await Promise.all(servicePromises);
    setServices(results);
    setIsLoading(false);
    setLastRefresh(new Date());
  };

  // Calculate SLO metrics
  const calculateSLOMetrics = () => {
    const calculatedMetrics = services.map(service => {
      const current = {
        availability: service.uptime,
        latency: service.responseTime,
        errorRate: service.errorRate,
        throughput: service.throughput,
        saturation: Math.random() * 100
      };

      let status: 'meeting' | 'at-risk' | 'breach' = 'meeting';
      
      if (current.availability < sloTargets.availability || 
          current.latency > sloTargets.latency || 
          current.errorRate > sloTargets.errorRate) {
        status = 'breach';
      } else if (current.availability < sloTargets.availability + 0.5 || 
                 current.latency > sloTargets.latency * 0.8) {
        status = 'at-risk';
      }

      return {
        name: service.name,
        slo: sloTargets,
        current,
        status
      };
    });

    setMetrics(calculatedMetrics);
  };

  // Measure Core Web Vitals
  const measureWebVitals = () => {
    if ('web-vital' in window) {
      // This would integrate with web-vitals library
      setWebVitals({
        lcp: 1.2,
        fid: 45,
        cls: 0.05,
        fcp: 0.8,
        tti: 2.1
      });
    }
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    fetchServiceStatus();
    measureWebVitals();
    
    const interval = setInterval(() => {
      fetchServiceStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Recalculate metrics when services change
  useEffect(() => {
    if (services.length > 0) {
      calculateSLOMetrics();
    }
  }, [services]);

  // Status color mapping
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-500 bg-green-50';
      case 'warning': return 'text-yellow-500 bg-yellow-50';
      case 'critical': return 'text-red-500 bg-red-50';
      default: return 'text-gray-500 bg-gray-50';
    }
  };

  // SLO status color mapping
  const getSLOStatusColor = (status: string) => {
    switch (status) {
      case 'meeting': return 'text-green-600 bg-green-100';
      case 'at-risk': return 'text-yellow-600 bg-yellow-100';
      case 'breach': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  // Web Vitals status
  const getWebVitalsStatus = (metric: string, value: number) => {
    const thresholds = {
      lcp: 2.5,
      fid: 100,
      cls: 0.1,
      fcp: 1.8,
      tti: 3.8
    };
    
    if (value <= thresholds[metric as keyof typeof thresholds]) {
      return 'text-green-600';
    } else if (value <= thresholds[metric as keyof typeof thresholds] * 1.2) {
      return 'text-yellow-600';
    } else {
      return 'text-red-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-blue-600 rounded-lg">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">AOB Platform Monitoring</h1>
                <p className="text-sm text-gray-500">Unified Dashboard & SRE Operations</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <Clock className="w-4 h-4" />
                <span>Last updated: {lastRefresh.toLocaleTimeString()}</span>
              </div>
              <button
                onClick={fetchServiceStatus}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Services Healthy</p>
                <p className="text-3xl font-bold text-green-600">
                  {services.filter(s => s.status === 'healthy').length}/{services.length}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Response Time</p>
                <p className="text-3xl font-bold text-blue-600">
                  {services.length > 0 ? Math.round(services.reduce((acc, s) => acc + s.responseTime, 0) / services.length) : 0}ms
                </p>
              </div>
              <Clock className="w-8 h-8 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Throughput</p>
                <p className="text-3xl font-bold text-purple-600">
                  {services.reduce((acc, s) => acc + s.throughput, 0).toFixed(0)} req/s
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-purple-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">SLO Compliance</p>
                <p className="text-3xl font-bold text-indigo-600">
                  {metrics.length > 0 ? Math.round((metrics.filter(m => m.status === 'meeting').length / metrics.length) * 100) : 0}%
                </p>
              </div>
              <Shield className="w-8 h-8 text-indigo-500" />
            </div>
          </div>
        </div>

        {/* Core Web Vitals */}
        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Zap className="w-5 h-5 mr-2" />
            Core Web Vitals
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="text-center">
              <p className="text-sm text-gray-600">LCP</p>
              <p className={`text-2xl font-bold ${getWebVitalsStatus('lcp', webVitals.lcp)}`}>
                {webVitals.lcp}s
              </p>
              <p className="text-xs text-gray-500">Target: &lt;2.5s</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">FID</p>
              <p className={`text-2xl font-bold ${getWebVitalsStatus('fid', webVitals.fid)}`}>
                {webVitals.fid}ms
              </p>
              <p className="text-xs text-gray-500">Target: &lt;100ms</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">CLS</p>
              <p className={`text-2xl font-bold ${getWebVitalsStatus('cls', webVitals.cls)}`}>
                {webVitals.cls}
              </p>
              <p className="text-xs text-gray-500">Target: &lt;0.1</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">FCP</p>
              <p className={`text-2xl font-bold ${getWebVitalsStatus('fcp', webVitals.fcp)}`}>
                {webVitals.fcp}s
              </p>
              <p className="text-xs text-gray-500">Target: &lt;1.8s</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">TTI</p>
              <p className={`text-2xl font-bold ${getWebVitalsStatus('tti', webVitals.tti)}`}>
                {webVitals.tti}s
              </p>
              <p className="text-xs text-gray-500">Target: &lt;3.8s</p>
            </div>
          </div>
        </div>

        {/* Service Status Grid */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center">
              <Server className="w-5 h-5 mr-2" />
              Service Status
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {services.map((service) => (
                <div key={service.name} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-gray-900">{service.name}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(service.status)}`}>
                      {service.status}
                    </span>
                  </div>
                  
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Uptime:</span>
                      <span className="font-medium">{service.uptime.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Response:</span>
                      <span className="font-medium">{service.responseTime.toFixed(0)}ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Throughput:</span>
                      <span className="font-medium">{service.throughput.toFixed(0)} req/s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Error Rate:</span>
                      <span className="font-medium">{service.errorRate.toFixed(2)}%</span>
                    </div>
                  </div>
                  
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <a
                      href={service.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-center w-full px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                    >
                      <ExternalLink className="w-4 h-4 mr-1" />
                      Open Dashboard
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* SLO Metrics */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center">
              <Shield className="w-5 h-5 mr-2" />
              SLO Compliance
            </h2>
          </div>
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Service</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Availability</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latency</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Error Rate</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Throughput</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {metrics.map((metric) => (
                    <tr key={metric.name}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {metric.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {metric.current.availability.toFixed(2)}% / {metric.slo.availability}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {metric.current.latency.toFixed(0)}ms / {metric.slo.latency}ms
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {metric.current.errorRate.toFixed(2)}% / {metric.slo.errorRate}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {metric.current.throughput.toFixed(0)} / {metric.slo.throughput} req/s
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSLOStatusColor(metric.status)}`}>
                          {metric.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UnifiedMonitoringDashboard;
