import React, { useState, useEffect } from 'react';
import { Play, FileText, Settings, TrendingUp, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import axios from 'axios';
import { useToast } from '../hooks/use-toast';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const QCAgentTester = () => {
  const { toast } = useToast();
  
  // Test configuration
  const [transcript, setTranscript] = useState('');
  const [duration, setDuration] = useState(180);
  const [leadId, setLeadId] = useState('');
  const [agentId, setAgentId] = useState('');
  
  // Custom tracking parameters
  const [trackKeywords, setTrackKeywords] = useState('');
  const [expectedCommitment, setExpectedCommitment] = useState('medium');
  const [expectedStages, setExpectedStages] = useState(['hook', 'qualification', 'closing']);
  
  // Results
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState('');
  
  const presets = [
    { id: 'high_quality', name: 'High Quality Call', description: 'Perfect execution with strong commitment' },
    { id: 'poor_quality', name: 'Poor Quality Call', description: 'Rushed, no value, weak commitment' },
    { id: 'medium_quality', name: 'Medium Quality Call', description: 'Some objections, moderate quality' },
    { id: 'objection_heavy', name: 'Objection Heavy', description: 'Multiple objections handled well' }
  ];
  
  const allStages = [
    { id: 'hook', label: 'Hook (Opening)' },
    { id: 'qualification', label: 'Qualification (BANT)' },
    { id: 'value_presentation', label: 'Value Presentation' },
    { id: 'objection_handling', label: 'Objection Handling' },
    { id: 'closing', label: 'Closing (Ask)' },
    { id: 'confirmation', label: 'Confirmation' }
  ];
  
  const handleStageToggle = (stageId) => {
    if (expectedStages.includes(stageId)) {
      setExpectedStages(expectedStages.filter(s => s !== stageId));
    } else {
      setExpectedStages([...expectedStages, stageId]);
    }
  };
  
  const loadPreset = async (presetId) => {
    try {
      setLoading(true);
      setSelectedPreset(presetId);
      
      const response = await axios.post(
        `${BACKEND_URL}/api/qc/test/preset/${presetId}`,
        {},
        { withCredentials: true }
      );
      
      setResults(response.data);
      
      toast({
        title: 'Preset Loaded',
        description: `Running QC analysis on ${presetId} scenario`,
      });
    } catch (error) {
      console.error('Error loading preset:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to load preset',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };
  
  const runTest = async () => {
    if (!transcript || transcript.length < 10) {
      toast({
        title: 'Invalid Transcript',
        description: 'Please enter a transcript of at least 10 characters',
        variant: 'destructive'
      });
      return;
    }
    
    try {
      setLoading(true);
      setResults(null);
      
      const requestData = {
        transcript: transcript,
        lead_id: leadId || undefined,
        agent_id: agentId || undefined,
        custom_parameters: {
          track_keywords: trackKeywords ? trackKeywords.split(',').map(k => k.trim()) : [],
          expected_commitment_level: expectedCommitment,
          expected_funnel_stages: expectedStages
        },
        metadata: {
          duration_seconds: parseInt(duration) || 180,
          call_hour: new Date().getHours(),
          day_of_week: new Date().getDay()
        }
      };
      
      const response = await axios.post(
        `${BACKEND_URL}/api/qc/test`,
        requestData,
        { withCredentials: true }
      );
      
      setResults(response.data);
      
      toast({
        title: 'QC Analysis Complete',
        description: 'All 3 agents have analyzed the transcript',
      });
    } catch (error) {
      console.error('Error running QC test:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to run QC analysis',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };
  
  const getScoreColor = (score) => {
    if (score >= 75) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };
  
  const getScoreBg = (score) => {
    if (score >= 75) return 'bg-green-500';
    if (score >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };
  
  const getRiskColor = (risk) => {
    if (risk === 'low') return 'text-green-400';
    if (risk === 'medium') return 'text-yellow-400';
    return 'text-red-400';
  };
  
  return (
    <div className="p-8 bg-gray-900 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">QC Agent Tester</h1>
        <p className="text-gray-400">Test the 3 QC agents with custom transcripts and parameters</p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Input */}
        <div className="space-y-6">
          {/* Preset Scenarios */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="text-blue-400" size={20} />
              <h2 className="text-xl font-semibold text-white">Quick Test Presets</h2>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {presets.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => loadPreset(preset.id)}
                  disabled={loading}
                  className={`p-4 rounded-lg border text-left transition-all ${
                    selectedPreset === preset.id
                      ? 'bg-blue-600 border-blue-500'
                      : 'bg-gray-700 border-gray-600 hover:border-blue-500'
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <p className="text-white font-medium">{preset.name}</p>
                  <p className="text-sm text-gray-400 mt-1">{preset.description}</p>
                </button>
              ))}
            </div>
          </div>
          
          {/* Custom Transcript */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="text-purple-400" size={20} />
              <h2 className="text-xl font-semibold text-white">Custom Test</h2>
            </div>
            
            <div className="space-y-4">
              {/* Transcript Input */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Call Transcript
                </label>
                <textarea
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder={`Agent: Hi, how can I help you today?\nUser: I'm interested in your services.\nAgent: Great! Tell me more about what you're looking for...`}
                  className="w-full h-48 px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none font-mono text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Format: "Agent: message" and "User: message" on separate lines
                </p>
              </div>
              
              {/* Duration */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Call Duration (seconds)
                </label>
                <input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              
              {/* Lead ID (optional) */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Lead ID (optional)
                </label>
                <input
                  type="text"
                  value={leadId}
                  onChange={(e) => setLeadId(e.target.value)}
                  placeholder="lead_abc123"
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              
              {/* Agent ID (optional) */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Agent ID (optional)
                </label>
                <input
                  type="text"
                  value={agentId}
                  onChange={(e) => setAgentId(e.target.value)}
                  placeholder="agent_xyz789"
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              
              {/* Track Keywords */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Track Keywords (comma-separated)
                </label>
                <input
                  type="text"
                  value={trackKeywords}
                  onChange={(e) => setTrackKeywords(e.target.value)}
                  placeholder="price, cost, budget, deadline"
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              
              {/* Expected Commitment Level */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Expected Commitment Level
                </label>
                <select
                  value={expectedCommitment}
                  onChange={(e) => setExpectedCommitment(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                >
                  <option value="high">High (75-100)</option>
                  <option value="medium">Medium (50-74)</option>
                  <option value="low">Low (0-49)</option>
                </select>
              </div>
              
              {/* Expected Funnel Stages */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Expected Funnel Stages
                </label>
                <div className="space-y-2">
                  {allStages.map((stage) => (
                    <label key={stage.id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={expectedStages.includes(stage.id)}
                        onChange={() => handleStageToggle(stage.id)}
                        className="w-4 h-4 bg-gray-900 border-gray-700 rounded focus:ring-blue-500"
                      />
                      <span className="text-gray-300 text-sm">{stage.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              
              {/* Run Test Button */}
              <button
                onClick={runTest}
                disabled={loading || !transcript}
                className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Play size={20} />
                    <span>Run QC Analysis</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
        
        {/* Right Column: Results */}
        <div className="space-y-6">
          {results ? (
            <>
              {/* Overall Scores */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="text-green-400" size={20} />
                  <h2 className="text-xl font-semibold text-white">Aggregated Scores</h2>
                </div>
                
                <div className="space-y-4">
                  {/* Commitment Score */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-300">Commitment Score</span>
                      <span className={`text-2xl font-bold ${getScoreColor(results.analysis.aggregated_scores?.commitment_score)}`}>
                        {results.analysis.aggregated_scores?.commitment_score || 'N/A'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${getScoreBg(results.analysis.aggregated_scores?.commitment_score)}`}
                        style={{ width: `${results.analysis.aggregated_scores?.commitment_score || 0}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  {/* Conversion Score */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-300">Conversion Score</span>
                      <span className={`text-2xl font-bold ${getScoreColor(results.analysis.aggregated_scores?.conversion_score)}`}>
                        {results.analysis.aggregated_scores?.conversion_score || 'N/A'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${getScoreBg(results.analysis.aggregated_scores?.conversion_score)}`}
                        style={{ width: `${results.analysis.aggregated_scores?.conversion_score || 0}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  {/* Excellence Score */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-300">Excellence Score</span>
                      <span className={`text-2xl font-bold ${getScoreColor(results.analysis.aggregated_scores?.excellence_score)}`}>
                        {results.analysis.aggregated_scores?.excellence_score || 'N/A'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${getScoreBg(results.analysis.aggregated_scores?.excellence_score)}`}
                        style={{ width: `${results.analysis.aggregated_scores?.excellence_score || 0}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  {/* Show-Up Probability */}
                  <div className="pt-4 border-t border-gray-700">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-300">Show-Up Probability</span>
                      <span className={`text-2xl font-bold ${getScoreColor(results.analysis.aggregated_scores?.show_up_probability)}`}>
                        {results.analysis.aggregated_scores?.show_up_probability || 'N/A'}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-gray-400 text-sm">Risk Level</span>
                      <span className={`text-sm font-semibold uppercase ${getRiskColor(results.analysis.aggregated_scores?.risk_level)}`}>
                        {results.analysis.aggregated_scores?.risk_level || 'N/A'}
                      </span>
                    </div>
                  </div>
                  
                  {/* Overall Quality */}
                  <div className="pt-4 border-t border-gray-700">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-300 font-semibold">Overall Quality Score</span>
                      <span className={`text-3xl font-bold ${getScoreColor(results.analysis.aggregated_scores?.overall_quality_score)}`}>
                        {results.analysis.aggregated_scores?.overall_quality_score || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Recommendations */}
              {results.analysis.recommendations && results.analysis.recommendations.length > 0 && (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <AlertCircle className="text-yellow-400" size={20} />
                    <h2 className="text-xl font-semibold text-white">Recommendations</h2>
                  </div>
                  <ul className="space-y-2">
                    {results.analysis.recommendations.slice(0, 10).map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-gray-300">
                        <span className="text-yellow-400 mt-1">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Detailed Analysis */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <h2 className="text-xl font-semibold text-white mb-4">Detailed Analysis</h2>
                
                {/* Commitment Analysis */}
                {results.analysis.commitment_analysis && (
                  <div className="mb-4">
                    <h3 className="text-lg font-medium text-blue-400 mb-2">Commitment Detector</h3>
                    <div className="bg-gray-900 rounded-lg p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Linguistic Score:</span>
                        <span className="text-white font-medium">
                          {results.analysis.commitment_analysis.commitment_analysis?.linguistic_score || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Progression:</span>
                        <span className="text-white font-medium">
                          {results.analysis.commitment_analysis.commitment_analysis?.behavioral_progression?.highest_stage_reached || 'N/A'}
                        </span>
                      </div>
                      {results.analysis.commitment_analysis.key_factors && (
                        <div className="pt-2 border-t border-gray-700">
                          <p className="text-gray-400 text-sm mb-1">Key Factors:</p>
                          <ul className="space-y-1">
                            {results.analysis.commitment_analysis.key_factors.map((factor, idx) => (
                              <li key={idx} className="text-gray-300 text-sm flex items-start gap-2">
                                <CheckCircle size={14} className="text-green-400 mt-0.5" />
                                <span>{factor}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Conversion Analysis */}
                {results.analysis.conversion_analysis && (
                  <div className="mb-4">
                    <h3 className="text-lg font-medium text-purple-400 mb-2">Conversion Pathfinder</h3>
                    <div className="bg-gray-900 rounded-lg p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Funnel Completion:</span>
                        <span className="text-white font-medium">
                          {results.analysis.conversion_analysis.funnel_analysis?.funnel_completion || 'N/A'}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Diagnosis:</span>
                        <span className="text-white font-medium text-sm">
                          {results.analysis.conversion_analysis.funnel_analysis?.diagnosis || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">BANT Score:</span>
                        <span className="text-white font-medium">
                          {results.analysis.conversion_analysis.framework_scores?.overall_score || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Excellence Analysis */}
                {results.analysis.excellence_analysis && (
                  <div>
                    <h3 className="text-lg font-medium text-green-400 mb-2">Excellence Replicator</h3>
                    <div className="bg-gray-900 rounded-lg p-4 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Excellence Score:</span>
                        <span className="text-white font-medium">
                          {results.analysis.excellence_analysis.excellence_score || 'N/A'}
                        </span>
                      </div>
                      {results.analysis.excellence_analysis.comparison_to_ideal && (
                        <>
                          <div className="pt-2 border-t border-gray-700">
                            <p className="text-gray-400 text-sm mb-1">Strengths:</p>
                            <ul className="space-y-1">
                              {results.analysis.excellence_analysis.comparison_to_ideal.strengths?.map((strength, idx) => (
                                <li key={idx} className="text-green-300 text-sm flex items-center gap-2">
                                  <CheckCircle size={14} />
                                  <span>{strength}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div className="pt-2 border-t border-gray-700">
                            <p className="text-gray-400 text-sm mb-1">Improvements:</p>
                            <ul className="space-y-1">
                              {results.analysis.excellence_analysis.comparison_to_ideal.improvements?.map((improvement, idx) => (
                                <li key={idx} className="text-yellow-300 text-sm flex items-center gap-2">
                                  <XCircle size={14} />
                                  <span>{improvement}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
              <TrendingUp className="mx-auto mb-4 text-gray-600" size={48} />
              <h3 className="text-xl font-semibold text-gray-400 mb-2">No Results Yet</h3>
              <p className="text-gray-500">Load a preset or enter a custom transcript to test the QC agents</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QCAgentTester;
