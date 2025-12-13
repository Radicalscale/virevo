import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { ScrollArea } from './ui/scroll-area';
import { Progress } from './ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  AlertCircle,
  CheckCircle2,
  Play,
  Plus,
  Trash2,
  Loader2,
  AlertTriangle,
  Wrench,
  Bot,
  StopCircle,
  ArrowRight,
  Sparkles,
  Check,
  X,
} from 'lucide-react';
import api from '../services/api';

const STATUS_ICONS = {
  initializing: Loader2,
  analyzing: Bot,
  testing: Play,
  identifying_issues: AlertTriangle,
  proposing_fix: Sparkles,
  applying_fix: Wrench,
  retesting: Loader2,
  success: CheckCircle2,
  failed: AlertCircle,
  cancelled: X,
  error: AlertCircle,
  started: Loader2,
  complete: CheckCircle2,
};

const STATUS_COLORS = {
  initializing: 'text-blue-500',
  analyzing: 'text-purple-500',
  testing: 'text-blue-500',
  identifying_issues: 'text-amber-500',
  proposing_fix: 'text-purple-500',
  applying_fix: 'text-green-500',
  retesting: 'text-blue-500',
  success: 'text-green-500',
  failed: 'text-red-500',
  cancelled: 'text-gray-500',
  error: 'text-red-500',
  started: 'text-blue-500',
  complete: 'text-green-500',
};

/**
 * AINodeFixer - AI-powered node sequence analyzer and fixer
 * Iteratively tests, identifies issues, and fixes nodes
 */
const AINodeFixer = ({ agentId, isOpen, onClose, onNodesFixed }) => {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Configuration
  const [selectedNodes, setSelectedNodes] = useState([]);
  const [responses, setResponses] = useState([]);
  const [expectedBehavior, setExpectedBehavior] = useState('');
  const [initialVariables, setInitialVariables] = useState([
    { key: 'customer_name', value: '' }
  ]);
  const [maxIterations, setMaxIterations] = useState(5);
  
  // Running state
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [updates, setUpdates] = useState([]);
  const [currentStatus, setCurrentStatus] = useState(null);
  const [fixedNodes, setFixedNodes] = useState(null);
  const [nodeChanges, setNodeChanges] = useState([]);
  
  const eventSourceRef = useRef(null);
  const updatesEndRef = useRef(null);

  // Load nodes
  const loadNodes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/agents/${agentId}/nodes-for-testing`);
      setNodes(response.data.nodes || []);
    } catch (err) {
      setError('Failed to load nodes: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    if (isOpen && agentId) {
      loadNodes();
    }
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [isOpen, agentId, loadNodes]);

  // Auto-scroll updates
  useEffect(() => {
    if (updatesEndRef.current) {
      updatesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [updates]);

  const addNodeToSequence = (nodeId) => {
    const node = nodes.find(n => n.id === nodeId);
    if (node) {
      setSelectedNodes([...selectedNodes, node]);
      setResponses([...responses, '']);
    }
  };

  const removeNodeFromSequence = (index) => {
    setSelectedNodes(selectedNodes.filter((_, i) => i !== index));
    setResponses(responses.filter((_, i) => i !== index));
  };

  const updateResponse = (index, value) => {
    const newResponses = [...responses];
    newResponses[index] = value;
    setResponses(newResponses);
  };

  const addVariable = () => {
    setInitialVariables([...initialVariables, { key: '', value: '' }]);
  };

  const updateVariable = (index, field, value) => {
    const newVars = [...initialVariables];
    newVars[index][field] = value;
    setInitialVariables(newVars);
  };

  const removeVariable = (index) => {
    setInitialVariables(initialVariables.filter((_, i) => i !== index));
  };

  const startFixer = async () => {
    if (selectedNodes.length === 0) {
      setError('Please select at least one node');
      return;
    }
    if (responses.some(r => !r.trim())) {
      setError('Please provide test responses for each node');
      return;
    }

    setIsRunning(true);
    setError(null);
    setUpdates([]);
    setCurrentStatus(null);
    setFixedNodes(null);
    setNodeChanges([]);

    try {
      // Convert initial variables to object
      const varsObj = {};
      initialVariables.forEach(v => {
        if (v.key.trim()) {
          varsObj[v.key.trim()] = v.value;
        }
      });

      const payload = {
        node_ids: selectedNodes.map(n => n.id),
        test_responses: responses,
        expected_behavior: expectedBehavior,
        initial_variables: Object.keys(varsObj).length > 0 ? varsObj : null,
        max_iterations: maxIterations
      };

      // Use fetch for SSE with cookie auth
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      
      const response = await fetch(`${backendUrl}/api/agents/${agentId}/fix-nodes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',  // Use cookies for authentication
        body: JSON.stringify(payload)
      });

      // Check for auth errors before trying to read stream
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error ${response.status}: ${errorText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.session_id) {
                setSessionId(data.session_id);
              }
              
              if (data.status) {
                setCurrentStatus(data.status);
                
                if (data.status !== 'started' && data.status !== 'complete') {
                  setUpdates(prev => [...prev, {
                    status: data.status,
                    iteration: data.iteration,
                    maxIterations: data.max_iterations,
                    message: data.message,
                    details: data.details,
                    nodeChanges: data.node_changes,
                    testResults: data.test_results,
                    timestamp: new Date()
                  }]);
                }
                
                if (data.node_changes) {
                  setNodeChanges(data.node_changes);
                }
              }
              
              if (data.fixed_nodes) {
                setFixedNodes(data.fixed_nodes);
              }
              
              if (data.status === 'success' || data.status === 'failed' || 
                  data.status === 'cancelled' || data.status === 'error') {
                setIsRunning(false);
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    } catch (err) {
      setError('Fixer failed: ' + err.message);
      setIsRunning(false);
    }
  };

  const cancelFixer = async () => {
    if (sessionId) {
      try {
        await api.post(`/agents/${agentId}/fix-nodes/cancel?session_id=${sessionId}`);
      } catch (e) {
        console.error('Cancel failed:', e);
      }
    }
    setIsRunning(false);
  };

  const applyFixes = async () => {
    if (!fixedNodes) return;

    try {
      const response = await api.post(`/agents/${agentId}/apply-fixed-nodes`, fixedNodes);
      if (response.data.success) {
        onNodesFixed?.(response.data);
        onClose();
      }
    } catch (err) {
      setError('Failed to apply fixes: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (!isOpen) return null;

  // Safe icon/color lookup with fallbacks
  const StatusIcon = (currentStatus && STATUS_ICONS[currentStatus]) || Loader2;
  const statusColor = (currentStatus && STATUS_COLORS[currentStatus]) || 'text-gray-500';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <CardHeader className="flex-shrink-0">
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="text-xl flex items-center gap-2">
                <Wrench className="w-5 h-5 text-purple-500" />
                AI Node Fixer
              </CardTitle>
              <CardDescription>
                AI analyzes, tests, and iteratively fixes your node sequence
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose} disabled={isRunning}>
              ×
            </Button>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-hidden flex gap-4">
          {/* Left Panel - Configuration */}
          <div className="w-1/2 flex flex-col gap-4 overflow-hidden">
            {/* Node Selector */}
            <div className="flex-shrink-0">
              <Label className="text-sm font-medium mb-2 block">Select Nodes to Fix</Label>
              <Select onValueChange={addNodeToSequence} disabled={isRunning}>
                <SelectTrigger>
                  <SelectValue placeholder="Add a node..." />
                </SelectTrigger>
                <SelectContent>
                  {nodes.map(node => (
                    <SelectItem key={node.id} value={node.id}>
                      {node.label || node.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Selected Nodes & Test Responses */}
            <ScrollArea className="flex-1 min-h-0">
              <div className="space-y-3 pr-4">
                {selectedNodes.map((node, index) => (
                  <Card key={`${node.id}-${index}`} className="p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{index + 1}</Badge>
                        <span className="font-medium text-sm">{node.label || node.id}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeNodeFromSequence(index)}
                        disabled={isRunning}
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                    
                    <Label className="text-xs text-muted-foreground">Test Response</Label>
                    <Textarea
                      placeholder="What would a user say at this node?"
                      value={responses[index]}
                      onChange={(e) => updateResponse(index, e.target.value)}
                      className="text-sm mt-1"
                      rows={2}
                      disabled={isRunning}
                    />
                    
                    {index < selectedNodes.length - 1 && (
                      <div className="flex justify-center mt-2">
                        <ArrowRight className="w-4 h-4 text-muted-foreground" />
                      </div>
                    )}
                  </Card>
                ))}

                {selectedNodes.length === 0 && (
                  <div className="text-center text-muted-foreground py-8">
                    Select nodes to create a sequence to fix
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Expected Behavior */}
            <div className="flex-shrink-0">
              <Label className="text-sm font-medium mb-1 block">Expected Behavior (Optional)</Label>
              <Textarea
                placeholder="Describe what should happen... e.g., 'Variables should be extracted and sent to webhook correctly'"
                value={expectedBehavior}
                onChange={(e) => setExpectedBehavior(e.target.value)}
                className="text-sm"
                rows={2}
                disabled={isRunning}
              />
            </div>

            {/* Initial Variables */}
            <div className="flex-shrink-0">
              <div className="flex justify-between items-center mb-2">
                <Label className="text-sm font-medium">Initial Variables</Label>
                <Button variant="ghost" size="sm" onClick={addVariable} disabled={isRunning}>
                  <Plus className="w-4 h-4 mr-1" /> Add
                </Button>
              </div>
              <div className="space-y-2 max-h-24 overflow-y-auto">
                {initialVariables.map((v, i) => (
                  <div key={i} className="flex gap-2">
                    <Input
                      placeholder="Name"
                      value={v.key}
                      onChange={(e) => updateVariable(i, 'key', e.target.value)}
                      className="flex-1"
                      disabled={isRunning}
                    />
                    <Input
                      placeholder="Value"
                      value={v.value}
                      onChange={(e) => updateVariable(i, 'value', e.target.value)}
                      className="flex-1"
                      disabled={isRunning}
                    />
                    <Button variant="ghost" size="sm" onClick={() => removeVariable(i)} disabled={isRunning}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              {!isRunning ? (
                <Button
                  className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600"
                  onClick={startFixer}
                  disabled={selectedNodes.length === 0}
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Start AI Fixer
                </Button>
              ) : (
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={cancelFixer}
                >
                  <StopCircle className="w-4 h-4 mr-2" />
                  Cancel
                </Button>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 text-destructive text-sm">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}
          </div>

          {/* Right Panel - Progress & Results */}
          <div className="w-1/2 flex flex-col overflow-hidden border-l pl-4">
            {/* Current Status */}
            {currentStatus && (
              <Card className={`mb-4 ${currentStatus === 'success' ? 'border-green-500' : currentStatus === 'failed' ? 'border-red-500' : ''}`}>
                <CardContent className="p-3">
                  <div className="flex items-center gap-2">
                    <StatusIcon className={`w-5 h-5 ${statusColor} ${isRunning ? 'animate-spin' : ''}`} />
                    <span className="font-medium capitalize">{currentStatus.replace('_', ' ')}</span>
                  </div>
                  {updates.length > 0 && updates[updates.length - 1]?.iteration && (
                    <div className="mt-2">
                      <Progress 
                        value={(updates[updates.length - 1].iteration / updates[updates.length - 1].maxIterations) * 100} 
                        className="h-2"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Iteration {updates[updates.length - 1].iteration} of {updates[updates.length - 1].maxIterations}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Progress Updates */}
            <Label className="text-sm font-medium mb-2">Progress Log</Label>
            <ScrollArea className="flex-1 min-h-0 border rounded-md p-2">
              <div className="space-y-2">
                {updates.map((update, i) => {
                  const Icon = STATUS_ICONS[update.status] || AlertCircle;
                  const color = STATUS_COLORS[update.status] || 'text-gray-500';
                  
                  return (
                    <div key={i} className="flex gap-2 text-sm">
                      <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${color}`} />
                      <div>
                        <p>{update.message}</p>
                        {update.details?.issues?.length > 0 && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Issues: {update.details.issues.map(i => i.description).join(', ')}
                          </div>
                        )}
                        {update.details?.fixes?.length > 0 && (
                          <div className="text-xs text-green-600 mt-1">
                            Fixes: {update.details.fixes.length} proposed
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
                {updates.length === 0 && !isRunning && (
                  <div className="text-center text-muted-foreground py-8">
                    Progress will appear here when you start the fixer
                  </div>
                )}
                <div ref={updatesEndRef} />
              </div>
            </ScrollArea>

            {/* Changes Made */}
            {nodeChanges.length > 0 && (
              <div className="mt-4">
                <Label className="text-sm font-medium mb-2 block">Changes Made ({nodeChanges.length})</Label>
                <ScrollArea className="max-h-32 border rounded-md p-2">
                  {nodeChanges.map((change, i) => (
                    <div key={i} className="text-xs mb-2">
                      <Badge variant="outline" className="mr-1">{change.node_id}</Badge>
                      <span className="text-muted-foreground">{change.reason}</span>
                    </div>
                  ))}
                </ScrollArea>
              </div>
            )}

            {/* Apply Fixes Button */}
            {fixedNodes && currentStatus === 'success' && (
              <div className="mt-4 flex gap-2">
                <Button
                  className="flex-1 bg-green-600 hover:bg-green-700"
                  onClick={applyFixes}
                >
                  <Check className="w-4 h-4 mr-2" />
                  Apply Fixes to Agent
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setFixedNodes(null);
                    setUpdates([]);
                    setCurrentStatus(null);
                  }}
                >
                  Discard
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AINodeFixer;
