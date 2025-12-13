import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Phone, Clock, TrendingUp, Edit, Trash2, Play, GitBranch, Copy, FlaskConical } from 'lucide-react';
import { agentAPI } from '../services/api';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { useToast } from '../hooks/use-toast';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';

const Agents = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [selectedAgentName, setSelectedAgentName] = useState('');

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await agentAPI.list();
      setAgents(response.data);
    } catch (error) {
      console.error('Error fetching agents:', error);
      toast({
        title: "Error",
        description: "Failed to load agents",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const confirmDelete = (agentId, agentName) => {
    setSelectedAgentId(agentId);
    setSelectedAgentName(agentName);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    try {
      await agentAPI.delete(selectedAgentId);
      setAgents(agents.filter(a => a.id !== selectedAgentId));
      toast({
        title: "Success",
        description: "Agent deleted successfully"
      });
      setDeleteDialogOpen(false);
    } catch (error) {
      console.error('Error deleting agent:', error);
      toast({
        title: "Error",
        description: "Failed to delete agent",
        variant: "destructive"
      });
    }
  };

  const confirmDuplicate = (agentId, agentName) => {
    setSelectedAgentId(agentId);
    setSelectedAgentName(agentName);
    setDuplicateDialogOpen(true);
  };

  const handleDuplicate = async () => {
    try {
      const response = await agentAPI.duplicate(selectedAgentId);
      setAgents([...agents, response.data]);
      toast({
        title: "Success",
        description: `Agent duplicated successfully as "${response.data.name}"`
      });
      setDuplicateDialogOpen(false);
    } catch (error) {
      console.error('Error duplicating agent:', error);
      toast({
        title: "Error",
        description: "Failed to duplicate agent",
        variant: "destructive"
      });
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="text-white text-xl">Loading agents...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">AI Agents</h1>
          <p className="text-gray-400">Create and manage your voice AI agents</p>
        </div>
        <Button
          onClick={() => navigate('/agents/new')}
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/20"
        >
          <Plus size={20} className="mr-2" />
          Create Agent
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent) => (
          <Card key={agent.id} className="bg-gray-800 border-gray-700 hover:border-gray-600 transition-all duration-200 overflow-hidden">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-xl">
                  {agent.name.charAt(0)}
                </div>
                <Badge className={agent.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}>
                  {agent.status}
                </Badge>
              </div>

              <h3 className="text-xl font-semibold text-white mb-2">{agent.name}</h3>
              <p className="text-gray-400 text-sm mb-4 line-clamp-2">{agent.description}</p>

              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400 flex items-center gap-2">
                    <Phone size={16} />
                    Calls
                  </span>
                  <span className="text-white font-medium">{agent.callsHandled}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400 flex items-center gap-2">
                    <Clock size={16} />
                    Latency
                  </span>
                  <span className="text-white font-medium">{agent.avgLatency}s</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400 flex items-center gap-2">
                    <TrendingUp size={16} />
                    Success
                  </span>
                  <span className="text-green-400 font-medium">{agent.successRate}%</span>
                </div>
              </div>

              <div className="grid grid-cols-5 gap-2">
                <Button
                  onClick={() => navigate(`/agents/${agent.id}/flow`)}
                  className="bg-purple-600 hover:bg-purple-700 text-white"
                  size="sm"
                  title="Edit Call Flow"
                >
                  <GitBranch size={16} />
                </Button>
                <Button
                  onClick={() => navigate(`/agents/${agent.id}/test`)}
                  className="bg-cyan-600 hover:bg-cyan-700 text-white"
                  size="sm"
                  title="Test Agent"
                >
                  <FlaskConical size={16} />
                </Button>
                <Button
                  onClick={() => navigate(`/agents/${agent.id}/edit`)}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                  size="sm"
                  title="Edit Agent"
                >
                  <Edit size={16} />
                </Button>
                <Button
                  onClick={() => confirmDuplicate(agent.id, agent.name)}
                  className="bg-green-600 hover:bg-green-700 text-white"
                  size="sm"
                  title="Duplicate Agent"
                >
                  <Copy size={16} />
                </Button>
                <Button
                  onClick={() => confirmDelete(agent.id, agent.name)}
                  className="bg-red-600 hover:bg-red-700 text-white"
                  size="sm"
                  title="Delete Agent"
                >
                  <Trash2 size={16} />
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-gray-800 border-gray-700">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Delete Agent</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              Are you sure you want to delete "{selectedAgentName}"? This action cannot be undone.
              All call flows, settings, and associated data will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-gray-700 text-white hover:bg-gray-600">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 text-white hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Duplicate Confirmation Dialog */}
      <AlertDialog open={duplicateDialogOpen} onOpenChange={setDuplicateDialogOpen}>
        <AlertDialogContent className="bg-gray-800 border-gray-700">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Duplicate Agent</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              Duplicate "{selectedAgentName}"? A copy will be created with "-copy" appended to the name.
              All settings, call flows, and configurations will be copied to the new agent.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-gray-700 text-white hover:bg-gray-600">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDuplicate}
              className="bg-green-600 text-white hover:bg-green-700"
            >
              Duplicate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Agents;
