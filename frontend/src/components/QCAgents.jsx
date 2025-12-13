import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Plus, 
  Brain, 
  Mic, 
  FileText, 
  Settings, 
  Trash2, 
  Edit,
  Activity,
  BookOpen,
  ChevronRight,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { useToast } from '../hooks/use-toast';
import { qcAgentsAPI } from '../services/api';

// QC Agent type icons and colors
const QC_AGENT_TYPES = {
  tonality: {
    icon: Mic,
    label: 'Tonality',
    color: 'bg-purple-100 text-purple-700',
    description: 'Voice analysis, ElevenLabs emotional directions'
  },
  language_pattern: {
    icon: FileText,
    label: 'Language Pattern',
    color: 'bg-blue-100 text-blue-700',
    description: 'Script quality, pattern detection, improvement suggestions'
  },
  tech_issues: {
    icon: Settings,
    label: 'Tech Issues',
    color: 'bg-orange-100 text-orange-700',
    description: 'Log analysis, code review, solution generation'
  },
  generic: {
    icon: Brain,
    label: 'Generic',
    color: 'bg-gray-100 text-gray-700',
    description: 'General-purpose QC analysis'
  }
};

/**
 * QC Agent Card Component
 */
const QCAgentCard = ({ agent, onEdit, onDelete, onView }) => {
  const typeConfig = QC_AGENT_TYPES[agent.agent_type] || QC_AGENT_TYPES.generic;
  const IconComponent = typeConfig.icon;
  
  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => onView(agent)}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${typeConfig.color}`}>
              <IconComponent className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg">{agent.name}</CardTitle>
              <Badge variant="outline" className="mt-1">
                {typeConfig.label}
              </Badge>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {agent.is_active ? (
              <Badge className="bg-green-100 text-green-700">Active</Badge>
            ) : (
              <Badge variant="outline" className="text-gray-500">Inactive</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {agent.description || typeConfig.description}
        </p>
        
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              {agent.analyses_run || 0} analyses
            </span>
            <span className="flex items-center gap-1">
              <BookOpen className="h-3 w-3" />
              {agent.kb_items?.length || 0} KB items
            </span>
          </div>
          
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => onEdit(agent)}
            >
              <Edit className="h-4 w-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm"
              className="text-red-500 hover:text-red-700"
              onClick={() => onDelete(agent)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {/* LLM Provider Badge */}
        <div className="mt-3 pt-3 border-t">
          <span className="text-xs text-gray-500">
            LLM: {agent.llm_provider}/{agent.llm_model}
          </span>
        </div>
      </CardContent>
    </Card>
  );
};

/**
 * QC Agents List Page
 */
const QCAgents = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  
  // Fetch QC agents
  const fetchAgents = async () => {
    try {
      setLoading(true);
      const response = await qcAgentsAPI.list();
      setAgents(response.data || []);
    } catch (error) {
      console.error('Error fetching QC agents:', error);
      toast({
        title: 'Error',
        description: 'Failed to load QC agents',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchAgents();
  }, []);
  
  // Filter agents by type
  const getFilteredAgents = () => {
    if (activeTab === 'all') return agents;
    return agents.filter(agent => agent.agent_type === activeTab);
  };
  
  // Handle delete
  const handleDelete = async (agent) => {
    if (deleteConfirm !== agent.id) {
      setDeleteConfirm(agent.id);
      return;
    }
    
    try {
      await qcAgentsAPI.delete(agent.id);
      toast({
        title: 'Success',
        description: 'QC Agent deleted successfully'
      });
      fetchAgents();
    } catch (error) {
      console.error('Error deleting QC agent:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete QC agent',
        variant: 'destructive'
      });
    }
    setDeleteConfirm(null);
  };
  
  // Handle view
  const handleView = (agent) => {
    navigate(`/qc/agents/${agent.id}`);
  };
  
  // Handle edit
  const handleEdit = (agent) => {
    navigate(`/qc/agents/${agent.id}/edit`);
  };
  
  // Handle create
  const handleCreate = (type) => {
    navigate(`/qc/agents/new?type=${type}`);
  };
  
  const filteredAgents = getFilteredAgents();
  
  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">QC Agents</h1>
          <p className="text-gray-600">Manage your Quality Control analysis agents</p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button onClick={() => handleCreate('generic')}>
            <Plus className="h-4 w-4 mr-2" />
            New QC Agent
          </Button>
        </div>
      </div>
      
      {/* Tabs by Type */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-6">
        <TabsList>
          <TabsTrigger value="all">
            All ({agents.length})
          </TabsTrigger>
          <TabsTrigger value="tonality" className="flex items-center gap-1">
            <Mic className="h-4 w-4" />
            Tonality ({agents.filter(a => a.agent_type === 'tonality').length})
          </TabsTrigger>
          <TabsTrigger value="language_pattern" className="flex items-center gap-1">
            <FileText className="h-4 w-4" />
            Language Pattern ({agents.filter(a => a.agent_type === 'language_pattern').length})
          </TabsTrigger>
          <TabsTrigger value="tech_issues" className="flex items-center gap-1">
            <Settings className="h-4 w-4" />
            Tech Issues ({agents.filter(a => a.agent_type === 'tech_issues').length})
          </TabsTrigger>
        </TabsList>
      </Tabs>
      
      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      )}
      
      {/* Empty State */}
      {!loading && filteredAgents.length === 0 && (
        <Card className="p-12 text-center">
          <Brain className="h-12 w-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium mb-2">No QC Agents Yet</h3>
          <p className="text-gray-600 mb-6">
            Create QC agents to analyze your calls for quality, patterns, and improvements.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
            {/* Quick Create Cards */}
            <Card 
              className="cursor-pointer hover:border-purple-500 transition-colors"
              onClick={() => handleCreate('tonality')}
            >
              <CardContent className="p-4 text-center">
                <Mic className="h-8 w-8 mx-auto mb-2 text-purple-600" />
                <h4 className="font-medium">Tonality Agent</h4>
                <p className="text-xs text-gray-500">Voice & emotion analysis</p>
              </CardContent>
            </Card>
            
            <Card 
              className="cursor-pointer hover:border-blue-500 transition-colors"
              onClick={() => handleCreate('language_pattern')}
            >
              <CardContent className="p-4 text-center">
                <FileText className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                <h4 className="font-medium">Language Pattern Agent</h4>
                <p className="text-xs text-gray-500">Script & pattern analysis</p>
              </CardContent>
            </Card>
            
            <Card 
              className="cursor-pointer hover:border-orange-500 transition-colors"
              onClick={() => handleCreate('tech_issues')}
            >
              <CardContent className="p-4 text-center">
                <Settings className="h-8 w-8 mx-auto mb-2 text-orange-600" />
                <h4 className="font-medium">Tech Issues Agent</h4>
                <p className="text-xs text-gray-500">Log & code analysis</p>
              </CardContent>
            </Card>
          </div>
        </Card>
      )}
      
      {/* Agents Grid */}
      {!loading && filteredAgents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAgents.map((agent) => (
            <QCAgentCard
              key={agent.id}
              agent={agent}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onView={handleView}
            />
          ))}
        </div>
      )}
      
      {/* Delete Confirmation Toast */}
      {deleteConfirm && (
        <div className="fixed bottom-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <span className="font-medium text-red-700">Confirm Delete</span>
          </div>
          <p className="text-sm text-red-600 mb-3">
            Click delete again to confirm removal
          </p>
          <div className="flex gap-2">
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => setDeleteConfirm(null)}
            >
              Cancel
            </Button>
            <Button 
              size="sm" 
              variant="destructive"
              onClick={() => handleDelete({ id: deleteConfirm })}
            >
              Delete
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default QCAgents;
