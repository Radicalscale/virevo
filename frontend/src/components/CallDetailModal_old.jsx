import React, { useState, useEffect, useRef } from 'react';
import { 
  X, Download, Phone, Clock, User, TrendingUp, AlertCircle, 
  Copy, Trash2, CheckCircle, Headphones, MessageCircle, PhoneOff,
  Timer, ChevronDown, ChevronUp, Volume2, Play, Pause
} from 'lucide-react';

const CallDetailModal = ({ callId, isOpen, onClose }) => {
  const [callData, setCallData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('transcript');
  const [expandedNodes, setExpandedNodes] = useState({});
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const audioRef = useRef(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  useEffect(() => {
    if (isOpen && callId) {
      fetchCallDetails();
    }
  }, [isOpen, callId]);

  const fetchCallDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/api/call-history/${callId}`);
      const data = await response.json();
      setCallData(data);
    } catch (error) {
      console.error('Error fetching call details:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const downloadTranscript = () => {
    if (!callData || !callData.transcript) return;

    const transcriptText = callData.transcript
      .map(msg => {
        // Support both old format (speaker) and new format (role)
        const isUser = msg.role === 'user' || msg.speaker === 'user';
        const label = isUser ? 'User' : 'Agent';
        return `[${msg.timestamp}] ${label}: ${msg.text}`;
      })
      .join('\n\n');

    const fullText = `Call Transcript
================
Call ID: ${callData.call_id}
Date: ${formatDate(callData.start_time)}
Duration: ${formatDuration(callData.duration)}
From: ${callData.from_number}
To: ${callData.to_number}
Status: ${callData.status}

Transcript:
${transcriptText}

Summary:
${callData.summary || 'No summary available'}
`;

    const blob = new Blob([fullText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `call-transcript-${callData.call_id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getSentimentColor = (sentiment) => {
    const colors = {
      positive: 'text-green-400',
      neutral: 'text-gray-400',
      negative: 'text-red-400',
      unknown: 'text-gray-500'
    };
    return colors[sentiment] || 'text-gray-400';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div>
            <h2 className="text-2xl font-bold text-white">Call Details</h2>
            <p className="text-gray-400 text-sm mt-1">
              {callData ? formatDate(callData.start_time) : 'Loading...'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading call details...</div>
            </div>
          ) : callData ? (
            <>
              {/* Call Info Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                    <Phone className="w-4 h-4" />
                    <span>From</span>
                  </div>
                  <div className="text-white font-mono">{callData.from_number || '-'}</div>
                </div>

                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                    <Phone className="w-4 h-4" />
                    <span>To</span>
                  </div>
                  <div className="text-white font-mono">{callData.to_number || '-'}</div>
                </div>

                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                    <Clock className="w-4 h-4" />
                    <span>Duration</span>
                  </div>
                  <div className="text-white font-semibold">{formatDuration(callData.duration)}</div>
                </div>

                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                    <AlertCircle className="w-4 h-4" />
                    <span>Status</span>
                  </div>
                  <div className="text-white capitalize">{callData.status}</div>
                </div>
              </div>

              {/* Conversation Analysis */}
              <div className="bg-gray-800 rounded-lg p-6 mb-6">
                <h3 className="text-lg font-semibold text-white mb-4">Conversation Analysis</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-gray-400 text-sm mb-1">Call Status</div>
                    <div className="text-white capitalize">{callData.status}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-sm mb-1">End Reason</div>
                    <div className="text-white capitalize">{callData.end_reason || 'Unknown'}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-sm mb-1">User Sentiment</div>
                    <div className={`capitalize font-semibold ${getSentimentColor(callData.sentiment)}`}>
                      {callData.sentiment || 'Unknown'}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-sm mb-1">Sentiment Score</div>
                    <div className="text-white">{callData.user_sentiment_score?.toFixed(2) || 'N/A'}</div>
                  </div>
                </div>
              </div>

              {/* Summary */}
              {callData.summary && (
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Summary</h3>
                  <p className="text-gray-300">{callData.summary}</p>
                </div>
              )}

              {/* Call Recording */}
              {callData.recording_url && (
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Call Recording</h3>
                  <div className="space-y-3">
                    <audio 
                      controls 
                      className="w-full"
                      style={{ filter: 'invert(1) hue-rotate(180deg)' }}
                    >
                      <source src={callData.recording_url} type="audio/mpeg" />
                      <source src={callData.recording_url} type="audio/wav" />
                      Your browser does not support the audio element.
                    </audio>
                    <div className="flex items-center gap-4 text-sm text-gray-400">
                      <span>Duration: {formatDuration(callData.recording_duration || callData.duration)}</span>
                      <a 
                        href={callData.recording_url} 
                        download
                        className="text-blue-400 hover:text-blue-300 underline"
                      >
                        Download Recording
                      </a>
                    </div>
                  </div>
                </div>
              )}

              {/* Tabs */}
              <div className="border-b border-gray-800 mb-4">
                <div className="flex gap-6">
                  <button
                    onClick={() => setActiveTab('transcript')}
                    className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
                      activeTab === 'transcript'
                        ? 'border-blue-500 text-blue-500'
                        : 'border-transparent text-gray-400 hover:text-white'
                    }`}
                  >
                    Transcription
                  </button>
                  <button
                    onClick={() => setActiveTab('data')}
                    className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
                      activeTab === 'data'
                        ? 'border-blue-500 text-blue-500'
                        : 'border-transparent text-gray-400 hover:text-white'
                    }`}
                  >
                    Data
                  </button>
                  <button
                    onClick={() => setActiveTab('logs')}
                    className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
                      activeTab === 'logs'
                        ? 'border-blue-500 text-blue-500'
                        : 'border-transparent text-gray-400 hover:text-white'
                    }`}
                  >
                    Detail Logs
                  </button>
                </div>
              </div>

              {/* Tab Content */}
              <div className="min-h-[300px]">
                {activeTab === 'transcript' && (
                  <div className="space-y-4">
                    {callData.transcript && callData.transcript.length > 0 ? (
                      callData.transcript.map((message, index) => {
                        // Support both old format (speaker: user/agent) and new format (role: user/assistant)
                        const isAssistant = message.role === 'assistant' || message.speaker === 'agent';
                        const isUser = message.role === 'user' || message.speaker === 'user';
                        
                        return (
                          <div
                            key={index}
                            className={`flex gap-3 ${
                              isAssistant ? 'flex-row' : 'flex-row-reverse'
                            }`}
                          >
                            <div
                              className={`flex-1 rounded-lg p-4 ${
                                isAssistant
                                  ? 'bg-gray-800 text-gray-100'
                                  : 'bg-blue-600 text-white'
                              }`}
                            >
                              <div className="flex items-center gap-2 mb-2">
                                <User className="w-4 h-4" />
                                <span className="font-semibold text-sm">
                                  {isAssistant ? 'Agent' : 'User'}
                                </span>
                                <span className="text-xs opacity-70 ml-auto">
                                  {new Date(message.timestamp).toLocaleTimeString()}
                                </span>
                              </div>
                              <p className="text-sm">{message.text}</p>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="text-center text-gray-400 py-12">
                        No transcript available
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'data' && (
                  <div className="bg-gray-800 rounded-lg p-6">
                    <h4 className="text-white font-semibold mb-4">Call Metadata</h4>
                    <div className="space-y-3">
                      <div>
                        <div className="text-gray-400 text-sm">Call ID</div>
                        <div className="text-white font-mono text-sm">{callData.call_id}</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-sm">Agent ID</div>
                        <div className="text-white font-mono text-sm">{callData.agent_id}</div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-sm">Direction</div>
                        <div className="text-white capitalize">{callData.direction}</div>
                      </div>
                      {callData.custom_variables && Object.keys(callData.custom_variables).length > 0 && (
                        <div>
                          <div className="text-gray-400 text-sm mb-2">Custom Variables</div>
                          <div className="bg-gray-900 rounded p-3">
                            {Object.entries(callData.custom_variables).map(([key, value]) => (
                              <div key={key} className="flex justify-between text-sm mb-1">
                                <span className="text-gray-400">{key}:</span>
                                <span className="text-white">{value}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === 'logs' && (
                  <div className="bg-gray-800 rounded-lg p-6">
                    <div className="space-y-2 font-mono text-xs">
                      <div className="text-gray-400">
                        <span className="text-gray-500">[{formatDate(callData.start_time)}]</span>
                        <span className="text-blue-400"> INFO:</span> Call initiated
                      </div>
                      {callData.answered_at && (
                        <div className="text-gray-400">
                          <span className="text-gray-500">[{formatDate(callData.answered_at)}]</span>
                          <span className="text-green-400"> INFO:</span> Call answered
                        </div>
                      )}
                      {callData.end_time && (
                        <div className="text-gray-400">
                          <span className="text-gray-500">[{formatDate(callData.end_time)}]</span>
                          <span className="text-yellow-400"> INFO:</span> Call ended - {callData.end_reason || 'unknown'}
                        </div>
                      )}
                      {callData.error_message && (
                        <div className="text-gray-400">
                          <span className="text-red-400"> ERROR:</span> {callData.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-center text-gray-400 py-12">
              Call details not found
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-800">
          <button
            onClick={downloadTranscript}
            disabled={!callData || !callData.transcript || callData.transcript.length === 0}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-4 py-2 rounded font-medium transition-colors"
          >
            <Download className="w-4 h-4" />
            Download Transcript
          </button>
          <button
            onClick={onClose}
            className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-2 rounded font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default CallDetailModal;
