import React, { useState } from 'react';
import { X, Brain, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { agentAPI } from '../services/api';

const TransitionAnalysisModal = ({ isOpen, onClose, agentId, transitions, onAnalysisComplete }) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedModel, setSelectedModel] = useState('grok-4');
  const [selectedProvider, setSelectedProvider] = useState('grok');
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const response = await agentAPI.analyzeTransitions(agentId, {
        transitions,
        model: selectedModel,
        llm_provider: selectedProvider
      });
      setAnalysisResult(response.data);
      if (onAnalysisComplete) {
        onAnalysisComplete(response.data);
      }
    } catch (err) {
      console.error('Error analyzing transitions:', err);
      setError(err.response?.data?.detail || 'Failed to analyze transitions');
    } finally {
      setAnalyzing(false);
    }
  };

  const getConfidenceBadge = (confidence) => {
    const colors = {
      high: 'bg-green-900/30 text-green-300 border-green-700',
      medium: 'bg-yellow-900/30 text-yellow-300 border-yellow-700',
      low: 'bg-red-900/30 text-red-300 border-red-700'
    };
    return colors[confidence] || colors.medium;
  };

  const getSeverityBadge = (severity) => {
    const colors = {
      high: 'bg-red-900/30 text-red-300 border-red-700',
      medium: 'bg-yellow-900/30 text-yellow-300 border-yellow-700',
      low: 'bg-blue-900/30 text-blue-300 border-blue-700'
    };
    return colors[severity] || colors.medium;
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg border border-gray-700 max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <Brain className="w-6 h-6 text-purple-400" />
            <h2 className="text-xl font-semibold text-white">Transition Analysis</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Model Selection */}
          <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Select LLM Model (Same model that will evaluate transitions in production)
            </label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-2">Provider</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => {
                    setSelectedProvider(e.target.value);
                    // Reset model when provider changes
                    if (e.target.value === 'grok') {
                      setSelectedModel('grok-4');
                    } else {
                      setSelectedModel('gpt-4o');
                    }
                  }}
                  className="w-full bg-gray-900 border border-gray-700 text-white rounded px-3 py-2 text-sm"
                  disabled={analyzing}
                >
                  <option value="grok">Grok (xAI)</option>
                  <option value="openai">OpenAI</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-2">Model</label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 text-white rounded px-3 py-2 text-sm"
                  disabled={analyzing}
                >
                  {selectedProvider === 'grok' ? (
                    <>
                      <option value="grok-4">Grok 4</option>
                      <option value="grok-3">Grok 3</option>
                      <option value="grok-2-1212">Grok 2 (Dec 2024)</option>
                      <option value="grok-beta">Grok Beta</option>
                    </>
                  ) : (
                    <>
                      <option value="gpt-4o">GPT-4o</option>
                      <option value="gpt-4-turbo">GPT-4 Turbo</option>
                      <option value="gpt-4">GPT-4</option>
                    </>
                  )}
                </select>
              </div>
            </div>
          </div>

          {/* Transitions Preview */}
          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-3">Transitions to Analyze ({transitions.length})</h3>
            <div className="space-y-2">
              {transitions.map((transition, index) => (
                <div key={index} className="bg-gray-800/50 rounded p-3 border border-gray-700">
                  <div className="text-xs text-gray-400 mb-1">Transition {index + 1}</div>
                  <div className="text-sm text-white">{transition.condition || 'No condition specified'}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Analyze Button */}
          {!analysisResult && (
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Brain className="w-5 h-5" />
              {analyzing ? 'Analyzing...' : 'Analyze Transitions'}
            </button>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-red-300 font-medium mb-1">Analysis Failed</div>
                  <div className="text-sm text-red-400">{error}</div>
                </div>
              </div>
            </div>
          )}

          {/* Analysis Results */}
          {analysisResult && (
            <div className="space-y-6">
              {/* Overall Assessment */}
              {analysisResult.overall_assessment && (
                <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="text-blue-300 font-medium mb-2">Overall Assessment</div>
                      <div className="text-sm text-blue-200">{analysisResult.overall_assessment}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Confusion Warnings */}
              {analysisResult.confusion_warnings && analysisResult.confusion_warnings.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-yellow-400" />
                    Confusion & Overlap Warnings
                  </h3>
                  {analysisResult.confusion_warnings.map((warning, index) => (
                    <div key={index} className={`rounded-lg p-4 border ${getSeverityBadge(warning.severity)}`}>
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="font-medium">
                          Transitions {warning.affected_transitions?.join(', ')}
                        </div>
                        <div className="text-xs uppercase font-semibold">
                          {warning.severity} severity
                        </div>
                      </div>
                      <div className="text-sm mb-2">{warning.issue}</div>
                      {warning.recommendation && (
                        <div className="text-xs mt-2 pt-2 border-t border-current/20">
                          <strong>Recommendation:</strong> {warning.recommendation}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Individual Transition Analyses */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-300">LLM's Understanding of Each Transition</h3>
                {analysisResult.transition_analyses?.map((analysis, index) => (
                  <div key={index} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium text-white">
                          Transition {analysis.transition_number}
                        </div>
                        <div className={`text-xs px-2 py-1 rounded border ${getConfidenceBadge(analysis.confidence)}`}>
                          {analysis.confidence} confidence
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div>
                        <div className="text-xs text-gray-400 mb-1">Understanding:</div>
                        <div className="text-sm text-white">{analysis.understanding}</div>
                      </div>
                      
                      {analysis.example_phrases && analysis.example_phrases.length > 0 && (
                        <div>
                          <div className="text-xs text-gray-400 mb-1">Example Phrases:</div>
                          <div className="flex flex-wrap gap-2">
                            {analysis.example_phrases.map((phrase, i) => (
                              <div key={i} className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">
                                "{phrase}"
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {analysis.notes && (
                        <div>
                          <div className="text-xs text-gray-400 mb-1">Notes:</div>
                          <div className="text-sm text-gray-300">{analysis.notes}</div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Re-analyze Button */}
              <button
                onClick={() => {
                  setAnalysisResult(null);
                  setError(null);
                }}
                className="w-full bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg font-medium transition-colors"
              >
                Analyze Again with Different Model
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-700 p-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default TransitionAnalysisModal;
