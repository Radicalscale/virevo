import React, { useState, useEffect } from 'react';
import { Plus, Search, Filter, Upload, Download, Phone, Mail, Calendar, Edit, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useToast } from '../hooks/use-toast';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const CRM = () => {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingLead, setDeletingLead] = useState(null);
  const { toast } = useToast();

  // Status colors
  const statusColors = {
    new: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    contacted: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    qualified: 'bg-green-500/20 text-green-400 border-green-500/30',
    appointment_set: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    appointment_confirmed: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    showed_up: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    no_show: 'bg-red-500/20 text-red-400 border-red-500/30',
    customer: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
    dead: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  };

  // Source icons
  const sourceIcons = {
    inbound_call: Phone,
    outbound_call: Phone,
    web_form: Mail,
    manual_entry: Plus,
    import: Upload,
    ad_campaign: Calendar
  };

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [searchTerm, statusFilter, sourceFilter]);

  const fetchLeads = async () => {
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (statusFilter) params.append('status', statusFilter);
      if (sourceFilter) params.append('source', sourceFilter);
      params.append('limit', '100');

      const response = await axios.get(`${BACKEND_URL}/api/crm/leads?${params.toString()}`, {
        withCredentials: true
      });
      setLeads(response.data);
    } catch (error) {
      console.error('Error fetching leads:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch leads',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/crm/leads/stats`, {
        withCredentials: true
      });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleEdit = (leadId) => {
    // Navigate to lead detail page where they can edit
    window.location.href = `/crm/leads/${leadId}`;
  };

  const handleDeleteClick = (lead) => {
    setDeletingLead(lead);
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    if (!deletingLead) return;

    try {
      await axios.delete(`${BACKEND_URL}/api/crm/leads/${deletingLead.id}`, {
        withCredentials: true
      });
      
      toast({
        title: 'Lead Deleted',
        description: `${deletingLead.name} has been removed from your CRM`,
      });
      
      setShowDeleteConfirm(false);
      setDeletingLead(null);
      fetchLeads(); // Refresh the list
      fetchStats(); // Refresh stats
    } catch (error) {
      console.error('Error deleting lead:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete lead',
        variant: 'destructive'
      });
    }
  };

  const formatStatus = (status) => {
    return status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const getScoreColor = (score) => {
    if (!score) return 'text-gray-400';
    if (score >= 75) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="p-8 bg-gray-900 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">CRM Dashboard</h1>
        <p className="text-gray-400">Manage your leads, appointments, and customer relationships</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-gray-400 text-sm font-medium">Total Leads</h3>
              <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <Phone className="text-blue-400" size={20} />
              </div>
            </div>
            <p className="text-3xl font-bold text-white">{stats.total}</p>
            <p className="text-xs text-gray-500 mt-1">All time</p>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-gray-400 text-sm font-medium">Appointments Set</h3>
              <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                <Calendar className="text-yellow-400" size={20} />
              </div>
            </div>
            <p className="text-3xl font-bold text-white">
              {stats.by_status?.appointment_set || 0 + stats.by_status?.appointment_confirmed || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">Active appointments</p>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-gray-400 text-sm font-medium">Showed Up</h3>
              <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
              </div>
            </div>
            <p className="text-3xl font-bold text-white">{stats.by_status?.showed_up || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Confirmed attendees</p>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-gray-400 text-sm font-medium">Customers</h3>
              <div className="w-10 h-10 bg-indigo-500/20 rounded-lg flex items-center justify-center">
                <div className="w-2 h-2 bg-indigo-400 rounded-full"></div>
              </div>
            </div>
            <p className="text-3xl font-bold text-white">{stats.by_status?.customer || 0}</p>
            <p className="text-xs text-gray-500 mt-1">Converted</p>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[300px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Search by name, email, or phone..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="appointment_set">Appointment Set</option>
            <option value="appointment_confirmed">Confirmed</option>
            <option value="showed_up">Showed Up</option>
            <option value="no_show">No Show</option>
            <option value="customer">Customer</option>
            <option value="dead">Dead</option>
          </select>

          {/* Source Filter */}
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Sources</option>
            <option value="inbound_call">Inbound Call</option>
            <option value="outbound_call">Outbound Call</option>
            <option value="ad_campaign">Ad Campaign</option>
            <option value="web_form">Web Form</option>
            <option value="manual_entry">Manual Entry</option>
            <option value="import">Import</option>
          </select>

          {/* Action Buttons */}
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 flex items-center gap-2"
          >
            <Plus size={20} />
            Add Lead
          </button>

          <Link
            to="/crm/import"
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-all duration-200 flex items-center gap-2"
          >
            <Upload size={20} />
            Import
          </Link>
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading leads...</div>
        ) : leads.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <p className="mb-4">No leads found</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Add Your First Lead
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-900 border-b border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Lead</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Contact</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Source</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">QC Scores</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Last Contact</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {leads.map((lead) => {
                  const SourceIcon = sourceIcons[lead.source] || Phone;
                  return (
                    <tr key={lead.id} className="hover:bg-gray-750 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <p className="text-white font-medium">{lead.name}</p>
                          <p className="text-sm text-gray-400">
                            {lead.total_calls} calls | {lead.total_appointments} appts
                          </p>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm">
                          <p className="text-gray-300">{lead.phone}</p>
                          {lead.email && <p className="text-gray-400">{lead.email}</p>}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${statusColors[lead.status]}`}>
                          {formatStatus(lead.status)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <SourceIcon size={16} className="text-gray-400" />
                          <span className="text-sm text-gray-300">{formatStatus(lead.source)}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex gap-3 text-sm">
                          {lead.commitment_score !== null && (
                            <div>
                              <span className="text-gray-400">C:</span>
                              <span className={`ml-1 font-medium ${getScoreColor(lead.commitment_score)}`}>
                                {lead.commitment_score}
                              </span>
                            </div>
                          )}
                          {lead.conversion_score !== null && (
                            <div>
                              <span className="text-gray-400">F:</span>
                              <span className={`ml-1 font-medium ${getScoreColor(lead.conversion_score)}`}>
                                {lead.conversion_score}
                              </span>
                            </div>
                          )}
                          {lead.show_up_probability !== null && (
                            <div>
                              <span className="text-gray-400">S:</span>
                              <span className={`ml-1 font-medium ${getScoreColor(lead.show_up_probability)}`}>
                                {lead.show_up_probability}%
                              </span>
                            </div>
                          )}
                          {lead.commitment_score === null && lead.conversion_score === null && (
                            <span className="text-gray-500 text-xs">No data</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                        {lead.last_contact ? formatDate(lead.last_contact) : 'Never'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/crm/leads/${lead.id}`}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs flex items-center gap-1"
                          >
                            View
                          </Link>
                          <button
                            onClick={() => handleEdit(lead.id)}
                            className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded text-xs flex items-center gap-1"
                            title="Edit Lead"
                          >
                            <Edit size={14} />
                          </button>
                          <button
                            onClick={() => handleDeleteClick(lead)}
                            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs flex items-center gap-1"
                            title="Delete Lead"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold text-white mb-4">Delete Lead</h3>
            <p className="text-gray-300 mb-6">
              Are you sure you want to delete <strong>{deletingLead?.name}</strong>? 
              This will permanently remove this lead and all associated data including calls, appointments, and QC analysis.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeletingLead(null);
                }}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CRM;
