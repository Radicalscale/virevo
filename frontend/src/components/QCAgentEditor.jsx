import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { 
  ArrowLeft, 
  Save, 
  Trash2, 
  Upload, 
  Plus,
  Brain,
  Mic,
  FileText,
  Settings,
  BookOpen,
  X,
  Sparkles,
  AlertCircle,
  CheckCircle,
  HelpCircle,
  GraduationCap
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { Switch } from './ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { useToast } from '../hooks/use-toast';
import { qcAgentsAPI } from '../services/api';
import QCPlaybookManager from './QCPlaybookManager';

// QC Agent type configurations
const QC_AGENT_TYPES = {
  tonality: {
    icon: Mic,
    label: 'Tonality',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    description: 'Analyzes voice tonality, emotional delivery, and provides ElevenLabs-compatible recommendations',
    defaultPrompt: `You are an expert voice delivery analyst specializing in sales and customer service calls.

Your task is to analyze the tonality, emotional delivery, and vocal characteristics of the AI agent's responses.

For each agent response, evaluate:
1. Tone appropriateness (warm, professional, empathetic, confident)
2. Energy level matching with the customer
3. Pacing and rhythm
4. Emotional resonance
5. Areas for improvement

Provide specific, actionable feedback with examples of how to improve delivery.`
  },
  language_pattern: {
    icon: FileText,
    label: 'Language Pattern',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    description: 'Analyzes script quality, conversation patterns, and suggests improvements',
    defaultPrompt: `You are an expert conversation analyst specializing in sales scripts and customer interactions.

Your task is to analyze the language patterns, script adherence, and conversation quality.

For each conversation, evaluate:
1. Goal alignment - Are responses moving toward the desired outcome?
2. Brevity - Are responses concise without unnecessary filler?
3. Clarity - Is the message clear and easy to understand?
4. Persuasion techniques - Are appropriate techniques being used?
5. Objection handling - How well are objections addressed?

Provide specific suggestions with rewritten examples.`
  },
  tech_issues: {
    icon: Settings,
    label: 'Tech Issues',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    description: 'Analyzes call logs, identifies technical issues, and generates solution documentation',
    defaultPrompt: `You are an expert technical analyst for voice AI systems.

Your task is to analyze call logs and identify technical issues.

Classify issues as:
- System/infrastructure problems
- Prompt/script issues requiring modification
- Multi-agent architecture needs
- Code bugs requiring fixes

For each issue:
1. Clearly describe the problem
2. Identify root cause
3. Provide step-by-step solution
4. Generate ready-to-use fix code or prompts`
  },
  generic: {
    icon: Brain,
    label: 'Generic',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    description: 'General-purpose QC analysis agent',
    defaultPrompt: `You are an expert QC analyst for voice AI calls.

Analyze the provided call data and provide:
1. Overall quality assessment
2. Key issues identified
3. Specific improvement recommendations
4. Priority actions`
  }
};

// LLM Provider options
const LLM_PROVIDERS = [
  { value: 'grok', label: 'Grok (xAI)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Google Gemini' }
];

// Model options by provider
const LLM_MODELS = {
  grok: [
    { value: 'grok-3', label: 'Grok 3' },
    { value: 'grok-2-1212', label: 'Grok 2' }
  ],
  openai: [
    { value: 'gpt-5', label: 'GPT-5' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' }
  ],
  anthropic: [
    { value: 'claude-4-opus', label: 'Claude 4 Opus' },
    { value: 'claude-3.5-sonnet', label: 'Claude 3.5 Sonnet' }
  ],
  gemini: [
    { value: 'gemini-3.0', label: 'Gemini 3.0' },
    { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' }
  ]
};

/**
 * QC Agent Editor Component
 */
const QCAgentEditor = () => {
  const navigate = useNavigate();
  const { agentId } = useParams();
  const [searchParams] = useSearchParams();
  const { toast } = useToast();
  const fileInputRef = useRef(null);
  
  const isNew = !agentId || agentId === 'new';
  const initialType = searchParams.get('type') || 'generic';
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    agent_type: initialType,
    mode: 'generic',
    llm_provider: 'grok',
    llm_model: 'grok-3',
    system_prompt: QC_AGENT_TYPES[initialType]?.defaultPrompt || '',
    analysis_rules: {},
    is_active: true,
    elevenlabs_settings: null,
    // New: Custom analysis instructions
    analysis_focus: '',
    custom_criteria: '',
    output_format_instructions: ''
  });
  
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [kbItems, setKbItems] = useState([]);
  const [uploadingKB, setUploadingKB] = useState(false);
  const [activeTab, setActiveTab] = useState('general');
  
  // Fetch existing agent
  useEffect(() => {
    if (!isNew) {
      fetchAgent();
    }
  }, [agentId, isNew]);
  
  // Update default prompt when type changes (for new agents)
  useEffect(() => {
    if (isNew && formData.agent_type) {
      const defaultPrompt = QC_AGENT_TYPES[formData.agent_type]?.defaultPrompt || '';
      if (!formData.system_prompt || formData.system_prompt === QC_AGENT_TYPES[initialType]?.defaultPrompt) {
        setFormData(prev => ({ ...prev, system_prompt: defaultPrompt }));
      }
    }
  }, [formData.agent_type, isNew, initialType]);
  
  const fetchAgent = async () => {
    try {
      setLoading(true);
      const response = await qcAgentsAPI.get(agentId);
      setFormData(response.data);
      
      // Fetch KB items
      try {
        const kbResponse = await qcAgentsAPI.listKB(agentId);
        setKbItems(kbResponse.data || []);
      } catch (e) {
        console.log('Could not fetch KB items');
      }
    } catch (error) {
      console.error('Error fetching QC agent:', error);
      toast({
        title: 'Error',
        description: 'Failed to load QC agent',
        variant: 'destructive'
      });
      navigate('/qc/agents');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle form changes
  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Reset model when provider changes
    if (field === 'llm_provider') {
      const models = LLM_MODELS[value] || [];
      setFormData(prev => ({
        ...prev,
        [field]: value,
        llm_model: models[0]?.value || ''
      }));
    }
  };
  
  // Handle save
  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Agent name is required',
        variant: 'destructive'
      });
      return;
    }
    
    try {
      setSaving(true);
      
      if (isNew) {
        const response = await qcAgentsAPI.create(formData);
        toast({
          title: 'Success',
          description: 'QC Agent created successfully'
        });
        // Navigate to edit mode so KB can be uploaded
        navigate(`/qc/agents/${response.data.id}`);
      } else {
        await qcAgentsAPI.update(agentId, formData);
        toast({
          title: 'Success',
          description: 'QC Agent updated successfully'
        });
      }
    } catch (error) {
      console.error('Error saving QC agent:', error);
      toast({
        title: 'Error',
        description: 'Failed to save QC agent',
        variant: 'destructive'
      });
    } finally {
      setSaving(false);
    }
  };
  
  // Handle KB upload
  const handleKBUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    if (isNew) {
      toast({
        title: 'Save First',
        description: 'Please save the agent before uploading knowledge base files',
        variant: 'destructive'
      });
      return;
    }
    
    try {
      setUploadingKB(true);
      
      for (const file of files) {
        const formDataUpload = new FormData();
        formDataUpload.append('file', file);
        formDataUpload.append('description', `Uploaded: ${file.name}`);
        
        await qcAgentsAPI.uploadKB(agentId, formDataUpload);
      }
      
      toast({
        title: 'Success',
        description: `${files.length} file(s) uploaded to knowledge base`
      });
      
      // Refresh KB items
      const kbResponse = await qcAgentsAPI.listKB(agentId);
      setKbItems(kbResponse.data || []);
    } catch (error) {
      console.error('Error uploading KB:', error);
      toast({
        title: 'Error',
        description: 'Failed to upload file(s)',
        variant: 'destructive'
      });
    } finally {
      setUploadingKB(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };
  
  // Handle KB delete
  const handleKBDelete = async (kbItemId) => {
    try {
      await qcAgentsAPI.deleteKB(agentId, kbItemId);
      toast({
        title: 'Success',
        description: 'KB item deleted'
      });
      setKbItems(prev => prev.filter(item => item.id !== kbItemId));
    } catch (error) {
      console.error('Error deleting KB:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete KB item',
        variant: 'destructive'
      });
    }
  };
  
  // Reset prompt to default
  const resetToDefaultPrompt = () => {
    const defaultPrompt = QC_AGENT_TYPES[formData.agent_type]?.defaultPrompt || '';
    setFormData(prev => ({ ...prev, system_prompt: defaultPrompt }));
    toast({
      title: 'Reset',
      description: 'Prompt reset to default template'
    });
  };
  
  const typeConfig = QC_AGENT_TYPES[formData.agent_type] || QC_AGENT_TYPES.generic;
  const TypeIcon = typeConfig.icon;
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }
  
  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/qc/agents')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold">
              {isNew ? 'Create QC Agent' : 'Edit QC Agent'}
            </h1>
            <p className="text-gray-600 text-sm">
              {isNew ? 'Configure a new quality control agent' : formData.name}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {!isNew && (
            <Badge variant="outline" className="mr-2">
              {kbItems.length} KB files
            </Badge>
          )}
          <Button onClick={handleSave} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : isNew ? 'Create Agent' : 'Save Changes'}
          </Button>
        </div>
      </div>
      
      {/* Agent Type Selection (only for new agents) */}
      {isNew && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Agent Type</CardTitle>
            <CardDescription>Select the type of QC analysis this agent will perform</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {Object.entries(QC_AGENT_TYPES).map(([type, config]) => {
                const Icon = config.icon;
                const isSelected = formData.agent_type === type;
                
                return (
                  <Card 
                    key={type}
                    className={`cursor-pointer transition-all ${
                      isSelected 
                        ? `border-2 border-primary ${config.bgColor}` 
                        : 'hover:border-gray-300'
                    }`}
                    onClick={() => handleChange('agent_type', type)}
                  >
                    <CardContent className="p-4 text-center">
                      <Icon className={`h-8 w-8 mx-auto mb-2 ${config.color}`} />
                      <h4 className="font-medium">{config.label}</h4>
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{config.description}</p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Main Form */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="prompt">Prompt & Instructions</TabsTrigger>
          <TabsTrigger value="kb">
            Knowledge Base
            {kbItems.length > 0 && (
              <Badge variant="secondary" className="ml-2 h-5 w-5 p-0 justify-center">
                {kbItems.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="llm">LLM Settings</TabsTrigger>
          <TabsTrigger value="rules">Analysis Rules</TabsTrigger>
          {!isNew && formData.agent_type !== 'tech_issues' && (
            <TabsTrigger value="learning">
              <GraduationCap className="h-4 w-4 mr-1" />
              Learning & Memory
            </TabsTrigger>
          )}
        </TabsList>
        
        {/* General Tab */}
        <TabsContent value="general">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${typeConfig.bgColor}`}>
                  <TypeIcon className={`h-5 w-5 ${typeConfig.color}`} />
                </div>
                <div>
                  <CardTitle>General Settings</CardTitle>
                  <CardDescription>{typeConfig.description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Agent Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => handleChange('name', e.target.value)}
                    placeholder="e.g., Sales Tonality Analyzer"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="mode">Operating Mode</Label>
                  <Select 
                    value={formData.mode} 
                    onValueChange={(v) => handleChange('mode', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="generic">Generic (Default Rules)</SelectItem>
                      <SelectItem value="custom">Custom (Campaign-Specific)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description || ''}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder="Describe what this QC agent does and when to use it..."
                  rows={3}
                />
              </div>
              
              <div className="flex items-center justify-between pt-4 border-t">
                <div>
                  <Label>Active</Label>
                  <p className="text-sm text-gray-500">Enable this agent for analysis</p>
                </div>
                <Switch
                  checked={formData.is_active}
                  onCheckedChange={(v) => handleChange('is_active', v)}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Prompt & Instructions Tab */}
        <TabsContent value="prompt">
          <div className="space-y-6">
            {/* System Prompt */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-purple-500" />
                      System Prompt
                    </CardTitle>
                    <CardDescription>
                      The main instructions that guide how this agent analyzes calls
                    </CardDescription>
                  </div>
                  <Button variant="outline" size="sm" onClick={resetToDefaultPrompt}>
                    Reset to Default
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={formData.system_prompt || ''}
                  onChange={(e) => handleChange('system_prompt', e.target.value)}
                  placeholder="Enter the system prompt that will guide this agent's analysis..."
                  rows={12}
                  className="font-mono text-sm"
                />
                <p className="text-xs text-gray-500 mt-2">
                  This prompt is sent to the LLM along with the call data. Be specific about what to analyze and how to format the output.
                </p>
              </CardContent>
            </Card>
            
            {/* Analysis Focus */}
            <Card>
              <CardHeader>
                <CardTitle>Analysis Focus</CardTitle>
                <CardDescription>
                  Specific areas this agent should focus on during analysis
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={formData.analysis_focus || ''}
                  onChange={(e) => handleChange('analysis_focus', e.target.value)}
                  placeholder="e.g., Focus on objection handling, closing techniques, and rapport building. Pay special attention to how the agent handles price objections."
                  rows={4}
                />
              </CardContent>
            </Card>
            
            {/* Custom Criteria */}
            <Card>
              <CardHeader>
                <CardTitle>Custom Evaluation Criteria</CardTitle>
                <CardDescription>
                  Define specific criteria or scoring rubrics for this agent
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={formData.custom_criteria || ''}
                  onChange={(e) => handleChange('custom_criteria', e.target.value)}
                  placeholder={`e.g.,
- Greeting: Was it warm and professional? (1-5)
- Discovery: Did the agent ask good questions? (1-5)
- Value Proposition: Was the value clearly communicated? (1-5)
- Close: Was there a clear call to action? (1-5)`}
                  rows={6}
                />
              </CardContent>
            </Card>
            
            {/* Output Format */}
            <Card>
              <CardHeader>
                <CardTitle>Output Format Instructions</CardTitle>
                <CardDescription>
                  How should the analysis results be formatted?
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={formData.output_format_instructions || ''}
                  onChange={(e) => handleChange('output_format_instructions', e.target.value)}
                  placeholder={`e.g.,
Provide the analysis in the following format:
1. Executive Summary (2-3 sentences)
2. Scores for each criterion
3. Top 3 strengths
4. Top 3 areas for improvement
5. Specific recommendations with examples`}
                  rows={6}
                />
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        {/* Knowledge Base Tab */}
        <TabsContent value="kb">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-green-500" />
                    Knowledge Base
                  </CardTitle>
                  <CardDescription>
                    Upload documents to provide context for analysis (scripts, guidelines, product info, etc.)
                  </CardDescription>
                </div>
                <div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".txt,.md,.pdf,.doc,.docx,.csv,.json"
                    multiple
                    onChange={handleKBUpload}
                  />
                  <Button 
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingKB || isNew}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    {uploadingKB ? 'Uploading...' : 'Upload Files'}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isNew ? (
                <div className="text-center py-12 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
                  <AlertCircle className="h-12 w-12 mx-auto mb-3 text-yellow-500" />
                  <h3 className="font-medium text-yellow-700 dark:text-yellow-300 mb-2">Save Agent First</h3>
                  <p className="text-sm text-yellow-600 dark:text-yellow-400">
                    Please save the agent before uploading knowledge base files.
                  </p>
                  <Button className="mt-4" onClick={handleSave} disabled={saving}>
                    {saving ? 'Saving...' : 'Save Agent Now'}
                  </Button>
                </div>
              ) : kbItems.length === 0 ? (
                <div className="text-center py-12">
                  <BookOpen className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                  <h3 className="font-medium mb-2">No Knowledge Base Files</h3>
                  <p className="text-sm text-gray-500 mb-4">
                    Upload documents to give this agent context for better analysis.
                  </p>
                  <div className="text-xs text-gray-400 mb-4">
                    Supported formats: .txt, .md, .pdf, .doc, .docx, .csv, .json
                  </div>
                  <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
                    <Upload className="h-4 w-4 mr-2" />
                    Upload Your First File
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-sm text-gray-500 mb-4">
                    {kbItems.length} file(s) uploaded. These documents provide context for the agent&apos;s analysis.
                  </div>
                  {kbItems.map((item) => (
                    <div 
                      key={item.id}
                      className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-blue-500" />
                        <div>
                          <p className="font-medium">{item.source_name}</p>
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                            <span>
                              {item.file_size > 0 
                                ? item.file_size > 1024 * 1024 
                                  ? `${(item.file_size / 1024 / 1024).toFixed(1)} MB`
                                  : `${(item.file_size / 1024).toFixed(1)} KB`
                                : 'Size unknown'}
                            </span>
                            {item.content_preview && (
                              <>
                                <span>•</span>
                                <span className="truncate max-w-xs">{item.content_preview}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-500 hover:text-red-700 hover:bg-red-50"
                        onClick={() => handleKBDelete(item.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
              
              {/* KB Usage Tips */}
              <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <h4 className="font-medium text-blue-700 dark:text-blue-300 mb-2 flex items-center gap-2">
                  <HelpCircle className="h-4 w-4" />
                  Knowledge Base Tips
                </h4>
                <ul className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
                  <li>• Upload your sales scripts so the agent can check adherence</li>
                  <li>• Include product documentation for accurate information checks</li>
                  <li>• Add company guidelines and compliance requirements</li>
                  <li>• Upload example perfect calls for comparison</li>
                  <li>• Include objection handling guides</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* LLM Settings Tab */}
        <TabsContent value="llm">
          <Card>
            <CardHeader>
              <CardTitle>LLM Configuration</CardTitle>
              <CardDescription>Configure the AI model used for analysis</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>LLM Provider</Label>
                  <Select 
                    value={formData.llm_provider} 
                    onValueChange={(v) => handleChange('llm_provider', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LLM_PROVIDERS.map(provider => (
                        <SelectItem key={provider.value} value={provider.value}>
                          {provider.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label>Model</Label>
                  <Select 
                    value={formData.llm_model} 
                    onValueChange={(v) => handleChange('llm_model', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(LLM_MODELS[formData.llm_provider] || []).map(model => (
                        <SelectItem key={model.value} value={model.value}>
                          {model.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <h4 className="font-medium mb-2">Model Recommendations</h4>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <li>• <strong>Grok 3:</strong> Best for detailed analysis and creative suggestions</li>
                  <li>• <strong>GPT-4o:</strong> Fast and accurate for standard QC tasks</li>
                  <li>• <strong>Claude 3.5:</strong> Excellent for nuanced conversation analysis</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Analysis Rules Tab */}
        <TabsContent value="rules">
          <Card>
            <CardHeader>
              <CardTitle>Analysis Rules</CardTitle>
              <CardDescription>Configure specific rules for QC analysis</CardDescription>
            </CardHeader>
            <CardContent>
              {formData.agent_type === 'tonality' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Generate ElevenLabs Directions</Label>
                      <p className="text-sm text-gray-500">Include copyable emotional directions</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.generate_elevenlabs ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        generate_elevenlabs: v
                      })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Include SSML/Prosody</Label>
                      <p className="text-sm text-gray-500">Generate prosody XML markup</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.include_ssml ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        include_ssml: v
                      })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Analyze Energy Matching</Label>
                      <p className="text-sm text-gray-500">Check if agent matches customer energy</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.analyze_energy ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        analyze_energy: v
                      })}
                    />
                  </div>
                </div>
              )}
              
              {formData.agent_type === 'language_pattern' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Check Goal Alignment</Label>
                      <p className="text-sm text-gray-500">Evaluate if responses move toward goals</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.check_goal_alignment ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        check_goal_alignment: v
                      })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Focus on Brevity</Label>
                      <p className="text-sm text-gray-500">Prioritize concise responses</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.focus_brevity ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        focus_brevity: v
                      })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Check Script Adherence</Label>
                      <p className="text-sm text-gray-500">Compare against uploaded scripts in KB</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.check_script ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        check_script: v
                      })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Suggest Rewrites</Label>
                      <p className="text-sm text-gray-500">Provide rewritten versions of weak responses</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.suggest_rewrites ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        suggest_rewrites: v
                      })}
                    />
                  </div>
                </div>
              )}
              
              {formData.agent_type === 'tech_issues' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Analyze Backend Code</Label>
                      <p className="text-sm text-gray-500">Read code to identify issues</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.analyze_code ?? false}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        analyze_code: v
                      })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Generate AI Coder Prompt</Label>
                      <p className="text-sm text-gray-500">Create ready-to-use fix prompts</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.generate_ai_prompt ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        generate_ai_prompt: v
                      })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Classify Issue Severity</Label>
                      <p className="text-sm text-gray-500">Rate issues as critical/high/medium/low</p>
                    </div>
                    <Switch
                      checked={formData.analysis_rules?.classify_severity ?? true}
                      onCheckedChange={(v) => handleChange('analysis_rules', {
                        ...formData.analysis_rules,
                        classify_severity: v
                      })}
                    />
                  </div>
                </div>
              )}
              
              {formData.agent_type === 'generic' && (
                <div className="text-center py-8 text-gray-500">
                  <Brain className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                  <p>Generic agents use the system prompt and custom criteria you define.</p>
                  <p className="text-sm mt-2">Go to the Prompt &amp; Instructions tab to customize.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Learning & Memory Tab */}
        {!isNew && formData.agent_type !== 'tech_issues' && (
          <TabsContent value="learning">
            <QCPlaybookManager
              agentId={agentId}
              agentType={formData.agent_type}
              agentName={formData.name}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
};

export default QCAgentEditor;
