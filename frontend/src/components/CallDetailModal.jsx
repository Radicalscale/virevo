import React, { useState, useEffect, useRef } from 'react';
import {
  X, Download, Phone, Clock, User, TrendingUp, AlertCircle,
  Copy, Trash2, CheckCircle, Headphones, MessageCircle, PhoneOff,
  Timer, ChevronDown, ChevronUp, Volume2, Play, Pause
} from 'lucide-react';
import { analyticsAPI } from '../services/api';

const CallDetailModal = ({ callId, isOpen, onClose }) => {
  const [callData, setCallData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('transcript');
  const [expandedNodes, setExpandedNodes] = useState({});
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [copied, setCopied] = useState('');
  const [recordingUrl, setRecordingUrl] = useState(null);
  const audioRef = useRef(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  useEffect(() => {
    if (isOpen && callId) {
      fetchCallDetails();
      setActiveTab('transcript');
      setExpandedNodes({});
    }
  }, [isOpen, callId]);

  // Load recording URL with cache-busting on each mount
  useEffect(() => {
    if (callData?.recording_url) {
      // Add timestamp to prevent caching issues
      const url = callData.recording_url;
      const separator = url.includes('?') ? '&' : '?';
      const freshUrl = `${url}${separator}_t=${Date.now()}`;
      setRecordingUrl(freshUrl);
    }
  }, [callData]);

  const fetchCallDetails = async () => {
    try {
      setLoading(true);
      const response = await analyticsAPI.callDetail(callId);
      const data = response.data;

      // If call has a recording_id, use our backend endpoint to serve it
      // Add cache-busting timestamp
      if (data.recording_id) {
        data.recording_url = `${backendUrl}/api/call-history/${callId}/recording?_t=${Date.now()}`;
        console.log('✅ Using on-demand recording download');
      } else if (data.recording_url) {
        // Add cache-busting to existing recording URL
        const url = data.recording_url;
        const separator = url.includes('?') ? '&' : '?';
        data.recording_url = `${url}${separator}_t=${Date.now()}`;
      }

      setCallData(data);
    } catch (error) {
      console.error('Error fetching call details:', error);
    } finally {
      setLoading(false);
    }
  };

  // Audio controls
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [callData]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio || !callData?.recording_url) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().catch(err => {
        console.error('Audio play failed:', err);
      });
      setIsPlaying(true);
    }
  };

  const handleSeek = (e) => {
    e.stopPropagation();
    const audio = audioRef.current;
    if (!audio || !callData?.recording_url || !duration || isNaN(duration)) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, x / rect.width));
    const newTime = percentage * duration;

    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const seekToTime = (seconds) => {
    const audio = audioRef.current;
    if (!audio || !callData?.recording_url || !duration || isNaN(duration)) return;

    const newTime = Math.max(0, Math.min(duration, seconds));
    audio.currentTime = newTime;
    setCurrentTime(newTime);

    if (!isPlaying) {
      audio.play().catch(err => {
        console.warn('Audio play failed:', err);
      });
      setIsPlaying(true);
    }
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      timeZone: 'America/New_York',
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '0:00';
    const date = new Date(timestamp);
    const callStart = callData?.start_time ? new Date(callData.start_time) : date;
    const secondsFromStart = Math.floor((date - callStart) / 1000);
    return formatDuration(secondsFromStart);
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(''), 2000);
  };

  const toggleNodeExpansion = (index) => {
    setExpandedNodes(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const downloadTranscript = () => {
    if (!callData || !callData.transcript) return;

    const transcriptText = callData.transcript
      .map(msg => {
        const isUser = msg.role === 'user' || msg.speaker === 'user';
        const label = isUser ? 'User' : 'Agent';
        return `[${msg.timestamp}] ${label}: ${msg.text}`;
      })
      .join('\n\n');

    const blob = new Blob([transcriptText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `call-transcript-${callId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadLogs = () => {
    if (!callData?.logs) return;

    // Build comprehensive log output
    let logOutput = '='.repeat(80) + '\n';
    logOutput += 'DETAILED CALL LOG REPORT\n';
    logOutput += '='.repeat(80) + '\n\n';

    // Call metadata
    logOutput += '📞 CALL INFORMATION\n';
    logOutput += '-'.repeat(80) + '\n';
    logOutput += `Call ID: ${callId}\n`;
    logOutput += `Duration: ${Math.floor(callData.duration / 60)}m ${callData.duration % 60}s\n`;
    logOutput += `Sentiment: ${callData.sentiment || 'N/A'}\n`;
    logOutput += `Date: ${new Date(callData.created_at).toLocaleString()}\n`;
    logOutput += '\n';

    // Latency logs
    logOutput += '⏱️  LATENCY LOGS\n';
    logOutput += '-'.repeat(80) + '\n';
    const logsText = callData.logs
      .map(log => `[${log.timestamp}] ${log.level?.toUpperCase() || 'INFO'}: ${log.message}`)
      .join('\n');
    logOutput += logsText + '\n\n';

    // Full call_log structure (if available)
    if (callData.call_log && Object.keys(callData.call_log).length > 0) {
      logOutput += '🔍 DETAILED CALL LOG (JSON)\n';
      logOutput += '-'.repeat(80) + '\n';
      logOutput += JSON.stringify(callData.call_log, null, 2) + '\n\n';
    }

    // Transcript (if available)
    if (callData.transcript && callData.transcript.length > 0) {
      logOutput += '💬 CONVERSATION TRANSCRIPT\n';
      logOutput += '-'.repeat(80) + '\n';
      callData.transcript.forEach((turn, idx) => {
        logOutput += `[${idx + 1}] ${turn.role === 'user' ? 'USER' : 'AGENT'}: ${turn.content}\n`;
      });
      logOutput += '\n';
    }

    logOutput += '='.repeat(80) + '\n';
    logOutput += 'END OF REPORT\n';
    logOutput += '='.repeat(80) + '\n';

    const blob = new Blob([logOutput], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `call-logs-${callId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-5xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex-1">
            <div className="flex items-center gap-4 mb-2">
              <h2 className="text-xl font-bold text-white">Call Details</h2>
              {callData?.start_time && (
                <span className="text-sm text-gray-400">
                  {formatDate(callData.start_time)} phone_call
                </span>
              )}
            </div>

            {/* Agent & Version Info */}
            {callData?.agent_name && (
              <div className="flex items-center gap-2 text-sm text-gray-300 mb-1">
                <span>Agent: {callData.agent_name}</span>
                {callData.agent_id && (
                  <>
                    <span className="text-gray-600">|</span>
                    <span className="font-mono text-xs">(agent_{callData.agent_id?.substring(0, 8)}...)</span>
                    <button
                      onClick={() => copyToClipboard(callData.agent_id, 'agent')}
                      className="text-gray-400 hover:text-white"
                      title="Copy Agent ID"
                    >
                      {copied === 'agent' ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </>
                )}
                <span className="text-gray-600">|</span>
                <span className="text-gray-400">Version: {callData?.version || 0}</span>
              </div>
            )}

            {/* Call ID */}
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span>Call ID:</span>
              <span className="font-mono text-xs">{callId?.substring(0, 30)}...</span>
              <button
                onClick={() => copyToClipboard(callId, 'call')}
                className="text-gray-400 hover:text-white"
                title="Copy Call ID"
              >
                {copied === 'call' ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-2"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center text-gray-400 py-12">Loading...</div>
          ) : (
            <>
              {/* Call Metadata */}
              <div className="bg-gray-800 rounded-lg p-4 mb-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Phone Call:</span>
                    <div className="text-white font-mono">
                      {callData?.from_number || '-'} → {callData?.to_number || '-'}
                      <span className="ml-2 text-blue-400">({callData?.direction || 'Unknown'})</span>
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-400">Duration:</span>
                    <div className="text-white">
                      {callData?.start_time && callData?.end_time ? (
                        <>
                          {formatDate(callData.start_time)} - {formatDate(callData.end_time)}
                        </>
                      ) : (
                        formatDuration(callData?.duration || 0)
                      )}
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-400">Cost:</span>
                    <div className="text-white">${(callData?.cost || 0).toFixed(3)}</div>
                  </div>
                  <div>
                    <span className="text-gray-400">LLM Token:</span>
                    <div className="text-white">{(callData?.llm_tokens || 0).toFixed(2)}</div>
                  </div>
                </div>
              </div>

              {/* Audio Recording */}
              {(recordingUrl || callData?.recording_url) && (
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Call Recording</h3>

                  <audio
                    key={recordingUrl}
                    ref={audioRef}
                    src={recordingUrl || callData?.recording_url}
                    preload="metadata"
                    style={{ display: 'none' }}
                  />

                  {/* Custom Audio Controls */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={togglePlay}
                        className="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-full"
                      >
                        {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                      </button>

                      <div className="flex-1">
                        <div
                          className="bg-gray-700 h-3 rounded-full cursor-pointer relative group"
                          onClick={handleSeek}
                          style={{ minHeight: '12px' }}
                        >
                          <div
                            className="bg-blue-500 h-3 rounded-full pointer-events-none"
                            style={{ width: `${(currentTime / duration) * 100 || 0}%` }}
                          />
                          {/* Scrubber handle for better UX */}
                          <div
                            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
                            style={{ left: `calc(${(currentTime / duration) * 100 || 0}% - 8px)` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-gray-400 mt-1">
                          <span>{formatDuration(currentTime)}</span>
                          <span>{formatDuration(duration)}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Volume2 className="w-4 h-4 text-gray-400" />
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={volume}
                          onChange={handleVolumeChange}
                          className="w-20"
                        />
                      </div>

                      <a
                        href={recordingUrl || callData?.recording_url}
                        download
                        className="text-blue-400 hover:text-blue-300 p-2"
                      >
                        <Download className="w-5 h-5" />
                      </a>
                    </div>
                  </div>
                </div>
              )}

              {/* Conversation Analysis */}
              <div className="bg-gray-800 rounded-lg p-6 mb-6">
                <h3 className="text-lg font-semibold text-white mb-4">Conversation Analysis</h3>
                <div className="grid grid-cols-2 gap-4">
                  {/* Call Successful */}
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-gray-400" />
                    <div>
                      <div className="text-sm text-gray-400">Call Successful</div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        <span className="text-white">{callData?.call_successful ? 'Successful' : 'Failed'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Call Status */}
                  <div className="flex items-center gap-3">
                    <Headphones className="w-5 h-5 text-gray-400" />
                    <div>
                      <div className="text-sm text-gray-400">Call Status</div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-gray-500"></span>
                        <span className="text-white capitalize">{callData?.status || 'Ended'}</span>
                      </div>
                    </div>
                  </div>

                  {/* User Sentiment */}
                  <div className="flex items-center gap-3">
                    <MessageCircle className="w-5 h-5 text-gray-400" />
                    <div>
                      <div className="text-sm text-gray-400">User Sentiment</div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        <span className="text-white">{callData?.sentiment || 'Positive'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Disconnection Reason */}
                  <div className="flex items-center gap-3">
                    <PhoneOff className="w-5 h-5 text-gray-400" />
                    <div>
                      <div className="text-sm text-gray-400">Disconnection Reason</div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        <span className="text-white">{callData?.disconnect_reason || 'User_hangup'}</span>
                      </div>
                    </div>
                  </div>

                  {/* End to End Latency */}
                  <div className="flex items-center gap-3">
                    <Timer className="w-5 h-5 text-gray-400" />
                    <div>
                      <div className="text-sm text-gray-400">End to End Latency</div>
                      <div className="flex items-center gap-2">
                        <span className="text-white">{callData?.e2e_latency || '-'}ms</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Summary */}
              {callData?.summary && (
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Summary</h3>
                  <p className="text-gray-300">{callData.summary}</p>
                </div>
              )}

              {/* Tabs */}
              <div className="border-b border-gray-700 mb-6">
                <div className="flex gap-6">
                  <button
                    onClick={() => setActiveTab('transcript')}
                    className={`pb-3 border-b-2 transition-colors ${activeTab === 'transcript'
                        ? 'border-blue-500 text-white'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                      }`}
                  >
                    Transcription
                  </button>
                  <button
                    onClick={() => setActiveTab('data')}
                    className={`pb-3 border-b-2 transition-colors ${activeTab === 'data'
                        ? 'border-blue-500 text-white'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                      }`}
                  >
                    Data
                  </button>
                  <button
                    onClick={() => setActiveTab('logs')}
                    className={`pb-3 border-b-2 transition-colors ${activeTab === 'logs'
                        ? 'border-blue-500 text-white'
                        : 'border-transparent text-gray-400 hover:text-gray-300'
                      }`}
                  >
                    Detail Logs
                  </button>

                  {/* Download button for current tab */}
                  <button
                    onClick={activeTab === 'transcript' ? downloadTranscript : downloadLogs}
                    className="ml-auto text-gray-400 hover:text-white"
                    title={`Download ${activeTab === 'transcript' ? 'Transcript' : 'Logs'}`}
                  >
                    <Download className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Tab Content */}
              {activeTab === 'transcript' && (
                <div className="space-y-4">
                  {callData?.transcript && callData.transcript.length > 0 ? (
                    callData.transcript.map((message, index) => {
                      const isAssistant = message.role === 'assistant' || message.speaker === 'agent';
                      const timestamp = formatTimestamp(message.timestamp);
                      const timestampSeconds = timestamp.split(':').reduce((acc, time) => (60 * acc) + +time, 0);

                      return (
                        <div key={index}>
                          <div
                            className={`flex gap-3 ${isAssistant ? 'flex-row' : 'flex-row-reverse'
                              }`}
                          >
                            <div
                              className={`flex-1 rounded-lg p-4 ${isAssistant
                                  ? 'bg-gray-800 text-gray-100'
                                  : 'bg-blue-600 text-white'
                                }`}
                            >
                              <div className="flex items-center gap-2 mb-2">
                                <User className="w-4 h-4" />
                                <span className="font-semibold text-sm">
                                  {isAssistant ? 'Agent' : 'User'}
                                </span>
                                <button
                                  onClick={() => seekToTime(timestampSeconds)}
                                  className="text-xs opacity-70 ml-auto hover:opacity-100 underline"
                                  title="Jump to this point in recording"
                                >
                                  {timestamp}
                                </button>
                              </div>
                              <p className="text-sm">{message.text}</p>
                            </div>
                          </div>

                          {/* Node Transition (if exists) */}
                          {message.node_transition && (
                            <div className="ml-4 mt-2 mb-4">
                              <button
                                onClick={() => toggleNodeExpansion(index)}
                                className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-300"
                              >
                                {expandedNodes[index] ? (
                                  <ChevronUp className="w-4 h-4" />
                                ) : (
                                  <ChevronDown className="w-4 h-4" />
                                )}
                                <span>Node Transition</span>
                              </button>

                              {expandedNodes[index] && (
                                <div className="mt-2 ml-6 p-3 bg-gray-800 rounded text-sm text-gray-300">
                                  <div>previous node: {message.node_transition.previous_node}</div>
                                  <div>new node: {message.node_transition.new_node}</div>
                                </div>
                              )}
                            </div>
                          )}
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
                  <h3 className="text-lg font-semibold text-white mb-4">Call Metadata</h3>
                  <div className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <span className="text-gray-400">Call ID:</span>
                        <div className="text-white font-mono text-xs break-all">{callData?.call_id}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Agent ID:</span>
                        <div className="text-white font-mono text-xs break-all">{callData?.agent_id || '-'}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Direction:</span>
                        <div className="text-white">{callData?.direction || '-'}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Status:</span>
                        <div className="text-white">{callData?.status || '-'}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">From:</span>
                        <div className="text-white">{callData?.from_number || '-'}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">To:</span>
                        <div className="text-white">{callData?.to_number || '-'}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Duration:</span>
                        <div className="text-white">{formatDuration(callData?.duration)}</div>
                      </div>
                      <div>
                        <span className="text-gray-400">Cost:</span>
                        <div className="text-white">${(callData?.cost || 0).toFixed(3)}</div>
                      </div>
                    </div>

                    {callData?.metadata && Object.keys(callData.metadata).length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-white font-semibold mb-2">Additional Metadata</h4>
                        <pre className="bg-gray-900 p-3 rounded text-xs overflow-auto max-h-60">
                          {JSON.stringify(callData.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'logs' && (
                <div className="bg-gray-800 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Detail Logs</h3>
                  <div className="space-y-2 font-mono text-xs">
                    {callData?.logs && callData.logs.length > 0 ? (
                      <div className="max-h-96 overflow-y-auto">
                        {callData.logs.map((log, index) => (
                          <div
                            key={index}
                            className={`py-1 ${log.level === 'error' ? 'text-red-400' :
                                log.level === 'warning' ? 'text-yellow-400' :
                                  'text-gray-300'
                              }`}
                          >
                            <span className="text-gray-500">[{log.timestamp}]</span>{' '}
                            <span className={log.level === 'error' ? 'text-red-400' : 'text-gray-400'}>
                              {log.level?.toUpperCase() || 'INFO'}:
                            </span>{' '}
                            {log.message}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center text-gray-400 py-12">
                        No logs available
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default CallDetailModal;
