import React, { useState, useEffect } from 'react';
import { Phone, TrendingUp, Clock, Activity, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { agentAPI, analyticsAPI } from '../services/api';
import { Card } from './ui/card';
import { Button } from './ui/button';

const Dashboard = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [recentCalls, setRecentCalls] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [agentsRes, callsRes, analyticsRes] = await Promise.all([
          agentAPI.list(),
          analyticsAPI.callHistory({ limit: 10 }),
          analyticsAPI.dashboardAnalytics()
        ]);

        setAgents(agentsRes.data);
        setRecentCalls(callsRes.data.calls); // Updated to handle paginated response
        setAnalytics(analyticsRes.data);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const stats = analytics ? [
    {
      label: 'Total Calls Today',
      value: analytics.total_calls_today,
      change: `${analytics.calls_change_percent >= 0 ? '+' : ''}${analytics.calls_change_percent}%`,
      icon: Phone,
      color: 'from-blue-500 to-blue-600',
      positive: analytics.calls_change_percent >= 0
    },
    {
      label: 'Total Agents',
      value: analytics.active_agents,
      change: '',
      icon: Activity,
      color: 'from-purple-500 to-purple-600'
    },
    {
      label: 'Avg Response Time',
      value: `${analytics.avg_response_time}s`,
      change: '',
      icon: Clock,
      color: 'from-green-500 to-green-600'
    },
    {
      label: 'Success Rate',
      value: `${analytics.success_rate}%`,
      change: '',
      icon: TrendingUp,
      color: 'from-pink-500 to-pink-600'
    },
    {
      label: 'Voicemail Detected',
      value: analytics.voicemail_detected_today,
      change: `${analytics.voicemail_rate}%`,
      icon: Phone,
      color: 'from-orange-500 to-red-600',
      subtitle: `${analytics.voicemail_detected_all_time} all-time`
    }
  ] : [];

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="text-white text-xl">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
          <p className="text-gray-400">Monitor your AI voice agents performance</p>
        </div>
        <Button
          onClick={() => navigate('/agents/new')}
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/20"
        >
          <Plus size={20} className="mr-2" />
          Create Agent
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="bg-gray-800 border-gray-700 p-6 hover:border-gray-600 transition-all duration-200">
              <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-lg bg-gradient-to-r ${stat.color} bg-opacity-10`}>
                  <Icon size={24} className="text-white" />
                </div>
                {stat.change && (
                  <span className={`text-sm font-medium ${stat.positive !== undefined
                      ? (stat.positive ? 'text-green-400' : 'text-red-400')
                      : 'text-orange-400'
                    }`}>
                    {stat.change}
                  </span>
                )}
              </div>
              <p className="text-gray-400 text-sm mb-1">{stat.label}</p>
              <p className="text-3xl font-bold text-white">{stat.value}</p>
              {stat.subtitle && (
                <p className="text-gray-500 text-xs mt-1">{stat.subtitle}</p>
              )}
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="bg-gray-800 border-gray-700 p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Agents</h2>
          <div className="space-y-3">
            {agents.length > 0 ? (
              agents.slice(0, 5).map((agent) => (
                <div
                  key={agent.id}
                  onClick={() => navigate(`/agents/${agent.id}`)}
                  className="flex items-center justify-between p-4 bg-gray-900 rounded-lg hover:bg-gray-850 cursor-pointer transition-all duration-200 border border-gray-700 hover:border-gray-600"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center text-white font-semibold">
                      {agent.name?.charAt(0) || 'A'}
                    </div>
                    <div>
                      <p className="text-white font-medium">{agent.name}</p>
                      <p className="text-gray-400 text-sm capitalize">{agent.agent_type || 'single_prompt'}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-blue-400 font-medium text-sm">View Agent</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-400">
                <p>No agents created yet</p>
                <button
                  onClick={() => navigate('/agents/new')}
                  className="mt-4 text-blue-400 hover:text-blue-300"
                >
                  Create your first agent
                </button>
              </div>
            )}
          </div>
        </Card>

        <Card className="bg-gray-800 border-gray-700 p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Recent Calls</h2>
          <div className="space-y-3">
            {recentCalls.length > 0 ? (
              recentCalls.map((call) => (
                <div
                  key={call.call_id}
                  onClick={() => navigate('/calls')}
                  className="flex items-center justify-between p-4 bg-gray-900 rounded-lg hover:bg-gray-850 cursor-pointer transition-all duration-200 border border-gray-700 hover:border-gray-600"
                >
                  <div>
                    <p className="text-white font-medium">{call.to_number || 'Unknown'}</p>
                    <p className="text-gray-400 text-sm capitalize">{call.direction || 'outbound'}</p>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium text-sm ${call.status === 'completed' ? 'text-green-400' : 'text-gray-400'
                      }`}>
                      {call.status}
                    </p>
                    <p className="text-gray-400 text-xs">
                      {call.duration ? `${Math.floor(call.duration / 60)}:${(call.duration % 60).toString().padStart(2, '0')}` : '0:00'}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-400">
                <p>No calls yet</p>
                <button
                  onClick={() => navigate('/test-call')}
                  className="mt-4 text-blue-400 hover:text-blue-300"
                >
                  Make a test call
                </button>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
