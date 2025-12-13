import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Settings,
  Download,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  Users,
  FileText,
  Zap,
  Sparkles,
  Upload,
  GraduationCap,
  Phone,
  Trash2,
  Plus,
  BookOpen,
  Brain,
  Mic,
  X,
  Loader2,
  ChevronDown,
  ChevronUp,
  Eye
} from 'lucide-react';
import { qcEnhancedAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import CampaignReportView from './CampaignReportView';

const CampaignDetailsPage = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const fileInputRef = useRef(null);
  
  const [loading, setLoading] = useState(true);
  const [campaign, setCampaign] = useState(null);
  const [calls, setCalls] = useState([]);
  const [trainingCalls, setTrainingCalls] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [kbItems, setKbItems] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [analyzingAll, setAnalyzingAll] = useState(false);
  
  // QC Results tab state
  const [qcResults, setQcResults] = useState(null);
  const [loadingQcResults, setLoadingQcResults] = useState(false);
  const [resettingAll, setResettingAll] = useState(false);
  const [resettingCallId, setResettingCallId] = useState(null);
  const [batchAnalysisPolling, setBatchAnalysisPolling] = useState(false);
  
  // New state for analysis options modal
  const [showAnalyzeModal, setShowAnalyzeModal] = useState(false);
  const [selectedAnalysisTypes, setSelectedAnalysisTypes] = useState(['script', 'tonality']);
  const [forceReanalyze, setForceReanalyze] = useState(false);
  
  // Report modal state
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  
  // Training calls analysis state
  const [analyzingTrainingCallId, setAnalyzingTrainingCallId] = useState(null);
  const [analyzingAllTrainingCalls, setAnalyzingAllTrainingCalls] = useState(false);
  const [expandedTrainingCallId, setExpandedTrainingCallId] = useState(null);
  
  // Call deletion state
  const [deleteMode, setDeleteMode] = useState(false);
  const [selectedCallsForDeletion, setSelectedCallsForDeletion] = useState(new Set());
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [deletingCalls, setDeletingCalls] = useState(false);

  useEffect(() => {
    fetchCampaignDetails();
  }, [campaignId]);
  
  // Fetch QC results when switching to QC Results tab
  useEffect(() => {
    if (activeTab === 'qc-results') {
      fetchQcResults();
    }
  }, [activeTab, campaignId]);

  // Auto-poll for batch analysis status updates
  useEffect(() => {
    let pollInterval;
    
    if (batchAnalysisPolling && activeTab === 'qc-results') {
      pollInterval = setInterval(async () => {
        try {
          const response = await qcEnhancedAPI.getCampaignQCResults(campaignId);
          const data = response.data;
          setQcResults(data);
          
          // Check if batch analysis is complete (no calls in "analyzing" status)
          const stillAnalyzing = data.calls?.some(call => call.analysis_status === 'analyzing');
          const hasPending = data.calls?.some(call => call.analysis_status === 'pending');
          
          if (!stillAnalyzing && !hasPending) {
            // Analysis complete - stop polling
            setBatchAnalysisPolling(false);
            toast({
              title: "Analysis Complete",
              description: `Analyzed ${data.summary?.analyzed || 0} calls`
            });
          }
        } catch (error) {
          console.error('Error polling QC results:', error);
        }
      }, 3000); // Poll every 3 seconds
    }
    
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [batchAnalysisPolling, activeTab, campaignId]);

  const fetchQcResults = async () => {
    try {
      setLoadingQcResults(true);
      const response = await qcEnhancedAPI.getCampaignQCResults(campaignId);
      setQcResults(response.data);
    } catch (error) {
      console.error('Error fetching QC results:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch QC results',
        variant: 'destructive'
      });
    } finally {
      setLoadingQcResults(false);
    }
  };

  const resetAllAnalysis = async () => {
    if (!window.confirm('Are you sure you want to reset all QC analysis for this campaign? This will clear all Script, Tech, and Tonality results.')) {
      return;
    }
    
    try {
      setResettingAll(true);
      await qcEnhancedAPI.resetAllAnalysis(campaignId);
      toast({
        title: 'Analysis Reset',
        description: 'All QC analysis has been reset. You can now re-analyze the calls.',
      });
      // Refresh QC results
      await fetchQcResults();
    } catch (error) {
      console.error('Error resetting analysis:', error);
      toast({
        title: 'Error',
        description: 'Failed to reset analysis',
        variant: 'destructive'
      });
    } finally {
      setResettingAll(false);
    }
  };

  const resetCallAnalysis = async (callId) => {
    try {
      setResettingCallId(callId);
      await qcEnhancedAPI.resetCallAnalysis(campaignId, callId);
      toast({
        title: 'Call Reset',
        description: 'Analysis has been reset for this call.',
      });
      // Refresh QC results
      await fetchQcResults();
    } catch (error) {
      console.error('Error resetting call analysis:', error);
      toast({
        title: 'Error',
        description: 'Failed to reset call analysis',
        variant: 'destructive'
      });
    } finally {
      setResettingCallId(null);
    }
  };

  // Toggle call selection for deletion
  const toggleCallSelection = (callId) => {
    const newSelection = new Set(selectedCallsForDeletion);
    if (newSelection.has(callId)) {
      newSelection.delete(callId);
    } else {
      newSelection.add(callId);
    }
    setSelectedCallsForDeletion(newSelection);
  };

  // Select/deselect all calls
  const toggleSelectAll = () => {
    if (selectedCallsForDeletion.size === calls.length) {
      setSelectedCallsForDeletion(new Set());
    } else {
      setSelectedCallsForDeletion(new Set(calls.map(c => c.call_id)));
    }
  };

  // Cancel delete mode
  const cancelDeleteMode = () => {
    setDeleteMode(false);
    setSelectedCallsForDeletion(new Set());
    setShowDeleteConfirmation(false);
  };

  // Delete selected calls
  const deleteSelectedCalls = async () => {
    if (selectedCallsForDeletion.size === 0) return;
    
    setDeletingCalls(true);
    try {
      const callIds = Array.from(selectedCallsForDeletion);
      
      // Call backend to delete calls
      await qcEnhancedAPI.deleteCampaignCalls(campaignId, callIds);
      
      toast({
        title: 'Calls Deleted',
        description: `Successfully deleted ${callIds.length} call(s) from campaign`,
      });
      
      // Refresh campaign details
      await fetchCampaignDetails();
      
      // Reset delete mode
      cancelDeleteMode();
      
    } catch (error) {
      console.error('Error deleting calls:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete calls',
        variant: 'destructive'
      });
    } finally {
      setDeletingCalls(false);
      setShowDeleteConfirmation(false);
    }
  };

  const fetchCampaignDetails = async () => {
    try {
      setLoading(true);
      const response = await qcEnhancedAPI.getCampaign(campaignId);
      const data = response.data;
      
      setCampaign(data);
      setCalls((data.calls || []).filter(c => c.call_type !== 'training'));
      setPatterns(data.patterns || []);
      setSuggestions(data.suggestions || []);
      
      // Fetch training calls
      try {
        const trainingResponse = await qcEnhancedAPI.getTrainingCalls(campaignId);
        setTrainingCalls(trainingResponse.data || []);
      } catch (e) {
        console.log('No training calls endpoint yet');
      }
      
      // Fetch KB items
      try {
        const kbResponse = await qcEnhancedAPI.getCampaignKB(campaignId);
        setKbItems(kbResponse.data || []);
      } catch (e) {
        console.log('No KB endpoint yet');
      }
    } catch (error) {
      console.error('Error fetching campaign details:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to load campaign details",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTrainingUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    try {
      setUploading(true);
      let successCount = 0;
      let failCount = 0;
      
      // Upload each file
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        try {
          const formData = new FormData();
          formData.append('file', file);
          formData.append('designation', '');
          formData.append('tags', '');
          
          await qcEnhancedAPI.uploadTrainingCall(campaignId, formData);
          successCount++;
        } catch (error) {
          console.error(`Error uploading ${file.name}:`, error);
          failCount++;
        }
      }
      
      if (successCount > 0) {
        toast({
          title: "Upload Complete",
          description: `${successCount} file${successCount > 1 ? 's' : ''} uploaded successfully${failCount > 0 ? `, ${failCount} failed` : ''}`
        });
      } else {
        toast({
          title: "Error",
          description: "Failed to upload training calls",
          variant: "destructive"
        });
      }
      
      fetchCampaignDetails();
    } catch (error) {
      console.error('Error uploading training calls:', error);
      toast({
        title: "Error",
        description: "Failed to upload training calls",
        variant: "destructive"
      });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleAnalyzeTrainingCall = async (trainingCallId) => {
    try {
      setAnalyzingTrainingCallId(trainingCallId);
      toast({
        title: "Analyzing...",
        description: "Processing training call"
      });
      
      await qcEnhancedAPI.analyzeTrainingCall(campaignId, trainingCallId);
      
      toast({
        title: "Analysis Complete",
        description: "Training call has been analyzed"
      });
      
      fetchCampaignDetails();
    } catch (error) {
      console.error('Error analyzing training call:', error);
      toast({
        title: "Error",
        description: "Failed to analyze training call",
        variant: "destructive"
      });
    } finally {
      setAnalyzingTrainingCallId(null);
    }
  };

  const handleAnalyzeAllTrainingCalls = async () => {
    try {
      setAnalyzingAllTrainingCalls(true);
      toast({
        title: "Analyzing...",
        description: "Processing all pending training calls"
      });
      
      const response = await qcEnhancedAPI.analyzeAllTrainingCalls(campaignId, { force_reanalyze: false });
      
      if (response.data.total_queued === 0) {
        toast({
          title: "No Pending Calls",
          description: "All training calls have already been analyzed"
        });
      } else {
        toast({
          title: "Analysis Complete",
          description: `Analyzed ${response.data.processed} training call${response.data.processed > 1 ? 's' : ''}${response.data.failed > 0 ? `, ${response.data.failed} failed` : ''}`
        });
      }
      
      fetchCampaignDetails();
    } catch (error) {
      console.error('Error analyzing training calls:', error);
      toast({
        title: "Error",
        description: "Failed to analyze training calls",
        variant: "destructive"
      });
    } finally {
      setAnalyzingAllTrainingCalls(false);
    }
  };

  const handleDeleteTrainingCall = async (trainingCallId) => {
    try {
      await qcEnhancedAPI.deleteTrainingCall(campaignId, trainingCallId);
      toast({
        title: "Success",
        description: "Training call deleted"
      });
      fetchCampaignDetails();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete training call",
        variant: "destructive"
      });
    }
  };

  const handleUpdateTrainingCallOutcome = async (trainingCallId, outcome) => {
    try {
      const response = await qcEnhancedAPI.updateTrainingCallOutcome(campaignId, trainingCallId, {
        outcome: outcome,
        trigger_learning: true
      });
      
      toast({
        title: "Outcome Updated",
        description: response.data.learning_triggered 
          ? "Outcome saved and learning triggered!" 
          : "Outcome saved successfully"
      });
      fetchCampaignDetails();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update outcome",
        variant: "destructive"
      });
    }
  };

  const handleExport = async () => {
    try {
      setGeneratingReport(true);
      toast({
        title: "Generating Report...",
        description: "Analyzing campaign data"
      });
      
      const response = await qcEnhancedAPI.generateReport(campaignId);
      setReportData(response.data);
      setShowReportModal(true);
      
      toast({
        title: "Report Ready",
        description: "Your campaign report has been generated"
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to generate report",
        variant: "destructive"
      });
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleDownloadReport = () => {
    if (!reportData) return;
    
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `campaign-${campaign?.name || campaignId}-report.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    toast({
      title: "Downloaded",
      description: "Report saved as JSON file"
    });
  };

  const handleAnalyzePatterns = async () => {
    try {
      toast({
        title: "Analyzing...",
        description: "Detecting patterns across calls"
      });
      
      const response = await qcEnhancedAPI.analyzePatterns(campaignId);
      setPatterns(response.data.patterns || []);
      
      toast({
        title: "Success",
        description: `Found ${response.data.patterns?.length || 0} patterns`
      });
      
      fetchCampaignDetails();
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to analyze patterns",
        variant: "destructive"
      });
    }
  };

  const handleAnalyzeAllCalls = async () => {
    // Check if QC agents are assigned for selected types
    const missingAgents = [];
    if (selectedAnalysisTypes.includes('script') && !campaign?.language_pattern_qc_agent_id) {
      missingAgents.push('Script Quality (Language Pattern)');
    }
    if (selectedAnalysisTypes.includes('tonality') && !campaign?.tonality_qc_agent_id) {
      missingAgents.push('Tonality');
    }
    
    if (missingAgents.length > 0) {
      toast({
        title: "QC Agents Not Assigned",
        description: `Please assign QC agents for: ${missingAgents.join(', ')}. Go to Campaign Settings → QC Agents tab.`,
        variant: "destructive",
        duration: 6000
      });
      return;
    }
    
    if (selectedAnalysisTypes.length === 0) {
      toast({
        title: "No Analysis Type Selected",
        description: "Please select at least one analysis type",
        variant: "destructive"
      });
      return;
    }
    
    try {
      setAnalyzingAll(true);
      setShowAnalyzeModal(false);
      
      toast({
        title: "Starting batch analysis...",
        description: `Running ${selectedAnalysisTypes.join(' & ')} analysis on all calls`
      });
      
      const response = await qcEnhancedAPI.analyzeAllCalls(campaignId, {
        analysis_types: selectedAnalysisTypes,
        force_reanalyze: forceReanalyze,
        // Pass QC agent IDs so backend uses their settings
        script_qc_agent_id: campaign?.language_pattern_qc_agent_id,
        tonality_qc_agent_id: campaign?.tonality_qc_agent_id,
        tech_qc_agent_id: campaign?.tech_issues_qc_agent_id
      });
      
      const data = response.data;
      
      if (data.calls_queued === 0 && data.training_calls_queued === 0) {
        toast({
          title: "No pending calls",
          description: "All calls have already been analyzed. Enable 'Force Re-analyze' to run again."
        });
      } else {
        toast({
          title: "Analysis started",
          description: `Queued ${data.calls_queued} calls and ${data.training_calls_queued} training calls for ${selectedAnalysisTypes.join(' & ')} analysis`
        });
        
        // Start polling for status updates
        setBatchAnalysisPolling(true);
        
        // Switch to QC Results tab to show progress
        setActiveTab('qc-results');
      }
      
      // Immediate refresh
      fetchCampaignDetails();
      if (activeTab === 'qc-results') {
        fetchQcResults();
      }
      
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to start batch analysis",
        variant: "destructive"
      });
    } finally {
      setAnalyzingAll(false);
    }
  };

  // Check if QC agents are assigned
  const getQCAgentStatus = () => {
    return {
      script: !!campaign?.language_pattern_qc_agent_id,
      tonality: !!campaign?.tonality_qc_agent_id,
      tech: !!campaign?.tech_issues_qc_agent_id
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading campaign details...</p>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle size={48} className="mx-auto text-red-500 mb-4" />
          <h2 className="text-2xl font-bold mb-2">Campaign Not Found</h2>
          <p className="text-gray-400 mb-6">This campaign doesn&apos;t exist or you don&apos;t have access to it.</p>
          <button
            onClick={() => navigate('/qc/campaigns')}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
          >
            Back to Campaigns
          </button>
        </div>
      </div>
    );
  }

  const stats = campaign.stats || {};

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigate('/qc/campaigns')}
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft size={20} />
              Back to Campaigns
            </button>
            
            <div className="flex gap-3">
              <button
                onClick={() => setShowAnalyzeModal(true)}
                disabled={analyzingAll}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                <Zap size={18} className={analyzingAll ? 'animate-pulse' : ''} />
                {analyzingAll ? 'Analyzing...' : 'Analyze All Calls'}
              </button>
              <button
                onClick={handleAnalyzePatterns}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                <Sparkles size={18} />
                Analyze Patterns
              </button>
              <button
                onClick={handleExport}
                disabled={generatingReport}
                className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-900 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                {generatingReport ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <BarChart3 size={18} />
                )}
                {generatingReport ? 'Generating...' : 'View Report'}
              </button>
              <button
                onClick={() => navigate(`/qc/campaigns/${campaignId}/settings`)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
              >
                <Settings size={18} />
                Settings
              </button>
            </div>
          </div>
          
          <div>
            <h1 className="text-3xl font-bold text-white">{campaign.name}</h1>
            <p className="text-gray-400 mt-1">
              {campaign.description || 'No description provided'}
            </p>
            <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
              <span>Created {new Date(campaign.created_at).toLocaleDateString()}</span>
              <span>•</span>
              <span>Updated {new Date(campaign.updated_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Content with Tabs */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">Real Calls</span>
                <Phone size={18} className="text-blue-400" />
              </div>
              <div className="text-2xl font-bold text-white">{campaign.total_real_calls || calls.length}</div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">Training Calls</span>
                <GraduationCap size={18} className="text-green-400" />
              </div>
              <div className="text-2xl font-bold text-white">{campaign.total_training_calls || trainingCalls.length}</div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">Patterns</span>
                <BarChart3 size={18} className="text-purple-400" />
              </div>
              <div className="text-2xl font-bold text-white">{stats.patterns_identified || patterns.length}</div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">KB Items</span>
                <BookOpen size={18} className="text-yellow-400" />
              </div>
              <div className="text-2xl font-bold text-white">{kbItems.length}</div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">QC Agents</span>
                <Brain size={18} className="text-orange-400" />
              </div>
              <div className="text-2xl font-bold text-white">
                {[campaign.tonality_qc_agent_id, campaign.language_pattern_qc_agent_id, campaign.tech_issues_qc_agent_id].filter(Boolean).length}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-gray-900 border border-gray-800 mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="training">
              Training Calls ({trainingCalls.length})
            </TabsTrigger>
            <TabsTrigger value="real">
              Real Calls ({calls.length})
            </TabsTrigger>
            <TabsTrigger value="patterns">
              Patterns ({patterns.length})
            </TabsTrigger>
            <TabsTrigger value="agents">Agents</TabsTrigger>
            <TabsTrigger value="qc-results" className="flex items-center gap-1">
              <Sparkles size={14} />
              QC Results
            </TabsTrigger>
          </TabsList>
          
          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Activity */}
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-white">Recent Activity</CardTitle>
                </CardHeader>
                <CardContent>
                  {calls.length === 0 && trainingCalls.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No activity yet. Start by uploading training calls.</p>
                  ) : (
                    <div className="space-y-3">
                      {[...calls, ...trainingCalls].slice(0, 5).map((call, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-gray-800/50 rounded">
                          <div className="flex items-center gap-3">
                            {call.call_type === 'training' || call.filename ? (
                              <GraduationCap size={16} className="text-green-400" />
                            ) : (
                              <Phone size={16} className="text-blue-400" />
                            )}
                            <span className="text-sm text-gray-300">
                              {call.filename || call.call_id?.slice(0, 20) || 'Call'}
                            </span>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {call.call_type === 'training' || call.filename ? 'Training' : 'Real'}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Quick Actions */}
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-white">Quick Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".mp3,.wav,.m4a,.webm"
                    multiple
                    className="hidden"
                    onChange={handleTrainingUpload}
                  />
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                  >
                    <Upload size={16} className="mr-2" />
                    {uploading ? 'Uploading...' : 'Upload Training Calls'}
                  </Button>
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    onClick={handleAnalyzePatterns}
                    disabled={calls.length + trainingCalls.length < 2}
                  >
                    <Sparkles size={16} className="mr-2" />
                    Run Pattern Detection
                  </Button>
                  <Button
                    className="w-full justify-start"
                    variant="outline"
                    onClick={() => navigate(`/qc/campaigns/${campaignId}/settings`)}
                  >
                    <Settings size={16} className="mr-2" />
                    Configure Campaign
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* Training Calls Tab */}
          <TabsContent value="training">
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white">Training Calls</CardTitle>
                  <div className="flex gap-2">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".mp3,.wav,.m4a,.webm"
                      multiple
                      className="hidden"
                      onChange={handleTrainingUpload}
                    />
                    <Button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      variant="outline"
                    >
                      <Upload size={16} className="mr-2" />
                      {uploading ? 'Uploading...' : 'Upload Calls'}
                    </Button>
                    {trainingCalls.length > 0 && (
                      <Button
                        onClick={handleAnalyzeAllTrainingCalls}
                        disabled={analyzingAllTrainingCalls || trainingCalls.every(c => c.processed)}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        {analyzingAllTrainingCalls ? (
                          <>
                            <Loader2 size={16} className="mr-2 animate-spin" />
                            Analyzing...
                          </>
                        ) : (
                          <>
                            <Zap size={16} className="mr-2" />
                            Analyze All
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {/* QC Agent Assignment Status */}
                <div className="mb-4 p-3 rounded-lg bg-gray-800/50 border border-gray-700">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <FileText size={14} className="text-blue-400" />
                        <span className="text-sm text-gray-400">Script QC Agent:</span>
                        {campaign?.language_pattern_qc_agent_id ? (
                          <Badge className="bg-green-600 text-xs">Assigned</Badge>
                        ) : (
                          <Badge variant="outline" className="text-yellow-400 border-yellow-600 text-xs">Not Assigned</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Mic size={14} className="text-purple-400" />
                        <span className="text-sm text-gray-400">Tonality QC Agent:</span>
                        {campaign?.tonality_qc_agent_id ? (
                          <Badge className="bg-green-600 text-xs">Assigned</Badge>
                        ) : (
                          <Badge variant="outline" className="text-yellow-400 border-yellow-600 text-xs">Not Assigned</Badge>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/qc/campaigns/${campaignId}/settings`)}
                      className="text-blue-400 border-blue-600 hover:bg-blue-600/20"
                    >
                      <Settings size={14} className="mr-1" />
                      Configure Agents
                    </Button>
                  </div>
                  {(!campaign?.language_pattern_qc_agent_id && !campaign?.tonality_qc_agent_id) && (
                    <p className="text-xs text-yellow-400 mt-2 flex items-center gap-1">
                      <AlertTriangle size={12} />
                      Assign QC agents to enable real analysis. Without agents, analysis will use default settings.
                    </p>
                  )}
                </div>

                <p className="text-gray-400 text-sm mb-4">
                  Training calls are analyzed using the assigned QC agents above. 
                  <span className="text-purple-400 ml-1">You can upload multiple files at once.</span>
                </p>
                
                {trainingCalls.length === 0 ? (
                  <div className="text-center py-12">
                    <GraduationCap size={48} className="mx-auto text-gray-600 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-300 mb-2">No Training Calls Yet</h3>
                    <p className="text-gray-500 mb-4">
                      Upload audio files to train the QC agent on what patterns to look for
                    </p>
                    <Button onClick={() => fileInputRef.current?.click()}>
                      <Upload size={16} className="mr-2" />
                      Upload First Training Call
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {trainingCalls.map((call) => (
                      <div key={call.id} className="bg-gray-800/50 rounded-lg overflow-hidden">
                        {/* Main Row */}
                        <div className="flex items-center justify-between p-4">
                          <div className="flex items-center gap-4">
                            <GraduationCap size={20} className="text-green-400" />
                            <div>
                              <p className="font-medium text-white">{call.filename}</p>
                              <p className="text-xs text-gray-500">
                                {call.file_size ? `${(call.file_size / 1024).toFixed(1)} KB` : ''}
                                {call.designation && ` • ${call.designation}`}
                                {call.qc_analyzed_at && ` • Analyzed ${new Date(call.qc_analyzed_at).toLocaleDateString()}`}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            {/* Outcome Selection */}
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-gray-400 mr-2">Outcome:</span>
                              <button
                                onClick={() => handleUpdateTrainingCallOutcome(call.id, 'showed')}
                                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                                  call.outcome === 'showed' 
                                    ? 'bg-green-600 text-white' 
                                    : 'bg-gray-700 text-gray-400 hover:bg-green-600/20 hover:text-green-400'
                                }`}
                              >
                                Showed
                              </button>
                              <button
                                onClick={() => handleUpdateTrainingCallOutcome(call.id, 'no_show')}
                                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                                  call.outcome === 'no_show' 
                                    ? 'bg-red-600 text-white' 
                                    : 'bg-gray-700 text-gray-400 hover:bg-red-600/20 hover:text-red-400'
                                }`}
                              >
                                No Show
                              </button>
                              <button
                                onClick={() => handleUpdateTrainingCallOutcome(call.id, 'unknown')}
                                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                                  call.outcome === 'unknown' || !call.outcome
                                    ? 'bg-gray-600 text-white' 
                                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600/20'
                                }`}
                              >
                                Unknown
                              </button>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAnalyzeTrainingCall(call.id)}
                              disabled={analyzingTrainingCallId === call.id || call.analysis_status === 'analyzing'}
                              className="text-purple-400 border-purple-600 hover:bg-purple-600/20"
                            >
                              {analyzingTrainingCallId === call.id || call.analysis_status === 'analyzing' ? (
                                <>
                                  <Loader2 size={14} className="mr-1 animate-spin" />
                                  Analyzing
                                </>
                              ) : (
                                <>
                                  <Brain size={14} className="mr-1" />
                                  {call.processed ? 'Re-Analyze' : 'Analyze'}
                                </>
                              )}
                            </Button>
                            {call.processed && call.analysis_result && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setExpandedTrainingCallId(expandedTrainingCallId === call.id ? null : call.id)}
                                className="text-blue-400 border-blue-600 hover:bg-blue-600/20"
                              >
                                <Eye size={14} className="mr-1" />
                                {expandedTrainingCallId === call.id ? 'Hide' : 'View'} Results
                                {expandedTrainingCallId === call.id ? <ChevronUp size={14} className="ml-1" /> : <ChevronDown size={14} className="ml-1" />}
                              </Button>
                            )}
                            <Badge 
                              variant={call.processed ? 'default' : 'outline'}
                              className={call.processed ? 'bg-green-600' : call.analysis_status === 'analyzing' ? 'bg-yellow-600' : ''}
                            >
                              {call.analysis_status === 'analyzing' ? 'Analyzing...' : call.processed ? 'Processed' : 'Pending'}
                            </Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-400 hover:text-red-300"
                              onClick={() => handleDeleteTrainingCall(call.id)}
                            >
                              <Trash2 size={16} />
                            </Button>
                          </div>
                        </div>
                        
                        {/* Expandable Results Section */}
                        {expandedTrainingCallId === call.id && call.analysis_result && (
                          <div className="border-t border-gray-700 p-4 bg-gray-900/50">
                            {/* Transcription & Agents Used Section */}
                            <div className="mb-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                              <h4 className="text-white font-medium mb-2 flex items-center gap-2 text-sm">
                                <Brain size={14} className="text-purple-400" />
                                Analysis Configuration
                              </h4>
                              <div className="flex flex-wrap gap-4 text-xs">
                                {/* Transcription Status */}
                                <div className="flex items-center gap-2">
                                  <Mic size={12} className="text-cyan-400" />
                                  <span className="text-gray-400">Transcription:</span>
                                  {call.analysis_result.transcription?.status === 'completed' ? (
                                    <Badge className="bg-cyan-600 text-xs">
                                      Soniox ({call.analysis_result.transcription?.text_length || 0} chars)
                                    </Badge>
                                  ) : call.analysis_result.transcription?.status === 'failed' ? (
                                    <Badge variant="outline" className="text-red-400 border-red-600 text-xs">Failed</Badge>
                                  ) : (
                                    <Badge variant="outline" className="text-yellow-400 border-yellow-600 text-xs">Pending</Badge>
                                  )}
                                </div>
                                {/* Script Agent */}
                                <div className="flex items-center gap-2">
                                  <FileText size={12} className="text-blue-400" />
                                  <span className="text-gray-400">Script Agent:</span>
                                  {call.analysis_result.agents_used?.script_qc_agent?.assigned ? (
                                    <Badge className="bg-green-600 text-xs">{call.analysis_result.agents_used.script_qc_agent.name}</Badge>
                                  ) : (
                                    <Badge variant="outline" className="text-yellow-400 border-yellow-600 text-xs">Default</Badge>
                                  )}
                                </div>
                                {/* Tonality Agent */}
                                <div className="flex items-center gap-2">
                                  <Mic size={12} className="text-purple-400" />
                                  <span className="text-gray-400">Tonality Agent:</span>
                                  {call.analysis_result.agents_used?.tonality_qc_agent?.assigned ? (
                                    <Badge className="bg-green-600 text-xs">{call.analysis_result.agents_used.tonality_qc_agent.name}</Badge>
                                  ) : (
                                    <Badge variant="outline" className="text-yellow-400 border-yellow-600 text-xs">Default</Badge>
                                  )}
                                </div>
                              </div>
                              {call.analysis_result.has_transcript === false && (
                                <p className="text-xs text-yellow-400 mt-2 flex items-center gap-1">
                                  <AlertTriangle size={12} />
                                  {call.analysis_result.transcription?.error || 'Transcription failed or pending - full analysis requires successful transcription'}
                                </p>
                              )}
                            </div>

                            {/* Transcript Preview */}
                            {call.analysis_result.script_analysis?.transcript_preview && (
                              <div className="mb-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                                <h4 className="text-white font-medium mb-2 flex items-center gap-2 text-sm">
                                  <FileText size={14} className="text-cyan-400" />
                                  Transcript Preview
                                </h4>
                                <p className="text-gray-300 text-xs leading-relaxed max-h-32 overflow-y-auto">
                                  {call.analysis_result.script_analysis.transcript_preview}
                                </p>
                              </div>
                            )}

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {/* Script Analysis */}
                              <div className="bg-gray-800 rounded-lg p-4">
                                <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                                  <FileText size={16} className="text-blue-400" />
                                  Script Analysis
                                  {call.analysis_result.script_analysis?.qc_agent_used && (
                                    <span className="text-xs text-gray-500 font-normal">
                                      ({call.analysis_result.script_analysis.qc_agent_used})
                                    </span>
                                  )}
                                </h4>
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between">
                                    <span className="text-gray-400 text-sm">Overall Quality:</span>
                                    <Badge className={
                                      call.analysis_result.script_analysis?.overall_quality === 'excellent' ? 'bg-green-600' :
                                      call.analysis_result.script_analysis?.overall_quality === 'good' ? 'bg-blue-600' :
                                      call.analysis_result.script_analysis?.overall_quality === 'needs_improvement' ? 'bg-yellow-600' :
                                      call.analysis_result.script_analysis?.overall_quality === 'pending_transcription' ? 'bg-gray-600' :
                                      'bg-red-600'
                                    }>
                                      {call.analysis_result.script_analysis?.overall_quality || 'N/A'}
                                    </Badge>
                                  </div>
                                  <p className="text-gray-300 text-sm">
                                    {call.analysis_result.script_analysis?.summary || 'No summary available'}
                                  </p>
                                  {call.analysis_result.script_analysis?.node_analyses?.length > 0 && (
                                    <div className="mt-3">
                                      <p className="text-gray-400 text-xs mb-2">Segment Analysis ({call.analysis_result.script_analysis.node_analyses.length} segments):</p>
                                      <div className="space-y-2 max-h-60 overflow-y-auto">
                                        {call.analysis_result.script_analysis.node_analyses.map((node, idx) => (
                                          <div key={idx} className="text-xs bg-gray-700/50 rounded p-3 border-l-2 border-l-blue-500">
                                            <div className="flex items-center justify-between mb-1">
                                              <span className="text-white font-medium">{node.node_name || `Segment ${idx + 1}`}</span>
                                              <Badge className={
                                                node.quality === 'excellent' ? 'bg-green-600' :
                                                node.quality === 'good' ? 'bg-blue-600' :
                                                node.quality === 'needs_improvement' ? 'bg-yellow-600' :
                                                'bg-red-600'
                                              } variant="secondary">
                                                {node.quality || 'N/A'}
                                              </Badge>
                                            </div>
                                            {node.segment_text && (
                                              <p className="text-gray-500 text-xs italic mb-1 line-clamp-2">&ldquo;{node.segment_text}&rdquo;</p>
                                            )}
                                            <p className="text-gray-300 mb-1">{node.analysis || ''}</p>
                                            {node.suggestion && (
                                              <p className="text-yellow-400 text-xs mt-1">💡 {node.suggestion}</p>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                              
                              {/* Tonality Analysis */}
                              <div className="bg-gray-800 rounded-lg p-4">
                                <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                                  <Mic size={16} className="text-purple-400" />
                                  Tonality Analysis
                                  {call.analysis_result.tonality_analysis?.qc_agent_used && (
                                    <span className="text-xs text-gray-500 font-normal">
                                      ({call.analysis_result.tonality_analysis.qc_agent_used})
                                    </span>
                                  )}
                                </h4>
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between">
                                    <span className="text-gray-400 text-sm">Overall Rating:</span>
                                    <Badge className={
                                      call.analysis_result.tonality_analysis?.overall_rating === 'excellent' ? 'bg-green-600' :
                                      call.analysis_result.tonality_analysis?.overall_rating === 'good' ? 'bg-blue-600' :
                                      call.analysis_result.tonality_analysis?.overall_rating === 'needs_improvement' ? 'bg-yellow-600' :
                                      call.analysis_result.tonality_analysis?.overall_rating === 'pending_transcription' ? 'bg-gray-600' :
                                      'bg-red-600'
                                    }>
                                      {call.analysis_result.tonality_analysis?.overall_rating || 'N/A'}
                                    </Badge>
                                  </div>
                                  <p className="text-gray-300 text-sm">
                                    {call.analysis_result.tonality_analysis?.assessment || 'No assessment available'}
                                  </p>
                                  {call.analysis_result.tonality_analysis?.node_analyses?.length > 0 && (
                                    <div className="mt-3">
                                      <p className="text-gray-400 text-xs mb-2">Segment Analysis ({call.analysis_result.tonality_analysis.node_analyses.length} segments):</p>
                                      <div className="space-y-2 max-h-60 overflow-y-auto">
                                        {call.analysis_result.tonality_analysis.node_analyses.map((node, idx) => (
                                          <div key={idx} className="text-xs bg-gray-700/50 rounded p-3 border-l-2 border-l-purple-500">
                                            <div className="flex items-center justify-between mb-1">
                                              <span className="text-white font-medium">{node.node_name || `Segment ${idx + 1}`}</span>
                                              <div className="flex items-center gap-2">
                                                {node.emotion_detected && (
                                                  <span className="text-purple-300 text-xs">{node.emotion_detected}</span>
                                                )}
                                                <Badge className={
                                                  node.tone_rating === 'excellent' ? 'bg-green-600' :
                                                  node.tone_rating === 'good' ? 'bg-blue-600' :
                                                  node.tone_rating === 'needs_improvement' ? 'bg-yellow-600' :
                                                  'bg-red-600'
                                                } variant="secondary">
                                                  {node.tone_rating || 'N/A'}
                                                </Badge>
                                              </div>
                                            </div>
                                            {node.segment_text && (
                                              <p className="text-gray-500 text-xs italic mb-1 line-clamp-2">&ldquo;{node.segment_text}&rdquo;</p>
                                            )}
                                            <p className="text-gray-300 mb-1">{node.tone_analysis || ''}</p>
                                            {node.suggestion && (
                                              <p className="text-yellow-400 text-xs mt-1">💡 {node.suggestion}</p>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  {call.analysis_result.tonality_analysis?.recommendations && call.analysis_result.tonality_analysis.recommendations.length > 0 && !call.analysis_result.tonality_analysis?.node_analyses?.length && (
                                    <div className="mt-3">
                                      <p className="text-gray-400 text-xs mb-2">Recommendations:</p>
                                      <ul className="text-xs text-gray-300 list-disc list-inside space-y-1">
                                        {Array.isArray(call.analysis_result.tonality_analysis.recommendations) 
                                          ? call.analysis_result.tonality_analysis.recommendations.map((rec, idx) => (
                                              <li key={idx}>{rec}</li>
                                            ))
                                          : <li>{call.analysis_result.tonality_analysis.recommendations}</li>
                                        }
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            {/* Analysis Metadata */}
                            <div className="mt-4 pt-3 border-t border-gray-700 flex items-center justify-between text-xs text-gray-500">
                              <span>Analysis ID: {call.analysis_result.id}</span>
                              <span>Analyzed: {new Date(call.analysis_result.analyzed_at).toLocaleString()}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Real Calls Tab */}
          <TabsContent value="real">
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-white">Real Campaign Calls</CardTitle>
                <div className="flex items-center gap-2">
                  {deleteMode ? (
                    <>
                      <span className="text-sm text-gray-400">
                        {selectedCallsForDeletion.size} selected
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={cancelDeleteMode}
                        className="border-gray-700 text-gray-300"
                      >
                        Cancel
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setShowDeleteConfirmation(true)}
                        disabled={selectedCallsForDeletion.size === 0}
                      >
                        <Trash2 size={14} className="mr-1" />
                        Delete ({selectedCallsForDeletion.size})
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setDeleteMode(true)}
                      className="border-gray-700 text-gray-300 hover:text-red-400 hover:border-red-700"
                      disabled={calls.length === 0}
                    >
                      <Trash2 size={14} className="mr-1" />
                      Delete Calls
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-gray-400 text-sm mb-4">
                  These are actual calls from agents linked to this campaign. Add calls from the QC Dashboard.
                </p>
                
                {calls.length === 0 ? (
                  <div className="text-center py-12">
                    <Phone size={48} className="mx-auto text-gray-600 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-300 mb-2">No Calls Yet</h3>
                    <p className="text-gray-500">
                      Calls will appear here once you add them from the QC Dashboard
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-800">
                          {deleteMode && (
                            <th className="py-3 px-4 w-10">
                              <input
                                type="checkbox"
                                checked={selectedCallsForDeletion.size === calls.length && calls.length > 0}
                                onChange={toggleSelectAll}
                                className="rounded border-gray-600 bg-gray-800 text-purple-500 focus:ring-purple-500"
                              />
                            </th>
                          )}
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">Call ID</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">Category</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">Date</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">Status</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calls.map((call) => (
                          <tr 
                            key={call.call_id} 
                            className={`border-b border-gray-800 hover:bg-gray-800/50 ${
                              deleteMode && selectedCallsForDeletion.has(call.call_id) ? 'bg-red-900/20' : ''
                            }`}
                          >
                            {deleteMode && (
                              <td className="py-3 px-4">
                                <input
                                  type="checkbox"
                                  checked={selectedCallsForDeletion.has(call.call_id)}
                                  onChange={() => toggleCallSelection(call.call_id)}
                                  className="rounded border-gray-600 bg-gray-800 text-red-500 focus:ring-red-500"
                                />
                              </td>
                            )}
                            <td className="py-3 px-4">
                              <code className="text-xs text-purple-400">{call.call_id?.slice(0, 20)}...</code>
                            </td>
                            <td className="py-3 px-4">
                              {call.category ? (
                                <Badge variant="outline">{call.category}</Badge>
                              ) : (
                                <span className="text-gray-500 text-sm">-</span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-sm text-gray-300">
                              {call.analyzed_at ? new Date(call.analyzed_at).toLocaleString() : 'N/A'}
                            </td>
                            <td className="py-3 px-4">
                              {call.analysis_status === 'analyzing' ? (
                                <span className="flex items-center gap-1 text-sm text-yellow-400">
                                  <Loader2 size={14} className="animate-spin" />
                                  Analyzing...
                                </span>
                              ) : call.analysis_status === 'failed' ? (
                                <span className="flex items-center gap-1 text-sm text-red-400" title={call.analysis_error || 'Analysis failed'}>
                                  <AlertTriangle size={14} />
                                  Failed
                                </span>
                              ) : call.script_qc_results || call.tech_qc_results || call.tonality_qc_results ? (
                                <span className="flex items-center gap-1 text-sm text-green-400">
                                  <CheckCircle size={14} />
                                  Analyzed
                                </span>
                              ) : (
                                <span className="flex items-center gap-1 text-sm text-gray-400">
                                  <Clock size={14} />
                                  Pending
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-4">
                              <button
                                onClick={() => window.open(`/qc/calls/${call.call_id}`, '_blank')}
                                className="text-purple-400 hover:text-purple-300 text-sm flex items-center gap-1"
                              >
                                <Zap size={14} />
                                View QC ↗
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                
                {/* Delete Confirmation Dialog */}
                {showDeleteConfirmation && (
                  <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
                    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-md mx-4">
                      <h3 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                        <AlertTriangle className="text-red-500" size={24} />
                        Confirm Deletion
                      </h3>
                      <p className="text-gray-300 mb-4">
                        Are you sure you want to delete <strong className="text-red-400">{selectedCallsForDeletion.size}</strong> call(s) from this campaign?
                      </p>
                      <p className="text-gray-500 text-sm mb-6">
                        This will remove the calls from the campaign and delete all associated QC analysis data. The original call logs will be preserved.
                      </p>
                      <div className="flex justify-end gap-3">
                        <Button
                          variant="outline"
                          onClick={() => setShowDeleteConfirmation(false)}
                          className="border-gray-700"
                          disabled={deletingCalls}
                        >
                          Cancel
                        </Button>
                        <Button
                          variant="destructive"
                          onClick={deleteSelectedCalls}
                          disabled={deletingCalls}
                        >
                          {deletingCalls ? (
                            <>
                              <Loader2 size={14} className="mr-1 animate-spin" />
                              Deleting...
                            </>
                          ) : (
                            <>
                              <Trash2 size={14} className="mr-1" />
                              Delete {selectedCallsForDeletion.size} Call(s)
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Patterns Tab */}
          <TabsContent value="patterns">
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white">Identified Patterns</CardTitle>
                  <Button onClick={handleAnalyzePatterns}>
                    <Sparkles size={16} className="mr-2" />
                    Re-analyze
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {patterns.length === 0 ? (
                  <div className="text-center py-12">
                    <TrendingUp size={48} className="mx-auto text-gray-600 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-300 mb-2">No Patterns Yet</h3>
                    <p className="text-gray-500 mb-4">
                      Add at least 2 analyzed calls to detect patterns
                    </p>
                    <Button onClick={handleAnalyzePatterns} disabled={calls.length < 2}>
                      Run Pattern Detection
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {patterns.map((pattern, idx) => (
                      <div key={idx} className="bg-gray-800/50 rounded-lg p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="font-semibold text-white mb-1 capitalize">{pattern.pattern_type}</h3>
                            <p className="text-sm text-gray-400 mb-2">{pattern.description}</p>
                            <div className="flex items-center gap-4 text-xs">
                              <span className="text-gray-500">Confidence:</span>
                              <span className="text-purple-400">{Math.round((pattern.confidence_score || 0) * 100)}%</span>
                              <span className="text-gray-500">Evidence calls:</span>
                              <span className="text-blue-400">{pattern.evidence_calls?.length || 0}</span>
                            </div>
                          </div>
                          <Badge className={`
                            ${pattern.pattern_type === 'bottleneck' ? 'bg-red-900/30 text-red-400' :
                              pattern.pattern_type === 'success' ? 'bg-green-900/30 text-green-400' :
                              'bg-purple-900/30 text-purple-400'}
                          `}>
                            {pattern.pattern_type}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Agents Tab */}
          <TabsContent value="agents">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Multi-Agent Configuration */}
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-white">Campaign Agents</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400 text-sm mb-4">
                    Configure different agents for different stages of the customer journey.
                  </p>
                  
                  {(!campaign.campaign_agents || campaign.campaign_agents.length === 0) ? (
                    <div className="text-center py-8">
                      <Users size={48} className="mx-auto text-gray-600 mb-4" />
                      <p className="text-gray-500 mb-4">No agents configured</p>
                      <Button variant="outline" onClick={() => navigate(`/qc/campaigns/${campaignId}/settings`)}>
                        <Plus size={16} className="mr-2" />
                        Configure Agents
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {campaign.campaign_agents.map((agent, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-gray-800/50 rounded">
                          <div>
                            <p className="font-medium text-white">{agent.agent_name || agent.agent_id}</p>
                            <p className="text-xs text-gray-500 capitalize">{agent.role?.replace(/_/g, ' ')}</p>
                          </div>
                          <Badge variant={agent.is_required ? 'default' : 'outline'}>
                            {agent.is_required ? 'Required' : 'Optional'}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* QC Agents */}
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-white">QC Agents</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400 text-sm mb-4">
                    Assign QC agents to analyze calls in this campaign.
                  </p>
                  
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded bg-purple-900/30">
                          <FileText size={16} className="text-purple-400" />
                        </div>
                        <div>
                          <p className="font-medium text-white">Tonality QC</p>
                          <p className="text-xs text-gray-500">Voice & emotion analysis</p>
                        </div>
                      </div>
                      {campaign.tonality_qc_agent_id ? (
                        <Badge className="bg-green-900/30 text-green-400">Assigned</Badge>
                      ) : (
                        <Badge variant="outline">Not Set</Badge>
                      )}
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded bg-blue-900/30">
                          <FileText size={16} className="text-blue-400" />
                        </div>
                        <div>
                          <p className="font-medium text-white">Language Pattern QC</p>
                          <p className="text-xs text-gray-500">Script & pattern analysis</p>
                        </div>
                      </div>
                      {campaign.language_pattern_qc_agent_id ? (
                        <Badge className="bg-green-900/30 text-green-400">Assigned</Badge>
                      ) : (
                        <Badge variant="outline">Not Set</Badge>
                      )}
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded bg-orange-900/30">
                          <Settings size={16} className="text-orange-400" />
                        </div>
                        <div>
                          <p className="font-medium text-white">Tech Issues QC</p>
                          <p className="text-xs text-gray-500">Log & code analysis</p>
                        </div>
                      </div>
                      {campaign.tech_issues_qc_agent_id ? (
                        <Badge className="bg-green-900/30 text-green-400">Assigned</Badge>
                      ) : (
                        <Badge variant="outline">Not Set</Badge>
                      )}
                    </div>
                  </div>
                  
                  <Button
                    className="w-full mt-4"
                    variant="outline"
                    onClick={() => navigate(`/qc/campaigns/${campaignId}/settings`)}
                  >
                    Manage QC Agents
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* QC Results Tab */}
          <TabsContent value="qc-results">
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white flex items-center gap-2">
                    <Sparkles size={20} className="text-purple-400" />
                    QC Analysis Results
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={resetAllAnalysis}
                      variant="outline"
                      size="sm"
                      disabled={resettingAll || loadingQcResults}
                      className="text-red-400 border-red-800 hover:bg-red-900/30"
                    >
                      {resettingAll ? <Loader2 className="animate-spin" size={14} /> : <Trash2 size={14} className="mr-1" />}
                      {resettingAll ? 'Resetting...' : 'Reset All'}
                    </Button>
                    <Button
                      onClick={fetchQcResults}
                      variant="outline"
                      size="sm"
                      disabled={loadingQcResults}
                    >
                      {loadingQcResults ? <Loader2 className="animate-spin" size={14} /> : 'Refresh'}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {loadingQcResults ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="animate-spin text-purple-400" size={32} />
                  </div>
                ) : qcResults ? (
                  <div className="space-y-6">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-gray-800 rounded-lg p-4">
                        <div className="text-2xl font-bold text-white">{qcResults.summary?.total_calls || 0}</div>
                        <div className="text-sm text-gray-400">Total Calls</div>
                      </div>
                      <div className="bg-green-900/30 rounded-lg p-4">
                        <div className="text-2xl font-bold text-green-400">{qcResults.summary?.analyzed || 0}</div>
                        <div className="text-sm text-gray-400">Analyzed</div>
                      </div>
                      <div className="bg-yellow-900/30 rounded-lg p-4">
                        <div className="text-2xl font-bold text-yellow-400">{qcResults.summary?.pending || 0}</div>
                        <div className="text-sm text-gray-400">Pending</div>
                      </div>
                      <div className="bg-red-900/30 rounded-lg p-4">
                        <div className="text-2xl font-bold text-red-400">{qcResults.summary?.failed || 0}</div>
                        <div className="text-sm text-gray-400">Failed</div>
                      </div>
                    </div>
                    
                    {/* Batch Analysis Status */}
                    {(batchAnalysisPolling || qcResults.batch_analysis_status === 'running' || qcResults.calls?.some(c => c.analysis_status === 'analyzing')) && (
                      <div className="bg-purple-900/20 border border-purple-700/30 rounded-lg p-4">
                        <div className="flex items-center gap-2 text-purple-300">
                          <Loader2 className="animate-spin" size={16} />
                          <span>
                            Analyzing calls... 
                            ({qcResults.calls?.filter(c => c.analysis_status === 'completed').length || 0} / {qcResults.calls?.length || 0} complete)
                          </span>
                          <span className="text-xs text-gray-500 ml-2">Auto-refreshing every 3s</span>
                        </div>
                        {/* Progress bar */}
                        <div className="mt-2 w-full bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                            style={{ 
                              width: `${qcResults.calls?.length > 0 
                                ? (qcResults.calls.filter(c => c.analysis_status === 'completed').length / qcResults.calls.length) * 100 
                                : 0}%` 
                            }}
                          />
                        </div>
                      </div>
                    )}
                    
                    {/* Completed status */}
                    {!batchAnalysisPolling && !qcResults.calls?.some(c => c.analysis_status === 'analyzing') && qcResults.summary?.analyzed > 0 && (
                      <div className="bg-green-900/20 border border-green-700/30 rounded-lg p-4">
                        <div className="flex items-center gap-2 text-green-300">
                          <CheckCircle size={16} />
                          <span>Analysis Complete: {qcResults.summary?.analyzed || 0} calls analyzed</span>
                        </div>
                      </div>
                    )}
                    
                    {/* Results Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-700 text-gray-400 text-sm">
                            <th className="text-left py-3 px-4">Call ID</th>
                            <th className="text-left py-3 px-4">Status</th>
                            <th className="text-center py-3 px-4">Tech QC</th>
                            <th className="text-center py-3 px-4">Script QC</th>
                            <th className="text-center py-3 px-4">Tonality</th>
                            <th className="text-left py-3 px-4">Script Summary</th>
                            <th className="text-left py-3 px-4">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {qcResults.calls && qcResults.calls.map((call, index) => (
                            <tr key={index} className="border-b border-gray-800 hover:bg-gray-800/50">
                              <td className="py-3 px-4 text-sm text-gray-300 font-mono">
                                {call.call_id?.slice(0, 25)}...
                              </td>
                              <td className="py-3 px-4">
                                {call.analysis_status === 'analyzing' ? (
                                  <span className="flex items-center gap-1 text-sm text-yellow-400">
                                    <Loader2 size={14} className="animate-spin" />
                                    Analyzing
                                  </span>
                                ) : call.analysis_status === 'failed' ? (
                                  <span className="flex items-center gap-1 text-sm text-red-400" title={call.analysis_error}>
                                    <AlertTriangle size={14} />
                                    Failed
                                  </span>
                                ) : call.has_tech_qc || call.has_script_qc || call.has_tonality_qc ? (
                                  <span className="flex items-center gap-1 text-sm text-green-400">
                                    <CheckCircle size={14} />
                                    Analyzed
                                  </span>
                                ) : (
                                  <span className="flex items-center gap-1 text-sm text-gray-400">
                                    <Clock size={14} />
                                    Pending
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-center">
                                {call.has_tech_qc ? (
                                  <CheckCircle size={16} className="text-green-400 mx-auto" />
                                ) : (
                                  <span className="text-gray-500">—</span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-center">
                                {call.has_script_qc ? (
                                  <CheckCircle size={16} className="text-green-400 mx-auto" />
                                ) : (
                                  <span className="text-gray-500">—</span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-center">
                                {call.has_tonality_qc ? (
                                  <CheckCircle size={16} className="text-green-400 mx-auto" />
                                ) : (
                                  <span className="text-gray-500">—</span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-sm">
                                {call.script_summary ? (
                                  <div className="flex items-center gap-2">
                                    <span className="text-green-400">{call.script_summary.good_quality}✓</span>
                                    <span className="text-yellow-400">{call.script_summary.needs_improvement}⚠</span>
                                    <span className="text-red-400">{call.script_summary.poor_quality}✗</span>
                                  </div>
                                ) : (
                                  <span className="text-gray-500">—</span>
                                )}
                              </td>
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-1">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => window.open(`/qc/calls/${encodeURIComponent(call.call_id)}?campaign=${campaignId}`, '_blank')}
                                    className="text-purple-400 hover:text-purple-300"
                                  >
                                    <Zap size={14} className="mr-1" />
                                    View QC ↗
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => resetCallAnalysis(call.call_id)}
                                    disabled={resettingCallId === call.call_id}
                                    className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                                    title="Reset analysis for this call"
                                  >
                                    {resettingCallId === call.call_id ? (
                                      <Loader2 size={14} className="animate-spin" />
                                    ) : (
                                      <Trash2 size={14} />
                                    )}
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    
                    {(!qcResults.calls || qcResults.calls.length === 0) && (
                      <div className="text-center py-12 text-gray-400">
                        <Sparkles size={48} className="mx-auto mb-4 opacity-30" />
                        <p>No QC analysis results yet.</p>
                        <p className="text-sm mt-2">Run &quot;Analyze All Calls&quot; to start batch analysis.</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-400">
                    <p>No QC results data available.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Analyze All Calls Modal */}
      {showAnalyzeModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-lg border border-gray-700 max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Zap className="text-green-400" />
                Analyze All Calls
              </h2>
              <button
                onClick={() => setShowAnalyzeModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <X size={20} />
              </button>
            </div>

            <p className="text-gray-400 text-sm mb-6">
              Select which types of QC analysis to run on all calls in this campaign.
              Each analysis will use the corresponding QC agent&apos;s settings.
            </p>

            {/* Analysis Type Selection */}
            <div className="space-y-3 mb-6">
              {/* Script Quality */}
              <label className="flex items-start gap-3 p-4 bg-gray-800/50 rounded-lg cursor-pointer hover:bg-gray-800 transition-colors">
                <input
                  type="checkbox"
                  checked={selectedAnalysisTypes.includes('script')}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedAnalysisTypes([...selectedAnalysisTypes, 'script']);
                    } else {
                      setSelectedAnalysisTypes(selectedAnalysisTypes.filter(t => t !== 'script'));
                    }
                  }}
                  className="mt-1 w-4 h-4 text-blue-600 bg-gray-800 border-gray-700 rounded focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <FileText size={16} className="text-blue-400" />
                    <span className="text-white font-medium">Script Quality Analysis</span>
                    {campaign?.language_pattern_qc_agent_id ? (
                      <Badge className="bg-green-900/30 text-green-400 text-xs">Agent Assigned</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-400 border-red-500 text-xs">No Agent</Badge>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Analyzes conversation quality, brevity, goal alignment, naturalness
                  </p>
                </div>
              </label>

              {/* Tonality */}
              <label className="flex items-start gap-3 p-4 bg-gray-800/50 rounded-lg cursor-pointer hover:bg-gray-800 transition-colors">
                <input
                  type="checkbox"
                  checked={selectedAnalysisTypes.includes('tonality')}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedAnalysisTypes([...selectedAnalysisTypes, 'tonality']);
                    } else {
                      setSelectedAnalysisTypes(selectedAnalysisTypes.filter(t => t !== 'tonality'));
                    }
                  }}
                  className="mt-1 w-4 h-4 text-purple-600 bg-gray-800 border-gray-700 rounded focus:ring-purple-500"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Mic size={16} className="text-purple-400" />
                    <span className="text-white font-medium">Tonality Analysis</span>
                    {campaign?.tonality_qc_agent_id ? (
                      <Badge className="bg-green-900/30 text-green-400 text-xs">Agent Assigned</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-400 border-red-500 text-xs">No Agent</Badge>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Analyzes voice delivery, emotion, pacing, provides SSML recommendations
                  </p>
                </div>
              </label>
            </div>

            {/* Warning if agents not assigned */}
            {(!campaign?.language_pattern_qc_agent_id && selectedAnalysisTypes.includes('script')) || 
             (!campaign?.tonality_qc_agent_id && selectedAnalysisTypes.includes('tonality')) ? (
              <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-red-400 mt-0.5" />
                  <div>
                    <h4 className="text-red-400 font-medium">QC Agents Required</h4>
                    <p className="text-sm text-gray-400 mt-1">
                      Please assign QC agents before running analysis. 
                      Without assigned agents, the analysis cannot use your custom settings.
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3 border-red-700 text-red-400 hover:bg-red-900/30"
                      onClick={() => {
                        setShowAnalyzeModal(false);
                        navigate(`/qc/campaigns/${campaignId}/settings`);
                      }}
                    >
                      <Settings size={14} className="mr-2" />
                      Go to Campaign Settings
                    </Button>
                  </div>
                </div>
              </div>
            ) : null}

            {/* Force Re-analyze Option */}
            <label className="flex items-center gap-3 mb-6">
              <input
                type="checkbox"
                checked={forceReanalyze}
                onChange={(e) => setForceReanalyze(e.target.checked)}
                className="w-4 h-4 text-purple-600 bg-gray-800 border-gray-700 rounded focus:ring-purple-500"
              />
              <div>
                <span className="text-white text-sm">Force re-analyze all calls</span>
                <p className="text-xs text-gray-500">Re-analyze even if already analyzed</p>
              </div>
            </label>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                onClick={handleAnalyzeAllCalls}
                disabled={selectedAnalysisTypes.length === 0 || analyzingAll}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                {analyzingAll ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Zap size={16} className="mr-2" />
                    Start Analysis
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowAnalyzeModal(false)}
                className="border-gray-700"
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Campaign Report Modal */}
      <CampaignReportView
        report={reportData}
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        onDownload={handleDownloadReport}
      />
    </div>
  );
};

export default CampaignDetailsPage;
