import React, { useState, useEffect } from 'react';
import { Settings, Zap, ClipboardList, Play, Check, X, ChevronDown, ChevronUp } from 'lucide-react';
import { qcEnhancedAPI } from '../services/api';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { useToast } from '../hooks/use-toast';

const AutoQCSettings = ({ agentId, agentName }) => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [campaigns, setCampaigns] = useState([]);
  const [settings, setSettings] = useState({
    enabled: false,
    campaign_id: null,
    run_tech_analysis: true,
    run_script_analysis: true,
    run_tonality_analysis: true
  });

  useEffect(() => {
    if (agentId) {
      fetchSettings();
      fetchCampaigns();
    }
  }, [agentId]);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await qcEnhancedAPI.getAgentAutoQCSettings(agentId);
      if (response.data?.auto_qc_settings) {
        setSettings(response.data.auto_qc_settings);
        // Auto-expand if enabled
        if (response.data.auto_qc_settings.enabled) {
          setExpanded(true);
        }
      }
    } catch (error) {
      console.error('Error fetching auto QC settings:', error);
      // Don't show error toast - settings may not exist yet
    } finally {
      setLoading(false);
    }
  };

  const fetchCampaigns = async () => {
    try {
      const response = await qcEnhancedAPI.listCampaigns();
      setCampaigns(response.data || []);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await qcEnhancedAPI.updateAgentAutoQCSettings(agentId, settings);
      toast({
        title: "Settings Saved",
        description: settings.enabled 
          ? `Auto QC enabled for ${agentName}` 
          : "Auto QC disabled",
      });
    } catch (error) {
      console.error('Error saving auto QC settings:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save settings",
        variant: "destructive"
      });
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = (enabled) => {
    setSettings(prev => ({ ...prev, enabled }));
    if (enabled) {
      setExpanded(true);
    }
  };

  if (loading) {
    return (
      <Card className="bg-[#1a1a2e] border-gray-800 p-4">
        <div className="flex items-center gap-2 text-gray-400">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-500"></div>
          Loading Auto QC settings...
        </div>
      </Card>
    );
  }

  return (
    <Card className="bg-[#1a1a2e] border-gray-800">
      {/* Header - Always visible */}
      <div 
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-[#252540] rounded-t-lg transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${settings.enabled ? 'bg-purple-500/20' : 'bg-gray-700/50'}`}>
            <Zap className={`h-5 w-5 ${settings.enabled ? 'text-purple-400' : 'text-gray-400'}`} />
          </div>
          <div>
            <h3 className="text-white font-medium flex items-center gap-2">
              Auto QC Analysis
              {settings.enabled && (
                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
                  Active
                </span>
              )}
            </h3>
            <p className="text-sm text-gray-400">
              {settings.enabled 
                ? `Auto-analyzing calls → ${campaigns.find(c => c.id === settings.campaign_id)?.name || 'Select campaign'}`
                : 'Automatically analyze calls when they end'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Switch
            checked={settings.enabled}
            onCheckedChange={handleToggle}
            onClick={(e) => e.stopPropagation()}
          />
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </div>

      {/* Expanded Settings */}
      {expanded && (
        <div className="border-t border-gray-800 p-4 space-y-4">
          {/* Campaign Selection */}
          <div className="space-y-2">
            <Label className="text-gray-300">Target Campaign</Label>
            <Select
              value={settings.campaign_id || ''}
              onValueChange={(value) => setSettings(prev => ({ ...prev, campaign_id: value }))}
            >
              <SelectTrigger className="bg-[#252540] border-gray-700 text-white">
                <SelectValue placeholder="Select a campaign" />
              </SelectTrigger>
              <SelectContent className="bg-[#252540] border-gray-700">
                {campaigns.length === 0 ? (
                  <SelectItem value="no-campaigns" disabled className="text-gray-400">
                    No campaigns available
                  </SelectItem>
                ) : (
                  campaigns.map((campaign) => (
                    <SelectItem key={campaign.id} value={campaign.id} className="text-white hover:bg-[#1a1a2e]">
                      <div className="flex items-center gap-2">
                        <ClipboardList className="h-4 w-4 text-purple-400" />
                        {campaign.name}
                        {campaign.stats && (
                          <span className="text-xs text-gray-400">
                            ({campaign.stats.total_calls || 0} calls)
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
            <p className="text-xs text-gray-500">
              Calls will be automatically added to this campaign after QC analysis
            </p>
          </div>

          {/* Analysis Options */}
          <div className="space-y-3">
            <Label className="text-gray-300">Analyses to Run</Label>
            
            <div className="space-y-2">
              {/* Tech Analysis */}
              <div className="flex items-center justify-between p-3 bg-[#252540] rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-1.5 bg-blue-500/20 rounded">
                    <Settings className="h-4 w-4 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm text-white">Tech/Latency Analysis</p>
                    <p className="text-xs text-gray-400">Analyze response times, bottlenecks</p>
                  </div>
                </div>
                <Switch
                  checked={settings.run_tech_analysis}
                  onCheckedChange={(checked) => setSettings(prev => ({ ...prev, run_tech_analysis: checked }))}
                />
              </div>

              {/* Script Analysis */}
              <div className="flex items-center justify-between p-3 bg-[#252540] rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-1.5 bg-green-500/20 rounded">
                    <ClipboardList className="h-4 w-4 text-green-400" />
                  </div>
                  <div>
                    <p className="text-sm text-white">Script Quality Analysis</p>
                    <p className="text-xs text-gray-400">Evaluate conversation effectiveness</p>
                  </div>
                </div>
                <Switch
                  checked={settings.run_script_analysis}
                  onCheckedChange={(checked) => setSettings(prev => ({ ...prev, run_script_analysis: checked }))}
                />
              </div>

              {/* Tonality Analysis */}
              <div className="flex items-center justify-between p-3 bg-[#252540] rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-1.5 bg-orange-500/20 rounded">
                    <Play className="h-4 w-4 text-orange-400" />
                  </div>
                  <div>
                    <p className="text-sm text-white">Tonality Analysis</p>
                    <p className="text-xs text-gray-400">Assess tone and emotional quality</p>
                  </div>
                </div>
                <Switch
                  checked={settings.run_tonality_analysis}
                  onCheckedChange={(checked) => setSettings(prev => ({ ...prev, run_tonality_analysis: checked }))}
                />
              </div>
            </div>
          </div>

          {/* Info Box */}
          {settings.enabled && !settings.campaign_id && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
              <p className="text-sm text-yellow-400">
                ⚠️ Please select a target campaign for auto QC to work
              </p>
            </div>
          )}

          {/* Save Button */}
          <div className="flex justify-end pt-2">
            <Button 
              onClick={handleSave}
              disabled={saving}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  Save Settings
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
};

export default AutoQCSettings;
