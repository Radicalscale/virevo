import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  TrendingUp,
  Users,
  FileText,
  Trash2,
  Settings,
  BarChart3,
  AlertCircle,
  CheckCircle,
  Download
} from 'lucide-react';
import { qcEnhancedAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';

const CampaignManager = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCampaign, setNewCampaign] = useState({
    name: '',
    description: '',
    rules: {
      analysis_rules: {
        focus_on_brevity: true,
        check_goal_alignment: true,
        evaluate_naturalness: true
      }
    },
    learning_parameters: {},
    linked_agents: []
  });

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
      const response = await qcEnhancedAPI.listCampaigns();
      setCampaigns(response.data);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
      toast({
        title: "Error",
        description: "Failed to load campaigns",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCampaign = async () => {
    if (!newCampaign.name.trim()) {
      toast({
        title: "Error",
        description: "Campaign name is required",
        variant: "destructive"
      });
      return;
    }

    try {
      await qcEnhancedAPI.createCampaign(newCampaign);
      toast({
        title: "Success",
        description: "Campaign created successfully"
      });
      setShowCreateModal(false);
      setNewCampaign({
        name: '',
        description: '',
        rules: {
          analysis_rules: {
            focus_on_brevity: true,
            check_goal_alignment: true,
            evaluate_naturalness: true
          }
        },
        learning_parameters: {},
        linked_agents: []
      });
      fetchCampaigns();
    } catch (error) {
      console.error('Error creating campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to create campaign",
        variant: "destructive"
      });
    }
  };

  const handleDeleteCampaign = async (campaignId) => {
    if (!window.confirm('Are you sure you want to delete this campaign? All associated data will be removed.')) {
      return;
    }

    try {
      await qcEnhancedAPI.deleteCampaign(campaignId);
      toast({
        title: "Success",
        description: "Campaign deleted successfully"
      });
      fetchCampaigns();
    } catch (error) {
      console.error('Error deleting campaign:', error);
      toast({
        title: "Error",
        description: "Failed to delete campaign",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">QC Campaigns</h1>
              <p className="text-gray-400 mt-1">
                Multi-call learning and pattern recognition across agent conversations
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              <Plus size={18} />
              New Campaign
            </button>
          </div>
        </div>
      </div>

      {/* Campaigns Grid */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading campaigns...</div>
        ) : campaigns.length === 0 ? (
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-12 text-center">
            <Users size={48} className="mx-auto text-gray-600 mb-4" />
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No Campaigns Yet</h3>
            <p className="text-gray-500 mb-6">
              Create a campaign to track patterns across multiple calls and improve your agents over time
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              <Plus size={18} />
              Create First Campaign
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {campaigns.map((campaign) => (
              <div
                key={campaign.id}
                className="bg-gray-900 rounded-lg border border-gray-800 p-6 hover:border-purple-700 transition-colors"
              >
                {/* Campaign Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white mb-1">{campaign.name}</h3>
                    <p className="text-sm text-gray-400 line-clamp-2">
                      {campaign.description || 'No description'}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteCampaign(campaign.id)}
                    className="text-gray-400 hover:text-red-400 transition-colors ml-2"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-gray-800/50 rounded p-3">
                    <div className="text-xs text-gray-400 mb-1">Total Calls</div>
                    <div className="text-xl font-bold text-white">
                      {campaign.stats?.total_calls || 0}
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded p-3">
                    <div className="text-xs text-gray-400 mb-1">Patterns</div>
                    <div className="text-xl font-bold text-purple-400">
                      {campaign.stats?.patterns_identified || 0}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/qc/campaigns/${campaign.id}`)}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded transition-colors"
                  >
                    <BarChart3 size={14} />
                    View Details
                  </button>
                  <button
                    onClick={() => navigate(`/qc/campaigns/${campaign.id}/settings`)}
                    className="flex items-center justify-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white text-sm rounded transition-colors"
                  >
                    <Settings size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Campaign Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-lg border border-gray-700 max-w-2xl w-full p-6">
            <h2 className="text-2xl font-bold mb-4">Create New Campaign</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Campaign Name *
                </label>
                <input
                  type="text"
                  value={newCampaign.name}
                  onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded px-3 py-2"
                  placeholder="e.g., Q4 Outbound Sales Campaign"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={newCampaign.description}
                  onChange={(e) => setNewCampaign({ ...newCampaign, description: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded px-3 py-2 h-24"
                  placeholder="Describe the campaign goal and what you're testing..."
                />
              </div>

              <div className="bg-gray-800/50 rounded p-4">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Analysis Focus</h3>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <input
                      type="checkbox"
                      checked={newCampaign.rules.analysis_rules.focus_on_brevity}
                      onChange={(e) => setNewCampaign({
                        ...newCampaign,
                        rules: {
                          ...newCampaign.rules,
                          analysis_rules: {
                            ...newCampaign.rules.analysis_rules,
                            focus_on_brevity: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    Focus on brevity and snappiness
                  </label>
                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <input
                      type="checkbox"
                      checked={newCampaign.rules.analysis_rules.check_goal_alignment}
                      onChange={(e) => setNewCampaign({
                        ...newCampaign,
                        rules: {
                          ...newCampaign.rules,
                          analysis_rules: {
                            ...newCampaign.rules.analysis_rules,
                            check_goal_alignment: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    Check alignment with conversation goals
                  </label>
                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <input
                      type="checkbox"
                      checked={newCampaign.rules.analysis_rules.evaluate_naturalness}
                      onChange={(e) => setNewCampaign({
                        ...newCampaign,
                        rules: {
                          ...newCampaign.rules,
                          analysis_rules: {
                            ...newCampaign.rules.analysis_rules,
                            evaluate_naturalness: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    Evaluate conversational naturalness
                  </label>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleCreateCampaign}
                className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-2 rounded transition-colors"
              >
                Create Campaign
              </button>
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-6 bg-gray-800 hover:bg-gray-700 text-white py-2 rounded transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CampaignManager;
