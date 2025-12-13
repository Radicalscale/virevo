import React, { useState, useRef, useEffect } from 'react';
import { X, Sparkles, Loader2, Copy, Check, Upload, FileText, Mic, Trash2, Database } from 'lucide-react';
import { agentAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

const OptimizeNodeModal = ({ isOpen, onClose, agentId, originalContent, onApply }) => {
  const { toast } = useToast();
  const [mode, setMode] = useState('optimize'); // 'optimize' or 'enhance'
  const [content, setContent] = useState(originalContent);
  const [guidelines, setGuidelines] = useState('');
  const [optimized, setOptimized] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [model, setModel] = useState('grok-4-0709');
  
  // Context file upload state
  const [contextFile, setContextFile] = useState(null);
  const [contextFileText, setContextFileText] = useState('');
  const [extractingText, setExtractingText] = useState(false);
  const fileInputRef = useRef(null);
  
  // KB context state
  const [useKBContext, setUseKBContext] = useState(true);
  const [kbItemCount, setKbItemCount] = useState(0);

  useEffect(() => {
    if (isOpen) {
      setContent(originalContent);
      setOptimized('');
      setGuidelines('');
      setCopied(false);
      setModel('grok-4-0709');
      setContextFile(null);
      setContextFileText('');
      setUseKBContext(true);
      
      // Fetch KB item count for this agent using the API client
      const fetchKBCount = async () => {
        try {
          const response = await agentAPI.getKBItems(agentId);
          const kbData = response.data;
          setKbItemCount(Array.isArray(kbData) ? kbData.length : 0);
          console.log('KB items fetched:', kbData);
        } catch (err) {
          console.log('Could not fetch KB count:', err);
          setKbItemCount(0);
        }
      };
      fetchKBCount();
    }
  }, [isOpen, originalContent, agentId]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['application/pdf', 'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/webm', 'audio/ogg', 'audio/m4a'];
    const isValidType = validTypes.includes(file.type) || 
                        file.name.endsWith('.pdf') || 
                        file.name.endsWith('.mp3') || 
                        file.name.endsWith('.wav') ||
                        file.name.endsWith('.m4a') ||
                        file.name.endsWith('.webm');

    if (!isValidType) {
      toast({
        title: "Invalid file type",
        description: "Please upload a PDF or audio file (MP3, WAV, M4A, WebM)",
        variant: "destructive"
      });
      return;
    }

    // Check file size (max 25MB)
    if (file.size > 25 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Maximum file size is 25MB",
        variant: "destructive"
      });
      return;
    }

    setContextFile(file);
    setExtractingText(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await agentAPI.extractContextFromFile(agentId, formData);
      setContextFileText(response.data.extracted_text);
      
      toast({
        title: "Context extracted",
        description: `Extracted ${response.data.extracted_text.length} characters from ${file.name}`
      });
    } catch (error) {
      console.error('Error extracting context:', error);
      toast({
        title: "Extraction failed",
        description: error.response?.data?.detail || "Failed to extract text from file",
        variant: "destructive"
      });
      setContextFile(null);
    } finally {
      setExtractingText(false);
    }
  };

  const removeContextFile = () => {
    setContextFile(null);
    setContextFileText('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleOptimize = async () => {
    if (!content.trim()) {
      toast({
        title: "Error",
        description: "Please enter content to optimize",
        variant: "destructive"
      });
      return;
    }

    setLoading(true);
    try {
      const response = await agentAPI.optimizeNode(
        agentId, 
        content, 
        guidelines, 
        model,
        contextFileText || null,  // Pass extracted context
        useKBContext  // Whether to include KB
      );
      setOptimized(response.data.optimized);
      toast({
        title: "Success",
        description: response.data.context_used 
          ? `Optimized with ${response.data.context_used}` 
          : "Node prompt optimized successfully"
      });
    } catch (error) {
      console.error('Error optimizing node:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to optimize node. Make sure you have added your Grok API key in Settings.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleEnhance = async () => {
    if (!content.trim()) {
      toast({
        title: "Error",
        description: "Please enter script to enhance",
        variant: "destructive"
      });
      return;
    }

    setLoading(true);
    try {
      const response = await agentAPI.enhanceScript(agentId, content, model);
      setOptimized(response.data.enhanced);
      toast({
        title: "Success",
        description: "Script enhanced for voice output"
      });
    } catch (error) {
      console.error('Error enhancing script:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to enhance script. Make sure you have added your Grok API key in Settings.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (optimized) {
      onApply(optimized);
      onClose();
      toast({
        title: "Success",
        description: "Optimized content applied to node"
      });
    }
  };

  const handleCopy = () => {
    if (optimized) {
      navigator.clipboard.writeText(optimized);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast({
        title: "Copied",
        description: "Optimized content copied to clipboard"
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <Sparkles className="text-purple-400" size={24} />
            <h2 className="text-2xl font-bold text-white">AI Node Optimizer</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Mode Tabs */}
        <div className="flex border-b border-gray-700">
          <button
            onClick={() => setMode('optimize')}
            className={`flex-1 py-3 px-6 font-medium transition-colors ${
              mode === 'optimize'
                ? 'text-purple-400 border-b-2 border-purple-400 bg-gray-750'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Optimize Node Prompt
          </button>
          <button
            onClick={() => setMode('enhance')}
            className={`flex-1 py-3 px-6 font-medium transition-colors ${
              mode === 'enhance'
                ? 'text-purple-400 border-b-2 border-purple-400 bg-gray-750'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Enhance Script for Voice
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {mode === 'optimize' ? (
            <div className="space-y-4">
              <div>
                <Label className="text-white mb-2">Grok Model</Label>
                <Select value={model} onValueChange={setModel}>
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700">
                    <SelectItem value="grok-4-0709">Grok 4 (Default - Best Balance)</SelectItem>
                    <SelectItem value="grok-3">Grok 3 (Reliable & Fast)</SelectItem>
                    <SelectItem value="grok-2-1212">Grok 2 (Dec 2024)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-400 mt-1">
                  Select which Grok model to use for optimization
                </p>
              </div>

              <div>
                <Label className="text-white mb-2">Original Node Content</Label>
                <Textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste your node prompt or content here..."
                  className="min-h-[150px] bg-gray-900 text-white border-gray-700"
                />
              </div>

              <div>
                <Label className="text-white mb-2">Custom Guidelines (Optional)</Label>
                <Textarea
                  value={guidelines}
                  onChange={(e) => setGuidelines(e.target.value)}
                  placeholder="Add any specific optimization rules or requirements..."
                  className="min-h-[80px] bg-gray-900 text-white border-gray-700"
                />
                <p className="text-sm text-gray-400 mt-1">
                  The optimizer will apply node-by-node best practices, hallucination prevention, and voice optimization automatically.
                </p>
              </div>

              {/* Context Sources Section */}
              <div className="border border-purple-700/30 rounded-lg p-4 bg-purple-900/10">
                <Label className="text-white mb-3 flex items-center gap-2 text-base">
                  <Sparkles size={16} className="text-purple-400" />
                  Context Sources for Optimizer
                </Label>
                <p className="text-xs text-gray-400 mb-4">
                  Give the AI optimizer additional context to make smarter decisions (e.g., objection handling techniques, product info, call scripts)
                </p>

                {/* KB Context Toggle */}
                <div className="flex items-center justify-between bg-gray-800 rounded-lg p-3 mb-3">
                  <div className="flex items-center gap-3">
                    <Database size={20} className="text-blue-400" />
                    <div>
                      <p className="text-sm text-white font-medium">Agent Knowledge Base</p>
                      <p className="text-xs text-gray-400">
                        {kbItemCount > 0 ? `${kbItemCount} items available` : 'No KB items'}
                      </p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useKBContext}
                      onChange={(e) => setUseKBContext(e.target.checked)}
                      className="sr-only peer"
                      disabled={kbItemCount === 0}
                    />
                    <div className={`w-11 h-6 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all ${kbItemCount === 0 ? 'bg-gray-700' : 'bg-gray-600 peer-checked:bg-blue-600'}`}></div>
                  </label>
                </div>

                {/* File Upload */}
                <div className="bg-gray-800 rounded-lg p-3">
                  <div className="flex items-center gap-3 mb-2">
                    <Upload size={20} className="text-purple-400" />
                    <div>
                      <p className="text-sm text-white font-medium">Upload Reference Material</p>
                      <p className="text-xs text-gray-400">PDF docs or audio clips with techniques/examples</p>
                    </div>
                  </div>
                  
                  {!contextFile ? (
                    <div className="flex items-center gap-2 mt-2">
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        accept=".pdf,.mp3,.wav,.m4a,.webm,audio/*,application/pdf"
                        className="hidden"
                        id="context-file-upload"
                      />
                      <label
                        htmlFor="context-file-upload"
                        className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded cursor-pointer transition-colors text-sm"
                      >
                        <FileText size={14} className="text-blue-400" />
                        <span className="text-gray-300">PDF</span>
                      </label>
                      <label
                        htmlFor="context-file-upload"
                        className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded cursor-pointer transition-colors text-sm"
                      >
                        <Mic size={14} className="text-green-400" />
                        <span className="text-gray-300">Audio</span>
                      </label>
                    </div>
                  ) : (
                    <div className="mt-2">
                      <div className="flex items-center justify-between bg-gray-900 rounded p-2">
                        <div className="flex items-center gap-2">
                          {contextFile.type.includes('pdf') || contextFile.name.endsWith('.pdf') ? (
                            <FileText size={16} className="text-blue-400" />
                          ) : (
                            <Mic size={16} className="text-green-400" />
                          )}
                          <div>
                            <p className="text-xs text-white font-medium truncate max-w-[200px]">{contextFile.name}</p>
                            <p className="text-xs text-gray-500">
                              {extractingText ? (
                                <span className="flex items-center gap-1">
                                  <Loader2 size={10} className="animate-spin" />
                                  Extracting...
                                </span>
                              ) : (
                                `${contextFileText.length.toLocaleString()} chars`
                              )}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={removeContextFile}
                          className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                          disabled={extractingText}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <Button
                onClick={handleOptimize}
                disabled={loading || extractingText}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 animate-spin" size={16} />
                    Optimizing with context...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2" size={16} />
                    Optimize Node Prompt
                    {(useKBContext && kbItemCount > 0) || contextFile ? ' (with context)' : ''}
                  </>
                )}
              </Button>

              {optimized && (
                <div className="mt-6">
                  <Label className="text-white mb-2">Optimized Content</Label>
                  <div className="relative">
                    <Textarea
                      value={optimized}
                      readOnly
                      className="min-h-[200px] bg-gray-900 text-white border-green-600 border-2"
                    />
                    <button
                      onClick={handleCopy}
                      className="absolute top-2 right-2 p-2 bg-gray-800 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
                    >
                      {copied ? <Check size={16} /> : <Copy size={16} />}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <Label className="text-white mb-2">Grok Model</Label>
                <Select value={model} onValueChange={setModel}>
                  <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700">
                    <SelectItem value="grok-4-0709">Grok 4 (Default - Best Balance)</SelectItem>
                    <SelectItem value="grok-3">Grok 3 (Reliable & Fast)</SelectItem>
                    <SelectItem value="grok-2-1212">Grok 2 (Dec 2024)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-400 mt-1">
                  Select which Grok model to use for enhancement
                </p>
              </div>

              <div>
                <Label className="text-white mb-2">Original Script</Label>
                <Textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste your script text here..."
                  className="min-h-[200px] bg-gray-900 text-white border-gray-700"
                />
                <p className="text-sm text-gray-400 mt-1">
                  This will normalize numbers/dates, add SSML tags, fix punctuation, and optimize for natural voice synthesis.
                </p>
              </div>

              <Button
                onClick={handleEnhance}
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-green-600 hover:from-blue-700 hover:to-green-700"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 animate-spin" size={16} />
                    Enhancing with Grok...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2" size={16} />
                    Enhance Script for Voice
                  </>
                )}
              </Button>

              {optimized && (
                <div className="mt-6">
                  <Label className="text-white mb-2">Enhanced Script (Ready for TTS)</Label>
                  <div className="relative">
                    <Textarea
                      value={optimized}
                      readOnly
                      className="min-h-[200px] bg-gray-900 text-white border-green-600 border-2"
                    />
                    <button
                      onClick={handleCopy}
                      className="absolute top-2 right-2 p-2 bg-gray-800 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
                    >
                      {copied ? <Check size={16} /> : <Copy size={16} />}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-700">
          <Button
            onClick={onClose}
            variant="ghost"
            className="text-gray-400 hover:text-white"
          >
            Cancel
          </Button>
          {optimized && (
            <Button
              onClick={handleApply}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              Apply to Node
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default OptimizeNodeModal;
