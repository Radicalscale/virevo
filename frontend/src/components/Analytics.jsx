import React, { useState, useEffect } from 'react';
import { BarChart3, Phone, Clock, TrendingUp, Calendar } from 'lucide-react';
import { analyticsAPI } from '../services/api';

const Analytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('all');

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const response = await analyticsAPI.callAnalytics();
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="text-white text-xl">Loading analytics...</div>
      </div>
    );
  }

  const metrics = analytics ? [
    {
      label: 'Total Calls',
      value: analytics.total_calls || 0,
      icon: Phone,
      color: 'from-blue-500 to-blue-600'
    },
    {
      label: 'Completed Calls',
      value: analytics.completed_calls || 0,
      icon: TrendingUp,
      color: 'from-green-500 to-green-600'
    },
    {
      label: 'Average Duration',
      value: analytics.avg_duration ? `${Math.floor(analytics.avg_duration / 60)}:${(analytics.avg_duration % 60).toString().padStart(2, '0')}` : '0:00',
      icon: Clock,
      color: 'from-purple-500 to-purple-600'
    },
    {
      label: 'Success Rate',
      value: analytics.success_rate ? `${analytics.success_rate.toFixed(1)}%` : '0%',
      icon: BarChart3,
      color: 'from-pink-500 to-pink-600'
    }
  ] : [];

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics</h1>
          <p className="text-gray-400">Comprehensive call analytics and insights</p>
        </div>
        
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 hover:bg-gray-700">
            <Calendar className="w-4 h-4" />
            <span>All Time</span>
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metrics.map((metric, index) => {
          const Icon = metric.icon;
          return (
            <div key={index} className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-gray-600 transition-all">
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

      {/* Call Status Breakdown */}
      {analytics?.by_status && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">Call Status Breakdown</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(analytics.by_status).map(([status, count]) => (
              <div key={status} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <p className="text-gray-400 text-sm mb-1 capitalize">{status}</p>
                <p className="text-2xl font-bold text-white">{count}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Call Direction Breakdown */}
      {analytics?.by_direction && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Call Direction</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(analytics.by_direction).map(([direction, count]) => (
              <div key={direction} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <p className="text-gray-400 text-sm mb-1 capitalize">{direction}</p>
                <p className="text-2xl font-bold text-white">{count}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;
