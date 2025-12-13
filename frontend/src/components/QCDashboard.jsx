import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { 
  ArrowLeft, 
  Zap, 
  MessageSquare, 
  Mic, 
  TestTube, 
  Upload,
  Download,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  ChevronDown,
  FileText,
  Settings,
  Save,
  Info
} from 'lucide-react';
import apiClient, { callAPI, qcEnhancedAPI, agentAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import ScriptQualityTab from './ScriptQualityTab';
import TonalityTab from './TonalityTab';
import UnifiedQCPanel from './UnifiedQCPanel';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

const QCDashboard = () => {
  const { callId } = useParams();
  const [searchParams] = useSearchParams();
  const campaignId = searchParams.get('campaign'); // Get campaign ID from URL if present
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [activeTab, setActiveTab] = useState('tech'); // 'tech', 'script', 'tonality', 'direct'
  const [loading, setLoading] = useState(false);
  const [callData, setCallData] = useState(null);
  const [techAnalysis, setTechAnalysis] = useState(null);
  const [scriptAnalysis, setScriptAnalysis] = useState(null);
  const [tonalityAnalysis, setTonalityAnalysis] = useState(null);
  const [audioTonalityAnalysis, setAudioTonalityAnalysis] = useState(null);
  
  const [logFile, setLogFile] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzingType, setAnalyzingType] = useState(null); // Which type is being analyzed
  
  // Node optimization state
  const [optimizingNode, setOptimizingNode] = useState(null);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [applyingOptimization, setApplyingOptimization] = useState(false);
  
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [showCallLogViewer, setShowCallLogViewer] = useState(false);
  const [showQCSettings, setShowQCSettings] = useState(false);
  
  // Agent selection for Direct Test tab
  const [agents, setAgents] = useState([]);
  const [selectedTestAgentId, setSelectedTestAgentId] = useState('');
  
  const [qcSettings, setQCSettings] = useState({
    llm_provider: 'grok',  // grok, openai, anthropic, google
    model: 'grok-4-1-fast-non-reasoning',
    tts_provider: 'elevenlabs',  // Only ElevenLabs shown in UI
    stt_provider: 'soniox',      // Only Soniox shown in UI
    tech_guidelines: 'Analyze call latency and identify bottlenecks. Flag any node with TTFS > 4 seconds. Focus on LLM processing time, KB retrieval, and transition evaluation delays.',
    script_guidelines: 'Evaluate conversation flow, clarity, and effectiveness. Check for brevity, goal alignment, and naturalness. Suggest improvements to make responses sharper and more engaging.',
    tonality_guidelines: 'Assess voice delivery, pacing, emotion, and tone. Identify monotone sections, rushed speech, or inappropriate emotional expression. Provide SSML/prosody recommendations for improvement.',
    // Individual agent settings (new)
    agentSettings: null,
    globalSettings: null,
    analysis_rules: {
      focus_on_brevity: true,
      check_goal_alignment: true,
      evaluate_naturalness: true,
      flag_latency_threshold: 4  // seconds
    }
  });
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState('');

  useEffect(() => {
    if (callId) {
      fetchCallData();
      fetchCampaigns();
    }
  }, [callId]);

  // Load agents when Direct Test tab is active
  useEffect(() => {
    if (activeTab === 'direct') {
      fetchAgents();
    }
  }, [activeTab]);

  const fetchAgents = async () => {
    try {
      const response = await agentAPI.list();
      // Filter to only call_flow agents (they have nodes to test)
      const callFlowAgents = (response.data || []).filter(a => 
        a.agent_type === 'call_flow' && a.call_flow && a.call_flow.length > 0
      );
      setAgents(callFlowAgents);
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

  const fetchCampaigns = async () => {
    try {
      const response = await qcEnhancedAPI.listCampaigns();
      setCampaigns(response.data);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
    }
  };

  const addToCampaign = async () => {
    if (!selectedCampaign) {
      toast({
        title: "No Campaign Selected",
        description: "Please select a campaign",
        variant: "destructive"
      });
      return;
    }

    try {
      await qcEnhancedAPI.addCallToCampaign(selectedCampaign, { call_id: callId });
      toast({
        title: "Success",
        description: "Call added to campaign"
      });
      setShowCampaignModal(false);
    } catch (error) {
      console.error('Error adding to campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to add call to campaign",
        variant: "destructive"
      });
    }
  };

  // Node optimization handler
  const handleOptimizeNode = async (node) => {
    if (!callData?.agent_id) {
      toast({
        title: "No Agent",
        description: "This call doesn't have an associated agent to optimize",
        variant: "destructive"
      });
      return;
    }
    
    try {
      setOptimizingNode(node.node_id || node.node_name);
      setOptimizationResult(null);
      
      toast({
        title: "Optimizing Node",
        description: `Running optimization and latency tests for ${node.node_name}...`
      });
      
      const response = await qcEnhancedAPI.optimizeNode({
        agent_id: callData.agent_id,
        node_id: node.node_id,
        optimization_type: 'both',
        test_input: 'Hello, I have a question about your services.',
        max_attempts: 2
      });
      
      setOptimizationResult(response.data);
      
      if (response.data.can_apply && response.data.improvement_percent > 0) {
        toast({
          title: "Optimization Complete!",
          description: `Improved latency by ${response.data.improvement_percent}% (${response.data.total_improvement_ms}ms)`
        });
      } else {
        toast({
          title: "Optimization Complete",
          description: "No significant improvement found. Check suggestions below.",
          variant: "default"
        });
      }
    } catch (error) {
      console.error('Optimization error:', error);
      toast({
        title: "Optimization Failed",
        description: error.response?.data?.detail || "Failed to optimize node",
        variant: "destructive"
      });
    } finally {
      setOptimizingNode(null);
    }
  };
  
  // Apply optimization handler
  const handleApplyOptimization = async () => {
    if (!optimizationResult?.best_optimization) return;
    
    try {
      setApplyingOptimization(true);
      
      const response = await qcEnhancedAPI.applyNodeOptimization({
        agent_id: optimizationResult.agent_id,
        node_id: optimizationResult.node_id,
        optimized_prompt: optimizationResult.best_optimization.optimized_prompt,
        optimized_content: optimizationResult.best_optimization.optimized_content
      });
      
      toast({
        title: "Changes Applied!",
        description: response.data.message
      });
      
      // Clear optimization result
      setOptimizationResult(null);
    } catch (error) {
      console.error('Apply optimization error:', error);
      toast({
        title: "Failed to Apply",
        description: error.response?.data?.detail || "Failed to apply optimization",
        variant: "destructive"
      });
    } finally {
      setApplyingOptimization(false);
    }
  };

  const fetchCallData = async () => {
    try {
      setLoading(true);
      // Use new QC-specific endpoint that handles special characters in call_id
      // Pass campaign_id if available to get results from campaign_calls collection
      const response = await qcEnhancedAPI.fetchCallForQC(callId, campaignId);
      setCallData(response.data);
      
      // Load saved QC results if they exist
      if (response.data.tech_qc_results) {
        setTechAnalysis(response.data.tech_qc_results);
      }
      if (response.data.script_qc_results) {
        setScriptAnalysis(response.data.script_qc_results);
      }
      if (response.data.tonality_qc_results) {
        setTonalityAnalysis(response.data.tonality_qc_results);
      }
      if (response.data.audio_tonality_results) {
        setAudioTonalityAnalysis(response.data.audio_tonality_results);
      }
    } catch (error) {
      console.error('Error fetching call:', error);
      
      // Handle specific errors
      if (error.response?.status === 401) {
        toast({
          title: "Authentication Required",
          description: "Please log in to access QC analysis",
          variant: "destructive"
        });
        // Redirect to login after 2 seconds
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else if (error.response?.status === 404) {
        toast({
          title: "Call Not Found",
          description: "This call doesn't exist or you don't have access to it",
          variant: "destructive"
        });
        setTimeout(() => {
          navigate('/calls');
        }, 2000);
      } else {
        toast({
          title: "Error",
          description: error.response?.data?.detail || "Failed to load call data",
          variant: "destructive"
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setLogFile(e.target.result);
        toast({
          title: "Log Loaded",
          description: `${file.name} ready for analysis`
        });
      };
      reader.readAsText(file);
    }
  };

  // Wrapper functions for unified QC panel - accept QC agent ID
  const analyzeTech = async (qcAgentId) => {
    await analyzeTechPerformance(qcAgentId);
  };

  const analyzeScript = async (qcAgentId) => {
    // Script analysis - pass QC agent ID to get its settings
    setActiveTab('script');
    // The ScriptQualityTab handles its own analysis
    toast({
      title: "Script Analysis",
      description: "Switch to Script Quality tab to run analysis"
    });
  };

  const analyzeTonality = async (qcAgentId) => {
    // Tonality analysis - pass QC agent ID  
    setActiveTab('tonality');
    // The TonalityTab handles its own analysis
    toast({
      title: "Tonality Analysis", 
      description: "Switch to Tonality tab to run analysis"
    });
  };
  
  // Handler for when TonalityTab completes an analysis
  const handleTonalityAnalysisComplete = (type, data) => {
    if (type === 'tonality') {
      setTonalityAnalysis(data);
    } else if (type === 'audio_tonality') {
      setAudioTonalityAnalysis(data);
    }
  };

  const analyzeTechPerformance = async (qcAgentId = null) => {
    // Try to use logs/call_log from database first, then fall back to uploaded file
    // The API returns logs as call_log, but also check for logs field
    const logsArray = callData?.call_log || callData?.logs;
    const hasLogs = logsArray && (Array.isArray(logsArray) ? logsArray.length > 0 : Object.keys(logsArray).length > 0);
    const logData = hasLogs ? JSON.stringify(logsArray, null, 2) : logFile;
    
    if (!logData) {
      toast({
        title: "No Log Data Available",
        description: "This call doesn't have log data. Please upload a log file or record a new call.",
        variant: "destructive"
      });
      return;
    }

    try {
      setAnalyzing(true);
      const response = await qcEnhancedAPI.analyzeTech({
        call_id: callId,
        call_log_data: typeof logData === 'string' ? logData : JSON.stringify(logData),
        custom_guidelines: qcSettings.tech_guidelines,
        llm_provider: qcSettings.llm_provider,
        model: qcSettings.model,
        qc_agent_id: qcAgentId  // Pass QC agent ID to use its settings
      });
      
      setTechAnalysis(response.data);
      toast({
        title: "Analysis Complete",
        description: `Analyzed ${response.data.total_nodes} nodes, ${response.data.flagged_nodes} flagged for optimization`
      });
    } catch (error) {
      console.error('Error analyzing tech performance:', error);
      toast({
        title: "Analysis Failed",
        description: error.response?.data?.detail || "Failed to analyze performance",
        variant: "destructive"
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const getPerformanceColor = (performance) => {
    const colors = {
      excellent: 'text-green-400 bg-green-900/30 border-green-700',
      good: 'text-blue-400 bg-blue-900/30 border-blue-700',
      'needs improvement': 'text-yellow-400 bg-yellow-900/30 border-yellow-700',
      poor: 'text-red-400 bg-red-900/30 border-red-700'
    };
    return colors[performance] || colors.good;
  };

  const getTTFSColor = (ttfs) => {
    if (ttfs < 2) return 'text-green-400';
    if (ttfs < 4) return 'text-yellow-400';
    return 'text-red-400';
  };

  const tabs = [
    { id: 'tech', label: 'Tech/Latency', icon: Zap, description: 'Performance bottlenecks' },
    { id: 'script', label: 'Script Quality', icon: MessageSquare, description: 'Conversation optimization' },
    { id: 'tonality', label: 'Tonality', icon: Mic, description: 'Voice delivery' },
    { id: 'direct', label: 'Direct Test', icon: TestTube, description: 'Test node changes' }
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/calls')}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <ArrowLeft size={24} />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-white">QC Analysis Dashboard</h1>
                <p className="text-sm text-gray-400 mt-1">
                  {callData ? `Call with ${callData.phone_number || 'Unknown'}` : 'Loading...'}
                </p>
              </div>
            </div>
            
            {callData && (
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-sm text-gray-400">Duration</div>
                  <div className="text-white font-medium">{Math.floor(callData.duration / 60)}m {callData.duration % 60}s</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-400">Sentiment</div>
                  <div className="text-white font-medium capitalize">{callData.sentiment}</div>
                </div>
                
                {/* Call Log Download Button - check both call_log and logs fields */}
                {(() => {
                  const logsData = callData?.call_log || callData?.logs;
                  const hasLogs = logsData && (Array.isArray(logsData) ? logsData.length > 0 : Object.keys(logsData).length > 0);
                  
                  if (hasLogs) {
                    return (
                      <button
                        onClick={() => {
                          const blob = new Blob([JSON.stringify(logsData, null, 2)], { type: 'application/json' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `call-log-${callId}.json`;
                          a.click();
                          URL.revokeObjectURL(url);
                          toast({
                            title: "Downloaded",
                            description: "Call log saved to your downloads"
                          });
                        }}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm transition-colors flex items-center gap-2"
                        title="Download call log JSON"
                      >
                        <Download size={16} />
                        Call Log
                      </button>
                    );
                  }
                  return null;
                })()}
                
                <button
                  onClick={() => setShowQCSettings(true)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors flex items-center gap-2"
                  title="QC Agent Settings"
                >
                  <Settings size={16} />
                  QC Settings
                </button>
                
                <button
                  onClick={() => setShowCampaignModal(true)}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition-colors"
                >
                  Add to Campaign
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Call Log Viewer (Collapsible) - Shows logs/call_log from API */}
      {callData && (callData.call_log || callData.logs) && (
        Array.isArray(callData.call_log || callData.logs) 
          ? (callData.call_log || callData.logs).length > 0
          : Object.keys(callData.call_log || callData.logs || {}).length > 0
      ) && (
        <div className="border-b border-gray-800 bg-gray-900">
          <div className="max-w-7xl mx-auto px-6">
            <button
              onClick={() => setShowCallLogViewer(!showCallLogViewer)}
              className="w-full py-3 flex items-center justify-between text-left hover:bg-gray-800/50 transition-colors"
            >
              <span className="flex items-center gap-2 text-sm font-medium text-gray-300">
                <FileText size={16} className="text-green-400" />
                Detailed Call Log ({
                  Array.isArray(callData.call_log || callData.logs)
                    ? (callData.call_log || callData.logs).length
                    : Object.keys((callData.call_log || callData.logs)?.nodes || {}).length
                } {Array.isArray(callData.call_log || callData.logs) ? 'entries' : 'nodes'})
              </span>
              <ChevronDown 
                size={20} 
                className={`text-gray-400 transition-transform ${showCallLogViewer ? 'rotate-180' : ''}`} 
              />
            </button>
            
            {showCallLogViewer && (
              <div className="pb-4 space-y-2">
                {/* Formatted Log Entries */}
                {Array.isArray(callData.call_log || callData.logs) && (callData.call_log || callData.logs).map((log, idx) => (
                  <div key={idx} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                        log.type === 'turn_complete' ? 'bg-blue-900/50 text-blue-300' :
                        log.type === 'call_start' ? 'bg-green-900/50 text-green-300' :
                        log.type === 'call_end' ? 'bg-red-900/50 text-red-300' :
                        log.level === 'metrics' ? 'bg-yellow-900/50 text-yellow-300' :
                        'bg-gray-700 text-gray-300'
                      }`}>
                        {log.type || log.level || 'info'}
                      </span>
                      <span className="text-xs text-gray-500">{log.timestamp}</span>
                    </div>
                    
                    {/* Show full user/agent text if available */}
                    {log.user_text && (
                      <div className="mb-2">
                        <span className="text-xs text-gray-400">User:</span>
                        <p className="text-sm text-white bg-gray-900/50 rounded p-2 mt-1">{log.user_text}</p>
                      </div>
                    )}
                    {log.agent_text && (
                      <div className="mb-2">
                        <span className="text-xs text-gray-400">Agent:</span>
                        <p className="text-sm text-green-300 bg-gray-900/50 rounded p-2 mt-1">{log.agent_text}</p>
                      </div>
                    )}
                    
                    {/* Show latency details if available */}
                    {log.latency && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {log.latency.e2e_ms !== undefined && (
                          <span className="text-xs bg-purple-900/30 text-purple-300 px-2 py-1 rounded">
                            E2E: {log.latency.e2e_ms}ms
                          </span>
                        )}
                        {log.latency.llm_ms !== undefined && (
                          <span className="text-xs bg-blue-900/30 text-blue-300 px-2 py-1 rounded">
                            LLM: {log.latency.llm_ms}ms
                          </span>
                        )}
                        {log.latency.stt_ms !== undefined && (
                          <span className="text-xs bg-green-900/30 text-green-300 px-2 py-1 rounded">
                            STT: {log.latency.stt_ms}ms
                          </span>
                        )}
                        {log.latency.tts_ms !== undefined && (
                          <span className="text-xs bg-yellow-900/30 text-yellow-300 px-2 py-1 rounded">
                            TTS: {log.latency.tts_ms}ms
                          </span>
                        )}
                      </div>
                    )}
                    
                    {/* Show details object if available */}
                    {log.details && (
                      <div className="mt-2 text-xs text-gray-400">
                        {Object.entries(log.details).map(([key, value]) => (
                          <span key={key} className="mr-3">
                            <span className="text-gray-500">{key}:</span> {String(value)}
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {/* Fallback to raw message if no structured data */}
                    {!log.user_text && !log.agent_text && log.message && (
                      <p className="text-sm text-gray-300">{log.message}</p>
                    )}
                  </div>
                ))}
                
                {/* Raw JSON Toggle */}
                <details className="mt-4">
                  <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
                    Show Raw JSON
                  </summary>
                  <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap mt-2 bg-gray-900 p-3 rounded overflow-auto max-h-64">
                    {JSON.stringify(callData.call_log || callData.logs, null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-4 border-b-2 transition-all ${
                    activeTab === tab.id
                      ? 'border-purple-500 text-white bg-gray-900'
                      : 'border-transparent text-gray-400 hover:text-white hover:bg-gray-900/50'
                  }`}
                >
                  <Icon size={18} />
                  <div className="text-left">
                    <div className="font-medium">{tab.label}</div>
                    <div className="text-xs opacity-70">{tab.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Tech/Latency Tab */}
        {activeTab === 'tech' && (
          <div className="space-y-6">
            {/* Upload Section */}
            {!techAnalysis && (
              <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <Upload size={20} className="text-purple-400" />
                  Upload Call Log for Analysis
                </h2>
                <div className="space-y-4">
                  {/* Show call log status - check both call_log and logs fields */}
                  {(() => {
                    const logsData = callData?.call_log || callData?.logs;
                    const hasLogs = logsData && (Array.isArray(logsData) ? logsData.length > 0 : Object.keys(logsData).length > 0);
                    const logCount = Array.isArray(logsData) ? logsData.length : Object.keys(logsData || {}).length;
                    
                    if (hasLogs) {
                      return (
                        <div className="bg-green-900/20 border border-green-700/50 rounded-lg p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2">
                              <CheckCircle size={20} className="text-green-400" />
                              <div>
                                <p className="text-sm font-medium text-green-300">
                                  Call log available from database ({logCount} {Array.isArray(logsData) ? 'entries' : 'nodes'})
                                </p>
                                <p className="text-xs text-gray-400 mt-1">
                                  Click &quot;Analyze&quot; below to process the call log automatically
                                </p>
                              </div>
                            </div>
                            <button
                              onClick={() => {
                                const blob = new Blob([JSON.stringify(logsData, null, 2)], { type: 'application/json' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `call-log-${callId}.json`;
                                a.click();
                                URL.revokeObjectURL(url);
                              }}
                              className="text-xs text-green-400 hover:text-green-300 flex items-center gap-1"
                            >
                              <Download size={14} />
                              Download
                            </button>
                          </div>
                        </div>
                      );
                    } else {
                      return (
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-2">
                            Call Log File (.log, .txt, .json)
                          </label>
                          <input
                            type="file"
                            accept=".log,.txt,.json"
                            onChange={handleLogUpload}
                            className="block w-full text-sm text-gray-400
                              file:mr-4 file:py-2 file:px-4
                              file:rounded-lg file:border-0
                              file:text-sm file:font-semibold
                              file:bg-purple-600 file:text-white
                              hover:file:bg-purple-700
                              file:cursor-pointer cursor-pointer"
                          />
                          <p className="text-xs text-gray-500 mt-2">
                            Upload the call log file that contains latency metrics and node information
                          </p>
                        </div>
                      );
                    }
                  })()}

                  <button
                    onClick={() => analyzeTechPerformance()}
                    disabled={(() => {
                      const logsData = callData?.call_log || callData?.logs;
                      const hasLogs = logsData && (Array.isArray(logsData) ? logsData.length > 0 : Object.keys(logsData).length > 0);
                      return (!hasLogs && !logFile) || analyzing;
                    })()}
                    className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    <Zap size={18} />
                    {analyzing ? 'Analyzing...' : 'Analyze Tech Performance'}
                  </button>
                </div>
              </div>
            )}

            {/* Analysis Results */}
            {techAnalysis && (
              <div className="space-y-6">
                {/* Overall Summary */}
                <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold">Performance Summary</h2>
                    <button
                      onClick={() => setTechAnalysis(null)}
                      className="text-sm text-gray-400 hover:text-white"
                    >
                      Analyze Another
                    </button>
                  </div>

                  <div className="grid grid-cols-4 gap-4">
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400 mb-1">Overall</div>
                      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm font-medium ${getPerformanceColor(techAnalysis.overall_performance)}`}>
                        {techAnalysis.overall_performance === 'excellent' || techAnalysis.overall_performance === 'good' ? (
                          <CheckCircle size={16} />
                        ) : (
                          <AlertTriangle size={16} />
                        )}
                        {techAnalysis.overall_performance}
                      </div>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400 mb-1">Total Nodes</div>
                      <div className="text-2xl font-bold text-white">{techAnalysis.total_nodes}</div>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400 mb-1">Flagged Nodes</div>
                      <div className="text-2xl font-bold text-red-400">{techAnalysis.flagged_nodes}</div>
                      <div className="text-xs text-gray-500 mt-1">&gt;4s TTFS</div>
                    </div>

                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400 mb-1">Performance</div>
                      <div className="text-2xl font-bold text-green-400">
                        {Math.round((1 - techAnalysis.flagged_nodes / techAnalysis.total_nodes) * 100)}%
                      </div>
                      <div className="text-xs text-gray-500 mt-1">nodes optimal</div>
                    </div>
                  </div>
                </div>

                {/* Recommendations */}
                {techAnalysis.recommendations && techAnalysis.recommendations.length > 0 && (
                  <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <TrendingUp size={20} className="text-blue-400" />
                      Recommendations
                    </h3>
                    <div className="space-y-2">
                      {techAnalysis.recommendations.map((rec, index) => (
                        <div key={index} className="text-sm text-blue-200 flex items-start gap-2">
                          <span className="mt-0.5">•</span>
                          <span>{rec}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Node-by-Node Analysis */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Node-by-Node Breakdown</h3>
                  {techAnalysis.node_analyses.map((node, index) => (
                    <div 
                      key={index}
                      className={`bg-gray-900 rounded-lg border p-6 ${
                        node.ttfs > 4 ? 'border-red-700 bg-red-900/10' : 'border-gray-800'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h4 className="text-white font-medium mb-1">{node.node_name}</h4>
                          <div className="flex items-center gap-3 text-sm">
                            <span className={`font-bold ${getTTFSColor(node.ttfs)}`}>
                              TTFS: {node.ttfs.toFixed(2)}s
                            </span>
                            {node.ttfs > 4 && (
                              <span className="text-red-400 text-xs flex items-center gap-1">
                                <AlertTriangle size={14} />
                                Exceeds 4s threshold
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <div className="text-right">
                          <div className="text-xs text-gray-400">Node {index + 1} of {techAnalysis.total_nodes}</div>
                        </div>
                      </div>

                      {/* Timing Breakdown */}
                      <div className="grid grid-cols-5 gap-3 mb-4">
                        <div className="bg-gray-800/50 rounded p-3">
                          <div className="text-xs text-gray-400 mb-1">LLM</div>
                          <div className="text-white font-medium">{node.llm_time}ms</div>
                        </div>
                        <div className="bg-gray-800/50 rounded p-3">
                          <div className="text-xs text-gray-400 mb-1" title="Time until audio starts playing">TTS First Chunk</div>
                          <div className="text-white font-medium">{node.tts_first_chunk || Math.round(node.tts_time * 0.15)}ms</div>
                        </div>
                        <div className="bg-gray-800/50 rounded p-3">
                          <div className="text-xs text-gray-400 mb-1" title="Total time to generate all audio">TTS Total</div>
                          <div className="text-white font-medium">{node.tts_time}ms</div>
                        </div>
                        <div className="bg-gray-800/50 rounded p-3">
                          <div className="text-xs text-gray-400 mb-1">Transition</div>
                          <div className="text-white font-medium">{node.transition_time}ms</div>
                        </div>
                        <div className="bg-gray-800/50 rounded p-3">
                          <div className="text-xs text-gray-400 mb-1">KB</div>
                          <div className="text-white font-medium">{node.kb_time}ms</div>
                        </div>
                      </div>
                      
                      {/* TTS Explanation */}
                      {node.tts_time > 0 && (
                        <div className="text-xs text-gray-500 mb-4 flex items-center gap-1">
                          <Info size={12} />
                          <span>TTS First Chunk = when audio starts playing | TTS Total = full generation time</span>
                        </div>
                      )}

                      {/* Bottlenecks */}
                      {node.bottlenecks && node.bottlenecks.length > 0 && (
                        <div className="bg-red-900/20 border border-red-700/30 rounded p-3">
                          <div className="text-sm font-medium text-red-300 mb-2">Bottlenecks:</div>
                          <div className="space-y-1">
                            {node.bottlenecks.map((bottleneck, bIndex) => (
                              <div key={bIndex} className="text-sm text-red-200 flex items-start gap-2">
                                <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                                <span>{bottleneck}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Auto-Optimize Button - Show for flagged nodes */}
                      {node.ttfs > 4 && callData?.agent_id && node.node_id && (
                        <div className="mt-4 pt-4 border-t border-gray-700">
                          <button
                            onClick={() => handleOptimizeNode(node)}
                            disabled={optimizingNode === (node.node_id || node.node_name)}
                            className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 disabled:cursor-wait text-white py-2 px-4 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors"
                          >
                            {optimizingNode === (node.node_id || node.node_name) ? (
                              <>
                                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                                Optimizing & Testing...
                              </>
                            ) : (
                              <>
                                <Zap size={16} />
                                Auto-Optimize This Node
                              </>
                            )}
                          </button>
                        </div>
                      )}
                      
                      {/* Optimization Result Display */}
                      {optimizationResult && optimizationResult.node_id === node.node_id && (
                        <div className="mt-4 bg-gray-800 rounded-lg p-4 border border-purple-700/50">
                          <h5 className="text-purple-300 font-medium mb-3 flex items-center gap-2">
                            <TrendingUp size={16} />
                            Optimization Results
                          </h5>
                          
                          {/* Metrics */}
                          <div className="grid grid-cols-3 gap-3 mb-4">
                            <div className="bg-gray-900 p-3 rounded">
                              <div className="text-xs text-gray-400">Baseline</div>
                              <div className="text-white font-bold">{optimizationResult.baseline_latency_ms}ms</div>
                            </div>
                            <div className="bg-gray-900 p-3 rounded">
                              <div className="text-xs text-gray-400">Optimized</div>
                              <div className="text-green-400 font-bold">{optimizationResult.best_latency_ms}ms</div>
                            </div>
                            <div className={`p-3 rounded ${optimizationResult.improvement_percent > 0 ? 'bg-green-900/30' : 'bg-gray-900'}`}>
                              <div className="text-xs text-gray-400">Improvement</div>
                              <div className={`font-bold ${optimizationResult.improvement_percent > 0 ? 'text-green-400' : 'text-gray-400'}`}>
                                {optimizationResult.improvement_percent > 0 ? '+' : ''}{optimizationResult.improvement_percent}%
                              </div>
                            </div>
                          </div>
                          
                          {/* Optimization attempts */}
                          <div className="text-xs text-gray-400 mb-3">
                            Tested {optimizationResult.optimization_attempts?.length || 0} optimization(s)
                          </div>
                          
                          {/* Apply Button */}
                          {optimizationResult.can_apply && optimizationResult.best_optimization && (
                            <button
                              onClick={handleApplyOptimization}
                              disabled={applyingOptimization}
                              className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-white py-2 px-4 rounded text-sm font-medium flex items-center justify-center gap-2"
                            >
                              {applyingOptimization ? (
                                <>
                                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                                  Applying...
                                </>
                              ) : (
                                <>
                                  <Save size={16} />
                                  Apply Changes to Node ({optimizationResult.best_optimization.prompt_reduction_chars + optimizationResult.best_optimization.content_reduction_chars} chars removed)
                                </>
                              )}
                            </button>
                          )}
                          
                          {/* Suggestions when no improvement */}
                          {optimizationResult.suggestions && optimizationResult.suggestions.length > 0 && (
                            <div className="mt-3 space-y-2">
                              <div className="text-xs text-gray-400 font-medium">Suggestions:</div>
                              {optimizationResult.suggestions.map((suggestion, sIdx) => (
                                <div 
                                  key={sIdx} 
                                  className={`text-xs p-2 rounded flex items-start gap-2 ${
                                    suggestion.type === 'critical' ? 'bg-red-900/30 text-red-200' :
                                    suggestion.type === 'warning' ? 'bg-yellow-900/30 text-yellow-200' :
                                    suggestion.type === 'success' ? 'bg-green-900/30 text-green-200' :
                                    'bg-blue-900/30 text-blue-200'
                                  }`}
                                >
                                  <div className="flex-1">
                                    <div className="font-medium">{suggestion.title}</div>
                                    <div className="mt-0.5 opacity-80">{suggestion.description}</div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                          
                          {/* Close button */}
                          <button
                            onClick={() => setOptimizationResult(null)}
                            className="mt-3 text-xs text-gray-400 hover:text-gray-300"
                          >
                            Dismiss
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Export Button */}
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => {
                      const dataStr = JSON.stringify(techAnalysis, null, 2);
                      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
                      const exportFileDefaultName = `tech-qc-${callId}-${Date.now()}.json`;
                      const linkElement = document.createElement('a');
                      linkElement.setAttribute('href', dataUri);
                      linkElement.setAttribute('download', exportFileDefaultName);
                      linkElement.click();
                      toast({
                        title: "Exported",
                        description: "Analysis exported as JSON"
                      });
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
                  >
                    <Download size={16} />
                    Export JSON
                  </button>
                  <button
                    onClick={() => {
                      // Generate markdown report
                      let markdown = `# Tech QC Report - ${callData?.phone_number || 'Call'}\n\n`;
                      markdown += `**Date:** ${new Date().toLocaleDateString()}\n`;
                      markdown += `**Overall Performance:** ${techAnalysis.overall_performance}\n`;
                      markdown += `**Total Nodes:** ${techAnalysis.total_nodes}\n`;
                      markdown += `**Flagged Nodes:** ${techAnalysis.flagged_nodes}\n\n`;
                      markdown += `## Recommendations\n\n`;
                      techAnalysis.recommendations.forEach(rec => {
                        markdown += `- ${rec}\n`;
                      });
                      markdown += `\n## Node Analysis\n\n`;
                      techAnalysis.node_analyses.forEach((node, idx) => {
                        markdown += `### ${idx + 1}. ${node.node_name}\n\n`;
                        markdown += `- **TTFS (Dead Air):** ${node.ttfs.toFixed(2)}s\n`;
                        markdown += `- **LLM Time:** ${node.llm_time}ms\n`;
                        markdown += `- **TTS First Chunk:** ${node.tts_first_chunk || Math.round(node.tts_time * 0.15)}ms (when audio starts)\n`;
                        markdown += `- **TTS Total:** ${node.tts_time}ms (full generation)\n`;
                        markdown += `- **Transition Time:** ${node.transition_time}ms\n`;
                        markdown += `- **KB Time:** ${node.kb_time}ms\n\n`;
                        if (node.bottlenecks && node.bottlenecks.length > 0) {
                          markdown += `**Bottlenecks:**\n`;
                          node.bottlenecks.forEach(b => {
                            markdown += `- ${b}\n`;
                          });
                          markdown += `\n`;
                        }
                      });
                      
                      const blob = new Blob([markdown], { type: 'text/markdown' });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = `tech-qc-report-${callId}-${Date.now()}.md`;
                      link.click();
                      toast({
                        title: "Exported",
                        description: "Report exported as Markdown"
                      });
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                  >
                    <Download size={16} />
                    Export Report (MD)
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Script Quality Tab */}
        {activeTab === 'script' && (
          <ScriptQualityTab 
            callId={callId}
            callData={callData}
            qcEnhancedAPI={qcEnhancedAPI}
            toast={toast}
            qcSettings={qcSettings}
            savedResults={scriptAnalysis}
            onAnalysisComplete={(type, results) => {
              setScriptAnalysis(results);
            }}
          />
        )}

        {/* Tonality Tab */}
        {activeTab === 'tonality' && (
          <TonalityTab 
            callId={callId}
            callData={callData}
            qcEnhancedAPI={qcEnhancedAPI}
            toast={toast}
            qcSettings={qcSettings}
            savedTonalityResults={tonalityAnalysis}
            savedAudioResults={audioTonalityAnalysis}
            onAnalysisComplete={handleTonalityAnalysisComplete}
          />
        )}

        {/* Direct Test Tab - QC Tester */}
        {activeTab === 'direct' && (
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <TestTube size={20} className="text-purple-400" />
              QC Tester - Direct Node Testing
            </h2>
            
            <p className="text-gray-400 mb-6">
              Test prompt changes directly without affecting your live agent. 
              Make edits to node prompts and see immediate results.
            </p>
            
            {/* Agent Selection - Show dropdown if no agent or allow changing */}
            <div className="bg-gray-800/50 rounded-lg p-4 mb-4">
              <h3 className="text-sm font-medium text-gray-300 mb-3">Select Agent to Test</h3>
              <Select 
                value={callData?.agent_id || selectedTestAgentId || "none"} 
                onValueChange={setSelectedTestAgentId}
              >
                <SelectTrigger className="bg-gray-800 border-gray-700">
                  <SelectValue placeholder="Select an agent to test..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Select an agent...</SelectItem>
                  {agents.map(agent => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name} ({agent.call_flow?.length || 0} nodes)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {agents.length === 0 && (
                <p className="text-xs text-gray-500 mt-2">
                  No call flow agents found. Create an agent with a call flow to use the tester.
                </p>
              )}
            </div>
            
            {(callData?.agent_id || selectedTestAgentId) && selectedTestAgentId !== "none" ? (
              <div className="space-y-4">
                {/* Quick Access to Agent Tester */}
                <div className="bg-gray-800/50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-300 mb-3">Agent Tester</h3>
                  <p className="text-xs text-gray-500 mb-4">
                    Open the full Agent Tester to test individual nodes with custom inputs. 
                    You can edit the node prompt temporarily and see how the AI responds.
                  </p>
                  <button
                    onClick={() => window.location.href = `/agents/${callData?.agent_id || selectedTestAgentId}/test`}
                    className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    <TestTube size={18} />
                    Open Agent Tester
                  </button>
                </div>
                
                {/* Quick Node Links - only show if we have transcript data */}
                {callData?.transcript && callData.transcript.length > 0 && (
                  <div className="bg-gray-800/50 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-gray-300 mb-3">Quick Test Nodes from This Call</h3>
                    <p className="text-xs text-gray-500 mb-4">
                      Jump directly to specific nodes that were used in this call:
                    </p>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {/* Extract unique nodes from transcript */}
                      {(() => {
                        const seenNodes = new Set();
                        const uniqueNodes = [];
                        callData.transcript.forEach((msg, idx) => {
                          if (msg._node_id && !seenNodes.has(msg._node_id)) {
                            seenNodes.add(msg._node_id);
                            uniqueNodes.push({
                              id: msg._node_id,
                              label: msg._node_label || null,
                              index: idx + 1
                            });
                          }
                        });
                        return uniqueNodes.length > 0 ? (
                          uniqueNodes.map((node, idx) => (
                            <button
                              key={idx}
                              onClick={() => window.location.href = `/agents/${callData.agent_id}/test?nodeId=${node.id}`}
                              className="w-full text-left px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors flex items-center justify-between"
                            >
                              <span>Turn {node.index} - {node.label || node.id.slice(0, 8) + '...'}</span>
                              <TestTube size={14} className="text-purple-400" />
                            </button>
                          ))
                        ) : (
                          <p className="text-gray-500 text-sm">No node IDs found in transcript</p>
                        );
                      })()}
                    </div>
                  </div>
                )}
                
                {/* Flow Builder Link */}
                <div className="bg-gray-800/50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-300 mb-3">Edit Agent Flow</h3>
                  <p className="text-xs text-gray-500 mb-4">
                    Open the flow builder to make permanent changes to your agent&apos;s conversation flow.
                  </p>
                  <button
                    onClick={() => window.open(`/agents/${callData?.agent_id || selectedTestAgentId}/flow`, '_blank')}
                    className="w-full bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    <Settings size={18} />
                    Open Flow Builder ↗
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <TestTube size={48} className="mx-auto mb-4 text-gray-600" />
                <h3 className="text-lg font-medium mb-2">Select an Agent</h3>
                <p className="text-sm">
                  Choose an agent from the dropdown above to start testing.
                </p>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Unified QC Panel - Uses assigned QC agents from voice agent */}
      <UnifiedQCPanel
        isOpen={showQCSettings}
        onClose={() => setShowQCSettings(false)}
        callData={callData}
        voiceAgentId={callData?.agent_id}
        voiceAgentName={callData?.agent_name}
        onAnalyze={async (type, qcAgentId) => {
          // Run analysis using the assigned QC agent
          setAnalyzingType(type);
          try {
            if (type === 'tech') {
              await analyzeTech(qcAgentId);
            } else if (type === 'script') {
              await analyzeScript(qcAgentId);
            } else if (type === 'tonality') {
              await analyzeTonality(qcAgentId);
            }
          } finally {
            setAnalyzingType(null);
          }
        }}
        techResults={techAnalysis}
        scriptResults={scriptAnalysis}
        tonalityResults={tonalityAnalysis}
        analyzingType={analyzingType}
      />

      {/* Add to Campaign Modal */}
      {showCampaignModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-lg border border-gray-700 max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">Add Call to Campaign</h2>
            
            {campaigns.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-400 mb-4">No campaigns available</p>
                <button
                  onClick={() => navigate('/qc/campaigns')}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors"
                >
                  Create Campaign
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Select Campaign
                  </label>
                  <select
                    value={selectedCampaign}
                    onChange={(e) => setSelectedCampaign(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded px-3 py-2"
                  >
                    <option value="">Select a campaign...</option>
                    {campaigns.map((campaign) => (
                      <option key={campaign.id} value={campaign.id}>
                        {campaign.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={addToCampaign}
                    className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-2 rounded transition-colors"
                  >
                    Add to Campaign
                  </button>
                  <button
                    onClick={() => setShowCampaignModal(false)}
                    className="px-6 bg-gray-800 hover:bg-gray-700 text-white py-2 rounded transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default QCDashboard;
