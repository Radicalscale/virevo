import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Phone,
  BarChart3,
  Settings,
  PhoneCall,
  LogOut,
  UserCheck,
  TestTube,
  TrendingUp,
  Brain,
  PieChart,
  Mic,
  FileText,
  Wrench,
  GraduationCap,
  Zap,
  ChevronDown,
  ChevronRight,
  Plus,
  Activity
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const Sidebar = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [qcAgentsExpanded, setQcAgentsExpanded] = useState(
    location.pathname.includes('/qc/agents')
  );

  // Main navigation items
  const mainItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/agents', icon: Users, label: 'Call Agents' },
    { path: '/test-call', icon: PhoneCall, label: 'Test Call', highlight: true },
    { path: '/calls', icon: Phone, label: 'Call History' },
    { path: '/numbers', icon: Phone, label: 'Phone Numbers' },
    { path: '/crm', icon: UserCheck, label: 'CRM' },
  ];

  // QC System items - grouped together (without QC Agents, handled separately)
  const qcItems = [
    { path: '/director', icon: Activity, label: 'Director Studio', highlight: true, description: 'Evolve agent tonality' },
    { path: '/qc/campaigns', icon: TrendingUp, label: 'QC Campaigns', description: 'Campaign analysis' },
    { path: '/qc/analytics', icon: PieChart, label: 'QC Analytics', highlight: true, description: 'Metrics & ratios' },
  ];

  // Settings
  const settingsItems = [
    { path: '/analytics', icon: BarChart3, label: 'Analytics' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  const renderNavItem = (item) => {
    const Icon = item.icon;
    const isActive = location.pathname === item.path ||
      (item.path !== '/' && location.pathname.startsWith(item.path));

    return (
      <Link
        key={item.path}
        to={item.path}
        className={`flex items-center gap-3 px-4 py-2.5 rounded-lg mb-1 transition-all duration-200 ${isActive
            ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/20'
            : item.highlight
              ? 'bg-purple-600/10 border border-purple-500/30 text-purple-400 hover:bg-purple-600/20'
              : 'text-gray-400 hover:bg-gray-800 hover:text-white'
          }`}
        title={item.description}
      >
        <Icon size={18} />
        <span className="font-medium text-sm">{item.label}</span>
        {item.highlight && (
          <span className="ml-auto text-xs bg-purple-500 text-white px-1.5 py-0.5 rounded-full">
            NEW
          </span>
        )}
      </Link>
    );
  };

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 h-screen fixed left-0 top-0 flex flex-col overflow-y-auto">
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          Andromeda
        </h1>
        <p className="text-gray-400 text-sm mt-1">Voice AI Platform</p>
      </div>

      <nav className="flex-1 p-4">
        {/* Main Navigation */}
        <div className="mb-6">
          <p className="text-xs text-gray-500 uppercase font-semibold px-4 mb-2">Main</p>
          {mainItems.map(renderNavItem)}
        </div>

        {/* QC System Section */}
        <div className="mb-6">
          <p className="text-xs text-gray-500 uppercase font-semibold px-4 mb-2 flex items-center gap-2">
            <Zap size={12} className="text-purple-400" />
            QC System
          </p>

          {/* QC Agents with Expandable Submenu */}
          <div className="mb-1">
            {/* Main QC Agents Link with Expand Toggle */}
            <div className="flex items-center">
              <Link
                to="/qc/agents"
                className={`flex-1 flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${location.pathname === '/qc/agents' || location.pathname.startsWith('/qc/agents/')
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`}
              >
                <Brain size={18} />
                <span className="text-sm">QC Agents</span>
              </Link>
              <button
                onClick={() => setQcAgentsExpanded(!qcAgentsExpanded)}
                className="p-2 text-gray-400 hover:text-white"
              >
                {qcAgentsExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </button>
            </div>

            {/* Submenu - Create QC Agent Types */}
            {qcAgentsExpanded && (
              <div className="ml-6 mt-1 pl-4 border-l border-gray-800 space-y-1">
                <p className="text-xs text-gray-600 mb-2 flex items-center gap-1">
                  <Plus size={10} />
                  Create New:
                </p>
                <Link
                  to="/qc/agents/new?type=tonality"
                  className={`flex items-center gap-2 text-xs py-1.5 px-2 rounded transition-colors ${location.search.includes('type=tonality')
                      ? 'text-purple-400 bg-purple-900/20'
                      : 'text-gray-500 hover:text-purple-400 hover:bg-gray-800/50'
                    }`}
                >
                  <Mic size={12} />
                  Tonality Agent
                </Link>
                <Link
                  to="/qc/agents/new?type=language_pattern"
                  className={`flex items-center gap-2 text-xs py-1.5 px-2 rounded transition-colors ${location.search.includes('type=language_pattern')
                      ? 'text-blue-400 bg-blue-900/20'
                      : 'text-gray-500 hover:text-blue-400 hover:bg-gray-800/50'
                    }`}
                >
                  <FileText size={12} />
                  Language Pattern
                </Link>
                <Link
                  to="/qc/agents/new?type=tech_issues"
                  className={`flex items-center gap-2 text-xs py-1.5 px-2 rounded transition-colors ${location.search.includes('type=tech_issues')
                      ? 'text-orange-400 bg-orange-900/20'
                      : 'text-gray-500 hover:text-orange-400 hover:bg-gray-800/50'
                    }`}
                >
                  <Wrench size={12} />
                  Tech Issues
                </Link>
              </div>
            )}
          </div>

          {/* Other QC Items */}
          {qcItems.map(renderNavItem)}
        </div>

        {/* Settings */}
        <div>
          <p className="text-xs text-gray-500 uppercase font-semibold px-4 mb-2">Settings</p>
          {settingsItems.map(renderNavItem)}
        </div>
      </nav>

      {/* User info and logout */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-3 px-4 py-3 bg-gray-800 rounded-lg mb-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-white font-medium">
            {user?.email?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.email || 'User'}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition-all duration-200 w-full"
        >
          <LogOut size={20} />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
