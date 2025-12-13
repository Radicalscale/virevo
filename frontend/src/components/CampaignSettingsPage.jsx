import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Save,
  Trash2,
  AlertTriangle,
  Settings as SettingsIcon,
  Zap,
  Brain,
  Mic,
  FileText,
  Wrench,
  Users,
  Plus,
  X,
  BookOpen,
  Upload
} from 'lucide-react';
import { qcEnhancedAPI, qcAgentsAPI, agentAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Switch } from './ui/switch';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

const AGENT_ROLES = [
  { value: 'first_touch', label: 'First Touch', required: true },
  { value: 'follow_up_pre_appointment', label: 'Follow-up (Pre-Appointment)', required: true },
  { value: 'no_show', label: 'No Show Follow-up', required: false },
  { value: 'second_no_show', label: '2nd No Show', required: false }
];

const CampaignSettingsPage = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  // QC Agents available
  const [qcAgents, setQcAgents] = useState([]);
  const [callAgents, setCallAgents] = useState([]);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rules: {
      analysis_rules: {
        focus_on_brevity: true,
        check_goal_alignment: true,
        evaluate_naturalness: true
      }
    },
    learning_parameters: {},
    linked_agents: [],
    auto_pattern_detection: false,
    // New fields
    campaign_agents: [],
    tonality_qc_agent_id: '',
    language_pattern_qc_agent_id: '',
    tech_issues_qc_agent_id: '',
    custom_prompt_instructions: '',
    auto_analysis_after_n_calls: null,
    auto_analysis_every_n_calls: null,
    crm_integration_enabled: false,
    auto_create_leads: false,
    auto_reanalyze_on_appointment_update: false
  });

  useEffect(() => {
    fetchData();
  }, [campaignId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch campaign
      const campaignRes = await qcEnhancedAPI.getCampaign(campaignId);
      const campaign = campaignRes.data;
      
      setFormData({
        name: campaign.name || '',
        description: campaign.description || '',
        rules: campaign.rules || { analysis_rules: { focus_on_brevity: true, check_goal_alignment: true, evaluate_naturalness: true } },
        learning_parameters: campaign.learning_parameters || {},
        linked_agents: campaign.linked_agents || [],
        auto_pattern_detection: campaign.auto_pattern_detection || false,
        campaign_agents: campaign.campaign_agents || [],
        tonality_qc_agent_id: campaign.tonality_qc_agent_id || '',
        language_pattern_qc_agent_id: campaign.language_pattern_qc_agent_id || '',
        tech_issues_qc_agent_id: campaign.tech_issues_qc_agent_id || '',
        custom_prompt_instructions: campaign.custom_prompt_instructions || '',
        auto_analysis_after_n_calls: campaign.auto_analysis_after_n_calls,
        auto_analysis_every_n_calls: campaign.auto_analysis_every_n_calls,
        crm_integration_enabled: campaign.crm_integration_enabled || false,
        auto_create_leads: campaign.auto_create_leads || false,
        auto_reanalyze_on_appointment_update: campaign.auto_reanalyze_on_appointment_update || false
      });
      
      // Fetch QC Agents
      try {
        const qcRes = await qcAgentsAPI.list();
        setQcAgents(qcRes.data || []);
      } catch (e) {
        console.log('Could not fetch QC agents');
      }
      
      // Fetch call agents (voice agents) for campaign agent selection
      try {
        const agentsRes = await agentAPI.list();
        setCallAgents(agentsRes.data || []);
      } catch (e) {
        console.log('Could not fetch call agents');
      }
      
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({
        title: "Error",
        description: "Failed to load campaign settings",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleRuleChange = (rule, value) => {
    setFormData(prev => ({
      ...prev,
      rules: {
        ...prev.rules,
        analysis_rules: {
          ...prev.rules.analysis_rules,
          [rule]: value
        }
      }
    }));
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast({ title: "Error", description: "Campaign name is required", variant: "destructive" });
      return;
    }

    try {
      setSaving(true);
      await qcEnhancedAPI.updateCampaign(campaignId, formData);
      toast({ title: "Success", description: "Campaign settings updated" });
      navigate(`/qc/campaigns/${campaignId}`);
    } catch (error) {
      console.error('Error saving:', error);
      toast({ title: "Error", description: "Failed to save settings", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      await qcEnhancedAPI.deleteCampaign(campaignId);
      toast({ title: "Success", description: "Campaign deleted" });
      navigate('/qc/campaigns');
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete campaign", variant: "destructive" });
      setDeleting(false);
    }
  };

  // Add campaign agent role
  const addCampaignAgent = (role) => {
    const existing = formData.campaign_agents.find(a => a.role === role);
    if (existing) return;
    
    setFormData(prev => ({
      ...prev,
      campaign_agents: [...prev.campaign_agents, { role, agent_id: '', agent_name: '', is_required: AGENT_ROLES.find(r => r.value === role)?.required || false }]
    }));
  };

  // Remove campaign agent role
  const removeCampaignAgent = (role) => {
    setFormData(prev => ({
      ...prev,
      campaign_agents: prev.campaign_agents.filter(a => a.role !== role)
    }));
  };

  // Update campaign agent
  const updateCampaignAgent = (role, agentId) => {
    setFormData(prev => ({
      ...prev,
      campaign_agents: prev.campaign_agents.map(a => 
        a.role === role ? { ...a, agent_id: agentId } : a
      )
    }));
  };

  // Filter QC agents by type
  const getQCAgentsByType = (type) => qcAgents.filter(a => a.agent_type === type);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigate(`/qc/campaigns/${campaignId}`)}
              className="flex items-center gap-2 text-gray-400 hover:text-white"
            >
              <ArrowLeft size={20} />
              Back to Campaign
            </button>
            
            <Button onClick={handleSave} disabled={saving}>
              <Save size={18} className="mr-2" />
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
          
          <div className="flex items-center gap-3">
            <SettingsIcon size={32} className="text-purple-400" />
            <div>
              <h1 className="text-3xl font-bold">Campaign Settings</h1>
              <p className="text-gray-400 mt-1">Configure analysis rules, QC agents, and automation</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-6 py-8">
        <Tabs defaultValue="general">
          <TabsList className="bg-gray-900 border border-gray-800 mb-6">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="qc-agents">QC Agents</TabsTrigger>
            <TabsTrigger value="campaign-agents">Campaign Agents</TabsTrigger>
            <TabsTrigger value="automation">Automation</TabsTrigger>
            <TabsTrigger value="crm">CRM Integration</TabsTrigger>
          </TabsList>
          
          {/* General Tab */}
          <TabsContent value="general">
            <Card className="bg-gray-900 border-gray-800 mb-6">
              <CardHeader>
                <CardTitle>Basic Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Campaign Name *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    className="mt-1 bg-gray-800 border-gray-700"
                    placeholder="e.g., Q4 Outbound Sales"
                  />
                </div>
                <div>
                  <Label>Description</Label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                    className="mt-1 bg-gray-800 border-gray-700"
                    rows={3}
                  />
                </div>
                <div>
                  <Label>Custom Prompt Instructions</Label>
                  <Textarea
                    value={formData.custom_prompt_instructions}
                    onChange={(e) => handleInputChange('custom_prompt_instructions', e.target.value)}
                    className="mt-1 bg-gray-800 border-gray-700"
                    rows={4}
                    placeholder="Additional instructions for QC analysis..."
                  />
                  <p className="text-xs text-gray-500 mt-1">These instructions will be included in all QC analyses for this campaign</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle>Analysis Rules</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Focus on Brevity</Label>
                    <p className="text-xs text-gray-500">Check if responses are concise</p>
                  </div>
                  <Switch
                    checked={formData.rules.analysis_rules.focus_on_brevity}
                    onCheckedChange={(v) => handleRuleChange('focus_on_brevity', v)}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Check Goal Alignment</Label>
                    <p className="text-xs text-gray-500">Verify responses align with goals</p>
                  </div>
                  <Switch
                    checked={formData.rules.analysis_rules.check_goal_alignment}
                    onCheckedChange={(v) => handleRuleChange('check_goal_alignment', v)}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Evaluate Naturalness</Label>
                    <p className="text-xs text-gray-500">Assess conversation flow</p>
                  </div>
                  <Switch
                    checked={formData.rules.analysis_rules.evaluate_naturalness}
                    onCheckedChange={(v) => handleRuleChange('evaluate_naturalness', v)}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* QC Agents Tab */}
          <TabsContent value="qc-agents">
            <Card className="bg-gray-900 border-gray-800 mb-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="text-purple-400" />
                  Assign QC Agents
                </CardTitle>
                <CardDescription>
                  Assign specialized QC agents to analyze calls in this campaign
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Tonality QC Agent */}
                <div className="p-4 bg-gray-800/50 rounded-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded bg-purple-900/30">
                      <Mic className="h-5 w-5 text-purple-400" />
                    </div>
                    <div>
                      <h3 className="font-medium">Tonality QC Agent</h3>
                      <p className="text-xs text-gray-500">Voice & emotional analysis</p>
                    </div>
                  </div>
                  <Select
                    value={formData.tonality_qc_agent_id || "none"}
                    onValueChange={(v) => handleInputChange('tonality_qc_agent_id', v === "none" ? "" : v)}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue placeholder="Select a tonality agent" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {getQCAgentsByType('tonality').map(agent => (
                        <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {getQCAgentsByType('tonality').length === 0 && (
                    <Button variant="link" className="mt-2 p-0 h-auto text-purple-400" onClick={() => navigate('/qc/agents/new?type=tonality')}>
                      <Plus size={14} className="mr-1" /> Create Tonality Agent
                    </Button>
                  )}
                </div>

                {/* Language Pattern QC Agent */}
                <div className="p-4 bg-gray-800/50 rounded-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded bg-blue-900/30">
                      <FileText className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <h3 className="font-medium">Language Pattern QC Agent</h3>
                      <p className="text-xs text-gray-500">Script & pattern analysis</p>
                    </div>
                  </div>
                  <Select
                    value={formData.language_pattern_qc_agent_id || "none"}
                    onValueChange={(v) => handleInputChange('language_pattern_qc_agent_id', v === "none" ? "" : v)}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue placeholder="Select a language pattern agent" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {getQCAgentsByType('language_pattern').map(agent => (
                        <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {getQCAgentsByType('language_pattern').length === 0 && (
                    <Button variant="link" className="mt-2 p-0 h-auto text-blue-400" onClick={() => navigate('/qc/agents/new?type=language_pattern')}>
                      <Plus size={14} className="mr-1" /> Create Language Pattern Agent
                    </Button>
                  )}
                </div>

                {/* Tech Issues QC Agent */}
                <div className="p-4 bg-gray-800/50 rounded-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded bg-orange-900/30">
                      <Wrench className="h-5 w-5 text-orange-400" />
                    </div>
                    <div>
                      <h3 className="font-medium">Tech Issues QC Agent</h3>
                      <p className="text-xs text-gray-500">Log & code analysis</p>
                    </div>
                  </div>
                  <Select
                    value={formData.tech_issues_qc_agent_id || "none"}
                    onValueChange={(v) => handleInputChange('tech_issues_qc_agent_id', v === "none" ? "" : v)}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue placeholder="Select a tech issues agent" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {getQCAgentsByType('tech_issues').map(agent => (
                        <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {getQCAgentsByType('tech_issues').length === 0 && (
                    <Button variant="link" className="mt-2 p-0 h-auto text-orange-400" onClick={() => navigate('/qc/agents/new?type=tech_issues')}>
                      <Plus size={14} className="mr-1" /> Create Tech Issues Agent
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Campaign Agents Tab */}
          <TabsContent value="campaign-agents">
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="text-green-400" />
                  Multi-Agent Configuration
                </CardTitle>
                <CardDescription>
                  Configure different call agents for different stages of the customer journey
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {AGENT_ROLES.map(role => {
                    const assigned = formData.campaign_agents.find(a => a.role === role.value);
                    
                    return (
                      <div key={role.value} className="p-4 bg-gray-800/50 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium">{role.label}</h3>
                            {role.required && <Badge variant="outline" className="text-xs">Required</Badge>}
                          </div>
                          {!assigned ? (
                            <Button size="sm" variant="outline" onClick={() => addCampaignAgent(role.value)}>
                              <Plus size={14} className="mr-1" /> Add
                            </Button>
                          ) : (
                            <Button size="sm" variant="ghost" className="text-red-400" onClick={() => removeCampaignAgent(role.value)}>
                              <X size={14} />
                            </Button>
                          )}
                        </div>
                        
                        {assigned && (
                          <Select
                            value={assigned.agent_id || "none"}
                            onValueChange={(v) => updateCampaignAgent(role.value, v === "none" ? "" : v)}
                          >
                            <SelectTrigger className="bg-gray-800 border-gray-700">
                              <SelectValue placeholder="Select a call agent" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">-- Select Agent --</SelectItem>
                              {callAgents.map(agent => (
                                <SelectItem key={agent.id} value={agent.id}>
                                  {agent.name} {agent.agent_type ? `(${agent.agent_type})` : ''}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                        
                        {assigned && callAgents.length === 0 && (
                          <p className="text-xs text-amber-400 mt-2">No call agents found. Create agents first.</p>
                        )}
                      </div>
                    );
                  })}
                </div>
                
                <div className="mt-6 p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                  <h4 className="font-medium text-blue-300 mb-2">How Multi-Agent Campaigns Work</h4>
                  <ul className="text-sm text-gray-400 space-y-1">
                    <li>• <strong>First Touch:</strong> Initial outreach to new leads</li>
                    <li>• <strong>Follow-up:</strong> Pre-appointment confirmation calls</li>
                    <li>• <strong>No Show:</strong> Follow-up after missed appointments</li>
                    <li>• <strong>2nd No Show:</strong> Second attempt after no-show</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Automation Tab */}
          <TabsContent value="automation">
            <Card className="bg-gray-900 border-gray-800 mb-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="text-yellow-400" />
                  Auto Pattern Detection
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <Label>Enable Auto Pattern Detection</Label>
                    <p className="text-xs text-gray-500">Automatically detect patterns when calls are added</p>
                  </div>
                  <Switch
                    checked={formData.auto_pattern_detection}
                    onCheckedChange={(v) => handleInputChange('auto_pattern_detection', v)}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle>Auto-Analysis Triggers</CardTitle>
                <CardDescription>Configure when to automatically run campaign analysis</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Analyze After N Calls</Label>
                  <Input
                    type="number"
                    value={formData.auto_analysis_after_n_calls || ''}
                    onChange={(e) => handleInputChange('auto_analysis_after_n_calls', e.target.value ? parseInt(e.target.value) : null)}
                    className="mt-1 bg-gray-800 border-gray-700 w-32"
                    placeholder="e.g., 10"
                  />
                  <p className="text-xs text-gray-500 mt-1">Run analysis once this many calls are reached</p>
                </div>
                
                <div>
                  <Label>Analyze Every N Calls</Label>
                  <Input
                    type="number"
                    value={formData.auto_analysis_every_n_calls || ''}
                    onChange={(e) => handleInputChange('auto_analysis_every_n_calls', e.target.value ? parseInt(e.target.value) : null)}
                    className="mt-1 bg-gray-800 border-gray-700 w-32"
                    placeholder="e.g., 5"
                  />
                  <p className="text-xs text-gray-500 mt-1">Run analysis every N calls (recurring)</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* CRM Integration Tab */}
          <TabsContent value="crm">
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle>CRM Integration</CardTitle>
                <CardDescription>Connect this campaign to your CRM for lead tracking and appointment re-analysis</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg">
                  <div>
                    <Label>Enable CRM Integration</Label>
                    <p className="text-xs text-gray-500">Connect calls to CRM leads</p>
                  </div>
                  <Switch
                    checked={formData.crm_integration_enabled}
                    onCheckedChange={(v) => handleInputChange('crm_integration_enabled', v)}
                  />
                </div>

                {formData.crm_integration_enabled && (
                  <>
                    <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg">
                      <div>
                        <Label>Auto-Create Leads</Label>
                        <p className="text-xs text-gray-500">Automatically create leads from calls if they don&apos;t exist</p>
                      </div>
                      <Switch
                        checked={formData.auto_create_leads}
                        onCheckedChange={(v) => handleInputChange('auto_create_leads', v)}
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg">
                      <div>
                        <Label>Auto Re-analyze on Appointment Update</Label>
                        <p className="text-xs text-gray-500">Re-run QC analysis when appointment status changes (show/no-show)</p>
                      </div>
                      <Switch
                        checked={formData.auto_reanalyze_on_appointment_update}
                        onCheckedChange={(v) => handleInputChange('auto_reanalyze_on_appointment_update', v)}
                      />
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Delete Section */}
        <Card className="bg-gray-900 border-red-900/50 mt-8">
          <CardHeader>
            <CardTitle className="text-red-400 flex items-center gap-2">
              <AlertTriangle />
              Danger Zone
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-400 mb-4">Deleting this campaign is permanent and cannot be undone.</p>
            
            {!showDeleteConfirm ? (
              <Button variant="destructive" onClick={() => setShowDeleteConfirm(true)}>
                <Trash2 size={16} className="mr-2" />
                Delete Campaign
              </Button>
            ) : (
              <div className="flex items-center gap-3">
                <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
                  {deleting ? 'Deleting...' : 'Confirm Delete'}
                </Button>
                <Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
                  Cancel
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CampaignSettingsPage;
