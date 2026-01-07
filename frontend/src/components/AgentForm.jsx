import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Save, Upload, Link as LinkIcon, Trash2, FileText, ExternalLink, Info } from 'lucide-react';
import { agentAPI, kbAPI } from '../services/api';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { useToast } from '../hooks/use-toast';
import AutoQCSettings from './AutoQCSettings';

const AgentForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const { toast } = useToast();
  const isNew = !id;  // No ID means we're creating a new agent
  const isEdit = !!id;  // Has ID means we're editing

  const [loading, setLoading] = useState(isEdit);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    voice: 'Rachel',
    language: 'English',
    model: 'gpt-4-turbo',
    agent_type: 'single_prompt',
    system_prompt: '',
    settings: {}
  });

  // Knowledge Base state
  const [kbItems, setKbItems] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [addingUrl, setAddingUrl] = useState(false);
  const [urlInput, setUrlInput] = useState('');

  useEffect(() => {
    if (isEdit) {
      fetchAgent();
      fetchKbItems();
    } else {
      setLoading(false);
    }
  }, [id]);

  const fetchAgent = async () => {
    try {
      const response = await agentAPI.get(id);
      console.log('🔍 Agent data loaded:', response.data);
      console.log('🔍 Settings from API:', response.data.settings);
      console.log('🔍 Webhook URL:', response.data.settings?.call_started_webhook_url);
      console.log('🔍 Webhook Active:', response.data.settings?.call_started_webhook_active);
      console.log('🔍 Post-Call Webhook URL:', response.data.settings?.post_call_webhook_url);
      console.log('🔍 Post-Call Webhook Active:', response.data.settings?.post_call_webhook_active);
      setFormData(response.data);
    } catch (error) {
      console.error('Error fetching agent:', error);
      toast({
        title: "Error",
        description: "Failed to load agent",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch KB items for this agent
  const fetchKbItems = async () => {
    if (!id) return;

    try {
      setKbLoading(true);
      const response = await kbAPI.list(id);
      setKbItems(response.data);
    } catch (error) {
      console.error('Error fetching KB items:', error);
    } finally {
      setKbLoading(false);
    }
  };

  // Handle file upload
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !id) return;

    // Check file type
    const validExtensions = ['pdf', 'txt', 'docx'];
    const fileExt = file.name.split('.').pop().toLowerCase();
    if (!validExtensions.includes(fileExt)) {
      toast({
        title: "Invalid file type",
        description: "Only PDF, TXT, and DOCX files are supported",
        variant: "destructive"
      });
      return;
    }

    try {
      setUploadingFile(true);
      const formData = new FormData();
      formData.append('file', file);

      await kbAPI.upload(id, formData);
      toast({
        title: "Success",
        description: `File "${file.name}" uploaded successfully`
      });
      fetchKbItems();
    } catch (error) {
      console.error('Error uploading file:', error);
      toast({
        title: "Error",
        description: "Failed to upload file",
        variant: "destructive"
      });
    } finally {
      setUploadingFile(false);
      e.target.value = ''; // Reset input
    }
  };

  // Handle URL addition
  const handleAddUrl = async () => {
    if (!urlInput.trim() || !id) return;

    try {
      setAddingUrl(true);
      await kbAPI.addUrl(id, urlInput);
      toast({
        title: "Success",
        description: "Website content added successfully"
      });
      setUrlInput('');
      fetchKbItems();
    } catch (error) {
      console.error('Error adding URL:', error);
      toast({
        title: "Error",
        description: "Failed to add URL",
        variant: "destructive"
      });
    } finally {
      setAddingUrl(false);
    }
  };

  // Handle KB item deletion
  const handleDeleteKbItem = async (kbId) => {
    if (!id) return;

    try {
      await kbAPI.delete(id, kbId);
      toast({
        title: "Success",
        description: "Knowledge base item deleted"
      });
      fetchKbItems();
    } catch (error) {
      console.error('Error deleting KB item:', error);
      toast({
        title: "Error",
        description: "Failed to delete item",
        variant: "destructive"
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    // Debug: Log what we're about to save
    console.log('💾 Saving agent - formData:', formData);
    console.log('💾 Settings being saved:', formData.settings);
    console.log('💾 Webhook URL being saved:', formData.settings?.call_started_webhook_url);
    console.log('💾 Webhook Active being saved:', formData.settings?.call_started_webhook_active);

    try {
      if (isEdit) {
        await agentAPI.update(id, formData);
        toast({
          title: "Success",
          description: "Agent updated successfully"
        });
      } else {
        await agentAPI.create(formData);
        toast({
          title: "Success",
          description: "Agent created successfully"
        });
      }
      navigate('/agents');
    } catch (error) {
      console.error('Error saving agent:', error);
      toast({
        title: "Error",
        description: `Failed to ${isEdit ? 'update' : 'create'} agent`,
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading && isEdit) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="text-white text-xl">Loading agent...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center gap-4 mb-8">
        <Button
          onClick={() => navigate('/agents')}
          variant="ghost"
          className="text-gray-400 hover:text-white"
        >
          <ArrowLeft size={20} />
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">
            {isNew ? 'Create New Agent' : 'Edit Agent'}
          </h1>
          <p className="text-gray-400">Configure your AI voice agent settings</p>
        </div>
      </div>

      <Card className="bg-gray-800 border-gray-700 p-6 max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Agent Type Selection - Only show for new agents */}
          {isNew && (
            <div className="border-b border-gray-700 pb-6">
              <Label className="text-gray-300 text-lg font-semibold">Agent Type</Label>
              <p className="text-sm text-gray-400 mt-1 mb-4">
                Choose how you want to configure your agent
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div
                  onClick={() => setFormData({ ...formData, agent_type: 'single_prompt' })}
                  className={`cursor-pointer p-4 rounded-lg border-2 transition-all ${formData.agent_type === 'single_prompt'
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-gray-700 hover:border-gray-600'
                    }`}
                >
                  <h3 className="font-semibold text-white mb-2">📝 Single Prompt</h3>
                  <p className="text-sm text-gray-400">
                    One system prompt for the entire conversation. Simple and straightforward.
                  </p>
                </div>
                <div
                  onClick={() => setFormData({ ...formData, agent_type: 'call_flow' })}
                  className={`cursor-pointer p-4 rounded-lg border-2 transition-all ${formData.agent_type === 'call_flow'
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-gray-700 hover:border-gray-600'
                    }`}
                >
                  <h3 className="font-semibold text-white mb-2">🔀 Call Flow</h3>
                  <p className="text-sm text-gray-400">
                    Multi-node conversation flow with branches and conditions. Advanced.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Show agent type for editing */}
          {isEdit && (
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 mb-4">
              <p className="text-sm text-gray-400">
                Agent Type: <span className="text-white font-semibold">
                  {formData.agent_type === 'single_prompt' ? '📝 Single Prompt' : '🔀 Call Flow'}
                </span>
              </p>
            </div>
          )}

          <div>
            <Label htmlFor="name" className="text-gray-300">Agent Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Customer Support Agent"
              className="bg-gray-900 border-gray-700 text-white mt-2"
              required
            />
          </div>

          <div>
            <Label htmlFor="description" className="text-gray-300">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe what this agent does..."
              className="bg-gray-900 border-gray-700 text-white mt-2"
              rows={3}
              required
            />
          </div>

          {/* System Prompt - Only for single_prompt agents */}
          {/* Global Prompt / System Prompt - Available for BOTH agent types */}
          <div>
            <Label htmlFor="system_prompt" className="text-gray-300">
              {formData.agent_type === 'call_flow' ? 'Global Prompt' : 'System Prompt'}
              <span className="text-gray-500 text-xs ml-2">
                {formData.agent_type === 'call_flow'
                  ? '(Universal personality and behavior across all nodes)'
                  : '(Main instructions for the AI agent)'}
              </span>
            </Label>
            <Textarea
              id="system_prompt"
              value={formData.system_prompt}
              onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
              placeholder={formData.agent_type === 'call_flow'
                ? "# WHO YOU ARE\nYou are [name], a [role] who [purpose]...\n\n# YOUR PERSONALITY\n- [trait 1]\n- [trait 2]\n\n# COMMUNICATION STYLE\n- [style 1]\n- [style 2]\n\n# RECOVERY STRATEGY\nWhen user is confused: [approach]"
                : "You are a helpful AI assistant that..."}
              className="bg-gray-900 border-gray-700 text-white mt-2"
              rows={formData.agent_type === 'call_flow' ? 8 : 5}
              required={formData.agent_type === 'single_prompt'}
            />
            <p className="text-xs text-gray-500 mt-1">
              {formData.agent_type === 'call_flow'
                ? 'Define your agent\'s universal personality, tone, and recovery strategies. This applies across ALL nodes and helps handle unexpected responses naturally.'
                : 'This is the core personality and instructions for your agent.'}
            </p>
          </div>


          {/* Call Flow Editor Button - Only for call_flow agents */}
          {formData.agent_type === 'call_flow' && (
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
              <p className="text-white font-semibold mb-2">🔀 Call Flow Configuration</p>
              <p className="text-sm text-gray-400 mb-3">
                After saving this agent, you'll be able to build your conversation flow with multiple nodes and branches.
              </p>
              {isEdit && (
                <Button
                  type="button"
                  onClick={() => navigate(`/agents/${id}/flow`)}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  Open Flow Builder
                </Button>
              )}
            </div>
          )}

          {/* Advanced Settings Section - Collapsible */}
          <details className="border border-gray-700 rounded-lg bg-gray-900" open>
            <summary className="cursor-pointer p-4 font-semibold text-white hover:bg-gray-800">
              ⚙️ Advanced Settings (LLM, Voice & TTS Providers)
            </summary>
            <div className="p-4 border-t border-gray-700 space-y-6">

              {/* LLM Provider Selection */}
              <div>
                <Label className="text-gray-300 font-semibold">LLM Provider</Label>
                <Select
                  value={formData.settings?.llm_provider || 'openai'}
                  onValueChange={(value) => {
                    // Reset model when provider changes
                    const defaultModel = value === 'grok' ? 'grok-3' : value === 'gemini' ? 'gemini-3-flash-preview' : 'gpt-4-turbo';
                    setFormData({
                      ...formData,
                      model: defaultModel,
                      settings: { ...formData.settings, llm_provider: value }
                    });
                  }}
                >
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-700">
                    <SelectItem value="openai">OpenAI (GPT)</SelectItem>
                    <SelectItem value="grok">Grok (xAI)</SelectItem>
                    <SelectItem value="gemini">Gemini (Google)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">Choose your AI provider</p>
              </div>

              {/* Model Selection - Dynamic based on provider */}
              <div>
                <Label className="text-gray-300 font-semibold">Model</Label>
                <Select
                  value={formData.model || 'gpt-4-turbo'}
                  onValueChange={(value) => setFormData({ ...formData, model: value })}
                >
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-700">
                    {(formData.settings?.llm_provider === 'grok') ? (
                      <>
                        <SelectItem value="grok-4-1-fast-non-reasoning">Grok 4.1 Fast Non-Reasoning (Latest & Fastest)</SelectItem>
                        <SelectItem value="grok-4-fast-non-reasoning">Grok 4 Fast Non-Reasoning</SelectItem>
                        <SelectItem value="grok-4-fast-reasoning">Grok 4 Fast Reasoning (Deeper Analysis)</SelectItem>
                        <SelectItem value="grok-3">Grok 3</SelectItem>
                        <SelectItem value="grok-2-1212">Grok 2 (Dec 2024)</SelectItem>
                        <SelectItem value="grok-beta">Grok Beta</SelectItem>
                      </>
                    ) : (formData.settings?.llm_provider === 'gemini') ? (
                      <>
                        <SelectItem value="gemini-3-flash-preview">Gemini 3.0 Flash Preview (Fastest)</SelectItem>
                        <SelectItem value="gemini-3-pro-preview">Gemini 3.0 Pro Preview (Most Capable)</SelectItem>
                      </>
                    ) : (
                      <>
                        <SelectItem value="gpt-4.1-2025-04-14">GPT-4.1 (Latest)</SelectItem>
                        <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                        <SelectItem value="gpt-4">GPT-4</SelectItem>
                        <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">
                  {(formData.settings?.llm_provider === 'grok') ? 'Grok model for conversation' :
                    (formData.settings?.llm_provider === 'gemini') ? 'Gemini model for conversation' :
                      'OpenAI model for conversation'}
                </p>
              </div>

              {/* LLM Temperature Slider */}
              <div>
                <Label className="text-gray-300 font-semibold">
                  Temperature: {formData.settings?.temperature?.toFixed(1) || '0.7'}
                </Label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={formData.settings?.temperature || 0.7}
                  onChange={(e) => setFormData({
                    ...formData,
                    settings: {
                      ...formData.settings,
                      temperature: parseFloat(e.target.value)
                    }
                  })}
                  className="w-full mt-2 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0 (Deterministic)</span>
                  <span>1 (Balanced)</span>
                  <span>2 (Creative)</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Lower values produce more consistent, focused responses. Higher values increase creativity and variability.
                </p>
              </div>

              <div className="border-t border-gray-600 my-4"></div>

              {/* TTS Provider Selection */}
              <div>
                <Label className="text-gray-300 font-semibold">TTS Provider (Optional Override)</Label>
                <Select
                  value={formData.settings?.tts_provider || 'cartesia'}
                  onValueChange={(value) => setFormData({
                    ...formData,
                    settings: { ...formData.settings, tts_provider: value }
                  })}
                >
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-700">
                    <SelectItem value="cartesia">Cartesia Sonic - Ultra-Fast (Default)</SelectItem>
                    <SelectItem value="elevenlabs">ElevenLabs - High Quality</SelectItem>
                    <SelectItem value="hume">Hume AI - Emotional</SelectItem>
                    {/* <SelectItem value="chattts">ChatTTS - Ultra-Fast Conversational</SelectItem> */}
                    {/* <SelectItem value="dia">Dia TTS - Ultra-Realistic</SelectItem> */}
                    {/* <SelectItem value="melo">MeloTTS - Fast & Free (GPU)</SelectItem> */}
                    {/* <SelectItem value="sesame">Sesame TTS - Custom (RunPod)</SelectItem> */}
                    <SelectItem value="maya">Maya - Adaptive Voice (RunPod)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">
                  {formData.settings?.tts_provider === 'cartesia'
                    ? 'Cartesia Sonic: Ultra-low latency (40-90ms TTFB), best for real-time conversations'
                    : formData.settings?.tts_provider === 'maya'
                      ? 'Maya: Adapts voice style/emotion based on description. High quality, requires GPU.'
                      : formData.settings?.tts_provider === 'hume'
                        ? 'Hume AI: Alternative for emotional voice synthesis'
                        : 'ElevenLabs: High-quality TTS with natural voices'}
                </p>
              </div>

              {/* Comfort Noise Toggle */}
              <div className="flex items-center justify-between py-3 px-4 bg-gray-800/50 rounded-lg border border-gray-700">
                <div className="flex-1">
                  <Label className="text-gray-300 font-semibold">Enable Comfort Noise</Label>
                  <p className="text-xs text-gray-500 mt-1">
                    Mix subtle background noise into TTS audio for a more natural phone-like experience
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={formData.settings?.enable_comfort_noise || false}
                  onChange={(e) => setFormData({
                    ...formData,
                    settings: {
                      ...formData.settings,
                      enable_comfort_noise: e.target.checked
                    }
                  })}
                  className="w-5 h-5 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                />
              </div>

              <div className="border-t border-gray-600 my-4"></div>

              {/* STT Provider Selection */}
              <div>
                <Label className="text-gray-300 font-semibold">STT Provider (Speech-to-Text)</Label>
                <Select
                  value={formData.settings?.stt_provider || 'deepgram'}
                  onValueChange={(value) => setFormData({
                    ...formData,
                    settings: { ...formData.settings, stt_provider: value }
                  })}
                >
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-700">
                    <SelectItem value="deepgram">Deepgram Nova-3</SelectItem>
                    <SelectItem value="assemblyai">AssemblyAI Universal</SelectItem>
                    <SelectItem value="soniox">Soniox Real-Time</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">
                  {formData.settings?.stt_provider === 'assemblyai'
                    ? 'AssemblyAI with Turn Detection for natural conversations'
                    : formData.settings?.stt_provider === 'soniox'
                      ? 'Soniox with advanced endpoint detection - Zero latency (native mulaw support)'
                      : 'Deepgram for real-time transcription'}
                </p>
              </div>

              {/* Deepgram Settings */}
              {formData.settings?.stt_provider === 'deepgram' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <Label className="text-gray-300 font-semibold block">Deepgram (STT) Settings</Label>

                  <div>
                    <Label className="text-gray-400 text-sm">Endpointing (ms)</Label>
                    <Input
                      type="number"
                      value={formData.settings?.deepgram_settings?.endpointing || 500}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          deepgram_settings: {
                            ...formData.settings?.deepgram_settings,
                            endpointing: parseInt(e.target.value)
                          }
                        }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">Silence duration before speech ends (200ms=responsive, 2000ms=patient)</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.settings?.deepgram_settings?.interim_results ?? false}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          deepgram_settings: {
                            ...formData.settings?.deepgram_settings,
                            interim_results: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    <Label className="text-gray-400 text-sm">Interim Results</Label>
                    <p className="text-xs text-gray-500">Receive partial transcripts as user speaks</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.settings?.deepgram_settings?.punctuate ?? true}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          deepgram_settings: {
                            ...formData.settings?.deepgram_settings,
                            punctuate: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    <Label className="text-gray-400 text-sm">Punctuate</Label>
                    <p className="text-xs text-gray-500">Add punctuation to transcripts</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.settings?.deepgram_settings?.smart_format ?? true}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          deepgram_settings: {
                            ...formData.settings?.deepgram_settings,
                            smart_format: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    <Label className="text-gray-400 text-sm">Smart Format</Label>
                    <p className="text-xs text-gray-500">Format numbers, dates, currency intelligently</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.settings?.deepgram_settings?.vad_events ?? true}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          deepgram_settings: {
                            ...formData.settings?.deepgram_settings,
                            vad_events: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    <Label className="text-gray-400 text-sm">VAD Events</Label>
                    <p className="text-xs text-gray-500">Voice activity detection events</p>
                  </div>
                </div>
              )}

              {/* AssemblyAI Settings */}
              {formData.settings?.stt_provider === 'assemblyai' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <Label className="text-gray-300 font-semibold block">AssemblyAI Settings</Label>

                  <div>
                    <Label className="text-gray-400 text-sm">Turn Detection Threshold (0.0-1.0)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      min="0"
                      max="1"
                      value={formData.settings?.assemblyai_settings?.threshold || 0.0}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          assemblyai_settings: {
                            ...formData.settings?.assemblyai_settings,
                            threshold: parseFloat(e.target.value)
                          }
                        }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">0.0 = most responsive, 1.0 = waits longer for turn end</p>
                  </div>

                  {/* Smart Endpointing Parameters */}
                  <div className="border-t border-gray-700 pt-3">
                    <Label className="text-gray-300 font-semibold block mb-3">Smart Endpointing (Advanced)</Label>

                    <div className="space-y-3">
                      <div>
                        <Label className="text-gray-400 text-sm">End of Turn Confidence (0.0-1.0)</Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          max="1"
                          value={formData.settings?.assemblyai_settings?.end_of_turn_confidence_threshold || 0.8}
                          onChange={(e) => setFormData({
                            ...formData,
                            settings: {
                              ...formData.settings,
                              assemblyai_settings: {
                                ...formData.settings?.assemblyai_settings,
                                end_of_turn_confidence_threshold: parseFloat(e.target.value)
                              }
                            }
                          })}
                          className="bg-gray-900 border-gray-700 text-white mt-1"
                        />
                        <p className="text-xs text-gray-500 mt-1">Confidence level required to detect turn end (higher = more certain)</p>
                      </div>

                      <div>
                        <Label className="text-gray-400 text-sm">Min Silence When Confident (ms)</Label>
                        <Input
                          type="number"
                          step="100"
                          min="100"
                          max="2000"
                          value={formData.settings?.assemblyai_settings?.min_end_of_turn_silence_when_confident || 500}
                          onChange={(e) => setFormData({
                            ...formData,
                            settings: {
                              ...formData.settings,
                              assemblyai_settings: {
                                ...formData.settings?.assemblyai_settings,
                                min_end_of_turn_silence_when_confident: parseInt(e.target.value)
                              }
                            }
                          })}
                          className="bg-gray-900 border-gray-700 text-white mt-1"
                        />
                        <p className="text-xs text-gray-500 mt-1">Minimum silence to confirm turn end when confident (lower = faster)</p>
                      </div>

                      <div>
                        <Label className="text-gray-400 text-sm">Max Turn Silence (ms)</Label>
                        <Input
                          type="number"
                          step="100"
                          min="500"
                          max="5000"
                          value={formData.settings?.assemblyai_settings?.max_turn_silence || 2000}
                          onChange={(e) => setFormData({
                            ...formData,
                            settings: {
                              ...formData.settings,
                              assemblyai_settings: {
                                ...formData.settings?.assemblyai_settings,
                                max_turn_silence: parseInt(e.target.value)
                              }
                            }
                          })}
                          className="bg-gray-900 border-gray-700 text-white mt-1"
                        />
                        <p className="text-xs text-gray-500 mt-1">Maximum silence before forcing turn end (prevents hanging)</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.settings?.assemblyai_settings?.disable_partial_transcripts ?? false}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          assemblyai_settings: {
                            ...formData.settings?.assemblyai_settings,
                            disable_partial_transcripts: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    <Label className="text-gray-400 text-sm">Disable Partial Transcripts</Label>
                    <p className="text-xs text-gray-500">Only receive final transcripts</p>
                  </div>
                </div>
              )}

              {/* Soniox Settings */}
              {formData.settings?.stt_provider === 'soniox' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3 mb-4">
                    <p className="text-blue-400 text-sm font-semibold">⚡ Zero Latency STT</p>
                    <p className="text-blue-300 text-xs mt-1">Native mulaw support - No audio conversion needed</p>
                  </div>

                  <Label className="text-gray-300 font-semibold block">Soniox Settings</Label>

                  {/* Model Selection */}
                  <div>
                    <Label className="text-gray-400 text-sm">Model</Label>
                    <Select
                      value={formData.settings?.soniox_settings?.model || 'stt-rt-v3'}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          soniox_settings: {
                            ...formData.settings?.soniox_settings,
                            model: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="stt-rt-v3">STT RT v3 (Latest - Recommended)</SelectItem>
                        <SelectItem value="stt-rt-v3-preview">STT RT v3 Preview (Alias)</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">
                      v3 models offer higher accuracy, 60+ languages, improved multilingual switching, and up to 5hr sessions
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.settings?.soniox_settings?.enable_endpoint_detection ?? true}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          soniox_settings: {
                            ...formData.settings?.soniox_settings,
                            enable_endpoint_detection: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    <Label className="text-gray-400 text-sm">Enable Endpoint Detection</Label>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Automatically detect when speaker finishes talking (recommended)</p>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.settings?.soniox_settings?.enable_speaker_diarization ?? false}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          soniox_settings: {
                            ...formData.settings?.soniox_settings,
                            enable_speaker_diarization: e.target.checked
                          }
                        }
                      })}
                      className="w-4 h-4"
                    />
                    <Label className="text-gray-400 text-sm">Enable Speaker Diarization</Label>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Identify different speakers in the conversation</p>

                  <div>
                    <Label className="text-gray-400 text-sm">Context (Optional)</Label>
                    <textarea
                      value={formData.settings?.soniox_settings?.context || ''}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          soniox_settings: {
                            ...formData.settings?.soniox_settings,
                            context: e.target.value
                          }
                        }
                      })}
                      placeholder="Add context to improve accuracy (names, terms, etc.)"
                      className="bg-gray-900 border-gray-700 text-white mt-1 w-full min-h-[80px] p-2 rounded"
                    />
                    <p className="text-xs text-gray-500 mt-1">Custom context for improved recognition accuracy</p>
                  </div>
                </div>
              )}

              {/* ElevenLabs Settings */}
              {formData.settings?.tts_provider === 'elevenlabs' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <Label className="text-gray-300 font-semibold block">ElevenLabs Settings</Label>

                  <div>
                    <Label className="text-gray-400 text-sm">Voice ID</Label>
                    <Input
                      type="text"
                      placeholder="21m00Tcm4TlvDq8ikWAM"
                      value={formData.settings?.elevenlabs_settings?.voice_id || ''}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          elevenlabs_settings: {
                            ...formData.settings?.elevenlabs_settings,
                            voice_id: e.target.value
                          }
                        }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">Custom voice ID from ElevenLabs</p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Model</Label>
                    <Select
                      value={formData.settings?.elevenlabs_settings?.model || 'eleven_turbo_v2_5'}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          elevenlabs_settings: {
                            ...formData.settings?.elevenlabs_settings,
                            model: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="eleven_v3">Eleven v3 (Alpha - Most Expressive)</SelectItem>
                        <SelectItem value="eleven_flash_v2_5">Flash v2.5 (Fastest - 75ms)</SelectItem>
                        <SelectItem value="eleven_turbo_v2_5">Turbo v2.5 (Best Quality)</SelectItem>
                        <SelectItem value="eleven_turbo_v2">Turbo v2 (Balanced)</SelectItem>
                        <SelectItem value="eleven_flash_v2">Flash v2 (Fast)</SelectItem>
                        <SelectItem value="eleven_multilingual_v2">Multilingual v2 (29 languages)</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">v3 is newest but not for real-time, Flash v2.5 is fastest</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-gray-400 text-sm flex items-center gap-1">
                        Stability (0-1)
                        <div className="relative group">
                          <Info size={14} className="text-blue-400 cursor-help" />
                          <div className="absolute z-50 hidden group-hover:block left-0 top-6 w-72 p-3 bg-gray-800 border border-gray-600 rounded-lg shadow-lg text-xs text-gray-200">
                            <strong className="text-blue-400">Stability</strong>
                            <p className="mt-1"><strong>Higher (0.7-1.0):</strong> More consistent, predictable voice. Better for professional/formal content. Less emotional variation.</p>
                            <p className="mt-1"><strong>Lower (0-0.3):</strong> More expressive and dynamic. Better for storytelling/emotional content. May have more variation between generations.</p>
                            <p className="mt-1 text-gray-400">Recommended: 0.5 for balanced output</p>
                          </div>
                        </div>
                      </Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        value={formData.settings?.elevenlabs_settings?.stability || 0.5}
                        onChange={(e) => setFormData({
                          ...formData,
                          settings: {
                            ...formData.settings,
                            elevenlabs_settings: {
                              ...formData.settings?.elevenlabs_settings,
                              stability: parseFloat(e.target.value)
                            }
                          }
                        })}
                        className="bg-gray-900 border-gray-700 text-white mt-1"
                      />
                    </div>

                    <div>
                      <Label className="text-gray-400 text-sm">Speed (0.7-1.2)</Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0.7"
                        max="1.2"
                        value={formData.settings?.elevenlabs_settings?.speed || 1.0}
                        onChange={(e) => setFormData({
                          ...formData,
                          settings: {
                            ...formData.settings,
                            elevenlabs_settings: {
                              ...formData.settings?.elevenlabs_settings,
                              speed: parseFloat(e.target.value)
                            }
                          }
                        })}
                        className="bg-gray-900 border-gray-700 text-white mt-1"
                      />
                      <p className="text-xs text-gray-500 mt-1">ElevenLabs API range: 0.7-1.2</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-gray-400 text-sm flex items-center gap-1">
                        Similarity Boost (0-1)
                        <div className="relative group">
                          <Info size={14} className="text-blue-400 cursor-help" />
                          <div className="absolute z-50 hidden group-hover:block left-0 top-6 w-72 p-3 bg-gray-800 border border-gray-600 rounded-lg shadow-lg text-xs text-gray-200">
                            <strong className="text-blue-400">Similarity Boost</strong>
                            <p className="mt-1"><strong>Higher (0.7-1.0):</strong> Closer to the original voice sample. More accurate voice cloning. May amplify artifacts if audio quality is poor.</p>
                            <p className="mt-1"><strong>Lower (0-0.3):</strong> More flexibility and variation. Can sound more natural but less like the original. Reduces artifacts.</p>
                            <p className="mt-1 text-gray-400">Recommended: 0.75 for good voice matching</p>
                          </div>
                        </div>
                      </Label>
                      <Input
                        type="number"
                        step="0.05"
                        min="0"
                        max="1"
                        value={formData.settings?.elevenlabs_settings?.similarity_boost || 0.75}
                        onChange={(e) => setFormData({
                          ...formData,
                          settings: {
                            ...formData.settings,
                            elevenlabs_settings: {
                              ...formData.settings?.elevenlabs_settings,
                              similarity_boost: parseFloat(e.target.value)
                            }
                          }
                        })}
                        className="bg-gray-900 border-gray-700 text-white mt-1"
                      />
                    </div>

                    <div>
                      <Label className="text-gray-400 text-sm flex items-center gap-1">
                        Style (0-1)
                        <div className="relative group">
                          <Info size={14} className="text-blue-400 cursor-help" />
                          <div className="absolute z-50 hidden group-hover:block right-0 top-6 w-72 p-3 bg-gray-800 border border-gray-600 rounded-lg shadow-lg text-xs text-gray-200">
                            <strong className="text-blue-400">Style Exaggeration</strong>
                            <p className="mt-1"><strong>Higher (0.3-1.0):</strong> More exaggerated speaking style from the original sample. More dramatic intonation and emphasis. Can sound theatrical.</p>
                            <p className="mt-1"><strong>Lower (0-0.2):</strong> More neutral speaking style. Reduces quirks from original sample. Better for consistent, professional output.</p>
                            <p className="mt-1 text-gray-400">Recommended: 0.0-0.2 for phone calls. Only works with v2+ models.</p>
                            <p className="mt-1 text-yellow-400">⚠️ High values increase latency and may cause instability.</p>
                          </div>
                        </div>
                      </Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        value={formData.settings?.elevenlabs_settings?.style || 0.0}
                        onChange={(e) => setFormData({
                          ...formData,
                          settings: {
                            ...formData.settings,
                            elevenlabs_settings: {
                              ...formData.settings?.elevenlabs_settings,
                              style: parseFloat(e.target.value)
                            }
                          }
                        })}
                        className="bg-gray-900 border-gray-700 text-white mt-1"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-gray-400 text-sm flex items-center gap-1">
                        Use Speaker Boost
                      </Label>
                      <div className="mt-2">
                        <label className="inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.settings?.elevenlabs_settings?.use_speaker_boost !== false}
                            onChange={(e) => setFormData({
                              ...formData,
                              settings: {
                                ...formData.settings,
                                elevenlabs_settings: {
                                  ...formData.settings?.elevenlabs_settings,
                                  use_speaker_boost: e.target.checked
                                }
                              }
                            })}
                            className="sr-only peer"
                          />
                          <div className="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                        <p className="text-xs text-gray-500 mt-1">Enhances voice similarity</p>
                      </div>
                    </div>

                    <div>
                      <Label className="text-gray-400 text-sm flex items-center gap-1">
                        Enable Text Normalization
                      </Label>
                      <div className="mt-2">
                        <label className="inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.settings?.elevenlabs_settings?.enable_normalization !== false}
                            onChange={(e) => setFormData({
                              ...formData,
                              settings: {
                                ...formData.settings,
                                elevenlabs_settings: {
                                  ...formData.settings?.elevenlabs_settings,
                                  enable_normalization: e.target.checked
                                }
                              }
                            })}
                            className="sr-only peer"
                          />
                          <div className="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                        <p className="text-xs text-gray-500 mt-1">Auto-converts numbers, dates to spoken form</p>
                      </div>
                    </div>
                  </div>

                  {/* Persistent TTS WebSocket - NEW */}
                  <div className="border-t border-gray-700 pt-4">
                    <Label className="text-gray-400 text-sm flex items-center gap-1">
                      🚀 Use Persistent TTS WebSocket (Recommended)
                    </Label>
                    <div className="mt-2">
                      <label className="inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.settings?.elevenlabs_settings?.use_persistent_tts !== false}
                          onChange={(e) => setFormData({
                            ...formData,
                            settings: {
                              ...formData.settings,
                              elevenlabs_settings: {
                                ...formData.settings?.elevenlabs_settings,
                                use_persistent_tts: e.target.checked
                              }
                            }
                          })}
                          className="sr-only peer"
                        />
                        <div className="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                      </label>
                      <p className="text-xs text-gray-500 mt-1">
                        Enables persistent WebSocket connection for ultra-low latency (&lt;1.5s). Eliminates connection overhead and provides seamless multi-sentence audio streaming.
                      </p>
                      <p className="text-xs text-green-500 mt-1">
                        ✨ Reduces latency by 50-70% (from ~3s to &lt;1.2s)
                      </p>
                    </div>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm flex items-center gap-1">
                      Enable SSML Parsing
                    </Label>
                    <div className="mt-2">
                      <label className="inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.settings?.elevenlabs_settings?.enable_ssml_parsing === true}
                          onChange={(e) => setFormData({
                            ...formData,
                            settings: {
                              ...formData.settings,
                              elevenlabs_settings: {
                                ...formData.settings?.elevenlabs_settings,
                                enable_ssml_parsing: e.target.checked
                              }
                            }
                          })}
                          className="sr-only peer"
                        />
                        <div className="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                      <p className="text-xs text-gray-500 mt-1">Support for &lt;break time="1s"/&gt; pauses (slight latency increase)</p>
                    </div>
                  </div>

                  {/* Documentation Links */}
                  <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4 mt-4 space-y-2">
                    <Label className="text-blue-400 font-semibold text-sm">📖 ElevenLabs Best Practices</Label>
                    <div className="space-y-1 text-xs">
                      <div>
                        <a
                          href="https://elevenlabs.io/docs/best-practices/prompting/eleven-v3"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 underline"
                        >
                          V3 Audio Tags Guide
                        </a>
                        <span className="text-gray-500"> - Use [laughs], [excited], [whispers], [sarcastic] in text</span>
                      </div>
                      <div>
                        <a
                          href="https://elevenlabs.io/docs/best-practices/prompting/normalization"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 underline"
                        >
                          Normalization Best Practices
                        </a>
                        <span className="text-gray-500"> - Auto-convert numbers, dates, special characters</span>
                      </div>
                      <div>
                        <a
                          href="https://elevenlabs.io/docs/best-practices/prompting/controls"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 underline"
                        >
                          SSML Controls Guide
                        </a>
                        <span className="text-gray-500"> - Add pauses and pronunciation tags</span>
                      </div>
                      <div>
                        <a
                          href="https://elevenlabs.io/docs/api-reference/voices/settings/get-default"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 underline"
                        >
                          Voice Settings Reference
                        </a>
                        <span className="text-gray-500"> - Detailed parameter explanations</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Cartesia Settings */}
              {formData.settings?.tts_provider === 'cartesia' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3 mb-4">
                    <p className="text-blue-400 text-sm font-semibold">⚡ Ultra-Low Latency TTS</p>
                    <p className="text-blue-300 text-xs mt-1">40-90ms TTFB - Best for real-time conversations</p>
                  </div>

                  <Label className="text-gray-300 font-semibold block">Cartesia Sonic Settings</Label>

                  <div>
                    <Label className="text-gray-400 text-sm">Voice ID</Label>
                    <Input
                      type="text"
                      placeholder="a0e99841-438c-4a64-b679-ae501e7d6091"
                      value={formData.settings?.cartesia_settings?.voice_id || 'a0e99841-438c-4a64-b679-ae501e7d6091'}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          cartesia_settings: {
                            ...formData.settings?.cartesia_settings,
                            voice_id: e.target.value
                          }
                        }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Default: a0e99841-438c-4a64-b679-ae501e7d6091 (Friendly Reading Man)
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Model</Label>
                    <Select
                      value={formData.settings?.cartesia_settings?.model || 'sonic-2'}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          cartesia_settings: {
                            ...formData.settings?.cartesia_settings,
                            model: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="sonic-2">Sonic 2 (Recommended - 90ms latency)</SelectItem>
                        <SelectItem value="sonic-turbo">Sonic Turbo (Ultra-fast - 40ms latency)</SelectItem>
                        <SelectItem value="sonic">Sonic v1 (Original)</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">
                      Sonic 2 recommended for best quality and low latency (90ms)
                    </p>
                  </div>
                </div>
              )}

              {/* Dia TTS Settings - DISABLED */}
              {/* {formData.settings?.tts_provider === 'dia' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3 mb-4">
                    <p className="text-blue-400 text-sm font-semibold">🎤 Dia TTS - Ultra-Realistic</p>
                    <p className="text-blue-300 text-xs mt-1">1.6B parameter model with natural dialogue and emotion</p>
                  </div>
                  
                  <Label className="text-gray-300 font-semibold block">Dia TTS Settings</Label>
                  
                  <div>
                    <Label className="text-gray-400 text-sm">Voice / Speaker</Label>
                    <Select
                      value={formData.settings?.dia_settings?.voice || 'S1'}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          dia_settings: {
                            ...formData.settings?.dia_settings,
                            voice: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="S1">Speaker 1 (S1) - Default Male</SelectItem>
                        <SelectItem value="S2">Speaker 2 (S2) - Default Female</SelectItem>
                        <SelectItem value="S3">Speaker 3 (S3)</SelectItem>
                        <SelectItem value="S4">Speaker 4 (S4)</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">Select voice/speaker for synthesis</p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Speed: {formData.settings?.dia_settings?.speed || 1.0}x</Label>
                    <input
                      type="range"
                      min="0.25"
                      max="2.0"
                      step="0.05"
                      value={formData.settings?.dia_settings?.speed || 1.0}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          dia_settings: {
                            ...formData.settings?.dia_settings,
                            speed: parseFloat(e.target.value)
                          }
                        }
                      })}
                      className="w-full mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Speech rate: {formData.settings?.dia_settings?.speed || 1.0}x (0.25 = very slow, 2.0 = very fast)
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Audio Format</Label>
                    <Select
                      value={formData.settings?.dia_settings?.response_format || 'wav'}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          dia_settings: {
                            ...formData.settings?.dia_settings,
                            response_format: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="wav">WAV (Recommended)</SelectItem>
                        <SelectItem value="mp3">MP3</SelectItem>
                        <SelectItem value="opus">Opus</SelectItem>
                        <SelectItem value="aac">AAC</SelectItem>
                        <SelectItem value="flac">FLAC</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">Audio output format (WAV recommended for best quality)</p>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                    <strong>💡 Pro Tips:</strong>
                    <ul className="list-disc list-inside mt-1 space-y-1 text-xs">
                      <li>Use [S1] and [S2] tags in your prompts for multi-speaker dialogue</li>
                      <li>Add non-verbal sounds like (laughs), (sighs), (gasps) for realism</li>
                      <li>Speed 0.9-1.1 works best for natural conversations</li>
                    </ul>
                  </div>
                </div>
              )} */}


              {/* Kokoro Settings - Hidden from UI but backend still functional */}
              {/* {formData.settings?.tts_provider === 'kokoro' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div className="bg-green-900/20 border border-green-700 rounded-lg p-3 mb-4">
                    <p className="text-green-400 text-sm font-semibold">🎤 Kokoro TTS - Fast & Free</p>
                    <p className="text-green-300 text-xs mt-1">Open-source 82M parameter model with natural voices</p>
                  </div>
                  
                  <Label className="text-gray-300 font-semibold block">Kokoro TTS Settings</Label>
                  
                  <div>
                    <Label className="text-gray-400 text-sm">Voice</Label>
                    <Select
                      value={formData.settings?.kokoro_settings?.voice || 'af_bella'}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          kokoro_settings: {
                            ...formData.settings?.kokoro_settings,
                            voice: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="af_bella">Bella - American Female 🇺🇸</SelectItem>
                        <SelectItem value="af_nicole">Nicole - American Female 🇺🇸</SelectItem>
                        <SelectItem value="af_sarah">Sarah - American Female 🇺🇸</SelectItem>
                        <SelectItem value="af_sky">Sky - American Female 🇺🇸</SelectItem>
                        <SelectItem value="bf_emma">Emma - British Female 🇬🇧</SelectItem>
                        <SelectItem value="bf_isabella">Isabella - British Female 🇬🇧</SelectItem>
                        <SelectItem value="am_adam">Adam - American Male 🇺🇸</SelectItem>
                        <SelectItem value="am_michael">Michael - American Male 🇺🇸</SelectItem>
                        <SelectItem value="bm_george">George - British Male 🇬🇧</SelectItem>
                        <SelectItem value="bm_lewis">Lewis - British Male 🇬🇧</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">Select voice for synthesis</p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Speed: {formData.settings?.kokoro_settings?.speed || 1.0}x</Label>
                    <input
                      type="range"
                      min="0.5"
                      max="2.0"
                      step="0.1"
                      value={formData.settings?.kokoro_settings?.speed || 1.0}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          kokoro_settings: {
                            ...formData.settings?.kokoro_settings,
                            speed: parseFloat(e.target.value)
                          }
                        }
                      })}
                      className="w-full mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Speech rate: {formData.settings?.kokoro_settings?.speed || 1.0}x (0.5 = slow, 2.0 = fast)
                    </p>
                  </div>
                </div>
              )} */}

              {/* ChatTTS Settings - DISABLED */}
              {/* {formData.settings?.tts_provider === 'chattts' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3 mb-4">
                    <p className="text-blue-400 text-sm font-semibold">🚀 ChatTTS - Ultra-Fast Conversational</p>
                    <p className="text-blue-300 text-xs mt-1">Optimized for dialogue, RTF &lt;0.5, &lt;500ms latency on RTX 4090</p>
                  </div>
                  
                  <Label className="text-gray-300 font-semibold block">ChatTTS Settings</Label>
                  
                  <div>
                    <Label className="text-gray-400 text-sm">Voice</Label>
                    <Select
                      value={formData.settings?.chattts_settings?.voice || 'female_1'}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          chattts_settings: {
                            ...formData.settings?.chattts_settings,
                            voice: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="female_1">Female Voice 1</SelectItem>
                        <SelectItem value="female_2">Female Voice 2</SelectItem>
                        <SelectItem value="female_3">Female Voice 3</SelectItem>
                        <SelectItem value="male_1">Male Voice 1</SelectItem>
                        <SelectItem value="male_2">Male Voice 2</SelectItem>
                        <SelectItem value="male_3">Male Voice 3</SelectItem>
                        <SelectItem value="neutral_1">Neutral Voice 1</SelectItem>
                        <SelectItem value="neutral_2">Neutral Voice 2</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">Select voice preset for synthesis</p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Speed: {formData.settings?.chattts_settings?.speed || 1.0}x</Label>
                    <input
                      type="range"
                      min="0.5"
                      max="2.0"
                      step="0.1"
                      value={formData.settings?.chattts_settings?.speed || 1.0}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          chattts_settings: {
                            ...formData.settings?.chattts_settings,
                            speed: parseFloat(e.target.value)
                          }
                        }
                      })}
                      className="w-full mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Speech rate: {formData.settings?.chattts_settings?.speed || 1.0}x (0.5 = slow, 2.0 = fast)
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Temperature: {formData.settings?.chattts_settings?.temperature || 0.3}</Label>
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.1"
                      value={formData.settings?.chattts_settings?.temperature || 0.3}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          chattts_settings: {
                            ...formData.settings?.chattts_settings,
                            temperature: parseFloat(e.target.value)
                          }
                        }
                      })}
                      className="w-full mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Sampling temperature: {formData.settings?.chattts_settings?.temperature || 0.3} (lower = faster & more stable)
                    </p>
                  </div>
                </div>
              )} */}

              {/* Hume Settings */}
              {formData.settings?.tts_provider === 'hume' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <Label className="text-gray-300 font-semibold block">Hume AI Settings</Label>

                  <div>
                    <Label className="text-gray-400 text-sm">Voice ID</Label>
                    <Input
                      type="text"
                      placeholder="e7af7ed6-3381-48aa-ab97-49485007470b"
                      value={formData.settings?.hume_settings?.voice_name || 'e7af7ed6-3381-48aa-ab97-49485007470b'}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          hume_settings: {
                            ...formData.settings?.hume_settings,
                            voice_name: e.target.value
                          }
                        }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">Your Hume custom voice ID (UUID format)</p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Emotional Description</Label>
                    <Input
                      type="text"
                      placeholder="e.g., warm and friendly"
                      value={formData.settings?.hume_settings?.description || ''}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          hume_settings: {
                            ...formData.settings?.hume_settings,
                            description: e.target.value
                          }
                        }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">Optional emotional guidance for Hume</p>
                  </div>
                </div>
              )}

              {/* Maya TTS Settings */}
              {formData.settings?.tts_provider === 'maya' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div className="bg-purple-900/20 border border-purple-700 rounded-lg p-3 mb-4">
                    <p className="text-purple-400 text-sm font-semibold">✨ Maya - Adaptive Voice</p>
                    <p className="text-purple-300 text-xs mt-1">Control voice style and emotion using natural language descriptions</p>
                  </div>

                  <Label className="text-gray-300 font-semibold block">Maya Voice Settings</Label>

                  <div>
                    <Label className="text-gray-400 text-sm">Quick Presets</Label>
                    <Select
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          maya_settings: {
                            ...formData.settings?.maya_settings,
                            voice_ref: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue placeholder="Select a preset to auto-fill description..." />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="default">Default Balanced</SelectItem>
                        <SelectItem value="American female voice, professional and clear">🇺🇸 American Female (Professional)</SelectItem>
                        <SelectItem value="American male voice, friendly and conversational">🇺🇸 American Male (Friendly)</SelectItem>
                        <SelectItem value="British female voice, calm and soothing">🇬🇧 British Female (Calm)</SelectItem>
                        <SelectItem value="Energetic and helpful customer support agent">⚡ Enthusiastic Support</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm flex items-center gap-1">
                      Voice Description (Emotional Guidance)
                      <div className="relative group">
                        <Info size={14} className="text-blue-400 cursor-help" />
                        <div className="absolute z-50 hidden group-hover:block right-0 top-6 w-72 p-3 bg-gray-800 border border-gray-600 rounded-lg shadow-lg text-xs text-gray-200">
                          <strong className="text-blue-400">Emotional Guidance</strong>
                          <p className="mt-1">Maya adapts the voice based on this description.</p>
                          <p className="mt-1">Try describing:</p>
                          <ul className="list-disc list-inside mt-1 text-gray-400">
                            <li>Accent (e.g., "British", "Southern")</li>
                            <li>Tone (e.g., "Serious", "Excited")</li>
                            <li>Persona (e.g., "Old wizard", "News anchor")</li>
                          </ul>
                        </div>
                      </div>
                    </Label>
                    <Textarea
                      value={formData.settings?.maya_settings?.voice_ref || ''}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          maya_settings: {
                            ...formData.settings?.maya_settings,
                            voice_ref: e.target.value
                          }
                        }
                      })}
                      placeholder="e.g., A calm and soothing female voice..."
                      className="bg-gray-900 border-gray-700 text-white mt-1"
                      rows={3}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Describe the voice you want. The AI will generate audio matching this description.
                    </p>
                  </div>
                </div>
              )}
              value={formData.settings?.hume_settings?.description || ''}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  hume_settings: {
                    ...formData.settings?.hume_settings,
                    description: e.target.value
                  }
                }
              })}
              className="bg-gray-900 border-gray-700 text-white mt-1"
                    />
              <p className="text-xs text-gray-500 mt-1">Describe the emotional tone of the voice</p>
            </div>
          </div>
              )}

          {/* Sesame TTS Settings */}
          {formData.settings?.tts_provider === 'sesame' && (
            <div className="space-y-4 border-t border-gray-700 pt-4">
              <div className="bg-purple-900/20 border border-purple-700 rounded-lg p-3 mb-4">
                <p className="text-purple-400 text-sm font-semibold">🎙️ Custom Sesame TTS (RunPod)</p>
                <p className="text-purple-300 text-xs mt-1">24kHz WAV audio, optimized for Telnyx</p>
              </div>

              <Label className="text-gray-300 font-semibold block">Sesame TTS Settings</Label>

              <div>
                <Label className="text-gray-400 text-sm">Speaker ID (Voice)</Label>
                <Select
                  value={String(formData.settings?.sesame_settings?.speaker_id ?? 0)}
                  onValueChange={(value) => setFormData({
                    ...formData,
                    settings: {
                      ...formData.settings,
                      sesame_settings: {
                        ...formData.settings?.sesame_settings,
                        speaker_id: parseInt(value)
                      }
                    }
                  })}
                >
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-700">
                    <SelectItem value="0">Speaker 0</SelectItem>
                    <SelectItem value="1">Speaker 1</SelectItem>
                    <SelectItem value="2">Speaker 2</SelectItem>
                    <SelectItem value="3">Speaker 3</SelectItem>
                    <SelectItem value="4">Speaker 4</SelectItem>
                    <SelectItem value="5">Speaker 5</SelectItem>
                    <SelectItem value="6">Speaker 6</SelectItem>
                    <SelectItem value="7">Speaker 7</SelectItem>
                    <SelectItem value="8">Speaker 8</SelectItem>
                    <SelectItem value="9">Speaker 9</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">Select speaker voice (0-9)</p>
              </div>

              <div>
                <Label className="text-gray-400 text-sm">Output Format</Label>
                <Select
                  value={formData.settings?.sesame_settings?.output_format || 'wav'}
                  onValueChange={(value) => setFormData({
                    ...formData,
                    settings: {
                      ...formData.settings,
                      sesame_settings: {
                        ...formData.settings?.sesame_settings,
                        output_format: value
                      }
                    }
                  })}
                >
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-700">
                    <SelectItem value="wav">WAV (Recommended - 24kHz PCM)</SelectItem>
                    <SelectItem value="mp3">MP3</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">Audio output format</p>
              </div>
            </div>
          )}

          {/* MeloTTS Settings */}
          {/* MeloTTS Settings - DISABLED */}
          {/* {formData.settings?.tts_provider === 'melo' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div className="bg-green-900/20 border border-green-700 rounded-lg p-3 mb-4">
                    <p className="text-green-400 text-sm font-semibold">🎤 MeloTTS - Open Source</p>
                    <p className="text-green-300 text-xs mt-1">Free multilingual TTS with GPU acceleration</p>
                  </div>
                  
                  <Label className="text-gray-300 font-semibold block">MeloTTS Settings</Label>
                  
                  <div>
                    <Label className="text-gray-400 text-sm">Voice</Label>
                    <Select
                      value={formData.settings?.melo_settings?.voice || 'EN-US'}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          melo_settings: {
                            ...formData.settings?.melo_settings,
                            voice: value
                          }
                        }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="EN-US">English (US) 🇺🇸</SelectItem>
                        <SelectItem value="EN-BR">English (British) 🇬🇧</SelectItem>
                        <SelectItem value="EN_INDIA">English (Indian) 🇮🇳</SelectItem>
                        <SelectItem value="EN-AU">English (Australian) 🇦🇺</SelectItem>
                        <SelectItem value="EN-Default">English (Default) 🌐</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">Select voice accent</p>
                  </div>

                  <div>
                    <Label className="text-gray-400 text-sm">Speed</Label>
                    <input
                      type="range"
                      min="0.5"
                      max="2.0"
                      step="0.1"
                      value={formData.settings?.melo_settings?.speed || 1.2}
                      onChange={(e) => setFormData({
                        ...formData,
                        settings: {
                          ...formData.settings,
                          melo_settings: {
                            ...formData.settings?.melo_settings,
                            speed: parseFloat(e.target.value)
                          }
                        }
                      })}
                      className="w-full mt-1"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Speech rate: {formData.settings?.melo_settings?.speed || 1.2}x (0.5 = slow, 2.0 = fast)
                    </p>
                  </div>
                </div>
              )} */}

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
            <strong>Note:</strong> API keys for these services must be configured in Settings. Go to Settings → API Key Management.
          </div>
        </div>
      </details>

      {/* Dead Air Prevention Settings */}
      <details className="border border-gray-700 rounded-lg bg-gray-900">
        <summary className="cursor-pointer p-4 font-semibold text-white hover:bg-gray-800">
          🔇 Dead Air Prevention & Call Management
        </summary>
        <div className="p-4 border-t border-gray-700 space-y-6">
          <p className="text-gray-400 text-sm mb-4">
            Configure automatic check-ins when the user goes silent and set maximum call duration limits.
            These settings help maintain engagement and prevent abandoned calls.
          </p>

          {/* Normal Silence Timeout */}
          <div>
            <Label className="text-gray-300 font-semibold">Normal Silence Timeout (seconds)</Label>
            <Input
              type="number"
              min="1"
              max="60"
              value={formData.settings?.dead_air_settings?.silence_timeout_normal ?? 7}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  dead_air_settings: {
                    ...formData.settings?.dead_air_settings,
                    silence_timeout_normal: parseInt(e.target.value) || 7
                  }
                }
              })}
              className="bg-gray-900 border-gray-700 text-white mt-2"
            />
            <p className="text-xs text-gray-500 mt-1">
              How long to wait (in seconds) before checking in when the user goes silent
            </p>
          </div>

          {/* Hold On Silence Timeout */}
          <div>
            <Label className="text-gray-300 font-semibold">"Hold On" Silence Timeout (seconds)</Label>
            <Input
              type="number"
              min="1"
              max="120"
              value={formData.settings?.dead_air_settings?.silence_timeout_hold_on ?? 25}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  dead_air_settings: {
                    ...formData.settings?.dead_air_settings,
                    silence_timeout_hold_on: parseInt(e.target.value) || 25
                  }
                }
              })}
              className="bg-gray-900 border-gray-700 text-white mt-2"
            />
            <p className="text-xs text-gray-500 mt-1">
              Longer timeout when user says "hold on", "wait", "one moment", etc. (allows time for user to handle something)
            </p>
          </div>

          {/* Max Check-ins */}
          <div>
            <Label className="text-gray-300 font-semibold">Max Check-ins Before Disconnect</Label>
            <Input
              type="number"
              min="1"
              max="10"
              value={formData.settings?.dead_air_settings?.max_checkins_before_disconnect ?? 2}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  dead_air_settings: {
                    ...formData.settings?.dead_air_settings,
                    max_checkins_before_disconnect: parseInt(e.target.value) || 2
                  }
                }
              })}
              className="bg-gray-900 border-gray-700 text-white mt-2"
            />
            <p className="text-xs text-gray-500 mt-1">
              Call will end after this many unanswered check-ins per silence period (resets when user responds)
            </p>
          </div>

          {/* Max Call Duration */}
          <div>
            <Label className="text-gray-300 font-semibold">Max Call Duration (minutes)</Label>
            <Input
              type="number"
              min="1"
              max="120"
              value={Math.round((formData.settings?.dead_air_settings?.max_call_duration ?? 1500) / 60)}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  dead_air_settings: {
                    ...formData.settings?.dead_air_settings,
                    max_call_duration: parseInt(e.target.value) * 60 || 1500
                  }
                }
              })}
              className="bg-gray-900 border-gray-700 text-white mt-2"
            />
            <p className="text-xs text-gray-500 mt-1">
              Call will automatically end after this duration, regardless of activity (prevents runaway calls)
            </p>
          </div>

          {/* Check-in Message */}
          <div>
            <Label className="text-gray-300 font-semibold">Check-in Message</Label>
            <Input
              type="text"
              placeholder="Are you still there?"
              value={formData.settings?.dead_air_settings?.checkin_message ?? "Are you still there?"}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  dead_air_settings: {
                    ...formData.settings?.dead_air_settings,
                    checkin_message: e.target.value || "Are you still there?"
                  }
                }
              })}
              className="bg-gray-900 border-gray-700 text-white mt-2"
            />
            <p className="text-xs text-gray-500 mt-1">
              Custom message the agent will say when checking in with a silent user
            </p>
          </div>

          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3 mt-4">
            <div className="flex items-start gap-2">
              <span className="text-blue-400 text-lg">ℹ️</span>
              <div className="text-xs text-blue-200">
                <strong>How it works:</strong> The system only counts silence between when the agent stops speaking and when the user starts.
                Time when either party is speaking is not counted. After a check-in, if the user responds, the count resets.
                This prevents accidental disconnects while maintaining natural conversation flow.
              </div>
            </div>
          </div>
        </div>
      </details>

      {/* Call Control (Barge-In) Settings */}
      <details className="border border-gray-700 rounded-lg bg-gray-900">
        <summary className="cursor-pointer p-4 font-semibold text-white hover:bg-gray-800">
          🚦 Call Control (Rambler Interruption)
        </summary>
        <div className="p-4 border-t border-gray-700 space-y-6">
          <p className="text-gray-400 text-sm mb-4">
            Configure when the agent should interrupt a user who is speaking for too long.
            This prevents filibustering and keeps the conversation on track.
          </p>

          {/* Enable Barge-In */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.settings?.barge_in_settings?.enable_verbose_barge_in ?? false}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  barge_in_settings: {
                    ...formData.settings?.barge_in_settings,
                    enable_verbose_barge_in: e.target.checked
                  }
                }
              })}
              className="w-4 h-4"
            />
            <Label className="text-gray-300">Enable Rambler Interruption</Label>
          </div>
          <p className="text-xs text-gray-500 ml-6">
            Agent will interrupt the user if they speak continuously beyond the threshold
          </p>

          {/* Word Count Threshold */}
          <div>
            <Label className="text-gray-300 font-semibold">
              Word Count Threshold: {formData.settings?.barge_in_settings?.word_count_threshold ?? 50} words
            </Label>
            <input
              type="range"
              min="10"
              max="100"
              step="5"
              value={formData.settings?.barge_in_settings?.word_count_threshold ?? 50}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  barge_in_settings: {
                    ...formData.settings?.barge_in_settings,
                    word_count_threshold: parseInt(e.target.value)
                  }
                }
              })}
              disabled={!formData.settings?.barge_in_settings?.enable_verbose_barge_in}
              className="w-full mt-2"
            />
            <p className="text-xs text-gray-500 mt-1">
              Interrupt after the user speaks this many words continuously (lower = more aggressive)
            </p>
          </div>

          {/* Interruption Prompt */}
          <div>
            <Label className="text-gray-300 font-semibold">Interruption Prompt</Label>
            <Textarea
              placeholder="The user is speaking for a long time. Interrupt them politely but firmly to acknowledge what they said and guide the conversation back to the goal."
              value={formData.settings?.barge_in_settings?.interruption_prompt || ''}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  barge_in_settings: {
                    ...formData.settings?.barge_in_settings,
                    interruption_prompt: e.target.value
                  }
                }
              })}
              disabled={!formData.settings?.barge_in_settings?.enable_verbose_barge_in}
              className="bg-gray-900 border-gray-700 text-white mt-2"
              rows={3}
            />
            <p className="text-xs text-gray-500 mt-1">
              Instructions for how the AI should interrupt the user. Leave empty for default behavior.
            </p>
          </div>

          <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 mt-4">
            <div className="flex items-start gap-2">
              <span className="text-red-400 text-lg">⚠️</span>
              <div className="text-xs text-red-200">
                <strong>Safeguards:</strong> The agent will NOT interrupt if:
                <ul className="list-disc ml-4 mt-1">
                  <li>A webhook is currently executing</li>
                  <li>Another interruption happened in the last 15 seconds (cooldown)</li>
                  <li>The user stops talking before the interruption is ready (Ghost Prevention)</li>
                </ul>
                Individual nodes can override or disable this setting in the Flow Builder.
              </div>
            </div>
          </div>
        </div>
      </details>

      {/* Voicemail & IVR Detection Settings */}
      <details className="border border-gray-700 rounded-lg bg-gray-900">
        <summary className="cursor-pointer p-4 font-semibold text-white hover:bg-gray-800">
          🤖 Voicemail & IVR Detection (Hybrid)
        </summary>
        <div className="p-4 border-t border-gray-700 space-y-6">
          <p className="text-gray-400 text-sm mb-4">
            Automatically detect and disconnect voicemail greetings and automated phone systems (IVR).
            Uses both Telnyx's ML-powered detection and real-time AI analysis for maximum accuracy.
          </p>

          {/* Enable Detection */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.settings?.voicemail_detection?.enabled ?? true}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  voicemail_detection: {
                    ...formData.settings?.voicemail_detection,
                    enabled: e.target.checked
                  }
                }
              })}
              className="w-4 h-4"
            />
            <Label className="text-gray-300">Enable Voicemail/IVR Detection</Label>
          </div>

          {/* Telnyx AMD */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.settings?.voicemail_detection?.use_telnyx_amd ?? true}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  voicemail_detection: {
                    ...formData.settings?.voicemail_detection,
                    use_telnyx_amd: e.target.checked
                  }
                }
              })}
              className="w-4 h-4"
              disabled={!formData.settings?.voicemail_detection?.enabled}
            />
            <Label className="text-gray-300">Use Telnyx AMD (First Line of Defense)</Label>
          </div>
          <p className="text-xs text-gray-500 ml-6">
            ML-powered detection at call answer. Premium: $0.0065/call, Standard: $0.002/call
          </p>

          {/* AMD Mode */}
          {formData.settings?.voicemail_detection?.use_telnyx_amd && (
            <div className="ml-6">
              <Label className="text-gray-300 font-semibold">Telnyx AMD Mode</Label>
              <Select
                value={formData.settings?.voicemail_detection?.telnyx_amd_mode || 'premium'}
                onValueChange={(value) => setFormData({
                  ...formData,
                  settings: {
                    ...formData.settings,
                    voicemail_detection: {
                      ...formData.settings?.voicemail_detection,
                      telnyx_amd_mode: value
                    }
                  }
                })}
              >
                <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-700">
                  <SelectItem value="premium">Premium ($0.0065) - Most Accurate</SelectItem>
                  <SelectItem value="standard">Standard ($0.002) - Basic</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500 mt-1">
                Premium uses advanced ML for higher accuracy and detects greeting end
              </p>
            </div>
          )}

          {/* LLM Detection */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.settings?.voicemail_detection?.use_llm_detection ?? true}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  voicemail_detection: {
                    ...formData.settings?.voicemail_detection,
                    use_llm_detection: e.target.checked
                  }
                }
              })}
              className="w-4 h-4"
              disabled={!formData.settings?.voicemail_detection?.enabled}
            />
            <Label className="text-gray-300">Use AI Detection (Second Line of Defense)</Label>
          </div>
          <p className="text-xs text-gray-500 ml-6">
            Real-time pattern matching during conversation. Zero latency, runs in parallel.
          </p>

          {/* Auto Disconnect */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.settings?.voicemail_detection?.disconnect_on_detection ?? true}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  voicemail_detection: {
                    ...formData.settings?.voicemail_detection,
                    disconnect_on_detection: e.target.checked
                  }
                }
              })}
              className="w-4 h-4"
              disabled={!formData.settings?.voicemail_detection?.enabled}
            />
            <Label className="text-gray-300">Auto-Disconnect on Detection</Label>
          </div>
          <p className="text-xs text-gray-500 ml-6">
            Automatically hang up when voicemail or IVR is detected
          </p>

          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3 mt-4">
            <div className="flex items-start gap-2">
              <span className="text-blue-400 text-lg">🛡️</span>
              <div className="text-xs text-blue-200">
                <strong>Hybrid Detection:</strong> Telnyx AMD detects at call answer (voicemail, business greeting).
                AI detection monitors during the call for IVR menus ("press 1 for sales") that appear mid-conversation.
                Together, they provide comprehensive protection with zero latency impact.
              </div>
            </div>
          </div>
        </div>
      </details>

      {/* Post-Call Webhook Settings */}
      <details className="border border-gray-700 rounded-lg bg-gray-900">
        <summary className="cursor-pointer p-4 font-semibold text-white hover:bg-gray-800">
          🔗 Post-Call Webhook (Optional)
        </summary>
        <div className="p-4 border-t border-gray-700 space-y-4">
          <p className="text-gray-400 text-sm mb-4">
            Send call transcript and details to an external webhook (n8n, Zapier, Make, etc.) when calls end.
            This is useful for custom analytics, CRM updates, or AI-powered call analysis.
          </p>

          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-gray-300 font-semibold">Webhook URL</Label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="webhook-active"
                  checked={formData.settings?.post_call_webhook_url ? formData.settings?.post_call_webhook_active !== false : false}
                  onChange={(e) => setFormData({
                    ...formData,
                    settings: {
                      ...formData.settings,
                      post_call_webhook_active: e.target.checked
                    }
                  })}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                />
                <Label htmlFor="webhook-active" className="text-sm text-gray-300 cursor-pointer">
                  Enable Webhook
                </Label>
              </div>
            </div>
            <Input
              type="url"
              placeholder="https://your-n8n-instance.com/webhook/your-webhook-id"
              value={formData.settings?.post_call_webhook_url || ''}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  post_call_webhook_url: e.target.value,
                  // Auto-enable when URL is entered (for backwards compatibility)
                  post_call_webhook_active: e.target.value ? (formData.settings?.post_call_webhook_active !== false ? true : formData.settings?.post_call_webhook_active) : formData.settings?.post_call_webhook_active
                }
              })}
              className="bg-gray-900 border-gray-700 text-white mt-1"
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter your webhook URL and check "Enable Webhook" to activate.
            </p>
          </div>

          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3 mt-4">
            <div className="flex items-start gap-2">
              <span className="text-blue-400 text-lg">📤</span>
              <div className="text-xs text-blue-200">
                <strong>Webhook Payload:</strong> The webhook will receive: call_id, agent_name, transcript (full array),
                duration, status, from_number, to_number, extracted_variables, custom_variables, and timestamps.
              </div>
            </div>
          </div>
        </div>
      </details>

      {/* Call Started Webhook Settings */}
      <details className="border border-gray-700 rounded-lg bg-gray-900">
        <summary className="cursor-pointer p-4 font-semibold text-white hover:bg-gray-800">
          📞 Call Started Webhook (Optional)
        </summary>
        <div className="p-4 border-t border-gray-700 space-y-4">
          <p className="text-gray-400 text-sm mb-4">
            Send a notification to an external webhook the moment a call is answered.
            Useful for tracking when calls are placed to leads, triggering CRM updates, or real-time dashboards.
          </p>

          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-gray-300 font-semibold">Webhook URL</Label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="call-started-webhook-active"
                  checked={formData.settings?.call_started_webhook_url ? formData.settings?.call_started_webhook_active !== false : false}
                  onChange={(e) => setFormData({
                    ...formData,
                    settings: {
                      ...formData.settings,
                      call_started_webhook_active: e.target.checked
                    }
                  })}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                />
                <Label htmlFor="call-started-webhook-active" className="text-sm text-gray-300 cursor-pointer">
                  Enable Webhook
                </Label>
              </div>
            </div>
            <Input
              type="url"
              placeholder="https://your-webhook.com/call-started"
              value={formData.settings?.call_started_webhook_url || ''}
              onChange={(e) => setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  call_started_webhook_url: e.target.value,
                  // Auto-enable when URL is entered (for backwards compatibility)
                  call_started_webhook_active: e.target.value ? (formData.settings?.call_started_webhook_active !== false ? true : formData.settings?.call_started_webhook_active) : formData.settings?.call_started_webhook_active
                }
              })}
              className="bg-gray-900 border-gray-700 text-white mt-1"
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter your webhook URL and check "Enable Webhook" to activate.
            </p>
          </div>

          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3 mt-4">
            <div className="flex items-start gap-2">
              <span className="text-blue-400 text-lg">📤</span>
              <div className="text-xs text-blue-200">
                <strong>Webhook Payload:</strong> The webhook will receive: event ("call.started"), call_id, agent_name,
                from_number, to_number, direction, and start_time.
              </div>
            </div>
          </div>
        </div>
      </details>

      {/* Auto QC Settings Section - Only for existing agents */}
      {isEdit && (
        <div className="mt-6">
          <AutoQCSettings agentId={id} agentName={formData.name} />
        </div>
      )}

      {/* Knowledge Base Section */}
      {isEdit && (
        <details className="bg-gray-800 rounded-lg p-6 border border-gray-700" open>
          <summary className="text-xl font-semibold text-white cursor-pointer mb-4">
            📚 Knowledge Base
          </summary>
          <div className="space-y-4">
            <p className="text-gray-400 text-sm">
              Upload documents or add website URLs to provide your agent with product information, company details, or any reference material.
              The AI will use this knowledge to answer questions accurately.
            </p>

            {/* File Upload */}
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
              <Label className="text-gray-300 font-medium mb-2 block">Upload Document</Label>
              <div className="flex items-center gap-2">
                <label className="flex-1 cursor-pointer">
                  <div className="border-2 border-dashed border-gray-600 rounded-lg p-4 hover:border-blue-500 transition-colors text-center">
                    <Upload className="mx-auto mb-2 text-gray-400" size={24} />
                    <p className="text-sm text-gray-400">
                      {uploadingFile ? 'Uploading...' : 'Click to upload PDF, TXT, or DOCX'}
                    </p>
                  </div>
                  <input
                    type="file"
                    accept=".pdf,.txt,.docx"
                    onChange={handleFileUpload}
                    disabled={uploadingFile}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* URL Input */}
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
              <Label className="text-gray-300 font-medium mb-2 block">Add Website URL</Label>
              <div className="flex gap-2">
                <Input
                  type="url"
                  placeholder="https://example.com/product-info"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  disabled={addingUrl}
                  className="flex-1 bg-gray-800 border-gray-600 text-white"
                />
                <Button
                  type="button"
                  onClick={handleAddUrl}
                  disabled={addingUrl || !urlInput.trim()}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <LinkIcon size={16} className="mr-1" />
                  {addingUrl ? 'Adding...' : 'Add'}
                </Button>
              </div>
            </div>

            {/* KB Items List */}
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
              <Label className="text-gray-300 font-medium mb-3 block">
                Knowledge Base Items ({kbItems.length})
              </Label>
              {kbLoading ? (
                <p className="text-gray-400 text-sm">Loading...</p>
              ) : kbItems.length === 0 ? (
                <p className="text-gray-500 text-sm italic">
                  No knowledge base items yet. Upload documents or add URLs above.
                </p>
              ) : (
                <div className="space-y-2">
                  {kbItems.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between p-3 bg-gray-800 rounded border border-gray-700 hover:border-gray-600 transition-colors"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        {item.source_type === 'file' ? (
                          <FileText className="text-blue-400 flex-shrink-0" size={20} />
                        ) : (
                          <ExternalLink className="text-green-400 flex-shrink-0" size={20} />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-white text-sm font-medium truncate">
                            {item.source_name}
                          </p>
                          {item.description && (
                            <p className="text-blue-400 text-xs mb-1 italic">
                              Contains: {item.description}
                            </p>
                          )}
                          <p className="text-gray-500 text-xs">
                            {(item.content_length / 1000).toFixed(1)}K chars • {new Date(item.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <Button
                        type="button"
                        onClick={() => handleDeleteKbItem(item.id)}
                        variant="ghost"
                        size="sm"
                        className="text-red-400 hover:text-red-300 hover:bg-red-900/20 flex-shrink-0"
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-4 text-sm text-blue-200 space-y-2">
              <div className="font-semibold text-blue-100 mb-2">📖 How to Use Knowledge Base Effectively:</div>
              <ul className="space-y-1 list-disc list-inside text-xs">
                <li><strong>Upload focused documents:</strong> Each file should cover a specific topic (e.g., "company_info.pdf", "pricing.pdf", "sales_scripts.pdf")</li>
                <li><strong>Name files clearly:</strong> Use descriptive names so you can identify content easily</li>
                <li><strong>Keep it relevant:</strong> Only upload information your agent needs to reference during conversations</li>
                <li><strong>The agent will intelligently match:</strong> When users ask questions, the AI will identify which KB source(s) contain relevant information</li>
                <li><strong>Multiple sources work together:</strong> You can have different KB items for different purposes (company info, products, methodologies, FAQs)</li>
              </ul>
              <div className="mt-3 pt-2 border-t border-blue-700/50 text-xs">
                <strong>✨ Pro Tip:</strong> The AI is instructed to ONLY use information from your KB - it will not make up facts or improvise details not in your documents.
              </div>
            </div>
          </div>
        </details>
      )}

      <div className="flex gap-4">
        <Button
          type="submit"
          disabled={loading}
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white flex-1"
        >
          <Save size={20} className="mr-2" />
          {loading ? 'Saving...' : (isNew ? 'Create Agent' : 'Update Agent')}
        </Button>
        <Button
          type="button"
          onClick={() => navigate('/agents')}
          variant="outline"
          className="border-gray-700 text-gray-300 hover:bg-gray-800"
        >
          Cancel
        </Button>
      </div>
    </form>
      </Card >
    </div >
  );
};

export default AgentForm;
