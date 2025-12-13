import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Phone, PhoneOff, Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { agentAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const WebCaller = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [agent, setAgent] = useState(null);
  const [isCallActive, setIsCallActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [callDuration, setCallDuration] = useState(0);
  const [transcript, setTranscript] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Refs for WebSocket and audio
  const deepgramWsRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const processorNodeRef = useRef(null);
  const isCallActiveRef = useRef(false);
  const sessionRef = useRef(null);

  useEffect(() => {
    fetchAgent();
    return () => {
      endCall();
    };
  }, [id]);

  useEffect(() => {
    let interval;
    if (isCallActive) {
      interval = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isCallActive]);

  const fetchAgent = async () => {
    try {
      const response = await agentAPI.get(id);
      setAgent(response.data);
    } catch (error) {
      console.error('Error fetching agent:', error);
      toast({
        title: "Error",
        description: "Failed to load agent",
        variant: "destructive"
      });
    }
  };

  const startCall = async () => {
    try {
      console.log('📞 Starting WebSocket-based call...');
      
      // Create session with backend
      const sessionResponse = await fetch(`${BACKEND_URL}/api/agents/${id}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '' }) // Initial session
      });
      
      if (!sessionResponse.ok) {
        throw new Error('Failed to create session');
      }
      
      const sessionData = await sessionResponse.json();
      sessionRef.current = sessionData.session_id;
      
      setIsCallActive(true);
      isCallActiveRef.current = true;
      
      // Get initial greeting if agent speaks first
      if (sessionData.text) {
        addTranscript('agent', sessionData.text);
        await playAudioResponse(sessionData.text);
      }
      
      // Request microphone access
      console.log('🎤 Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      console.log('✅ Microphone access granted!');
      mediaStreamRef.current = stream;
      
      // Connect to Deepgram WebSocket for real-time transcription
      const wsUrl = `${BACKEND_URL.replace('http', 'ws')}/api/deepgram-live`;
      const ws = new WebSocket(wsUrl);
      deepgramWsRef.current = ws;
      
      ws.onopen = () => {
        console.log('✅ Connected to Deepgram WebSocket');
        
        // Start sending audio stream
        const audioContext = new AudioContext({ sampleRate: 16000 });
        audioContextRef.current = audioContext;
        
        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorNodeRef.current = processor;
        
        source.connect(processor);
        processor.connect(audioContext.destination);
        
        processor.onaudioprocess = (e) => {
          if (ws.readyState === WebSocket.OPEN && !isMuted) {
            const inputData = e.inputBuffer.getChannelData(0);
            // Convert Float32Array to Int16Array for Deepgram
            const int16Data = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              int16Data[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
            }
            ws.send(int16Data.buffer);
          }
        };
      };
      
      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'config') {
          console.log('⚙️ Deepgram config:', data.config);
          return;
        }
        
        // Handle transcription results
        if (data.channel && data.channel.alternatives && data.channel.alternatives[0]) {
          const transcript_text = data.channel.alternatives[0].transcript;
          const is_final = data.is_final;
          const speech_final = data.speech_final;
          
          if (speech_final && transcript_text) {
            console.log('💬 Final transcript:', transcript_text);
            addTranscript('user', transcript_text);
            
            // Get AI response
            await getAIResponse(transcript_text);
          }
        }
      };
      
      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };
      
      ws.onclose = () => {
        console.log('🔌 Deepgram WebSocket closed');
      };
      
      toast({
        title: "Call Active! 🎙️",
        description: "Speak naturally - AI will respond in real-time"
      });
      
    } catch (error) {
      console.error('Error starting call:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to start call",
        variant: "destructive"
      });
    }
  };
  
  const addTranscript = (speaker, text) => {
    setTranscript(prev => [...prev, {
      speaker,
      text,
      timestamp: new Date()
    }]);
  };
  
  const getAIResponse = async (userText) => {
    if (!userText || isProcessing) return;
    
    setIsProcessing(true);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/agents/${id}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          session_id: sessionRef.current
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to get AI response');
      }
      
      const data = await response.json();
      
      if (data.text) {
        addTranscript('agent', data.text);
        await playAudioResponse(data.text);
      }
      
      // Check if call should end
      if (data.should_end_call) {
        console.log('📞 AI requested call end');
        setTimeout(() => endCall(), 2000);
      }
      
    } catch (error) {
      console.error('Error getting AI response:', error);
    } finally {
      setIsProcessing(false);
    }
  };
  
  const playAudioResponse = async (text) => {
    try {
      // Generate TTS audio
      const response = await fetch(`${BACKEND_URL}/api/text-to-speech`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, agent_id: id })
      });
      
      if (!response.ok) {
        console.error('TTS generation failed');
        return;
      }
      
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      
      // Play audio
      const audio = new Audio(audioUrl);
      audio.volume = isSpeakerOn ? 1.0 : 0.0;
      
      await audio.play();
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
      };
      
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  };

  const endCall = () => {
    console.log('📞 Ending call...');
    
    isCallActiveRef.current = false;
    setIsCallActive(false);
    
    // Close WebSocket
    if (deepgramWsRef.current) {
      deepgramWsRef.current.close();
      deepgramWsRef.current = null;
    }
    
    // Stop microphone
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    
    // Stop audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }
    
    setCallDuration(0);
    sessionRef.current = null;
    
    toast({
      title: "Call Ended",
      description: "Call has been terminated"
    });
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    toast({
      title: isMuted ? "Microphone On" : "Microphone Muted",
      description: isMuted ? "You can speak now" : "Your microphone is muted"
    });
  };

  const toggleSpeaker = () => {
    setIsSpeakerOn(!isSpeakerOn);
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900 p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/agents')}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-xl font-bold text-white">{agent?.name || 'Agent'}</h1>
              <p className="text-sm text-gray-400">Web Call Tester</p>
            </div>
          </div>
          <Badge variant={isCallActive ? "default" : "secondary"} className="bg-green-600 text-white">
            {isCallActive ? 'Active' : 'Ready'}
          </Badge>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full p-6">
        {/* Call Controls */}
        <Card className="bg-gray-900 border-gray-800 p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex gap-4">
              {!isCallActive ? (
                <Button
                  size="lg"
                  onClick={startCall}
                  className="bg-green-600 hover:bg-green-700 text-white"
                  disabled={!agent}
                >
                  <Phone className="w-5 h-5 mr-2" />
                  Start Call
                </Button>
              ) : (
                <>
                  <Button
                    size="lg"
                    onClick={endCall}
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    <PhoneOff className="w-5 h-5 mr-2" />
                    End Call
                  </Button>
                  <Button
                    variant={isMuted ? "destructive" : "secondary"}
                    size="lg"
                    onClick={toggleMute}
                  >
                    {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                  </Button>
                  <Button
                    variant={isSpeakerOn ? "secondary" : "destructive"}
                    size="lg"
                    onClick={toggleSpeaker}
                  >
                    {isSpeakerOn ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                  </Button>
                </>
              )}
            </div>
            
            {isCallActive && (
              <div className="text-right">
                <div className="text-2xl font-mono text-white">{formatDuration(callDuration)}</div>
                <div className="text-sm text-gray-400">Duration</div>
              </div>
            )}
          </div>
        </Card>

        {/* Transcript */}
        <Card className="bg-gray-900 border-gray-800 flex-1 p-6 overflow-auto">
          <h2 className="text-lg font-semibold text-white mb-4">Conversation</h2>
          <div className="space-y-4">
            {transcript.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                {isCallActive ? 'Listening...' : 'Start a call to begin conversation'}
              </p>
            ) : (
              transcript.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.speaker === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[70%] p-3 rounded-lg ${
                      msg.speaker === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-100'
                    }`}
                  >
                    <div className="text-xs opacity-70 mb-1">
                      {msg.speaker === 'user' ? 'You' : agent?.name || 'Agent'}
                    </div>
                    <div>{msg.text}</div>
                    <div className="text-xs opacity-50 mt-1">
                      {msg.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default WebCaller;
