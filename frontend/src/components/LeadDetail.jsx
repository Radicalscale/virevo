import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Phone, Mail, Calendar, Clock, Edit, Trash2, Plus, ChevronDown, ChevronUp } from 'lucide-react';
import axios from 'axios';
import { useToast } from '../hooks/use-toast';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const LeadDetail = () => {
  const { leadId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [lead, setLead] = useState(null);
  const [calls, setCalls] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [analytics, setAnalytics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedAppointments, setExpandedAppointments] = useState({});

  useEffect(() => {
    fetchLeadData();
  }, [leadId]);

  const fetchLeadData = async () => {
    try {
      // Fetch lead
      const leadResponse = await axios.get(`${BACKEND_URL}/api/crm/leads/${leadId}`, {
        withCredentials: true
      });
      setLead(leadResponse.data);

      // Fetch appointments for this lead
      const apptsResponse = await axios.get(`${BACKEND_URL}/api/crm/appointments?lead_id=${leadId}`, {
        withCredentials: true
      });
      setAppointments(apptsResponse.data);

      // Fetch call analytics for this lead
      const analyticsResponse = await axios.get(`${BACKEND_URL}/api/crm/analytics/lead/${leadId}`, {
        withCredentials: true
      });
      setAnalytics(analyticsResponse.data);

      // Fetch calls for this lead (if calls are linked)
      // This assumes calls have a lead_id field
      const callsResponse = await axios.get(`${BACKEND_URL}/api/calls?limit=100`, {
        withCredentials: true
      });
      // Filter calls for this lead (you may need to add lead_id to Call model)
      setCalls(callsResponse.data.filter(call => call.metadata?.lead_id === leadId));

    } catch (error) {
      console.error('Error fetching lead data:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch lead data',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const toggleAppointment = (apptId) => {
    setExpandedAppointments(prev => ({
      ...prev,
      [apptId]: !prev[apptId]
    }));
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatStatus = (status) => {
    return status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  const getStatusColor = (status) => {
    const colors = {
      new: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      contacted: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      qualified: 'bg-green-500/20 text-green-400 border-green-500/30',
      appointment_set: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      appointment_confirmed: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      showed_up: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      no_show: 'bg-red-500/20 text-red-400 border-red-500/30',
      customer: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
      scheduled: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      confirmed: 'bg-green-500/20 text-green-400 border-green-500/30',
      cancelled: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    };
    return colors[status] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  };

  const getScoreColor = (score) => {
    if (!score) return 'text-gray-400';
    if (score >= 75) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  if (loading) {
    return (
      <div className="p-8 bg-gray-900 min-h-screen">
        <div className="text-center text-gray-400">Loading lead details...</div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="p-8 bg-gray-900 min-h-screen">
        <div className="text-center text-gray-400">Lead not found</div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-900 min-h-screen">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/crm')}
            className="p-2 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <ArrowLeft size={20} className="text-gray-400" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-white">{lead.name}</h1>
            <p className="text-gray-400 mt-1">Lead ID: {lead.id}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/crm/leads/${leadId}/edit`)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <Edit size={18} />
            Edit
          </button>
        </div>
      </div>

      {/* Main Info Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Lead Info Card */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Contact Information</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <Phone className="text-gray-400 mt-1" size={18} />
              <div>
                <p className="text-xs text-gray-400 mb-1">Phone</p>
                <p className="text-white">{lead.phone}</p>
              </div>
            </div>
            {lead.email && (
              <div className="flex items-start gap-3">
                <Mail className="text-gray-400 mt-1" size={18} />
                <div>
                  <p className="text-xs text-gray-400 mb-1">Email</p>
                  <p className="text-white">{lead.email}</p>
                </div>
              </div>
            )}
            <div className="pt-4 border-t border-gray-700">
              <p className="text-xs text-gray-400 mb-1">Status</p>
              <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(lead.status)}`}>
                {formatStatus(lead.status)}
              </span>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Source</p>
              <p className="text-white">{formatStatus(lead.source)}</p>
            </div>
            {lead.tags && lead.tags.length > 0 && (
              <div>
                <p className="text-xs text-gray-400 mb-2">Tags</p>
                <div className="flex flex-wrap gap-2">
                  {lead.tags.map((tag, idx) => (
                    <span key={idx} className="px-2 py-1 bg-gray-700 text-gray-300 text-xs rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Stats Card */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Activity Stats</h2>
          <div className="space-y-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">Total Calls</p>
              <p className="text-2xl font-bold text-white">{lead.total_calls}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Total Appointments</p>
              <p className="text-2xl font-bold text-white">{lead.total_appointments}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Show-Up Rate</p>
              <p className="text-2xl font-bold text-white">
                {lead.total_appointments > 0 
                  ? Math.round((lead.appointments_showed / lead.total_appointments) * 100) 
                  : 0}%
              </p>
            </div>
            <div className="pt-4 border-t border-gray-700">
              <p className="text-xs text-gray-400 mb-1">Last Contact</p>
              <p className="text-white">
                {lead.last_contact ? formatDate(lead.last_contact) : 'Never'}
              </p>
            </div>
          </div>
        </div>

        {/* QC Scores Card */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Quality Scores</h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-400">Commitment Score</p>
                <span className={`text-lg font-bold ${getScoreColor(lead.commitment_score)}`}>
                  {lead.commitment_score || 'N/A'}
                </span>
              </div>
              {lead.commitment_score && (
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${lead.commitment_score >= 75 ? 'bg-green-500' : lead.commitment_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${lead.commitment_score}%` }}
                  ></div>
                </div>
              )}
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-400">Conversion Score</p>
                <span className={`text-lg font-bold ${getScoreColor(lead.conversion_score)}`}>
                  {lead.conversion_score || 'N/A'}
                </span>
              </div>
              {lead.conversion_score && (
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${lead.conversion_score >= 75 ? 'bg-green-500' : lead.conversion_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${lead.conversion_score}%` }}
                  ></div>
                </div>
              )}
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-400">Show-Up Probability</p>
                <span className={`text-lg font-bold ${getScoreColor(lead.show_up_probability)}`}>
                  {lead.show_up_probability ? `${lead.show_up_probability}%` : 'N/A'}
                </span>
              </div>
              {lead.show_up_probability && (
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${lead.show_up_probability >= 75 ? 'bg-green-500' : lead.show_up_probability >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${lead.show_up_probability}%` }}
                  ></div>
                </div>
              )}
            </div>
            {!lead.commitment_score && !lead.conversion_score && !lead.show_up_probability && (
              <p className="text-gray-500 text-sm text-center py-4">No quality data available yet</p>
            )}
          </div>
        </div>
      </div>

      {/* QC Analysis Details */}
      {analytics && analytics.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">📊 QC Analysis History</h2>
          <div className="space-y-4">
            {analytics.slice(0, 3).map((analysis, index) => (
              <div key={index} className="bg-gray-900 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-white font-medium">
                    Analysis #{analytics.length - index}
                  </h3>
                  <span className="text-xs text-gray-500">
                    {analysis.created_at ? new Date(analysis.created_at).toLocaleDateString() : 'Recent'}
                  </span>
                </div>
                
                {/* Scores Summary */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">Commitment</p>
                    <p className={`text-lg font-bold ${getScoreColor(analysis.aggregated_scores?.commitment_score)}`}>
                      {analysis.aggregated_scores?.commitment_score || 'N/A'}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">Conversion</p>
                    <p className={`text-lg font-bold ${getScoreColor(analysis.aggregated_scores?.conversion_score)}`}>
                      {analysis.aggregated_scores?.conversion_score || 'N/A'}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">Excellence</p>
                    <p className={`text-lg font-bold ${getScoreColor(analysis.aggregated_scores?.excellence_score)}`}>
                      {analysis.aggregated_scores?.excellence_score || 'N/A'}
                    </p>
                  </div>
                </div>

                {/* Recommendations */}
                {analysis.recommendations && analysis.recommendations.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-300 mb-2">💡 Recommendations:</p>
                    <ul className="space-y-1">
                      {analysis.recommendations.map((rec, recIndex) => (
                        <li key={recIndex} className="text-sm text-gray-400 pl-4">
                          • {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
            {analytics.length > 3 && (
              <p className="text-center text-sm text-gray-500">
                Showing 3 most recent analyses • Total: {analytics.length}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Appointments Section */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Appointments</h2>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2">
            <Plus size={18} />
            Add Appointment
          </button>
        </div>
        {appointments.length === 0 ? (
          <p className="text-gray-400 text-center py-4">No appointments scheduled</p>
        ) : (
          <div className="space-y-3">
            {appointments.map((appt) => (
              <div key={appt.id} className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
                <div 
                  className="p-4 cursor-pointer hover:bg-gray-850 transition-colors flex items-center justify-between"
                  onClick={() => toggleAppointment(appt.id)}
                >
                  <div className="flex items-center gap-4 flex-1">
                    <Calendar className="text-gray-400" size={20} />
                    <div>
                      <p className="text-white font-medium">{formatDate(appt.scheduled_time)}</p>
                      <p className="text-sm text-gray-400">
                        {appt.duration_minutes} minutes • Agent: {appt.agent_name}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(appt.status)}`}>
                      {formatStatus(appt.status)}
                    </span>
                    {expandedAppointments[appt.id] ? <ChevronUp size={20} className="text-gray-400" /> : <ChevronDown size={20} className="text-gray-400" />}
                  </div>
                </div>
                {expandedAppointments[appt.id] && (
                  <div className="p-4 bg-gray-850 border-t border-gray-700">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-gray-400 mb-1">Created</p>
                        <p className="text-white text-sm">{formatDate(appt.created_at)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-1">Updated</p>
                        <p className="text-white text-sm">{formatDate(appt.updated_at)}</p>
                      </div>
                      {appt.showed_up_at && (
                        <div>
                          <p className="text-xs text-gray-400 mb-1">Showed Up At</p>
                          <p className="text-white text-sm">{formatDate(appt.showed_up_at)}</p>
                        </div>
                      )}
                      {appt.notes && (
                        <div className="col-span-2">
                          <p className="text-xs text-gray-400 mb-1">Notes</p>
                          <p className="text-white text-sm">{appt.notes}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Notes Section */}
      {lead.notes && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Notes</h2>
          <p className="text-gray-300 whitespace-pre-wrap">{lead.notes}</p>
        </div>
      )}
    </div>
  );
};

export default LeadDetail;
