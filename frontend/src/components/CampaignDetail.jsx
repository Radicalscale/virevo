import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  TrendingUp,
  BarChart3,
  FileText,
  AlertTriangle,
  CheckCircle,
  Download,
  RefreshCw
} from 'lucide-react';
import { qcEnhancedAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';

const CampaignDetail = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzingPatterns, setAnalyzingPatterns] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [patterns, setPatterns] = useState(null);
  const [report, setReport] = useState(null);

  useEffect(() => {
    fetchCampaignDetails();
  }, [campaignId]);

  const fetchCampaignDetails = async () => {
    try {
      setLoading(true);
      const response = await qcEnhancedAPI.getCampaign(campaignId);
      setCampaign(response.data);
    } catch (error) {
      console.error('Error fetching campaign:', error);
      toast({
        title: "Error",
        description: "Failed to load campaign details",
        variant: "destructive"
      });
      navigate('/qc/campaigns');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzePatterns = async () => {
    if (campaign?.stats?.total_calls < 2) {
      toast({
        title: "Not Enough Data",
        description: "At least 2 calls required for pattern analysis",
        variant: "destructive"
      });
      return;
    }

    try {
      setAnalyzingPatterns(true);
      const response = await qcEnhancedAPI.analyzePatterns(campaignId);
      setPatterns(response.data);
      toast({
        title: "Analysis Complete",
        description: `${response.data.patterns?.length || 0} patterns identified`
      });
    } catch (error) {
      console.error('Error analyzing patterns:', error);
      toast({
        title: "Analysis Failed",
        description: error.response?.data?.detail || "Failed to analyze patterns",
        variant: "destructive"
      });
    } finally {
      setAnalyzingPatterns(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      setGeneratingReport(true);
      const response = await qcEnhancedAPI.generateReport(campaignId);
      setReport(response.data);
      toast({
        title: "Report Generated",
        description: "Campaign report is ready"
      });
    } catch (error) {
      console.error('Error generating report:', error);
      toast({
        title: "Report Failed",
        description: error.response?.data?.detail || "Failed to generate report",
        variant: "destructive"
      });
    } finally {
      setGeneratingReport(false);
    }
  };

  const exportReport = () => {
    if (!report) return;
    
    const dataStr = JSON.stringify(report, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileDefaultName = `campaign-report-${campaignId}-${Date.now()}.json`;
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    toast({
      title: "Exported",
      description: "Report downloaded as JSON"
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-gray-400">Loading campaign...</div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-gray-400">Campaign not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => navigate('/qc/campaigns')}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft size={24} />
            </button>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white">{campaign.name}</h1>
              {campaign.description && (
                <p className="text-gray-400 mt-1">{campaign.description}</p>
              )}
            </div>
            <button
              onClick={() => navigate(`/qc/campaigns/${campaignId}/settings`)}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
            >
              Settings
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Total Calls</div>
              <div className="text-2xl font-bold text-white">{campaign.stats?.total_calls || 0}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Patterns</div>
              <div className="text-2xl font-bold text-purple-400">{campaign.stats?.patterns_identified || 0}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Suggestions</div>
              <div className="text-2xl font-bold text-blue-400">{campaign.stats?.total_suggestions || 0}</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Last Analyzed</div>
              <div className="text-sm font-medium text-white">
                {campaign.stats?.last_analyzed 
                  ? new Date(campaign.stats.last_analyzed).toLocaleDateString()
                  : 'Never'
                }
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Actions */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
          <h2 className="text-xl font-semibold mb-4">Campaign Analysis</h2>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={handleAnalyzePatterns}
              disabled={analyzingPatterns || (campaign.stats?.total_calls < 2)}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              <BarChart3 size={18} />
              {analyzingPatterns ? 'Analyzing...' : 'Analyze Patterns'}
            </button>
            <button
              onClick={handleGenerateReport}
              disabled={generatingReport}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              <FileText size={18} />
              {generatingReport ? 'Generating...' : 'Generate Report'}
            </button>
          </div>
          {campaign.stats?.total_calls < 2 && (
            <p className="text-sm text-yellow-400 mt-3">
              ⚠️ Add at least 2 calls to enable pattern analysis
            </p>
          )}
        </div>

        {/* Pattern Results */}
        {patterns && (
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Pattern Analysis Results</h2>
              <span className="text-sm text-gray-400">
                {patterns.calls_analyzed} calls analyzed
              </span>
            </div>
            
            {patterns.patterns && patterns.patterns.length > 0 ? (
              <div className="space-y-3">
                {patterns.patterns.map((pattern, index) => (
                  <div
                    key={index}
                    className="bg-gray-800/50 rounded-lg p-4 border border-gray-700"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {pattern.pattern_type === 'bottleneck' && (
                          <AlertTriangle className="w-5 h-5 text-red-400" />
                        )}
                        {pattern.pattern_type === 'success' && (
                          <CheckCircle className="w-5 h-5 text-green-400" />
                        )}
                        {pattern.pattern_type === 'improvement_opportunity' && (
                          <TrendingUp className="w-5 h-5 text-yellow-400" />
                        )}
                        <span className="text-xs uppercase font-semibold text-gray-400">
                          {pattern.pattern_type.replace('_', ' ')}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500">
                        Confidence: {Math.round(pattern.confidence_score * 100)}%
                      </span>
                    </div>
                    <p className="text-white">{pattern.description}</p>
                    {pattern.affected_nodes && pattern.affected_nodes.length > 0 && (
                      <p className="text-xs text-gray-400 mt-2">
                        Affected: {pattern.affected_nodes.join(', ')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-center py-8">No patterns identified</p>
            )}
          </div>
        )}

        {/* Report */}
        {report && (
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Campaign Report</h2>
              <button
                onClick={exportReport}
                className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
              >
                <Download size={16} />
                Export
              </button>
            </div>

            {/* Summary */}
            {report.summary && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3">Summary</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-800/50 rounded p-3">
                    <div className="text-sm text-gray-400">Total Turns</div>
                    <div className="text-xl font-bold text-white">
                      {report.summary.total_conversation_turns}
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded p-3">
                    <div className="text-sm text-gray-400">Avg Quality</div>
                    <div className="text-xl font-bold text-white">
                      {report.summary.average_quality_score.toFixed(1)}/4.0
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Insights */}
            {report.insights && report.insights.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3">Insights</h3>
                <div className="space-y-2">
                  {report.insights.map((insight, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded border ${
                        insight.type === 'positive'
                          ? 'bg-green-900/20 border-green-700'
                          : insight.type === 'critical'
                          ? 'bg-red-900/20 border-red-700'
                          : insight.type === 'warning'
                          ? 'bg-yellow-900/20 border-yellow-700'
                          : 'bg-blue-900/20 border-blue-700'
                      }`}
                    >
                      <div className="font-medium">{insight.title}</div>
                      <div className="text-sm text-gray-300 mt-1">{insight.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {report.recommendations && report.recommendations.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3">Recommendations</h3>
                <div className="space-y-2">
                  {report.recommendations.map((rec, index) => (
                    <div key={index} className="bg-gray-800/50 rounded p-3">
                      <div className="flex items-start justify-between mb-1">
                        <span className="text-sm font-medium text-white">{rec.title}</span>
                        <span className="text-xs uppercase font-semibold text-purple-400">
                          {rec.priority}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300">{rec.action}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Impact: {rec.estimated_impact}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CampaignDetail;
