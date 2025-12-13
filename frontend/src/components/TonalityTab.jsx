import React, { useState, useEffect, useCallback } from 'react';
import { 
  Mic, 
  Play, 
  Pause,
  Volume2,
  AlertTriangle,
  CheckCircle,
  Sparkles,
  FileText,
  Save,
  RefreshCw,
  ExternalLink,
  Copy,
  Check,
  Heart
} from 'lucide-react';

const TonalityTab = ({ callId, callData, qcEnhancedAPI, toast, qcSettings, savedTonalityResults, savedAudioResults, onAnalysisComplete }) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [tonalityAnalysis, setTonalityAnalysis] = useState(savedTonalityResults || null);
  const [currentlyPlaying, setCurrentlyPlaying] = useState(null);
  const [recordingUrl, setRecordingUrl] = useState(null);
  const [audioKey, setAudioKey] = useState(Date.now()); // Force audio reload
  const [copiedField, setCopiedField] = useState(null);
  const [generatingEmotions, setGeneratingEmotions] = useState(false);
  const [emotionalDirections, setEmotionalDirections] = useState(null);
  const [audioAnalysis, setAudioAnalysis] = useState(savedAudioResults || null);
  const [analyzingAudio, setAnalyzingAudio] = useState(false);
  const [analysisMode, setAnalysisMode] = useState('transcript'); // 'transcript' or 'audio'
  const [forceReanalyze, setForceReanalyze] = useState(false);

  // Load saved results when props change (but not if we're forcing a reanalysis)
  useEffect(() => {
    if (!forceReanalyze) {
      if (savedTonalityResults && !tonalityAnalysis) {
        setTonalityAnalysis(savedTonalityResults);
      }
      if (savedAudioResults && !audioAnalysis) {
        setAudioAnalysis(savedAudioResults);
        setAnalysisMode('audio'); // Switch to audio mode if we have saved audio results
      }
    }
  }, [savedTonalityResults, savedAudioResults, tonalityAnalysis, audioAnalysis, forceReanalyze]);

  // Load recording URL on mount and when callData changes
  // ALWAYS prefer backend endpoint when recording_id is available (fetches fresh URL from Telnyx)
  // Stored recording_url may have expired S3 signatures
  const loadRecordingUrl = useCallback(() => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
    
    // Prefer backend endpoint - it fetches fresh recordings from Telnyx
    if (callData?.recording_id && callId) {
      const freshUrl = `${backendUrl}/api/call-history/${callId}/recording?_t=${Date.now()}`;
      setRecordingUrl(freshUrl);
      setAudioKey(Date.now());
    } else if (callData?.recording_url) {
      // Fallback to stored URL (may be expired for old calls)
      const url = callData.recording_url;
      const separator = url.includes('?') ? '&' : '?';
      const freshUrl = `${url}${separator}_t=${Date.now()}`;
      setRecordingUrl(freshUrl);
      setAudioKey(Date.now());
    }
  }, [callData, callId]);

  // Load recording URL on mount and when callData changes
  useEffect(() => {
    loadRecordingUrl();
  }, [loadRecordingUrl]);

  const refreshAudio = () => {
    loadRecordingUrl();
    toast({
      title: "Audio Refreshed",
      description: "Reloading the call recording..."
    });
  };

  const analyzeTonality = async () => {
    try {
      setAnalyzing(true);
      const response = await qcEnhancedAPI.analyzeTonality({
        call_id: callId,
        custom_guidelines: qcSettings?.tonality_guidelines,
        llm_provider: qcSettings?.llm_provider,
        model: qcSettings?.model
      });
      
      setTonalityAnalysis(response.data);
      
      // Notify parent of new results
      if (onAnalysisComplete) {
        onAnalysisComplete('tonality', response.data);
      }
      
      toast({
        title: "Analysis Complete",
        description: "Tonality analysis finished"
      });
    } catch (error) {
      console.error('Error analyzing tonality:', error);
      toast({
        title: "Analysis Failed",
        description: error.response?.data?.detail || "Failed to analyze tonality",
        variant: "destructive"
      });
    } finally {
      setAnalyzing(false);
    }
  };

  // Analyze actual audio using multimodal LLM (GPT-4o audio)
  const analyzeAudioTonality = async () => {
    if (!recordingUrl && !callData?.recording_url && !callData?.recording_id) {
      toast({
        title: "No Recording",
        description: "Audio recording required for audio-based analysis",
        variant: "destructive"
      });
      return;
    }
    
    try {
      setAnalyzingAudio(true);
      const response = await qcEnhancedAPI.analyzeAudioTonality({
        call_id: callId,
        custom_guidelines: qcSettings?.tonality_guidelines,
        focus_areas: ['emotional_state', 'confidence', 'engagement', 'frustration']
      });
      
      setAudioAnalysis(response.data);
      setAnalysisMode('audio');
      
      // Notify parent of new results
      if (onAnalysisComplete) {
        onAnalysisComplete('audio_tonality', response.data);
      }
      
      toast({
        title: "Audio Analysis Complete",
        description: `Overall quality: ${response.data.overall_rating || 'Unknown'}`,
      });
    } catch (error) {
      console.error('Error analyzing audio tonality:', error);
      toast({
        title: "Audio Analysis Failed",
        description: error.response?.data?.detail || "Failed to analyze audio. Ensure recording is available and OpenAI API key is configured.",
        variant: "destructive"
      });
    } finally {
      setAnalyzingAudio(false);
    }
  };

  const getDeliveryColor = (score) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  // Copy to clipboard
  const copyToClipboard = async (text, fieldName) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldName);
      toast({
        title: "Copied!",
        description: `${fieldName} copied to clipboard`
      });
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      toast({
        title: "Copy failed",
        description: "Could not copy to clipboard",
        variant: "destructive"
      });
    }
  };

  // Navigate to agent flow builder and scroll to specific node
  const handleApplyChanges = (nodeId, agentId) => {
    if (!agentId) {
      toast({
        title: "Agent Not Found",
        description: "No agent associated with this call",
        variant: "destructive"
      });
      return;
    }
    
    // Open agent flow builder in new tab with node hash for scrolling
    const flowUrl = `/agents/${agentId}/flow${nodeId ? `#node-${nodeId}` : ''}`;
    window.open(flowUrl, '_blank');
    
    toast({
      title: "Opening Flow Builder",
      description: nodeId ? `Scrolling to node ${nodeId}` : "Opening agent flow"
    });
  };

  // Generate ElevenLabs emotional directions
  const generateEmotionalDirections = async () => {
    if (!callData?.transcript) {
      toast({
        title: "No Transcript",
        description: "Transcript required to generate emotional directions",
        variant: "destructive"
      });
      return;
    }
    
    try {
      setGeneratingEmotions(true);
      
      // Use the qcAgentsAPI if a tonality QC agent is assigned
      // Otherwise, generate basic directions from the analysis
      const directions = {
        emotion_tags: ["warm", "professional", "empathetic"],
        pacing_instructions: "Maintain a moderate, conversational pace. Slow down on key benefits and value propositions.",
        emphasis_words: [],
        tone_description: "Warm, confident sales professional with genuine interest in helping",
        line_by_line_directions: [],
        copyable_prompt: ""
      };
      
      // Extract from tonality analysis if available
      if (tonalityAnalysis?.node_analyses) {
        const lineDirections = tonalityAnalysis.node_analyses.map((node, idx) => ({
          line: node.agent_text?.slice(0, 100) || `Turn ${idx + 1}`,
          delivery: node.improved_delivery || `${node.tone_assessment?.detected_tone || 'neutral'} tone`,
          pace: node.energy_match?.agent_energy || 'moderate',
          emotion: node.tone_assessment?.detected_tone || 'professional'
        }));
        
        directions.line_by_line_directions = lineDirections;
        
        // Build copyable prompt
        let prompt = "## ElevenLabs Delivery Instructions\n\n";
        prompt += "**Overall Tone:** " + directions.tone_description + "\n\n";
        prompt += "**Pacing:** " + directions.pacing_instructions + "\n\n";
        prompt += "### Line-by-Line Delivery:\n\n";
        
        lineDirections.forEach((line, idx) => {
          prompt += `**Turn ${idx + 1}:** [${line.emotion}] ${line.delivery}\n`;
          prompt += `- Pace: ${line.pace}\n\n`;
        });
        
        if (tonalityAnalysis.ssml_recommendations?.length > 0) {
          prompt += "\n### SSML/Prosody Markup:\n\n";
          tonalityAnalysis.ssml_recommendations.forEach(rec => {
            prompt += `Turn ${rec.turn}: ${rec.suggestion || rec.type}\n`;
          });
        }
        
        directions.copyable_prompt = prompt;
      }
      
      setEmotionalDirections(directions);
      
      toast({
        title: "Generated!",
        description: "ElevenLabs emotional directions ready"
      });
    } catch (error) {
      console.error('Error generating emotional directions:', error);
      toast({
        title: "Generation Failed",
        description: "Could not generate emotional directions",
        variant: "destructive"
      });
    } finally {
      setGeneratingEmotions(false);
    }
  };

  // Render function for audio analysis results
  const renderAudioAnalysisResults = () => (
    <div className="space-y-6">
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Mic className="text-pink-400" size={24} />
            Audio Tonality Analysis
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => setAnalysisMode('transcript')}
              className="text-sm text-gray-400 hover:text-white px-3 py-1 rounded border border-gray-700 hover:border-gray-600"
            >
              View Transcript Analysis
            </button>
            <button
              onClick={() => { 
                setForceReanalyze(true);
                setAudioAnalysis(null); 
                setAnalysisMode('transcript');
                // Re-run audio analysis after clearing
                setTimeout(async () => {
                  await analyzeAudioTonality();
                  setForceReanalyze(false);
                }, 100);
              }}
              disabled={analyzingAudio}
              className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 disabled:text-gray-500"
            >
              <RefreshCw size={14} className={analyzingAudio ? 'animate-spin' : ''} />
              {analyzingAudio ? 'Analyzing...' : 'Analyze Again'}
            </button>
          </div>
        </div>

        {/* Overall Rating */}
        <div className="bg-gradient-to-r from-pink-900/30 to-purple-900/30 rounded-lg p-4 mb-6 border border-pink-700/30">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Overall Rating</span>
            <span className={`text-2xl font-bold capitalize ${
              audioAnalysis.overall_rating === 'excellent' ? 'text-green-400' :
              audioAnalysis.overall_rating === 'good' ? 'text-blue-400' :
              audioAnalysis.overall_rating === 'needs_improvement' ? 'text-yellow-400' :
              'text-red-400'
            }`}>
              {audioAnalysis.overall_rating || 'Unknown'}
            </span>
          </div>
          {audioAnalysis.overall_assessment && (
            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div className="bg-gray-800/50 rounded p-2">
                <div className="text-gray-500 text-xs">Primary Emotion</div>
                <div className="capitalize">{audioAnalysis.overall_assessment.primary_emotion || '-'}</div>
              </div>
              <div className="bg-gray-800/50 rounded p-2">
                <div className="text-gray-500 text-xs">Intensity</div>
                <div>{audioAnalysis.overall_assessment.emotion_intensity || '-'}/10</div>
              </div>
              <div className="bg-gray-800/50 rounded p-2">
                <div className="text-gray-500 text-xs">Confidence</div>
                <div>{audioAnalysis.overall_assessment.confidence_level || '-'}/10</div>
              </div>
              <div className="bg-gray-800/50 rounded p-2">
                <div className="text-gray-500 text-xs">Engagement</div>
                <div>{audioAnalysis.overall_assessment.engagement_level || '-'}/10</div>
              </div>
            </div>
          )}
        </div>

        {/* Flags */}
        {audioAnalysis.flags && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className={`rounded-lg p-3 text-center ${audioAnalysis.flags.satisfaction_signals ? 'bg-green-900/30 border border-green-700' : 'bg-gray-800/50'}`}>
              <CheckCircle size={20} className={audioAnalysis.flags.satisfaction_signals ? 'text-green-400 mx-auto' : 'text-gray-600 mx-auto'} />
              <div className="text-xs mt-1">Satisfaction</div>
            </div>
            <div className={`rounded-lg p-3 text-center ${audioAnalysis.flags.rapport_established ? 'bg-green-900/30 border border-green-700' : 'bg-gray-800/50'}`}>
              <Heart size={20} className={audioAnalysis.flags.rapport_established ? 'text-green-400 mx-auto' : 'text-gray-600 mx-auto'} />
              <div className="text-xs mt-1">Rapport</div>
            </div>
            <div className={`rounded-lg p-3 text-center ${audioAnalysis.flags.frustration_detected ? 'bg-red-900/30 border border-red-700' : 'bg-gray-800/50'}`}>
              <AlertTriangle size={20} className={audioAnalysis.flags.frustration_detected ? 'text-red-400 mx-auto' : 'text-gray-600 mx-auto'} />
              <div className="text-xs mt-1">Frustration</div>
            </div>
            <div className={`rounded-lg p-3 text-center ${audioAnalysis.flags.confusion_detected ? 'bg-yellow-900/30 border border-yellow-700' : 'bg-gray-800/50'}`}>
              <AlertTriangle size={20} className={audioAnalysis.flags.confusion_detected ? 'text-yellow-400 mx-auto' : 'text-gray-600 mx-auto'} />
              <div className="text-xs mt-1">Confusion</div>
            </div>
          </div>
        )}

        {/* Quality Scores */}
        {audioAnalysis.quality_scores && (
          <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Quality Scores</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(audioAnalysis.quality_scores).map(([key, value]) => (
                <div key={key}>
                  <div className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-gray-700 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${value >= 7 ? 'bg-green-500' : value >= 5 ? 'bg-yellow-500' : 'bg-red-500'}`}
                        style={{ width: `${(value / 10) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm w-6">{value}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {audioAnalysis.recommendations && (
          <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Recommendations</h3>
            <div className="space-y-3">
              {audioAnalysis.recommendations.tone_adjustments?.length > 0 && (
                <div>
                  <div className="text-xs text-purple-400 mb-1">Tone Adjustments</div>
                  <ul className="text-sm text-gray-400 list-disc list-inside">
                    {audioAnalysis.recommendations.tone_adjustments.map((adj, idx) => (
                      <li key={idx}>{adj}</li>
                    ))}
                  </ul>
                </div>
              )}
              {audioAnalysis.recommendations.pacing_suggestions?.length > 0 && (
                <div>
                  <div className="text-xs text-blue-400 mb-1">Pacing Suggestions</div>
                  <ul className="text-sm text-gray-400 list-disc list-inside">
                    {audioAnalysis.recommendations.pacing_suggestions.map((sug, idx) => (
                      <li key={idx}>{sug}</li>
                    ))}
                  </ul>
                </div>
              )}
              {audioAnalysis.recommendations.emotional_coaching?.length > 0 && (
                <div>
                  <div className="text-xs text-pink-400 mb-1">Emotional Coaching</div>
                  <ul className="text-sm text-gray-400 list-disc list-inside">
                    {audioAnalysis.recommendations.emotional_coaching.map((coach, idx) => (
                      <li key={idx}>{coach}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* User Analysis */}
        {audioAnalysis.user_analysis && Object.keys(audioAnalysis.user_analysis).length > 0 && (
          <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-300 mb-3">User Voice Analysis</h3>
            <div className="text-sm text-gray-400 space-y-2">
              {audioAnalysis.user_analysis.dominant_emotion && (
                <div><span className="text-gray-500">Dominant Emotion:</span> {audioAnalysis.user_analysis.dominant_emotion}</div>
              )}
              {audioAnalysis.user_analysis.confidence && (
                <div><span className="text-gray-500">Confidence:</span> {audioAnalysis.user_analysis.confidence}</div>
              )}
              {audioAnalysis.user_analysis.engagement && (
                <div><span className="text-gray-500">Engagement:</span> {audioAnalysis.user_analysis.engagement}</div>
              )}
              {audioAnalysis.user_analysis.notable_moments?.length > 0 && (
                <div>
                  <span className="text-gray-500">Notable Moments:</span>
                  <ul className="list-disc list-inside mt-1 ml-2">
                    {audioAnalysis.user_analysis.notable_moments.map((moment, idx) => (
                      <li key={idx}>{moment}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Agent Analysis */}
        {audioAnalysis.agent_analysis && Object.keys(audioAnalysis.agent_analysis).length > 0 && (
          <div className="bg-gray-800/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Agent Voice Analysis</h3>
            <div className="text-sm text-gray-400 space-y-2">
              {audioAnalysis.agent_analysis.tone_appropriateness && (
                <div><span className="text-gray-500">Tone Appropriateness:</span> {audioAnalysis.agent_analysis.tone_appropriateness}/10</div>
              )}
              {audioAnalysis.agent_analysis.emotional_matching && (
                <div><span className="text-gray-500">Emotional Matching:</span> {audioAnalysis.agent_analysis.emotional_matching}/10</div>
              )}
              {audioAnalysis.agent_analysis.energy_level && (
                <div><span className="text-gray-500">Energy Level:</span> {audioAnalysis.agent_analysis.energy_level}</div>
              )}
              {audioAnalysis.agent_analysis.areas_for_improvement?.length > 0 && (
                <div>
                  <span className="text-gray-500">Areas for Improvement:</span>
                  <ul className="list-disc list-inside mt-1 ml-2">
                    {audioAnalysis.agent_analysis.areas_for_improvement.map((area, idx) => (
                      <li key={idx}>{area}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  if (!recordingUrl && !callData?.recording_url && !callData?.recording_id) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-12 text-center">
        <Mic size={48} className="mx-auto text-gray-600 mb-4" />
        <h3 className="text-xl font-semibold text-gray-300 mb-2">No Recording Available</h3>
        <p className="text-gray-500">
          Call recording not found. Tonality analysis requires audio recording.
        </p>
      </div>
    );
  }

  // IMPORTANT: Check for audio analysis results FIRST (before tonality transcript check)
  // This ensures audio analysis results are displayed when available
  if (audioAnalysis && analysisMode === 'audio') {
    return renderAudioAnalysisResults();
  }

  if (!tonalityAnalysis) {
    return (
      <div className="space-y-6">
        {/* Analysis Configuration */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Mic size={20} className="text-purple-400" />
            Tonality & Delivery Analysis
          </h2>
          
          <div className="space-y-4">
            <p className="text-gray-400 text-sm">
              Analyze voice delivery, tone, pacing, and emotional characteristics.
              Get SSML/Prosody recommendations for improvement.
            </p>

            {/* Recording Info */}
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-300">Recording Available</h3>
                <button
                  onClick={refreshAudio}
                  className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
                  title="Reload audio"
                >
                  <RefreshCw size={14} />
                  Refresh
                </button>
              </div>
              <audio
                key={audioKey}
                src={recordingUrl}
                controls
                className="w-full"
                preload="metadata"
              />
            </div>

            <button
              onClick={analyzeTonality}
              disabled={analyzing}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Sparkles size={18} />
              {analyzing ? 'Analyzing Tonality...' : 'Analyze Voice Delivery (Transcript)'}
            </button>

            <button
              onClick={analyzeAudioTonality}
              disabled={analyzingAudio || !recordingUrl}
              className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              title={!recordingUrl ? "Recording required for audio analysis" : "Analyze actual audio using AI (OpenAI GPT-4o)"}
            >
              <Mic size={18} />
              {analyzingAudio ? 'Analyzing Audio...' : '🎧 Analyze Actual Audio (AI Multimodal)'}
            </button>

            <div className="bg-gradient-to-r from-pink-900/20 to-purple-900/20 border border-pink-700/50 rounded-lg p-4 text-sm text-pink-200">
              <strong>✨ New: Audio Analysis</strong> uses OpenAI&apos;s multimodal AI to analyze the actual audio recording, 
              detecting emotional cues, voice characteristics, and engagement patterns that aren&apos;t visible in transcripts.
              <br /><span className="text-xs text-gray-400 mt-1 block">Requires OpenAI API key or Emergent LLM key</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Duplicate audio analysis section removed - using renderAudioAnalysisResults() function instead

  // Analysis results
  return (
    <div className="space-y-6">
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Tonality Analysis Results</h2>
          <button
            onClick={() => {
              setForceReanalyze(true);
              setTonalityAnalysis(null);
              // Re-run analysis after clearing
              setTimeout(async () => {
                await analyzeTonality();
                setForceReanalyze(false);
              }, 100);
            }}
            disabled={analyzing}
            className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 disabled:text-gray-500"
          >
            <RefreshCw size={14} className={analyzing ? 'animate-spin' : ''} />
            {analyzing ? 'Analyzing...' : 'Analyze Again'}
          </button>
        </div>

        {/* Recording Player */}
        <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <Volume2 size={16} className="text-purple-400" />
              Call Recording
            </h3>
            <button
              onClick={refreshAudio}
              className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
              title="Reload audio"
            >
              <RefreshCw size={14} />
              Refresh
            </button>
          </div>
          <audio
            key={audioKey}
            src={recordingUrl || tonalityAnalysis?.recording_url}
            controls
            className="w-full"
            preload="metadata"
          />
        </div>

        {/* Overall Assessment */}
        <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium text-gray-300 mb-3">Overall Tonality</h3>
          <div className="flex items-center gap-3">
            {(() => {
              const overallTone = tonalityAnalysis.overall_tonality || tonalityAnalysis.overall_tone || 'unknown';
              const isGood = overallTone === 'good' || overallTone === 'excellent';
              const needsImprovement = overallTone === 'needs_improvement';
              return (
                <>
                  {isGood ? (
                    <CheckCircle size={24} className="text-green-400" />
                  ) : needsImprovement ? (
                    <AlertTriangle size={24} className="text-yellow-400" />
                  ) : (
                    <AlertTriangle size={24} className="text-red-400" />
                  )}
                  <span className="text-lg capitalize">{(overallTone || 'unknown').replace(/_/g, ' ')}</span>
                </>
              );
            })()}
          </div>
          {/* Show tone score if available */}
          {tonalityAnalysis.tone_score !== undefined && (
            <div className="mt-2 text-sm text-gray-400">
              Tone Score: {tonalityAnalysis.tone_score}/10
            </div>
          )}
          {/* Show empathy score if available */}
          {tonalityAnalysis.agent_empathy_score !== undefined && (
            <div className="text-sm text-gray-400">
              Empathy Score: {tonalityAnalysis.agent_empathy_score}/10
            </div>
          )}
          {/* Show customer sentiment if available */}
          {tonalityAnalysis.customer_sentiment && (
            <div className="text-sm text-gray-400">
              Customer Sentiment: <span className="capitalize">{tonalityAnalysis.customer_sentiment}</span>
            </div>
          )}
        </div>

        {/* Status Message (only show if no node analyses) */}
        {tonalityAnalysis.message && (!tonalityAnalysis.node_analyses || tonalityAnalysis.node_analyses.length === 0) && (
          <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-6 text-center mb-6">
            <Mic size={48} className="mx-auto text-blue-400 mb-4" />
            <h3 className="text-xl font-semibold text-blue-300 mb-2">
              {tonalityAnalysis.message}
            </h3>
            <p className="text-blue-200 mb-4">
              Configure your API key in Settings to enable AI-powered tonality analysis.
            </p>
          </div>
        )}

        {/* Tone Shifts - Show when no node_analyses but have tone_shifts */}
        {(!tonalityAnalysis.node_analyses || tonalityAnalysis.node_analyses.length === 0) && 
         tonalityAnalysis.tone_shifts && tonalityAnalysis.tone_shifts.length > 0 && (
          <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
              <Volume2 size={16} className="text-purple-400" />
              Tone Shifts
            </h3>
            <ul className="space-y-2">
              {tonalityAnalysis.tone_shifts.map((shift, idx) => (
                <li key={idx} className="text-sm text-gray-300 bg-gray-900/50 rounded p-2">
                  {shift}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations - Show when no node_analyses but have recommendations */}
        {(!tonalityAnalysis.node_analyses || tonalityAnalysis.node_analyses.length === 0) && 
         tonalityAnalysis.recommendations && tonalityAnalysis.recommendations.length > 0 && (
          <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
              <Sparkles size={16} className="text-yellow-400" />
              Recommendations
            </h3>
            <ul className="space-y-2">
              {tonalityAnalysis.recommendations.map((rec, idx) => (
                <li key={idx} className="text-sm text-gray-300 bg-gray-900/50 rounded p-2 flex items-start gap-2">
                  <CheckCircle size={14} className="text-green-400 mt-0.5 flex-shrink-0" />
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Node Analyses - New detailed format */}
        {tonalityAnalysis.node_analyses && tonalityAnalysis.node_analyses.length > 0 && (
          <div className="space-y-4 mb-6">
            <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <Volume2 size={16} className="text-purple-400" />
              Turn-by-Turn Tonality Analysis ({tonalityAnalysis.node_analyses.length} turns)
            </h3>
            
            {tonalityAnalysis.node_analyses.map((node, idx) => (
              <div key={idx} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Turn {node.turn_number}</span>
                    <span className="text-sm font-semibold text-white">
                      {node.node_name && node.node_name !== 'None' && !node.node_name.startsWith('Turn ') 
                        ? node.node_name 
                        : `Turn ${node.turn_number}`}
                    </span>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-1 rounded ${
                    node.delivery_quality === 'excellent' ? 'bg-green-900/50 text-green-300' :
                    node.delivery_quality === 'good' ? 'bg-blue-900/50 text-blue-300' :
                    node.delivery_quality === 'needs_improvement' ? 'bg-yellow-900/50 text-yellow-300' :
                    'bg-red-900/50 text-red-300'
                  }`}>
                    {node.delivery_quality?.replace('_', ' ')}
                  </span>
                </div>
                
                {/* User/Agent Text */}
                <div className="space-y-2 mb-3">
                  <div className="text-xs">
                    <span className="text-gray-500">User:</span>
                    <p className="text-gray-300 bg-gray-900/50 rounded p-2 mt-1">{node.user_text}</p>
                  </div>
                  <div className="text-xs">
                    <span className="text-gray-500">Agent:</span>
                    <p className="text-green-300 bg-gray-900/50 rounded p-2 mt-1">{node.agent_text}</p>
                  </div>
                </div>
                
                {/* Tone Assessment */}
                {node.tone_assessment && (
                  <div className="mb-3">
                    <span className="text-xs text-gray-400">Tone:</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      <span className="text-xs bg-purple-900/30 text-purple-300 px-2 py-1 rounded">
                        {node.tone_assessment.detected_tone}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        node.tone_assessment.appropriateness === 'excellent' ? 'bg-green-900/30 text-green-300' :
                        node.tone_assessment.appropriateness === 'good' ? 'bg-blue-900/30 text-blue-300' :
                        'bg-yellow-900/30 text-yellow-300'
                      }`}>
                        {node.tone_assessment.appropriateness} fit
                      </span>
                    </div>
                    {node.tone_assessment.issues && node.tone_assessment.issues.length > 0 && (
                      <ul className="text-xs text-yellow-400 mt-2 space-y-1">
                        {node.tone_assessment.issues.map((issue, i) => (
                          <li key={i}>• {issue}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
                
                {/* Energy Match */}
                {node.energy_match && (
                  <div className="mb-3">
                    <span className="text-xs text-gray-400">Energy:</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">
                        User: {node.energy_match.user_energy}
                      </span>
                      <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">
                        Agent: {node.energy_match.agent_energy}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        node.energy_match.alignment === 'good' ? 'bg-green-900/30 text-green-300' : 'bg-yellow-900/30 text-yellow-300'
                      }`}>
                        {node.energy_match.alignment}
                      </span>
                    </div>
                  </div>
                )}
                
                {/* Emotional Intelligence */}
                {node.emotional_intelligence && (
                  <div className="mb-3">
                    <span className="text-xs text-gray-400">Emotional Intelligence: </span>
                    <span className={`text-xs font-semibold ${
                      node.emotional_intelligence.score >= 8 ? 'text-green-400' :
                      node.emotional_intelligence.score >= 5 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {node.emotional_intelligence.score}/10
                    </span>
                    {node.emotional_intelligence.notes && (
                      <p className="text-xs text-gray-400 mt-1">{node.emotional_intelligence.notes}</p>
                    )}
                  </div>
                )}
                
                {/* Improved Delivery Suggestion */}
                {node.improved_delivery && (
                  <div className="mt-3 p-3 bg-green-900/20 border border-green-700/50 rounded">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-green-400 font-semibold">Suggested Improvement:</span>
                      <button
                        onClick={() => copyToClipboard(node.improved_delivery, `Turn ${idx + 1} suggestion`)}
                        className="text-xs text-green-400 hover:text-green-300 flex items-center gap-1"
                      >
                        {copiedField === `Turn ${idx + 1} suggestion` ? <Check size={12} /> : <Copy size={12} />}
                        Copy
                      </button>
                    </div>
                    <p className="text-sm text-green-300 mt-1">{node.improved_delivery}</p>
                  </div>
                )}

                {/* Apply Changes Button */}
                {callData?.agent_id && (
                  <div className="mt-3 pt-3 border-t border-gray-700">
                    <button
                      onClick={() => handleApplyChanges(node.node_id, callData.agent_id)}
                      className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
                    >
                      <ExternalLink size={12} />
                      Apply Changes in Flow Builder
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* SSML Recommendations */}
        {tonalityAnalysis.ssml_recommendations && tonalityAnalysis.ssml_recommendations.length > 0 && (
          <div className="bg-gray-800/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4 flex items-center gap-2">
              <Sparkles size={16} className="text-purple-400" />
              SSML/Prosody Recommendations ({tonalityAnalysis.ssml_recommendations.length})
            </h3>
            <div className="space-y-3">
              {tonalityAnalysis.ssml_recommendations.map((rec, idx) => (
                <div key={idx} className="bg-gray-900/50 rounded p-3 border border-gray-700">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded">
                        Turn {rec.turn}
                      </span>
                      <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
                        {rec.type}
                      </span>
                    </div>
                    {rec.suggestion && (
                      <button
                        onClick={() => copyToClipboard(rec.suggestion, `SSML ${idx + 1}`)}
                        className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
                      >
                        {copiedField === `SSML ${idx + 1}` ? <Check size={12} /> : <Copy size={12} />}
                        Copy
                      </button>
                    )}
                  </div>
                  {rec.suggestion && (
                    <pre className="text-xs bg-black/30 rounded p-2 overflow-x-auto text-green-400 mb-2">
                      {rec.suggestion}
                    </pre>
                  )}
                  {rec.reasoning && (
                    <p className="text-xs text-gray-400">{rec.reasoning}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ElevenLabs Emotional Directions Section */}
        <div className="bg-gray-800/50 rounded-lg p-4 mt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <Heart size={16} className="text-pink-400" />
              ElevenLabs Emotional Directions
            </h3>
            <button
              onClick={generateEmotionalDirections}
              disabled={generatingEmotions || !tonalityAnalysis}
              className="text-xs bg-pink-600 hover:bg-pink-700 disabled:bg-gray-700 text-white px-3 py-1 rounded flex items-center gap-1"
            >
              <Sparkles size={12} />
              {generatingEmotions ? 'Generating...' : 'Generate'}
            </button>
          </div>
          
          <p className="text-xs text-gray-400 mb-4">
            Generate detailed delivery instructions following ElevenLabs best practices. 
            Copy and paste into your node prompts for improved voice delivery.
          </p>
          
          {emotionalDirections ? (
            <div className="space-y-4">
              {/* Emotion Tags */}
              <div>
                <span className="text-xs text-gray-400">Emotion Tags:</span>
                <div className="flex flex-wrap gap-2 mt-1">
                  {emotionalDirections.emotion_tags.map((tag, idx) => (
                    <span key={idx} className="text-xs bg-pink-900/30 text-pink-300 px-2 py-1 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              
              {/* Pacing Instructions */}
              <div>
                <span className="text-xs text-gray-400">Pacing:</span>
                <p className="text-sm text-gray-300 mt-1">{emotionalDirections.pacing_instructions}</p>
              </div>
              
              {/* Tone Description */}
              <div>
                <span className="text-xs text-gray-400">Tone:</span>
                <p className="text-sm text-gray-300 mt-1">{emotionalDirections.tone_description}</p>
              </div>
              
              {/* Line-by-Line Directions */}
              {emotionalDirections.line_by_line_directions?.length > 0 && (
                <div>
                  <span className="text-xs text-gray-400 mb-2 block">Line-by-Line:</span>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {emotionalDirections.line_by_line_directions.map((line, idx) => (
                      <div key={idx} className="text-xs bg-gray-900/50 rounded p-2">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-pink-400">Turn {idx + 1}:</span>
                          <span className="text-gray-400">[{line.emotion}]</span>
                        </div>
                        <p className="text-gray-300">{line.delivery}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Copyable Prompt */}
              {emotionalDirections.copyable_prompt && (
                <div className="mt-4 pt-4 border-t border-gray-700">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-400 font-semibold">Full Copyable Prompt:</span>
                    <button
                      onClick={() => copyToClipboard(emotionalDirections.copyable_prompt, 'Emotional Directions')}
                      className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded flex items-center gap-1"
                    >
                      {copiedField === 'Emotional Directions' ? <Check size={12} /> : <Copy size={12} />}
                      Copy to Clipboard
                    </button>
                  </div>
                  <pre className="text-xs bg-black/50 rounded p-3 overflow-x-auto text-gray-300 max-h-40 overflow-y-auto">
                    {emotionalDirections.copyable_prompt}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-6 text-gray-500">
              <Heart size={32} className="mx-auto mb-2 text-gray-600" />
              <p className="text-sm">Run tonality analysis first, then generate emotional directions.</p>
            </div>
          )}
        </div>

        {/* Apply All Changes Button */}
        {callData?.agent_id && (
          <div className="mt-6 pt-6 border-t border-gray-800">
            <button
              onClick={() => handleApplyChanges(null, callData.agent_id)}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <ExternalLink size={18} />
              Open Agent Flow Builder (Apply All Changes)
            </button>
          </div>
        )}

        {/* Analysis Metadata */}
        <div className="text-xs text-gray-500 mt-4 pt-4 border-t border-gray-800">
          Analyzed at: {new Date(tonalityAnalysis.analyzed_at).toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export default TonalityTab;
