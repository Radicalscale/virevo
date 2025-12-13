import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, 
  ThumbsUp, 
  AlertTriangle, 
  Lightbulb,
  Target,
  FileText,
  Save,
  TestTube,
  Sparkles,
  RefreshCw,
  Settings
} from 'lucide-react';

const ScriptQualityTab = ({ callId, callData, qcEnhancedAPI, toast, qcSettings, savedResults, onAnalysisComplete }) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [scriptAnalysis, setScriptAnalysis] = useState(savedResults || null);
  const [forceReanalyze, setForceReanalyze] = useState(false);
  const [customRules, setCustomRules] = useState({
    analysis_rules: {
      focus_on_brevity: true,
      check_goal_alignment: true,
      evaluate_naturalness: true
    }
  });

  // Load saved results when props change (but not if we're forcing a reanalysis)
  useEffect(() => {
    if (savedResults && !scriptAnalysis && !forceReanalyze) {
      setScriptAnalysis(savedResults);
    }
  }, [savedResults, forceReanalyze]);

  const analyzeScript = async () => {
    try {
      setAnalyzing(true);
      const response = await qcEnhancedAPI.analyzeScript({
        call_id: callId,
        custom_rules: customRules,
        custom_guidelines: qcSettings?.script_guidelines,
        llm_provider: qcSettings?.llm_provider,
        model: qcSettings?.model,
        // Include transcript data from frontend in case DB doesn't have it
        transcript: callData?.transcript || [],
        call_log: callData?.call_log || callData?.logs || [],
        agent_id: callData?.agent_id
      });
      
      setScriptAnalysis(response.data);
      
      // Notify parent to save results
      if (onAnalysisComplete) {
        onAnalysisComplete('script', response.data);
      }
      
      toast({
        title: "Analysis Complete",
        description: `Analyzed ${response.data.node_analyses?.length || 0} conversation turns`
      });
      
      // Check if response has a message about no transcript
      if (response.data.message) {
        toast({
          title: "Note",
          description: response.data.message,
          variant: "default"
        });
      }
    } catch (error) {
      console.error('Error analyzing script:', error);
      toast({
        title: "Analysis Failed",
        description: error.response?.data?.detail || "Failed to analyze script",
        variant: "destructive"
      });
    } finally {
      setAnalyzing(false);
    }
  };

  // Re-run analysis (clear results and analyze again)
  const reanalyze = async () => {
    setForceReanalyze(true);  // Prevent useEffect from restoring saved results
    setScriptAnalysis(null);
    // Give UI time to update, then run analysis
    setTimeout(async () => {
      await analyzeScript();
      setForceReanalyze(false);  // Allow saved results again after analysis completes
    }, 100);
  };

  const getQualityColor = (quality) => {
    const colors = {
      excellent: 'text-green-400 bg-green-900/30 border-green-700',
      good: 'text-blue-400 bg-blue-900/30 border-blue-700',
      needs_improvement: 'text-yellow-400 bg-yellow-900/30 border-yellow-700',
      poor: 'text-red-400 bg-red-900/30 border-red-700'
    };
    return colors[quality] || colors.good;
  };

  const getEfficiencyColor = (efficiency) => {
    const colors = {
      excellent: 'text-green-400',
      good: 'text-blue-400',
      poor: 'text-red-400'
    };
    return colors[efficiency] || colors.good;
  };

  if (!scriptAnalysis) {
    return (
      <div className="space-y-6">
        {/* Analysis Configuration */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <MessageSquare size={20} className="text-purple-400" />
            Script Quality Analysis
          </h2>
          
          <div className="space-y-4">
            <p className="text-gray-400 text-sm">
              Analyze conversation quality with AI to identify areas for improvement.
              The analysis will evaluate snappiness, relevance, goal efficiency, and more.
            </p>

            {/* Custom Rules */}
            <div className="bg-gray-800/50 rounded-lg p-4 space-y-3">
              <h3 className="text-sm font-medium text-gray-300">Analysis Focus</h3>
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={customRules.analysis_rules.focus_on_brevity}
                    onChange={(e) => setCustomRules({
                      ...customRules,
                      analysis_rules: {
                        ...customRules.analysis_rules,
                        focus_on_brevity: e.target.checked
                      }
                    })}
                    className="w-4 h-4 text-purple-600 bg-gray-900 border-gray-700 rounded focus:ring-purple-500"
                  />
                  Focus on brevity and snappiness
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={customRules.analysis_rules.check_goal_alignment}
                    onChange={(e) => setCustomRules({
                      ...customRules,
                      analysis_rules: {
                        ...customRules.analysis_rules,
                        check_goal_alignment: e.target.checked
                      }
                    })}
                    className="w-4 h-4 text-purple-600 bg-gray-900 border-gray-700 rounded focus:ring-purple-500"
                  />
                  Check alignment with conversation goals
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={customRules.analysis_rules.evaluate_naturalness}
                    onChange={(e) => setCustomRules({
                      ...customRules,
                      analysis_rules: {
                        ...customRules.analysis_rules,
                        evaluate_naturalness: e.target.checked
                      }
                    })}
                    className="w-4 h-4 text-purple-600 bg-gray-900 border-gray-700 rounded focus:ring-purple-500"
                  />
                  Evaluate conversational naturalness
                </label>
              </div>
            </div>

            <button
              onClick={analyzeScript}
              disabled={analyzing}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Sparkles size={18} />
              {analyzing ? 'Analyzing Conversation...' : 'Analyze Script Quality'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Analysis results view
  const { node_analyses, bulk_suggestions } = scriptAnalysis;

  return (
    <div className="space-y-6">
      {/* Summary Section */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Conversation Analysis</h2>
          <button
            onClick={reanalyze}
            disabled={analyzing}
            className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 disabled:text-gray-500"
          >
            <RefreshCw size={14} className={analyzing ? 'animate-spin' : ''} />
            {analyzing ? 'Analyzing...' : 'Analyze Again'}
          </button>
        </div>

        {bulk_suggestions?.summary && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Total Turns</div>
              <div className="text-2xl font-bold text-white">{bulk_suggestions.summary.total_turns}</div>
            </div>
            <div className="bg-green-900/20 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Good Quality</div>
              <div className="text-2xl font-bold text-green-400">{bulk_suggestions.summary.good_quality}</div>
            </div>
            <div className="bg-yellow-900/20 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Needs Work</div>
              <div className="text-2xl font-bold text-yellow-400">{bulk_suggestions.summary.needs_improvement}</div>
            </div>
            <div className="bg-red-900/20 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Poor Quality</div>
              <div className="text-2xl font-bold text-red-400">{bulk_suggestions.summary.poor_quality}</div>
            </div>
          </div>
        )}

        {/* Bulk Suggestions */}
        {bulk_suggestions && (bulk_suggestions.prompt_improvements?.length > 0 || bulk_suggestions.kb_additions?.length > 0) && (
          <div className="bg-purple-900/20 border border-purple-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <Lightbulb size={18} className="text-purple-400" />
              Key Recommendations
            </h3>
            <div className="space-y-2 text-sm">
              {bulk_suggestions.prompt_improvements.slice(0, 3).map((improvement, idx) => (
                <div key={idx} className="text-purple-200">
                  • Turn {improvement.turn}: {improvement.suggestion}
                </div>
              ))}
              {bulk_suggestions.kb_additions.length > 0 && (
                <div className="text-purple-200 mt-2 pt-2 border-t border-purple-700/30">
                  💡 Consider adding {bulk_suggestions.kb_additions.length} knowledge base enhancements
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Turn-by-Turn Analysis */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Turn-by-Turn Analysis</h3>
        
        {/* Show error if present */}
        {scriptAnalysis?.error && (
          <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-6 text-center">
            <AlertTriangle size={32} className="mx-auto mb-3 text-red-400" />
            <p className="text-red-200 font-medium">Analysis Error</p>
            <p className="text-red-300/70 text-sm mt-2">{scriptAnalysis.error}</p>
            <button
              onClick={reanalyze}
              disabled={analyzing}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm"
            >
              {analyzing ? 'Analyzing...' : 'Try Manual Analysis'}
            </button>
          </div>
        )}
        
        {/* Show message if no analysis data and no error */}
        {(!node_analyses || node_analyses.length === 0) && !scriptAnalysis?.error && (
          <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-6 text-center">
            <AlertTriangle size={32} className="mx-auto mb-3 text-yellow-400" />
            <p className="text-yellow-200 font-medium">No Analysis Data Available</p>
            <p className="text-yellow-300/70 text-sm mt-2">
              The analysis ran but produced no turn-by-turn results. This could mean:
            </p>
            <ul className="text-yellow-300/70 text-sm mt-2 text-left max-w-md mx-auto list-disc list-inside">
              <li>The call had no transcript data</li>
              <li>The LLM analysis failed or returned empty</li>
              <li>The QC agent configuration needs adjustment</li>
            </ul>
            <button
              onClick={reanalyze}
              disabled={analyzing}
              className="mt-4 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-sm"
            >
              {analyzing ? 'Analyzing...' : 'Try Manual Analysis'}
            </button>
            
            {/* Debug info */}
            <details className="mt-4 text-left text-xs text-gray-500">
              <summary className="cursor-pointer">Debug Info</summary>
              <pre className="mt-2 p-2 bg-gray-900 rounded overflow-auto max-h-40">
                {JSON.stringify(scriptAnalysis, null, 2)}
              </pre>
            </details>
          </div>
        )}
        
        {node_analyses && node_analyses.map((analysis, index) => {
          // Check if this is the alternate format (from auto QC)
          const isAlternateFormat = analysis.turn && !analysis.turn_number && !analysis.quality;
          
          if (isAlternateFormat) {
            // Render alternate format (from run_full_qc_analysis)
            return (
              <div
                key={index}
                className="bg-gray-900 rounded-lg border border-gray-800 p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <h4 className="text-white font-medium">
                    {analysis.turn || `Turn ${index + 1}`}
                  </h4>
                </div>
                
                <div className="space-y-4">
                  {/* Simple analysis format (just turn + analysis string) */}
                  {analysis.analysis && typeof analysis.analysis === 'string' && (
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 mb-1">Analysis:</div>
                      <div className="text-sm text-white">{analysis.analysis}</div>
                    </div>
                  )}
                  
                  {/* Detailed format with separate fields */}
                  {analysis.response_relevance_helpfulness && (
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 mb-1">Response Relevance & Helpfulness:</div>
                      <div className="text-sm text-white">{analysis.response_relevance_helpfulness}</div>
                    </div>
                  )}
                  
                  {analysis.flow_naturalness && (
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 mb-1">Flow & Naturalness:</div>
                      <div className="text-sm text-white">{analysis.flow_naturalness}</div>
                    </div>
                  )}
                  
                  {analysis.goal_achievement && (
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-xs text-gray-400 mb-1">Goal Achievement:</div>
                      <div className="text-sm text-white">{analysis.goal_achievement}</div>
                    </div>
                  )}
                  
                  {analysis.improvement && (
                    <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-3">
                      <div className="text-xs text-yellow-400 mb-1 flex items-center gap-1">
                        <AlertTriangle size={12} />
                        Improvement Suggestion:
                      </div>
                      <div className="text-sm text-yellow-200">{analysis.improvement}</div>
                    </div>
                  )}
                </div>
              </div>
            );
          }
          
          // Original format rendering
          return (
          <div
            key={index}
            className={`bg-gray-900 rounded-lg border p-6 ${
              analysis.quality === 'poor' || analysis.quality === 'needs_improvement'
                ? 'border-yellow-700 bg-yellow-900/10'
                : 'border-gray-800'
            }`}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h4 className="text-white font-medium">
                    {analysis.node_name && analysis.node_name !== 'None' && !analysis.node_name.startsWith('Turn ')
                      ? analysis.node_name 
                      : `Turn ${analysis.turn_number}`}
                    {analysis.node_id && analysis.node_id !== 'None' && analysis.node_id !== '' && (
                      <span className="text-xs text-gray-500 ml-2">({analysis.node_id.slice(0, 8)}...)</span>
                    )}
                  </h4>
                  <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full border text-xs font-medium ${getQualityColor(analysis.quality)}`}>
                    {analysis.quality === 'excellent' || analysis.quality === 'good' ? (
                      <ThumbsUp size={12} />
                    ) : (
                      <AlertTriangle size={12} />
                    )}
                    {analysis.quality}
                  </span>
                  <span className={`text-sm font-medium ${getEfficiencyColor(analysis.goal_efficiency)}`}>
                    <Target size={14} className="inline mr-1" />
                    {analysis.goal_efficiency} goal efficiency
                  </span>
                  {analysis.brevity_score && (
                    <span className={`text-sm font-medium ${getEfficiencyColor(analysis.brevity_score)}`}>
                      📏 {analysis.brevity_score} brevity
                    </span>
                  )}
                </div>
                {analysis.node_goal && (
                  <div className="text-xs text-gray-400 mt-1">
                    <span className="text-purple-400">Node Goal:</span> {analysis.node_goal}
                  </div>
                )}
              </div>
            </div>

            {/* Transcript */}
            <div className="bg-gray-800/50 rounded-lg p-4 mb-4">
              <div className="text-sm font-medium text-gray-400 mb-2">📜 ACTUAL TRANSCRIPT</div>
              <div className="space-y-3">
                <div>
                  <div className="text-xs text-gray-500 mb-1">User:</div>
                  <div className="text-white">{analysis.user_message}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">AI:</div>
                  <div className="text-white">{analysis.ai_response}</div>
                </div>
              </div>
            </div>

            {/* Positives */}
            {analysis.positives && analysis.positives.length > 0 && (
              <div className="mb-4">
                <div className="text-sm font-medium text-green-400 mb-2 flex items-center gap-2">
                  <ThumbsUp size={14} />
                  What Worked Well
                </div>
                <div className="space-y-1">
                  {analysis.positives.map((positive, idx) => (
                    <div key={idx} className="text-sm text-green-200 flex items-start gap-2">
                      <span className="mt-0.5">✓</span>
                      <span>{positive}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Issues */}
            {analysis.issues && analysis.issues.length > 0 && (
              <div className="mb-4">
                <div className="text-sm font-medium text-yellow-400 mb-2 flex items-center gap-2">
                  <AlertTriangle size={14} />
                  Issues Identified
                </div>
                <div className="space-y-1">
                  {analysis.issues.map((issue, idx) => (
                    <div key={idx} className="text-sm text-yellow-200 flex items-start gap-2">
                      <span className="mt-0.5">⚠</span>
                      <span>{issue}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Improved Response */}
            {analysis.improved_response && (
              <div className="mb-4">
                <div className="text-sm font-medium text-blue-400 mb-2 flex items-center gap-2">
                  <Sparkles size={14} />
                  Suggested Improved Response
                </div>
                <div className="bg-blue-900/20 border border-blue-700/30 rounded p-3 text-sm text-blue-100">
                  {analysis.improved_response}
                </div>
              </div>
            )}

            {/* Prompt Suggestions */}
            {analysis.prompt_suggestions && analysis.prompt_suggestions.suggestion && (
              <div className="bg-purple-900/20 border border-purple-700/30 rounded p-4">
                <div className="text-sm font-medium text-purple-300 mb-2 flex items-center gap-2">
                  <FileText size={14} />
                  Prompt Improvement Suggestion
                  {analysis.prompt_suggestions.impact && (
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      analysis.prompt_suggestions.impact === 'high' ? 'bg-red-600 text-white' :
                      analysis.prompt_suggestions.impact === 'medium' ? 'bg-yellow-600 text-white' :
                      'bg-gray-600 text-gray-200'
                    }`}>
                      {analysis.prompt_suggestions.impact} impact
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="text-xs text-purple-400 uppercase font-semibold flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded ${
                      analysis.prompt_suggestions.type === 'new_prompt' ? 'bg-blue-700' :
                      analysis.prompt_suggestions.type === 'kb_addition' ? 'bg-green-700' :
                      'bg-purple-700'
                    }`}>
                      {analysis.prompt_suggestions.type === 'kb_addition' ? '📚 KB Addition' :
                       analysis.prompt_suggestions.type === 'new_prompt' ? '📝 New Prompt' :
                       '🔧 Adjustment'}
                    </span>
                  </div>
                  <div className="text-sm text-purple-100">
                    {analysis.prompt_suggestions.suggestion}
                  </div>
                  <div className="text-xs text-purple-300 mt-2 pt-2 border-t border-purple-700/30">
                    <strong>Why:</strong> {analysis.prompt_suggestions.reasoning}
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button 
                      onClick={() => {
                        navigator.clipboard.writeText(analysis.prompt_suggestions.suggestion);
                        toast({
                          title: "Copied to Clipboard",
                          description: "Prompt suggestion copied. Paste into your agent's node prompt."
                        });
                      }}
                      className="flex items-center gap-1 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded transition-colors"
                    >
                      <Save size={12} />
                      Copy Suggestion
                    </button>
                    <button 
                      onClick={() => {
                        // Navigate to agent tester with the specific node and suggestion - OPEN IN NEW TAB
                        const agentId = callData?.agent_id;
                        const nodeId = analysis.node_id;
                        const suggestion = analysis.prompt_suggestions?.suggestion || '';
                        if (agentId && nodeId) {
                          // Encode suggestion for URL safety
                          const encodedSuggestion = encodeURIComponent(suggestion);
                          window.open(`/agents/${agentId}/test?nodeId=${nodeId}&suggestion=${encodedSuggestion}`, '_blank');
                        } else if (agentId) {
                          window.open(`/agents/${agentId}/test`, '_blank');
                        } else {
                          toast({
                            title: "Agent Tester",
                            description: "Navigate to your agent settings and click 'Test Agent' to test this node.",
                            variant: "default"
                          });
                        }
                      }}
                      className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors"
                    >
                      <TestTube size={12} />
                      Test in Agent Tester ↗
                    </button>
                    <button 
                      onClick={() => {
                        // Open Flow Builder in new tab
                        const agentId = callData?.agent_id;
                        if (agentId) {
                          window.open(`/agents/${agentId}/flow`, '_blank');
                        } else {
                          toast({
                            title: "No Agent",
                            description: "Could not find agent ID for this call.",
                            variant: "destructive"
                          });
                        }
                      }}
                      className="flex items-center gap-1 px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white text-xs rounded transition-colors"
                    >
                      <Settings size={12} />
                      Open Flow Builder ↗
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Goal Progress & Conciseness Feedback */}
            {(analysis.goal_progress_explanation || analysis.conciseness_feedback) && (
              <div className="mt-4 grid grid-cols-2 gap-4 text-xs">
                {analysis.goal_progress_explanation && (
                  <div className="bg-gray-800/50 p-3 rounded">
                    <div className="text-purple-400 font-medium mb-1">🎯 Goal Progress</div>
                    <div className="text-gray-300">{analysis.goal_progress_explanation}</div>
                  </div>
                )}
                {analysis.conciseness_feedback && (
                  <div className="bg-gray-800/50 p-3 rounded">
                    <div className="text-blue-400 font-medium mb-1">📏 Brevity Analysis</div>
                    <div className="text-gray-300">{analysis.conciseness_feedback}</div>
                  </div>
                )}
              </div>
            )}

            {/* Reasoning */}
            {analysis.reasoning && (
              <div className="mt-4 text-xs text-gray-400 border-t border-gray-800 pt-3">
                <strong>Analysis:</strong> {analysis.reasoning}
              </div>
            )}
          </div>
          );
        })}
      </div>
    </div>
  );
};

export default ScriptQualityTab;
