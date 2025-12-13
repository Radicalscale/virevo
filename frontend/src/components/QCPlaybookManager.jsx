import React, { useState, useEffect, useCallback } from 'react';
import { 
  Brain, 
  BookOpen, 
  History, 
  Play, 
  Settings, 
  TrendingUp,
  RefreshCw,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Clock,
  Zap,
  Target,
  BarChart3,
  Sparkles,
  Edit3,
  Save,
  RotateCcw,
  Eye,
  EyeOff,
  Code,
  Cpu
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Input } from './ui/input';
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
import { qcLearningAPI } from '../services/api';

/**
 * QC Playbook Manager Component
 * Manages the learning/memory system for QC agents
 */
const QCPlaybookManager = ({ agentId, agentType, agentName }) => {
  const { toast } = useToast();
  
  // State
  const [loading, setLoading] = useState(true);
  const [playbook, setPlaybook] = useState(null);
  const [playbookHistory, setPlaybookHistory] = useState([]);
  const [learningConfig, setLearningConfig] = useState(null);
  const [learningStats, setLearningStats] = useState(null);
  const [patterns, setPatterns] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [brainPrompts, setBrainPrompts] = useState(null);
  
  const [isEditing, setIsEditing] = useState(false);
  const [editedMarkdown, setEditedMarkdown] = useState('');
  const [triggering, setTriggering] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [savingPlaybook, setSavingPlaybook] = useState(false);
  const [savingBrainPrompts, setSavingBrainPrompts] = useState(false);
  const [editingBrain, setEditingBrain] = useState(null); // 'reflection' or 'training'
  const [editedBrainPrompts, setEditedBrainPrompts] = useState({});
  const [previewingBrain, setPreviewingBrain] = useState(null);
  const [brainPreview, setBrainPreview] = useState(null);
  const [activeTab, setActiveTab] = useState('playbook');
  
  // Don't show for tech_issues agents
  const supportsLearning = agentType !== 'tech_issues';
  
  // Fetch all data
  const fetchData = useCallback(async () => {
    if (!agentId || !supportsLearning) return;
    
    try {
      setLoading(true);
      
      // Fetch in parallel
      const [
        playbookRes,
        historyRes,
        configRes,
        statsRes,
        patternsRes,
        sessionsRes,
        brainPromptsRes
      ] = await Promise.all([
        qcLearningAPI.getPlaybook(agentId).catch(() => ({ data: null })),
        qcLearningAPI.getPlaybookHistory(agentId).catch(() => ({ data: [] })),
        qcLearningAPI.getLearningConfig(agentId).catch(() => ({ data: null })),
        qcLearningAPI.getLearningStats(agentId).catch(() => ({ data: null })),
        qcLearningAPI.getPatterns(agentId).catch(() => ({ data: [] })),
        qcLearningAPI.getLearningSessions(agentId).catch(() => ({ data: [] })),
        qcLearningAPI.getBrainPrompts(agentId).catch(() => ({ data: null }))
      ]);
      
      setPlaybook(playbookRes.data);
      setPlaybookHistory(historyRes.data || []);
      setLearningConfig(configRes.data);
      setLearningStats(statsRes.data);
      setPatterns(patternsRes.data || []);
      setSessions(sessionsRes.data || []);
      setBrainPrompts(brainPromptsRes.data);
      
      if (playbookRes.data?.content?.raw_markdown) {
        setEditedMarkdown(playbookRes.data.content.raw_markdown);
      }
      
      if (brainPromptsRes.data?.prompts) {
        setEditedBrainPrompts(brainPromptsRes.data.prompts);
      }
    } catch (error) {
      console.error('Error fetching learning data:', error);
    } finally {
      setLoading(false);
    }
  }, [agentId, supportsLearning]);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  // Handle learning config update
  const handleConfigUpdate = async (field, value) => {
    try {
      setSavingConfig(true);
      const newConfig = { ...learningConfig, [field]: value };
      await qcLearningAPI.updateLearningConfig(agentId, newConfig);
      setLearningConfig(newConfig);
      toast({
        title: 'Settings Updated',
        description: 'Learning configuration saved'
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update settings',
        variant: 'destructive'
      });
    } finally {
      setSavingConfig(false);
    }
  };
  
  // Handle trigger learning
  const handleTriggerLearning = async () => {
    try {
      setTriggering(true);
      const response = await qcLearningAPI.triggerLearning(agentId);
      
      if (response.data.success) {
        toast({
          title: 'Learning Complete',
          description: response.data.message
        });
        // Refresh data
        fetchData();
      } else {
        toast({
          title: 'Learning Failed',
          description: response.data.message,
          variant: 'destructive'
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to trigger learning',
        variant: 'destructive'
      });
    } finally {
      setTriggering(false);
    }
  };
  
  // Handle playbook save
  const handleSavePlaybook = async () => {
    try {
      setSavingPlaybook(true);
      await qcLearningAPI.updatePlaybook(agentId, {
        raw_markdown: editedMarkdown
      });
      
      setIsEditing(false);
      toast({
        title: 'Playbook Saved',
        description: 'Your changes have been saved'
      });
      fetchData();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save playbook',
        variant: 'destructive'
      });
    } finally {
      setSavingPlaybook(false);
    }
  };
  
  // Handle restore version
  const handleRestoreVersion = async (version) => {
    try {
      await qcLearningAPI.restorePlaybookVersion(agentId, version);
      toast({
        title: 'Version Restored',
        description: `Restored version ${version} as the current playbook`
      });
      fetchData();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to restore version',
        variant: 'destructive'
      });
    }
  };
  
  // Handle brain prompt save
  const handleSaveBrainPrompts = async () => {
    try {
      setSavingBrainPrompts(true);
      await qcLearningAPI.updateBrainPrompts(agentId, editedBrainPrompts);
      
      setEditingBrain(null);
      toast({
        title: 'Brain Prompts Saved',
        description: 'Your custom prompts have been saved'
      });
      fetchData();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save brain prompts',
        variant: 'destructive'
      });
    } finally {
      setSavingBrainPrompts(false);
    }
  };
  
  // Handle reset brain prompts to defaults
  const handleResetBrainPrompts = async () => {
    try {
      setSavingBrainPrompts(true);
      await qcLearningAPI.updateBrainPrompts(agentId, { reset_to_defaults: true });
      
      toast({
        title: 'Prompts Reset',
        description: 'Brain prompts reset to defaults'
      });
      fetchData();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to reset prompts',
        variant: 'destructive'
      });
    } finally {
      setSavingBrainPrompts(false);
    }
  };
  
  // Handle preview brain prompt
  const handlePreviewBrain = async (brainType) => {
    try {
      setPreviewingBrain(brainType);
      const response = await qcLearningAPI.previewBrainPrompts(agentId, { brain_type: brainType });
      setBrainPreview(response.data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to generate preview',
        variant: 'destructive'
      });
      setBrainPreview(null);
    } finally {
      setPreviewingBrain(null);
    }
  };
  
  if (!supportsLearning) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-8 text-center">
          <Brain className="h-12 w-12 mx-auto mb-3 text-gray-400" />
          <h3 className="font-medium mb-2">Learning Not Available</h3>
          <p className="text-sm text-gray-500">
            Tech Issues agents are diagnostic-only and do not support the learning system.
          </p>
        </CardContent>
      </Card>
    );
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Playbook Version</p>
                <p className="text-2xl font-bold">v{playbook?.version || 1}</p>
              </div>
              <BookOpen className="h-8 w-8 text-blue-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Prediction Accuracy</p>
                <p className="text-2xl font-bold">
                  {learningStats?.average_prediction_accuracy 
                    ? `${(learningStats.average_prediction_accuracy * 100).toFixed(1)}%`
                    : 'N/A'}
                </p>
              </div>
              <Target className="h-8 w-8 text-green-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Patterns Learned</p>
                <p className="text-2xl font-bold">{learningStats?.patterns_learned || 0}</p>
              </div>
              <Sparkles className="h-8 w-8 text-purple-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Verified Outcomes</p>
                <p className="text-2xl font-bold">{learningStats?.verified_outcomes || 0}</p>
              </div>
              <BarChart3 className="h-8 w-8 text-orange-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="playbook">
            <BookOpen className="h-4 w-4 mr-2" />
            Playbook
          </TabsTrigger>
          <TabsTrigger value="brains">
            <Cpu className="h-4 w-4 mr-2" />
            Brains
          </TabsTrigger>
          <TabsTrigger value="learning">
            <Brain className="h-4 w-4 mr-2" />
            Learning Settings
          </TabsTrigger>
          <TabsTrigger value="patterns">
            <Sparkles className="h-4 w-4 mr-2" />
            Patterns ({patterns.length})
          </TabsTrigger>
          <TabsTrigger value="history">
            <History className="h-4 w-4 mr-2" />
            History
          </TabsTrigger>
        </TabsList>
        
        {/* Playbook Tab */}
        <TabsContent value="playbook" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-blue-500" />
                    Active Playbook
                    <Badge variant="outline">v{playbook?.version || 1}</Badge>
                  </CardTitle>
                  <CardDescription>
                    This playbook is injected into every QC analysis prompt
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          setIsEditing(false);
                          setEditedMarkdown(playbook?.content?.raw_markdown || '');
                        }}
                      >
                        Cancel
                      </Button>
                      <Button 
                        size="sm"
                        onClick={handleSavePlaybook}
                        disabled={savingPlaybook}
                      >
                        <Save className="h-4 w-4 mr-2" />
                        {savingPlaybook ? 'Saving...' : 'Save Changes'}
                      </Button>
                    </>
                  ) : (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setIsEditing(true)}
                    >
                      <Edit3 className="h-4 w-4 mr-2" />
                      Edit Playbook
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isEditing ? (
                <Textarea
                  value={editedMarkdown}
                  onChange={(e) => setEditedMarkdown(e.target.value)}
                  className="font-mono text-sm min-h-[500px]"
                  placeholder="# Playbook content..."
                />
              ) : (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 overflow-auto max-h-[600px]">
                  <pre className="text-sm whitespace-pre-wrap font-mono">
                    {playbook?.content?.raw_markdown || 'No playbook content yet. Trigger a learning session to generate one.'}
                  </pre>
                </div>
              )}
              
              {playbook?.user_edited && (
                <div className="mt-4 flex items-center gap-2 text-sm text-amber-600">
                  <AlertCircle className="h-4 w-4" />
                  This playbook has been manually edited
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Brains Tab */}
        <TabsContent value="brains" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Cpu className="h-5 w-5 text-purple-500" />
                    Learning Brains
                    {brainPrompts?.is_customized && <Badge variant="outline">Customized</Badge>}
                  </CardTitle>
                  <CardDescription>
                    View and customize the prompts sent to the AI during learning sessions
                  </CardDescription>
                </div>
                {brainPrompts?.is_customized && (
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleResetBrainPrompts}
                    disabled={savingBrainPrompts}
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Reset to Defaults
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Reflection Brain */}
              <div className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-full bg-blue-100 dark:bg-blue-900">
                      <Brain className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <h4 className="font-medium">Reflection Brain</h4>
                      <p className="text-sm text-gray-500">Analyzes outcomes to identify patterns</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePreviewBrain('reflection')}
                      disabled={previewingBrain === 'reflection'}
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      {previewingBrain === 'reflection' ? 'Loading...' : 'Preview'}
                    </Button>
                    <Button
                      variant={editingBrain === 'reflection' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setEditingBrain(editingBrain === 'reflection' ? null : 'reflection')}
                    >
                      <Edit3 className="h-4 w-4 mr-2" />
                      {editingBrain === 'reflection' ? 'Close' : 'Edit'}
                    </Button>
                  </div>
                </div>
                
                {editingBrain === 'reflection' && (
                  <div className="space-y-4 mt-4 pt-4 border-t">
                    <div>
                      <Label>System Prompt</Label>
                      <Textarea
                        value={editedBrainPrompts.reflection_system_prompt || ''}
                        onChange={(e) => setEditedBrainPrompts({...editedBrainPrompts, reflection_system_prompt: e.target.value})}
                        className="font-mono text-sm mt-2"
                        rows={3}
                        placeholder="System prompt for the reflection brain..."
                      />
                    </div>
                    <div>
                      <Label>Prefix (added before dynamic content)</Label>
                      <Textarea
                        value={editedBrainPrompts.reflection_prefix || ''}
                        onChange={(e) => setEditedBrainPrompts({...editedBrainPrompts, reflection_prefix: e.target.value})}
                        className="font-mono text-sm mt-2"
                        rows={4}
                        placeholder="Custom instructions added at the start..."
                      />
                    </div>
                    <div>
                      <Label>Suffix (added after dynamic content)</Label>
                      <Textarea
                        value={editedBrainPrompts.reflection_suffix || ''}
                        onChange={(e) => setEditedBrainPrompts({...editedBrainPrompts, reflection_suffix: e.target.value})}
                        className="font-mono text-sm mt-2"
                        rows={4}
                        placeholder="Custom instructions added at the end..."
                      />
                    </div>
                  </div>
                )}
                
                {brainPreview?.brain_type === 'reflection' && (
                  <div className="mt-4 pt-4 border-t">
                    <h5 className="font-medium mb-2 flex items-center gap-2">
                      <Code className="h-4 w-4" />
                      Full Prompt Preview
                    </h5>
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 max-h-[400px] overflow-auto">
                      <p className="text-xs text-gray-500 mb-2">System: {brainPreview.system_prompt}</p>
                      <pre className="text-sm whitespace-pre-wrap font-mono">{brainPreview.full_task_prompt}</pre>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Training Brain */}
              <div className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-full bg-green-100 dark:bg-green-900">
                      <Sparkles className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <h4 className="font-medium">Training Brain</h4>
                      <p className="text-sm text-gray-500">Synthesizes patterns into playbooks</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePreviewBrain('training')}
                      disabled={previewingBrain === 'training'}
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      {previewingBrain === 'training' ? 'Loading...' : 'Preview'}
                    </Button>
                    <Button
                      variant={editingBrain === 'training' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setEditingBrain(editingBrain === 'training' ? null : 'training')}
                    >
                      <Edit3 className="h-4 w-4 mr-2" />
                      {editingBrain === 'training' ? 'Close' : 'Edit'}
                    </Button>
                  </div>
                </div>
                
                {editingBrain === 'training' && (
                  <div className="space-y-4 mt-4 pt-4 border-t">
                    <div>
                      <Label>System Prompt</Label>
                      <Textarea
                        value={editedBrainPrompts.training_system_prompt || ''}
                        onChange={(e) => setEditedBrainPrompts({...editedBrainPrompts, training_system_prompt: e.target.value})}
                        className="font-mono text-sm mt-2"
                        rows={3}
                        placeholder="System prompt for the training brain..."
                      />
                    </div>
                    <div>
                      <Label>Prefix (added before dynamic content)</Label>
                      <Textarea
                        value={editedBrainPrompts.training_prefix || ''}
                        onChange={(e) => setEditedBrainPrompts({...editedBrainPrompts, training_prefix: e.target.value})}
                        className="font-mono text-sm mt-2"
                        rows={4}
                        placeholder="Custom instructions added at the start..."
                      />
                    </div>
                    <div>
                      <Label>Suffix (added after dynamic content)</Label>
                      <Textarea
                        value={editedBrainPrompts.training_suffix || ''}
                        onChange={(e) => setEditedBrainPrompts({...editedBrainPrompts, training_suffix: e.target.value})}
                        className="font-mono text-sm mt-2"
                        rows={4}
                        placeholder="Custom instructions added at the end..."
                      />
                    </div>
                  </div>
                )}
                
                {brainPreview?.brain_type === 'training' && (
                  <div className="mt-4 pt-4 border-t">
                    <h5 className="font-medium mb-2 flex items-center gap-2">
                      <Code className="h-4 w-4" />
                      Full Prompt Preview
                    </h5>
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 max-h-[400px] overflow-auto">
                      <p className="text-xs text-gray-500 mb-2">System: {brainPreview.system_prompt}</p>
                      <pre className="text-sm whitespace-pre-wrap font-mono">{brainPreview.full_task_prompt}</pre>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Custom Instructions */}
              <div className="border rounded-lg p-4">
                <Label>Custom Instructions (Applied to Both Brains)</Label>
                <Textarea
                  value={editedBrainPrompts.custom_instructions || ''}
                  onChange={(e) => setEditedBrainPrompts({...editedBrainPrompts, custom_instructions: e.target.value})}
                  className="font-mono text-sm mt-2"
                  rows={3}
                  placeholder="Additional instructions applied to both brains..."
                />
              </div>
              
              {/* Save Button */}
              {(editingBrain || editedBrainPrompts.custom_instructions) && (
                <div className="flex justify-end">
                  <Button onClick={handleSaveBrainPrompts} disabled={savingBrainPrompts}>
                    <Save className="h-4 w-4 mr-2" />
                    {savingBrainPrompts ? 'Saving...' : 'Save Brain Prompts'}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
          
          {/* Info Card */}
          <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200">
            <CardContent className="pt-4">
              <div className="flex gap-3">
                <AlertCircle className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-900 dark:text-blue-100">How Brain Prompts Work</h4>
                  <ul className="text-sm text-blue-700 dark:text-blue-300 mt-2 space-y-1">
                    <li>• <strong>Reflection Brain</strong>: Runs after outcomes are recorded. Analyzes what worked/didn&apos;t work.</li>
                    <li>• <strong>Training Brain</strong>: Runs after reflection. Turns insights into playbook updates.</li>
                    <li>• <strong>Prefix/Suffix</strong>: Your custom text added before/after the auto-generated analysis content.</li>
                    <li>• Changes take effect on the next learning session.</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Learning Settings Tab */}
        <TabsContent value="learning" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-gray-500" />
                Learning Configuration
              </CardTitle>
              <CardDescription>
                Control how and when the agent learns from QC analyses
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Enable/Disable Learning */}
              <div className="flex items-center justify-between">
                <div>
                  <Label>Enable Learning</Label>
                  <p className="text-sm text-gray-500">Allow this agent to learn from outcomes</p>
                </div>
                <Switch
                  checked={learningConfig?.is_enabled ?? true}
                  onCheckedChange={(v) => handleConfigUpdate('is_enabled', v)}
                  disabled={savingConfig}
                />
              </div>
              
              {/* Learning Mode */}
              <div className="space-y-2">
                <Label>Learning Mode</Label>
                <Select
                  value={learningConfig?.mode || 'manual'}
                  onValueChange={(v) => handleConfigUpdate('mode', v)}
                  disabled={savingConfig}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">
                      <div className="flex items-center gap-2">
                        <Play className="h-4 w-4" />
                        Manual - Only when you click Train
                      </div>
                    </SelectItem>
                    <SelectItem value="auto">
                      <div className="flex items-center gap-2">
                        <Zap className="h-4 w-4" />
                        Auto - After each appointment outcome
                      </div>
                    </SelectItem>
                    <SelectItem value="every_x">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4" />
                        Every X - After X appointment outcomes
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {/* Trigger Count (for every_x mode) */}
              {learningConfig?.mode === 'every_x' && (
                <div className="space-y-2">
                  <Label>Trigger After X Outcomes</Label>
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    value={learningConfig?.trigger_count || 10}
                    onChange={(e) => handleConfigUpdate('trigger_count', parseInt(e.target.value))}
                    disabled={savingConfig}
                  />
                  <p className="text-xs text-gray-500">
                    Currently {learningConfig?.outcomes_since_last_learning || 0} outcomes since last learning
                  </p>
                </div>
              )}
              
              {/* Manual Trigger */}
              <div className="pt-4 border-t">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Train Now</Label>
                    <p className="text-sm text-gray-500">
                      Manually trigger a learning session ({learningStats?.verified_outcomes || 0} outcomes available)
                    </p>
                  </div>
                  <Button 
                    onClick={handleTriggerLearning}
                    disabled={triggering || (learningStats?.verified_outcomes || 0) < 5}
                  >
                    <Brain className="h-4 w-4 mr-2" />
                    {triggering ? 'Training...' : 'Train Agent'}
                  </Button>
                </div>
                {(learningStats?.verified_outcomes || 0) < 5 && (
                  <p className="text-xs text-amber-600 mt-2">
                    Need at least 5 verified outcomes to train. Currently have {learningStats?.verified_outcomes || 0}.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
          
          {/* Stats Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-green-500" />
                Learning Statistics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-2xl font-bold text-green-600">{learningStats?.showed_count || 0}</p>
                  <p className="text-sm text-gray-500">Showed</p>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-2xl font-bold text-red-600">{learningStats?.no_show_count || 0}</p>
                  <p className="text-sm text-gray-500">No-Shows</p>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">{learningStats?.total_analyses || 0}</p>
                  <p className="text-sm text-gray-500">Total Analyses</p>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-2xl font-bold text-purple-600">{learningStats?.learning_sessions || 0}</p>
                  <p className="text-sm text-gray-500">Training Sessions</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Patterns Tab */}
        <TabsContent value="patterns" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-500" />
                Learned Patterns
              </CardTitle>
              <CardDescription>
                Patterns identified from QC analyses and appointment outcomes
              </CardDescription>
            </CardHeader>
            <CardContent>
              {patterns.length === 0 ? (
                <div className="text-center py-8">
                  <Sparkles className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                  <p className="text-gray-500">No patterns learned yet</p>
                  <p className="text-sm text-gray-400 mt-1">
                    Run QC analyses and record outcomes to start learning
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Victory Patterns */}
                  <div>
                    <h4 className="font-medium text-green-600 mb-2 flex items-center gap-2">
                      <CheckCircle className="h-4 w-4" />
                      Victory Patterns (Predict Showed)
                    </h4>
                    {patterns.filter(p => p.outcome_impact === 'showed').map((pattern) => (
                      <div 
                        key={pattern.id}
                        className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg mb-2"
                      >
                        <div>
                          <p className="font-medium">{pattern.signal}</p>
                          <p className="text-sm text-gray-500">
                            {pattern.sample_size} samples • {(pattern.confidence * 100).toFixed(0)}% confidence
                          </p>
                        </div>
                        <Badge variant="outline" className="text-green-600">
                          +{(pattern.impact_percentage * 100).toFixed(0)}%
                        </Badge>
                      </div>
                    ))}
                  </div>
                  
                  {/* Defeat Patterns */}
                  <div className="mt-6">
                    <h4 className="font-medium text-red-600 mb-2 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4" />
                      Defeat Patterns (Predict No-Show)
                    </h4>
                    {patterns.filter(p => p.outcome_impact === 'no_show').map((pattern) => (
                      <div 
                        key={pattern.id}
                        className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg mb-2"
                      >
                        <div>
                          <p className="font-medium">{pattern.signal}</p>
                          <p className="text-sm text-gray-500">
                            {pattern.sample_size} samples • {(pattern.confidence * 100).toFixed(0)}% confidence
                          </p>
                        </div>
                        <Badge variant="outline" className="text-red-600">
                          +{(pattern.impact_percentage * 100).toFixed(0)}% no-show
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5 text-gray-500" />
                Playbook History
              </CardTitle>
              <CardDescription>
                Previous versions of the playbook that can be restored
              </CardDescription>
            </CardHeader>
            <CardContent>
              {playbookHistory.length === 0 ? (
                <div className="text-center py-8">
                  <History className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                  <p className="text-gray-500">No history yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {playbookHistory.map((version) => (
                    <div 
                      key={version.id}
                      className={`flex items-center justify-between p-4 rounded-lg border ${
                        version.is_current ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${version.is_current ? 'bg-blue-100' : 'bg-gray-100'}`}>
                          <BookOpen className={`h-4 w-4 ${version.is_current ? 'text-blue-600' : 'text-gray-500'}`} />
                        </div>
                        <div>
                          <p className="font-medium flex items-center gap-2">
                            Version {version.version}
                            {version.is_current && <Badge>Current</Badge>}
                            {version.user_edited && <Badge variant="outline">Edited</Badge>}
                          </p>
                          <p className="text-sm text-gray-500">
                            {new Date(version.created_at).toLocaleDateString()} • 
                            {version.patterns_count} patterns • 
                            {(version.prediction_accuracy * 100).toFixed(1)}% accuracy
                          </p>
                        </div>
                      </div>
                      {!version.is_current && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRestoreVersion(version.version)}
                        >
                          <RotateCcw className="h-4 w-4 mr-2" />
                          Restore
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
          
          {/* Learning Sessions */}
          <Card>
            <CardHeader>
              <CardTitle>Learning Sessions</CardTitle>
              <CardDescription>Recent training runs</CardDescription>
            </CardHeader>
            <CardContent>
              {sessions.length === 0 ? (
                <p className="text-center py-4 text-gray-500">No learning sessions yet</p>
              ) : (
                <div className="space-y-2">
                  {sessions.map((session) => (
                    <div 
                      key={session.id}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        {session.success ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : (
                          <AlertCircle className="h-5 w-5 text-red-500" />
                        )}
                        <div>
                          <p className="font-medium">
                            {session.trigger === 'manual' ? 'Manual Training' : 
                             session.trigger === 'auto' ? 'Auto Training' : 'Scheduled Training'}
                          </p>
                          <p className="text-sm text-gray-500">
                            {new Date(session.started_at).toLocaleString()} • 
                            {session.analyses_reviewed_count} analyses reviewed
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium">
                          v{session.playbook_version_before || '?'} → v{session.playbook_version_after || '?'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {session.patterns_identified} patterns identified
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default QCPlaybookManager;
