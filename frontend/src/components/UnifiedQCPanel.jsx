import React, { useState, useEffect } from 'react';
import { 
  Brain, 
  Mic, 
  FileText, 
  Zap,
  Settings,
  X,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Plus,
  Check,
  AlertCircle,
  Loader2,
  ExternalLink
} from 'lucide-react';
import { qcAgentsAPI, agentAPI } from '../services/api';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { useToast } from '../hooks/use-toast';

// QC Agent type configurations
const QC_TYPES = {
  tech: {
    icon: Zap,
    label: 'Tech/Latency',
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/20',
    field: 'tech_issues_qc_agent_id',
    agentType: 'tech_issues',
    description: 'Analyzes latency, performance bottlenecks'
  },
  script: {
    icon: FileText,
    label: 'Script Quality',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/20',
    field: 'language_pattern_qc_agent_id',
    agentType: 'language_pattern',
    description: 'Analyzes conversation quality, brevity'
  },
  tonality: {
    icon: Mic,
    label: 'Tonality',
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/20',
    field: 'tonality_qc_agent_id',
    agentType: 'tonality',
    description: 'Analyzes voice delivery, emotion'
  }
};

/**
 * QC Agent Assignment Card
 * Shows the assigned QC agent for a specific type, allows changing assignment
 */
const QCAgentCard = ({ 
  type, 
  config, 
  assignedAgentId, 
  availableAgents, 
  onAssign, 
  onAnalyze,
  analyzing,
  hasResults,
  isExpanded,
  onToggleExpand
}) => {
  const IconComponent = config.icon;
  const assignedAgent = availableAgents.find(a => a.id === assignedAgentId);
  
  return (
    <div className={`border rounded-lg overflow-hidden ${assignedAgent ? 'border-gray-700' : 'border-dashed border-gray-600'}`}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 bg-gray-800/50 cursor-pointer hover:bg-gray-800"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${config.bgColor}`}>
            <IconComponent className={`h-5 w-5 ${config.color}`} />
          </div>
          <div>
            <h3 className="text-white font-medium flex items-center gap-2">
              {config.label}
              {assignedAgent ? (
                <Badge className="bg-green-500/20 text-green-400 text-xs">{assignedAgent.name}</Badge>
              ) : (
                <Badge variant="outline" className="text-gray-500 text-xs">Not Assigned</Badge>
              )}
            </h3>
            <p className="text-xs text-gray-400">{config.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasResults && (
            <Badge className="bg-blue-500/20 text-blue-400 text-xs">
              <Check size={12} className="mr-1" />
              Analyzed
            </Badge>
          )}
          {isExpanded ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4 border-t border-gray-700 space-y-4">
          {/* Agent Assignment */}
          <div>
            <Label className="text-gray-300 text-sm mb-2 block">Assigned QC Agent</Label>
            <Select
              value={assignedAgentId || "none"}
              onValueChange={(v) => onAssign(v === "none" ? null : v)}
            >
              <SelectTrigger className="bg-gray-800 border-gray-700">
                <SelectValue placeholder="Select a QC agent" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None (Use defaults)</SelectItem>
                {availableAgents.map(agent => (
                  <SelectItem key={agent.id} value={agent.id}>
                    {agent.name}
                    {agent.description && (
                      <span className="text-gray-500 ml-2 text-xs">- {agent.description.slice(0, 30)}...</span>
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {availableAgents.length === 0 && (
              <p className="text-xs text-gray-500 mt-2">
                No {config.label} QC agents found.{' '}
                <a href={`/qc/agents/new?type=${config.agentType}`} className="text-purple-400 hover:underline">
                  Create one →
                </a>
              </p>
            )}
          </div>

          {/* Agent Details (if assigned) */}
          {assignedAgent && (
            <div className="bg-gray-900/50 rounded-lg p-3 text-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400">Using settings from:</span>
                <a 
                  href={`/qc/agents/${assignedAgent.id}`}
                  className="text-purple-400 hover:underline flex items-center gap-1"
                >
                  Edit Agent <ExternalLink size={12} />
                </a>
              </div>
              <div className="text-xs text-gray-500 space-y-1">
                <p><strong>Provider:</strong> {assignedAgent.llm_provider || 'Default'}</p>
                <p><strong>Model:</strong> {assignedAgent.llm_model || 'Default'}</p>
                {assignedAgent.kb_items?.length > 0 && (
                  <p><strong>KB Items:</strong> {assignedAgent.kb_items.length}</p>
                )}
              </div>
            </div>
          )}

          {/* Analyze Button */}
          <Button
            onClick={onAnalyze}
            disabled={analyzing}
            className={`w-full ${config.bgColor} hover:opacity-90 text-white`}
          >
            {analyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Run {config.label} Analysis
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
};

/**
 * Unified QC Panel
 * Shows QC agents assigned to the voice agent that made the call
 * Allows inline assignment and analysis
 */
const UnifiedQCPanel = ({ 
  isOpen, 
  onClose, 
  callData,
  voiceAgentId,
  voiceAgentName,
  onAnalyze,
  techResults,
  scriptResults,
  tonalityResults,
  analyzingType
}) => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [expandedType, setExpandedType] = useState('tech');
  
  // Voice agent's QC assignments
  const [assignments, setAssignments] = useState({
    tech_issues_qc_agent_id: null,
    language_pattern_qc_agent_id: null,
    tonality_qc_agent_id: null
  });
  
  // Available QC agents by type
  const [qcAgentsByType, setQcAgentsByType] = useState({
    tech_issues: [],
    language_pattern: [],
    tonality: []
  });

  useEffect(() => {
    if (isOpen && voiceAgentId) {
      fetchData();
    }
  }, [isOpen, voiceAgentId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch voice agent to get current QC assignments
      const agentRes = await agentAPI.get(voiceAgentId);
      const agent = agentRes.data;
      
      setAssignments({
        tech_issues_qc_agent_id: agent.tech_issues_qc_agent_id || null,
        language_pattern_qc_agent_id: agent.language_pattern_qc_agent_id || null,
        tonality_qc_agent_id: agent.tonality_qc_agent_id || null
      });
      
      // Fetch all QC agents
      const qcRes = await qcAgentsAPI.list();
      const allQCAgents = qcRes.data || [];
      
      // Group by type
      setQcAgentsByType({
        tech_issues: allQCAgents.filter(a => a.agent_type === 'tech_issues'),
        language_pattern: allQCAgents.filter(a => a.agent_type === 'language_pattern'),
        tonality: allQCAgents.filter(a => a.agent_type === 'tonality')
      });
      
    } catch (error) {
      console.error('Error fetching QC data:', error);
      toast({
        title: "Error",
        description: "Failed to load QC agent assignments",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async (field, qcAgentId) => {
    try {
      setSaving(true);
      
      // Update voice agent with new QC assignment
      await agentAPI.update(voiceAgentId, {
        [field]: qcAgentId
      });
      
      setAssignments(prev => ({
        ...prev,
        [field]: qcAgentId
      }));
      
      toast({
        title: "Assignment Updated",
        description: qcAgentId 
          ? "QC agent assigned successfully" 
          : "QC agent unassigned"
      });
      
    } catch (error) {
      console.error('Error updating assignment:', error);
      toast({
        title: "Error",
        description: "Failed to update assignment",
        variant: "destructive"
      });
    } finally {
      setSaving(false);
    }
  };

  const handleAnalyze = (type) => {
    const config = QC_TYPES[type];
    const qcAgentId = assignments[config.field];
    
    // Pass the QC agent ID to the analysis function
    onAnalyze(type, qcAgentId);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg border border-gray-700 max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <Brain className="h-6 w-6 text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">QC Analysis</h2>
              <p className="text-sm text-gray-400">
                Voice Agent: <span className="text-purple-400">{voiceAgentName || 'Unknown'}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-gray-800"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Info Banner */}
              <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 border border-purple-700/30 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-purple-400 mt-0.5" />
                  <div>
                    <h4 className="text-white font-medium">QC Agents for this Voice Agent</h4>
                    <p className="text-sm text-gray-400 mt-1">
                      Assign QC agents to analyze calls from <strong>{voiceAgentName}</strong>. 
                      Each QC agent has its own LLM settings, prompts, and knowledge base.
                    </p>
                  </div>
                </div>
              </div>

              {/* QC Agent Cards */}
              <QCAgentCard
                type="tech"
                config={QC_TYPES.tech}
                assignedAgentId={assignments.tech_issues_qc_agent_id}
                availableAgents={qcAgentsByType.tech_issues}
                onAssign={(id) => handleAssign('tech_issues_qc_agent_id', id)}
                onAnalyze={() => handleAnalyze('tech')}
                analyzing={analyzingType === 'tech'}
                hasResults={!!techResults}
                isExpanded={expandedType === 'tech'}
                onToggleExpand={() => setExpandedType(expandedType === 'tech' ? null : 'tech')}
              />

              <QCAgentCard
                type="script"
                config={QC_TYPES.script}
                assignedAgentId={assignments.language_pattern_qc_agent_id}
                availableAgents={qcAgentsByType.language_pattern}
                onAssign={(id) => handleAssign('language_pattern_qc_agent_id', id)}
                onAnalyze={() => handleAnalyze('script')}
                analyzing={analyzingType === 'script'}
                hasResults={!!scriptResults}
                isExpanded={expandedType === 'script'}
                onToggleExpand={() => setExpandedType(expandedType === 'script' ? null : 'script')}
              />

              <QCAgentCard
                type="tonality"
                config={QC_TYPES.tonality}
                assignedAgentId={assignments.tonality_qc_agent_id}
                availableAgents={qcAgentsByType.tonality}
                onAssign={(id) => handleAssign('tonality_qc_agent_id', id)}
                onAnalyze={() => handleAnalyze('tonality')}
                analyzing={analyzingType === 'tonality'}
                hasResults={!!tonalityResults}
                isExpanded={expandedType === 'tonality'}
                onToggleExpand={() => setExpandedType(expandedType === 'tonality' ? null : 'tonality')}
              />

              {/* Quick Create Links */}
              <div className="pt-4 border-t border-gray-700">
                <p className="text-sm text-gray-400 mb-3">Need to create QC agents?</p>
                <div className="flex flex-wrap gap-2">
                  <a 
                    href="/qc/agents/new?type=tech_issues"
                    className="text-xs bg-yellow-500/10 text-yellow-400 px-3 py-1.5 rounded-lg hover:bg-yellow-500/20 flex items-center gap-1"
                  >
                    <Plus size={12} /> Tech QC Agent
                  </a>
                  <a 
                    href="/qc/agents/new?type=language_pattern"
                    className="text-xs bg-blue-500/10 text-blue-400 px-3 py-1.5 rounded-lg hover:bg-blue-500/20 flex items-center gap-1"
                  >
                    <Plus size={12} /> Script QC Agent
                  </a>
                  <a 
                    href="/qc/agents/new?type=tonality"
                    className="text-xs bg-purple-500/10 text-purple-400 px-3 py-1.5 rounded-lg hover:bg-purple-500/20 flex items-center gap-1"
                  >
                    <Plus size={12} /> Tonality QC Agent
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-6 border-t border-gray-700 bg-gray-900">
          <Button
            onClick={onClose}
            variant="outline"
            className="border-gray-700"
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

export default UnifiedQCPanel;
