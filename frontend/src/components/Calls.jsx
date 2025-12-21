import React, { useState, useEffect } from 'react';
import { Phone, Download, Trash2, Filter, Calendar, Search, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import CallDetailModal from './CallDetailModal';
import { analyticsAPI } from '../services/api';

const Calls = () => {
  const navigate = useNavigate();
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCalls, setTotalCalls] = useState(0);
  const [limit] = useState(50);
  const [filters, setFilters] = useState({
    agent_id: '',
    direction: '',
    status: '',
    start_date: '',
    end_date: ''
  });
  const [durationFilter, setDurationFilter] = useState({
    enabled: false,
    operator: 'greater_than', // 'greater_than', 'less_than', 'between'
    value: '',
    value2: '', // for 'between'
    unit: 'mins' // 'secs', 'mins'
  });
  const [showDurationModal, setShowDurationModal] = useState(false);

  const [dateFilter, setDateFilter] = useState({
    enabled: false,
    operator: 'on', // 'on', 'before', 'after', 'between'
    value: '',
    value2: '' // for 'between'
  });
  const [showDateModal, setShowDateModal] = useState(false);

  const [fromNumberFilter, setFromNumberFilter] = useState({
    enabled: false,
    operator: 'contains', // 'contains', 'equals', 'starts_with', 'ends_with'
    value: ''
  });
  const [showFromNumberModal, setShowFromNumberModal] = useState(false);

  const [toNumberFilter, setToNumberFilter] = useState({
    enabled: false,
    operator: 'contains', // 'contains', 'equals', 'starts_with', 'ends_with'
    value: ''
  });
  const [showToNumberModal, setShowToNumberModal] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  useEffect(() => {
    fetchCalls();
    fetchAnalytics();
  }, [currentPage]); // Re-fetch when page changes

  const fetchCalls = async () => {
    try {
      setLoading(true);
      const params = {
        limit: limit,
        offset: (currentPage - 1) * limit
      };

      if (filters.agent_id) params.agent_id = filters.agent_id;
      if (filters.direction) params.direction = filters.direction;
      if (filters.status) params.status = filters.status;
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;

      const response = await analyticsAPI.callHistory(params);

      // Handle both paginated and legacy responses
      if (response.data.calls) {
        setCalls(response.data.calls);
        setTotalCalls(response.data.total);
      } else if (Array.isArray(response.data)) {
        setCalls(response.data);
        setTotalCalls(response.data.length);
      } else {
        setCalls([]);
        setTotalCalls(0);
      }
    } catch (error) {
      console.error('Error fetching calls:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await analyticsAPI.callAnalytics();
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const applyFilters = () => {
    setCurrentPage(1); // Reset to first page
    fetchCalls();
    fetchAnalytics();
  };

  const clearFilters = () => {
    setFilters({
      agent_id: '',
      direction: '',
      status: '',
      start_date: '',
      end_date: ''
    });
    setDurationFilter({
      enabled: false,
      operator: 'greater_than',
      value: '',
      value2: '',
      unit: 'mins'
    });
    setDateFilter({
      enabled: false,
      operator: 'on',
      value: '',
      value2: ''
    });
    setFromNumberFilter({
      enabled: false,
      operator: 'contains',
      value: ''
    });
    setToNumberFilter({
      enabled: false,
      operator: 'contains',
      value: ''
    });
    setTimeout(() => {
      fetchCalls();
      fetchAnalytics();
    }, 100);
  };

  const applyDurationFilter = () => {
    if (durationFilter.value) {
      setDurationFilter(prev => ({ ...prev, enabled: true }));
    }
    setShowDurationModal(false);
    setTimeout(() => fetchCalls(), 100);
  };

  const applyDateFilter = () => {
    if (dateFilter.value) {
      setDateFilter(prev => ({ ...prev, enabled: true }));
    }
    setShowDateModal(false);
    setTimeout(() => fetchCalls(), 100);
  };

  const applyFromNumberFilter = () => {
    if (fromNumberFilter.value) {
      setFromNumberFilter(prev => ({ ...prev, enabled: true }));
    }
    setShowFromNumberModal(false);
    setTimeout(() => fetchCalls(), 100);
  };

  const applyToNumberFilter = () => {
    if (toNumberFilter.value) {
      setToNumberFilter(prev => ({ ...prev, enabled: true }));
    }
    setShowToNumberModal(false);
    setTimeout(() => fetchCalls(), 100);
  };

  const getFilteredCalls = () => {
    let filteredCalls = calls;

    // Apply duration filter
    if (durationFilter.enabled && durationFilter.value) {
      const multiplier = durationFilter.unit === 'mins' ? 60 : 1;
      const targetDuration = parseFloat(durationFilter.value) * multiplier;
      const targetDuration2 = durationFilter.value2 ? parseFloat(durationFilter.value2) * multiplier : 0;

      filteredCalls = filteredCalls.filter(call => {
        const callDuration = call.duration || 0;
        switch (durationFilter.operator) {
          case 'greater_than':
            return callDuration > targetDuration;
          case 'less_than':
            return callDuration < targetDuration;
          case 'between':
            return callDuration >= targetDuration && callDuration <= targetDuration2;
          default:
            return true;
        }
      });
    }

    // Apply date filter
    if (dateFilter.enabled && dateFilter.value) {
      filteredCalls = filteredCalls.filter(call => {
        if (!call.start_time) return false;
        const callDate = new Date(call.start_time).toISOString().split('T')[0];
        const filterDate = dateFilter.value;
        const filterDate2 = dateFilter.value2;

        switch (dateFilter.operator) {
          case 'on':
            return callDate === filterDate;
          case 'before':
            return callDate < filterDate;
          case 'after':
            return callDate > filterDate;
          case 'between':
            return callDate >= filterDate && callDate <= filterDate2;
          default:
            return true;
        }
      });
    }

    // Apply from number filter
    if (fromNumberFilter.enabled && fromNumberFilter.value) {
      const searchValue = fromNumberFilter.value.toLowerCase();
      filteredCalls = filteredCalls.filter(call => {
        const fromNumber = (call.from_number || '').toLowerCase();
        switch (fromNumberFilter.operator) {
          case 'contains':
            return fromNumber.includes(searchValue);
          case 'equals':
            return fromNumber === searchValue;
          case 'starts_with':
            return fromNumber.startsWith(searchValue);
          case 'ends_with':
            return fromNumber.endsWith(searchValue);
          default:
            return true;
        }
      });
    }

    // Apply to number filter
    if (toNumberFilter.enabled && toNumberFilter.value) {
      const searchValue = toNumberFilter.value.toLowerCase();
      filteredCalls = filteredCalls.filter(call => {
        const toNumber = (call.to_number || '').toLowerCase();
        switch (toNumberFilter.operator) {
          case 'contains':
            return toNumber.includes(searchValue);
          case 'equals':
            return toNumber === searchValue;
          case 'starts_with':
            return toNumber.startsWith(searchValue);
          case 'ends_with':
            return toNumber.endsWith(searchValue);
          default:
            return true;
        }
      });
    }

    return filteredCalls;
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getStatusBadge = (status) => {
    const colors = {
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      queued: 'bg-yellow-100 text-yellow-800',
      answered: 'bg-blue-100 text-blue-800',
      voicemail_detected: 'bg-orange-100 text-orange-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const handleViewDetails = (callId) => {
    setSelectedCallId(callId);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedCallId(null);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <CallDetailModal
        callId={selectedCallId}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Phone className="w-8 h-8" />
              Call History
            </h1>
            <p className="text-gray-400 mt-2">View and analyze your call logs</p>
          </div>
        </div>

        {/* Analytics Cards */}
        {analytics && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <div className="text-gray-400 text-sm mb-2">Total Calls</div>
              <div className="text-3xl font-bold">{analytics.total_calls}</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <div className="text-gray-400 text-sm mb-2">Successful</div>
              <div className="text-3xl font-bold text-green-400">{analytics.successful_calls}</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
              <div className="text-gray-400 text-sm mb-2">Avg Duration</div>
              <div className="text-3xl font-bold">{formatDuration(analytics.avg_duration || 0)}</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-gray-900 rounded-lg p-6 border border-gray-800 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-5 h-5" />
            <h2 className="text-lg font-semibold">Filters</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Direction</label>
              <select
                name="direction"
                value={filters.direction}
                onChange={handleFilterChange}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              >
                <option value="">All</option>
                <option value="inbound">Inbound</option>
                <option value="outbound">Outbound</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Status</label>
              <select
                name="status"
                value={filters.status}
                onChange={handleFilterChange}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              >
                <option value="">All</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="queued">Queued</option>
                <option value="voicemail_detected">Voicemail Detected</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Start Date</label>
              <input
                type="date"
                name="start_date"
                value={filters.start_date}
                onChange={handleFilterChange}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">End Date</label>
              <input
                type="date"
                name="end_date"
                value={filters.end_date}
                onChange={handleFilterChange}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              />
            </div>

            <div className="flex items-end gap-2">
              <button
                onClick={applyFilters}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium"
              >
                Apply
              </button>
              <button
                onClick={clearFilters}
                className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Advanced Filter Buttons */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {/* Duration Filter Button */}
            <button
              onClick={() => setShowDurationModal(true)}
              className={`flex items-center gap-2 px-4 py-2 rounded border ${durationFilter.enabled
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
                }`}
            >
              <Filter className="w-4 h-4" />
              Duration
              {durationFilter.enabled && (
                <span className="ml-1 px-2 py-0.5 bg-blue-500 rounded text-xs">
                  {durationFilter.operator === 'greater_than' && `> ${durationFilter.value} ${durationFilter.unit}`}
                  {durationFilter.operator === 'less_than' && `< ${durationFilter.value} ${durationFilter.unit}`}
                  {durationFilter.operator === 'between' && `${durationFilter.value}-${durationFilter.value2} ${durationFilter.unit}`}
                </span>
              )}
            </button>

            {/* Date Filter Button */}
            <button
              onClick={() => setShowDateModal(true)}
              className={`flex items-center gap-2 px-4 py-2 rounded border ${dateFilter.enabled
                ? 'bg-green-600 border-green-500 text-white'
                : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
                }`}
            >
              <Calendar className="w-4 h-4" />
              Date
              {dateFilter.enabled && (
                <span className="ml-1 px-2 py-0.5 bg-green-500 rounded text-xs">
                  {dateFilter.operator === 'on' && `on ${dateFilter.value}`}
                  {dateFilter.operator === 'before' && `before ${dateFilter.value}`}
                  {dateFilter.operator === 'after' && `after ${dateFilter.value}`}
                  {dateFilter.operator === 'between' && `${dateFilter.value} - ${dateFilter.value2}`}
                </span>
              )}
            </button>

            {/* From Number Filter Button */}
            <button
              onClick={() => setShowFromNumberModal(true)}
              className={`flex items-center gap-2 px-4 py-2 rounded border ${fromNumberFilter.enabled
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
                }`}
            >
              <Phone className="w-4 h-4" />
              From Number
              {fromNumberFilter.enabled && (
                <span className="ml-1 px-2 py-0.5 bg-purple-500 rounded text-xs">
                  {fromNumberFilter.operator === 'contains' && `contains "${fromNumberFilter.value}"`}
                  {fromNumberFilter.operator === 'equals' && `= "${fromNumberFilter.value}"`}
                  {fromNumberFilter.operator === 'starts_with' && `starts "${fromNumberFilter.value}"`}
                  {fromNumberFilter.operator === 'ends_with' && `ends "${fromNumberFilter.value}"`}
                </span>
              )}
            </button>

            {/* To Number Filter Button */}
            <button
              onClick={() => setShowToNumberModal(true)}
              className={`flex items-center gap-2 px-4 py-2 rounded border ${toNumberFilter.enabled
                ? 'bg-orange-600 border-orange-500 text-white'
                : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
                }`}
            >
              <Phone className="w-4 h-4" />
              To Number
              {toNumberFilter.enabled && (
                <span className="ml-1 px-2 py-0.5 bg-orange-500 rounded text-xs">
                  {toNumberFilter.operator === 'contains' && `contains "${toNumberFilter.value}"`}
                  {toNumberFilter.operator === 'equals' && `= "${toNumberFilter.value}"`}
                  {toNumberFilter.operator === 'starts_with' && `starts "${toNumberFilter.value}"`}
                  {toNumberFilter.operator === 'ends_with' && `ends "${toNumberFilter.value}"`}
                </span>
              )}
            </button>

            {/* Clear individual filters */}
            {(durationFilter.enabled || dateFilter.enabled || fromNumberFilter.enabled || toNumberFilter.enabled) && (
              <button
                onClick={() => {
                  setDurationFilter({ enabled: false, operator: 'greater_than', value: '', value2: '', unit: 'mins' });
                  setDateFilter({ enabled: false, operator: 'on', value: '', value2: '' });
                  setFromNumberFilter({ enabled: false, operator: 'contains', value: '' });
                  setToNumberFilter({ enabled: false, operator: 'contains', value: '' });
                  setTimeout(() => fetchCalls(), 100);
                }}
                className="text-sm text-gray-400 hover:text-white ml-2"
              >
                Clear All Advanced Filters
              </button>
            )}
          </div>
        </div>

        {/* Calls Table */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Direction
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    From
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    To
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {loading ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-12 text-center text-gray-400">
                      Loading calls...
                    </td>
                  </tr>
                ) : getFilteredCalls().length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-12 text-center text-gray-400">
                      No calls found
                    </td>
                  </tr>
                ) : (
                  getFilteredCalls().map((call) => (
                    <tr
                      key={call.id}
                      className="hover:bg-gray-800 cursor-pointer"
                      onClick={() => handleViewDetails(call.call_id)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {formatDate(call.start_time)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className="capitalize">{call.direction}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                        {call.from_number || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                        {call.to_number || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {formatDuration(call.duration || 0)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(call.status)}`}>
                          {call.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleViewDetails(call.call_id)}
                          className="text-gray-400 hover:text-white mr-3"
                          title="View Details"
                        >
                          <Search className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => navigate(`/qc/calls/${call.call_id}`)}
                          className="text-purple-400 hover:text-purple-300 mr-3"
                          title="QC Analysis"
                        >
                          <Zap className="w-4 h-4" />
                        </button>
                        <button
                          className="text-red-400 hover:text-red-300"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination Controls */}
        <div className="mt-4 flex items-center justify-between bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-sm text-gray-400">
            Showing <span className="font-medium text-white">{Math.min((currentPage - 1) * limit + 1, totalCalls)}</span> to <span className="font-medium text-white">{Math.min(currentPage * limit, totalCalls)}</span> of <span className="font-medium text-white">{totalCalls}</span> results
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={currentPage * limit >= totalCalls}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Duration Filter Modal */}
      {showDurationModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg p-6 w-full max-w-md border border-gray-700">
            <h3 className="text-xl font-bold text-white mb-4">Filter by Duration</h3>

            <div className="space-y-4">
              {/* Operator Selection */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Condition</label>
                <select
                  value={durationFilter.operator}
                  onChange={(e) => setDurationFilter(prev => ({ ...prev, operator: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                >
                  <option value="greater_than">is greater than</option>
                  <option value="less_than">is less than</option>
                  <option value="between">is between</option>
                </select>
              </div>

              {/* Value Input */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block text-sm text-gray-400 mb-2">
                    {durationFilter.operator === 'between' ? 'Min Value' : 'Value'}
                  </label>
                  <input
                    type="number"
                    value={durationFilter.value}
                    onChange={(e) => setDurationFilter(prev => ({ ...prev, value: e.target.value }))}
                    placeholder="0"
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                    min="0"
                    step="0.1"
                  />
                </div>

                {durationFilter.operator === 'between' && (
                  <div className="flex-1">
                    <label className="block text-sm text-gray-400 mb-2">Max Value</label>
                    <input
                      type="number"
                      value={durationFilter.value2}
                      onChange={(e) => setDurationFilter(prev => ({ ...prev, value2: e.target.value }))}
                      placeholder="0"
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                      min="0"
                      step="0.1"
                    />
                  </div>
                )}

                {/* Unit Selection */}
                <div className="w-24">
                  <label className="block text-sm text-gray-400 mb-2">Unit</label>
                  <select
                    value={durationFilter.unit}
                    onChange={(e) => setDurationFilter(prev => ({ ...prev, unit: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  >
                    <option value="secs">secs</option>
                    <option value="mins">mins</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowDurationModal(false)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
              <button
                onClick={applyDurationFilter}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                disabled={!durationFilter.value}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Date Filter Modal */}
      {showDateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg p-6 w-full max-w-md border border-gray-700">
            <h3 className="text-xl font-bold text-white mb-4">Filter by Date</h3>

            <div className="space-y-4">
              {/* Operator Selection */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Condition</label>
                <select
                  value={dateFilter.operator}
                  onChange={(e) => setDateFilter(prev => ({ ...prev, operator: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                >
                  <option value="on">is on</option>
                  <option value="before">is before</option>
                  <option value="after">is after</option>
                  <option value="between">is between</option>
                </select>
              </div>

              {/* Date Input */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block text-sm text-gray-400 mb-2">
                    {dateFilter.operator === 'between' ? 'Start Date' : 'Date'}
                  </label>
                  <input
                    type="date"
                    value={dateFilter.value}
                    onChange={(e) => setDateFilter(prev => ({ ...prev, value: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  />
                </div>

                {dateFilter.operator === 'between' && (
                  <div className="flex-1">
                    <label className="block text-sm text-gray-400 mb-2">End Date</label>
                    <input
                      type="date"
                      value={dateFilter.value2}
                      onChange={(e) => setDateFilter(prev => ({ ...prev, value2: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowDateModal(false)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
              <button
                onClick={applyDateFilter}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
                disabled={!dateFilter.value}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* From Number Filter Modal */}
      {showFromNumberModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg p-6 w-full max-w-md border border-gray-700">
            <h3 className="text-xl font-bold text-white mb-4">Filter by From Number</h3>

            <div className="space-y-4">
              {/* Operator Selection */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Condition</label>
                <select
                  value={fromNumberFilter.operator}
                  onChange={(e) => setFromNumberFilter(prev => ({ ...prev, operator: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                >
                  <option value="contains">contains</option>
                  <option value="equals">equals</option>
                  <option value="starts_with">starts with</option>
                  <option value="ends_with">ends with</option>
                </select>
              </div>

              {/* Phone Number Input */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Phone Number</label>
                <input
                  type="text"
                  value={fromNumberFilter.value}
                  onChange={(e) => setFromNumberFilter(prev => ({ ...prev, value: e.target.value }))}
                  placeholder="e.g., +1234567890"
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowFromNumberModal(false)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
              <button
                onClick={applyFromNumberFilter}
                className="flex-1 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded"
                disabled={!fromNumberFilter.value}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* To Number Filter Modal */}
      {showToNumberModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg p-6 w-full max-w-md border border-gray-700">
            <h3 className="text-xl font-bold text-white mb-4">Filter by To Number</h3>

            <div className="space-y-4">
              {/* Operator Selection */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Condition</label>
                <select
                  value={toNumberFilter.operator}
                  onChange={(e) => setToNumberFilter(prev => ({ ...prev, operator: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                >
                  <option value="contains">contains</option>
                  <option value="equals">equals</option>
                  <option value="starts_with">starts with</option>
                  <option value="ends_with">ends with</option>
                </select>
              </div>

              {/* Phone Number Input */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Phone Number</label>
                <input
                  type="text"
                  value={toNumberFilter.value}
                  onChange={(e) => setToNumberFilter(prev => ({ ...prev, value: e.target.value }))}
                  placeholder="e.g., +1234567890"
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowToNumberModal(false)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
              <button
                onClick={applyToNumberFilter}
                className="flex-1 bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded"
                disabled={!toNumberFilter.value}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Calls;
