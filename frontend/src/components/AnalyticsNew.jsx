import React, { useState, useEffect } from 'react';
import { 
  BarChart3, Phone, Clock, TrendingUp, Calendar, Filter as FilterIcon,
  Plus, Edit2, RotateCcw, PhoneIncoming, PhoneOutgoing, CheckCircle,
  XCircle, MessageCircle, Timer
} from 'lucide-react';
import { VictoryBar, VictoryChart, VictoryAxis, VictoryPie, VictoryTheme } from 'victory';

const AnalyticsNew = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('all');
  const [showFilters, setShowFilters] = useState(false);
  const [activeFilters, setActiveFilters] = useState({});
  const [filterValues, setFilterValues] = useState({
    agent_id: '',
    call_id: '',
    batch_call_id: '',
    type: '',
    duration_min: '',
    duration_max: '',
    from_number: '',
    to_number: '',
    user_sentiment: '',
    disconnection_reason: '',
    call_status: '',
    call_successful: '',
    e2e_latency_min: '',
    e2e_latency_max: ''
  });

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
  const COLORS = ['#3b82f6', '#f97316', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899'];

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange, activeFilters]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      
      // Build query params
      const params = new URLSearchParams();
      
      // Add time range
      if (timeRange !== 'all') {
        const now = new Date();
        let startDate;
        if (timeRange === '7d') {
          startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        } else if (timeRange === '30d') {
          startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        } else if (timeRange === '90d') {
          startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
        }
        if (startDate) {
          params.append('start_date', startDate.toISOString());
        }
      }
      
      // Add active filters
      Object.entries(activeFilters).forEach(([key, value]) => {
        if (value) {
          params.append(key, value);
        }
      });
      
      const url = `${backendUrl}/api/call-analytics${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);
      const data = await response.json();
      setAnalytics(data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    const newFilters = {};
    Object.entries(filterValues).forEach(([key, value]) => {
      if (value && value !== '') {
        newFilters[key] = value;
      }
    });
    setActiveFilters(newFilters);
    setShowFilters(false);
  };

  const resetFilters = () => {
    setFilterValues({
      agent_id: '',
      call_id: '',
      batch_call_id: '',
      type: '',
      duration_min: '',
      duration_max: '',
      from_number: '',
      to_number: '',
      user_sentiment: '',
      disconnection_reason: '',
      call_status: '',
      call_successful: '',
      e2e_latency_min: '',
      e2e_latency_max: ''
    });
    setActiveFilters({});
  };

  const updateFilter = (key, value) => {
    setFilterValues(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="text-white text-xl">Loading analytics...</div>
      </div>
    );
  }

  // Prepare data
  const callCountData = analytics?.call_count_by_date || [];
  
  const successData = [
    { name: 'Successful', value: analytics?.completed_calls || 0, color: '#10b981' },
    { name: 'Unsuccessful', value: (analytics?.total_calls || 0) - (analytics?.completed_calls || 0), color: '#ef4444' }
  ].filter(item => item.value > 0);

  const sentimentData = [
    { name: 'Positive', value: analytics?.sentiment_positive || 0, color: '#10b981' },
    { name: 'Negative', value: analytics?.sentiment_negative || 0, color: '#ef4444' },
    { name: 'Neutral', value: analytics?.sentiment_neutral || 0, color: '#6b7280' },
    { name: 'Unknown', value: analytics?.sentiment_unknown || 0, color: '#9ca3af' }
  ].filter(item => item.value > 0);

  const directionData = [
    { name: 'Outbound', value: analytics?.by_direction?.outbound || 0, color: '#f97316' },
    { name: 'Inbound', value: analytics?.by_direction?.inbound || 0, color: '#3b82f6' }
  ].filter(item => item.value > 0);

  const disconnectionData = Object.entries(analytics?.by_status || {}).map(([key, value], index) => ({
    name: key.replace(/_/g, ' '),
    value,
    color: COLORS[index % COLORS.length]
  }));

  // Debug logging
  console.log('📊 Analytics Data:', {
    callCountData,
    callCountDataMapped: callCountData.map(d => ({ x: d.date, y: d.count })),
    successData,
    sentimentData,
    directionData,
    disconnectionData
  });

  const metrics = [
    {
      label: 'Total Calls',
      value: analytics?.total_calls || 0,
      icon: Phone,
      color: 'from-blue-500 to-blue-600'
    },
    {
      label: 'Avg Duration',
      value: analytics?.avg_duration ? `${Math.floor(analytics.avg_duration)}s` : '0s',
      icon: Clock,
      color: 'from-purple-500 to-purple-600'
    },
    {
      label: 'Avg Latency',
      value: analytics?.avg_latency ? `${Math.floor(analytics.avg_latency)}ms` : '0ms',
      icon: Timer,
      color: 'from-green-500 to-green-600'
    },
    {
      label: 'Success Rate',
      value: analytics?.success_rate ? `${analytics.success_rate.toFixed(1)}%` : '0%',
      icon: TrendingUp,
      color: 'from-pink-500 to-pink-600'
    }
  ];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics</h1>
          <p className="text-gray-400">All agents</p>
        </div>
        
        <div className="flex items-center gap-3">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 hover:bg-gray-700"
          >
            <option value="all">All time</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>

          <button 
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
              Object.keys(activeFilters).length > 0
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-gray-800 border-gray-700 text-white hover:bg-gray-700'
            }`}
          >
            <FilterIcon className="w-4 h-4" />
            Filter
            {Object.keys(activeFilters).length > 0 && (
              <span className="ml-1 px-2 py-0.5 bg-blue-500 rounded-full text-xs">
                {Object.keys(activeFilters).length}
              </span>
            )}
          </button>

          <button 
            onClick={resetFilters}
            className="px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 hover:bg-gray-700"
            title="Reset Filters"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button className="px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 hover:bg-gray-700">
            <Plus className="w-4 h-4" />
          </button>

          <button className="px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 hover:bg-gray-700">
            <Edit2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="mb-6 p-6 bg-gray-800 rounded-lg border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Filters</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Agent ID */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Agent ID</label>
              <input
                type="text"
                value={filterValues.agent_id}
                onChange={(e) => updateFilter('agent_id', e.target.value)}
                placeholder="Enter agent ID"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              />
            </div>

            {/* Call ID */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Call ID</label>
              <input
                type="text"
                value={filterValues.call_id}
                onChange={(e) => updateFilter('call_id', e.target.value)}
                placeholder="Enter call ID"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              />
            </div>

            {/* Type (Direction) */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Type</label>
              <select
                value={filterValues.type}
                onChange={(e) => updateFilter('type', e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              >
                <option value="">All</option>
                <option value="inbound">Inbound</option>
                <option value="outbound">Outbound</option>
              </select>
            </div>

            {/* Duration Min */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Duration Min (seconds)</label>
              <input
                type="number"
                value={filterValues.duration_min}
                onChange={(e) => updateFilter('duration_min', e.target.value)}
                placeholder="0"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              />
            </div>

            {/* Duration Max */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Duration Max (seconds)</label>
              <input
                type="number"
                value={filterValues.duration_max}
                onChange={(e) => updateFilter('duration_max', e.target.value)}
                placeholder="999999"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              />
            </div>

            {/* From Number */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">From Number</label>
              <input
                type="text"
                value={filterValues.from_number}
                onChange={(e) => updateFilter('from_number', e.target.value)}
                placeholder="+1234567890"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              />
            </div>

            {/* To Number */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">To Number</label>
              <input
                type="text"
                value={filterValues.to_number}
                onChange={(e) => updateFilter('to_number', e.target.value)}
                placeholder="+1234567890"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              />
            </div>

            {/* User Sentiment */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">User Sentiment</label>
              <select
                value={filterValues.user_sentiment}
                onChange={(e) => updateFilter('user_sentiment', e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              >
                <option value="">All</option>
                <option value="positive">Positive</option>
                <option value="neutral">Neutral</option>
                <option value="negative">Negative</option>
              </select>
            </div>

            {/* Call Status */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Call Status</label>
              <select
                value={filterValues.call_status}
                onChange={(e) => updateFilter('call_status', e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              >
                <option value="">All</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="busy">Busy</option>
                <option value="no-answer">No Answer</option>
              </select>
            </div>

            {/* Call Successful */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Call Successful</label>
              <select
                value={filterValues.call_successful}
                onChange={(e) => updateFilter('call_successful', e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              >
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>

            {/* E2E Latency Min */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">E2E Latency Min (ms)</label>
              <input
                type="number"
                value={filterValues.e2e_latency_min}
                onChange={(e) => updateFilter('e2e_latency_min', e.target.value)}
                placeholder="0"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              />
            </div>

            {/* E2E Latency Max */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">E2E Latency Max (ms)</label>
              <input
                type="number"
                value={filterValues.e2e_latency_max}
                onChange={(e) => updateFilter('e2e_latency_max', e.target.value)}
                placeholder="9999"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={applyFilters}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
            >
              Apply Filters
            </button>
            <button
              onClick={() => setShowFilters(false)}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metrics.map((metric, index) => {
          const Icon = metric.icon;
          return (
            <div key={index} className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-lg bg-gradient-to-r ${metric.color} bg-opacity-10`}>
                  <Icon size={24} className="text-white" />
                </div>
              </div>
              <p className="text-gray-400 text-sm mb-1">{metric.label}</p>
              <p className="text-3xl font-bold text-white">{metric.value}</p>
            </div>
          );
        })}
      </div>

      {/* Charts Grid */}
      <div className="flex flex-col gap-6">
        {/* Call Counts Over Time */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Call Counts</h3>
          <p className="text-sm text-gray-400 mb-4">All agents</p>
          {callCountData.length > 0 ? (
            <>
              <div className="space-y-6">
                {callCountData.map((item, index) => {
                  const maxCount = Math.max(...callCountData.map(d => d.count));
                  const barHeight = (item.count / maxCount) * 200;
                  return (
                    <div key={index} className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-300">{item.date}</span>
                        <span className="text-white font-semibold">{item.count} calls</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-8 flex items-center">
                        <div 
                          className="h-8 rounded-full transition-all duration-300 flex items-center justify-end pr-3"
                          style={{ 
                            width: `${(item.count / maxCount) * 100}%`,
                            backgroundColor: '#3b82f6',
                            minWidth: item.count > 0 ? '60px' : '0'
                          }}
                        >
                          <span className="text-white text-sm font-bold">{item.count}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center gap-2 mt-6">
                <div className="w-3 h-3 bg-blue-500 rounded"></div>
                <span className="text-sm text-gray-400">Total calls: {callCountData.reduce((sum, d) => sum + d.count, 0)}</span>
              </div>
            </>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500 border border-gray-700 rounded">
              <div className="text-center">
                <p className="mb-2">No call data available</p>
                <p className="text-xs text-gray-600">Try adjusting your filters or time range</p>
              </div>
            </div>
          )}
        </div>

        {/* Call Success Rate */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Success Rate</h3>
          <p className="text-sm text-gray-400 mb-4">All agents</p>
          <div className="flex flex-col items-center justify-center h-[250px]">
            <div className="text-6xl font-bold text-green-500 mb-4">
              {analytics?.success_rate ? `${analytics.success_rate.toFixed(1)}%` : '0%'}
            </div>
            <div className="grid grid-cols-2 gap-6 w-full max-w-md">
              <div className="text-center">
                <div className="text-3xl font-bold text-white">{analytics?.completed_calls || 0}</div>
                <div className="text-sm text-gray-400 mt-1">Successful</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-red-500">
                  {(analytics?.total_calls || 0) - (analytics?.completed_calls || 0)}
                </div>
                <div className="text-sm text-gray-400 mt-1">Failed</div>
              </div>
            </div>
          </div>
        </div>

        {/* Call Status Breakdown */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Call Status</h3>
          <p className="text-sm text-gray-400 mb-4">All agents</p>
          <div className="space-y-4 mt-6">
            {disconnectionData.length > 0 ? (
              disconnectionData.map((item, index) => (
                <div key={item.name} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-300 capitalize">{item.name.replace(/_/g, ' ')}</span>
                    <span className="text-white font-semibold">{item.value}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full transition-all duration-300"
                      style={{ 
                        width: `${(item.value / (analytics?.total_calls || 1)) * 100}%`,
                        backgroundColor: item.color 
                      }}
                    ></div>
                  </div>
                </div>
              ))
            ) : (
              <div className="h-[200px] flex items-center justify-center text-gray-500">
                <p>No status data available</p>
              </div>
            )}
          </div>
        </div>

        {/* User Sentiment */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">User Sentiment</h3>
          <p className="text-sm text-gray-400 mb-4">All agents</p>
          <div className="grid grid-cols-2 gap-4 mt-6">
            <div className="bg-gray-700 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-green-500">{analytics?.sentiment_positive || 0}</div>
              <div className="text-sm text-gray-400 mt-1">Positive</div>
            </div>
            <div className="bg-gray-700 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-red-500">{analytics?.sentiment_negative || 0}</div>
              <div className="text-sm text-gray-400 mt-1">Negative</div>
            </div>
            <div className="bg-gray-700 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-blue-500">{analytics?.sentiment_neutral || 0}</div>
              <div className="text-sm text-gray-400 mt-1">Neutral</div>
            </div>
            <div className="bg-gray-700 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-gray-400">{analytics?.sentiment_unknown || 0}</div>
              <div className="text-sm text-gray-400 mt-1">Unknown</div>
            </div>
          </div>
        </div>

        {/* Call Direction */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Call Direction</h3>
          <p className="text-sm text-gray-400 mb-4">All agents</p>
          <div className="flex items-center justify-around h-[250px]">
            <div className="text-center">
              <div className="mb-2">
                <PhoneIncoming size={48} className="text-blue-500 mx-auto" />
              </div>
              <div className="text-4xl font-bold text-white">{analytics?.by_direction?.inbound || 0}</div>
              <div className="text-sm text-gray-400 mt-2">Inbound</div>
            </div>
            <div className="h-32 w-px bg-gray-700"></div>
            <div className="text-center">
              <div className="mb-2">
                <PhoneOutgoing size={48} className="text-orange-500 mx-auto" />
              </div>
              <div className="text-4xl font-bold text-white">{analytics?.by_direction?.outbound || 0}</div>
              <div className="text-sm text-gray-400 mt-2">Outbound</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsNew;
