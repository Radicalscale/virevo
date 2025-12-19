import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Save, Play, Trash2, MessageSquare, Zap, PhoneForwarded, Hash, GitBranch, UserPlus, MessageCircle, FileText, StopCircle, FormInput, MessageSquareText, ArrowRight, Settings, Sparkles, Brain, X, TestTube2, Wrench } from 'lucide-react';
import { agentAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import OptimizeNodeModal from './OptimizeNodeModal';
import OptimizeTransitionModal from './OptimizeTransitionModal';
import TransitionAnalysisModal from './TransitionAnalysisModal';
import NodeSequenceTester from './NodeSequenceTester';
import AINodeFixer from './AINodeFixer';

const FlowBuilder = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [nodes, setNodes] = useState([
    {
      id: '1',
      type: 'start',
      label: 'Begin',
      data: {
        whoSpeaksFirst: 'user', // 'ai' or 'user'
        aiSpeaksAfterSilence: true,
        silenceTimeout: 2000, // milliseconds
        transitions: []
      }
    },
    {
      id: '2',
      type: 'conversation',
      label: 'Greeting',
      data: {
        mode: 'script', // 'prompt' or 'script'
        content: 'Hello! I am an AI assistant. How can I help you today?',
        transitions: [{ id: '1', condition: '', nextNode: '' }]
      }
    }
  ]);

  const [selectedNode, setSelectedNode] = useState(nodes[0]);
  const [loading, setLoading] = useState(true);
  const [agent, setAgent] = useState(null);
  const [showNodePalette, setShowNodePalette] = useState(false);
  const [showOptimizeModal, setShowOptimizeModal] = useState(false);
  const [optimizeContent, setOptimizeContent] = useState('');
  const [showTransitionModal, setShowTransitionModal] = useState(false);
  const [currentTransitionId, setCurrentTransitionId] = useState(null);
  const [transitionContent, setTransitionContent] = useState('');
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);

  // Webhook tester state
  const [webhookTestVariables, setWebhookTestVariables] = useState({});
  const [webhookTestResponse, setWebhookTestResponse] = useState(null);
  const [webhookTestLoading, setWebhookTestLoading] = useState(false);
  const [showWebhookTester, setShowWebhookTester] = useState(false);
  const [customTestVariables, setCustomTestVariables] = useState([]);  // [{name: '', value: ''}]

  // Node sequence tester state
  const [showNodeTester, setShowNodeTester] = useState(false);

  // AI Node Fixer state
  const [showNodeFixer, setShowNodeFixer] = useState(false);

  useEffect(() => {
    fetchAgentFlow();
  }, [id]);

  const fetchAgentFlow = async () => {
    try {
      const [agentRes, flowRes] = await Promise.all([
        agentAPI.get(id),
        agentAPI.getFlow(id)
      ]);
      setAgent(agentRes.data);
      if (flowRes.data.flow && flowRes.data.flow.length > 0) {
        setNodes(flowRes.data.flow);
        setSelectedNode(flowRes.data.flow[0]);
      }
    } catch (error) {
      console.error('Error fetching agent flow:', error);
      toast({
        title: "Error",
        description: "Failed to load agent flow",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const saveFlow = async () => {
    try {
      await agentAPI.updateFlow(id, nodes);
      toast({
        title: "Success",
        description: "Flow saved successfully"
      });
    } catch (error) {
      console.error('Error saving flow:', error);
      toast({
        title: "Error",
        description: "Failed to save flow",
        variant: "destructive"
      });
    }
  };

  // Webhook tester function
  const testWebhook = async () => {
    if (!selectedNode || selectedNode.type !== 'function') return;

    const webhookUrl = selectedNode.data?.webhook_url;
    if (!webhookUrl) {
      toast({
        title: "Error",
        description: "Please enter a webhook URL first",
        variant: "destructive"
      });
      return;
    }

    setWebhookTestLoading(true);
    setWebhookTestResponse(null);

    try {
      // Get all variables from the node's extract_variables
      const extractVariables = selectedNode.data?.extract_variables || [];

      // Build the request body - handle both JSON Schema and Template formats
      let parsedBody;
      const bodyTemplate = selectedNode.data?.webhook_body || '';

      // Try to parse as JSON first
      let bodyObj = null;
      try {
        if (bodyTemplate.trim()) {
          bodyObj = JSON.parse(bodyTemplate);
        }
      } catch {
        bodyObj = null;
      }

      // Check if it's a JSON Schema format (has "type" and "properties" keys)
      if (bodyObj && typeof bodyObj === 'object' && bodyObj.type === 'object' && bodyObj.properties) {
        // It's a JSON Schema - build request body from test variables
        console.log('📋 Detected JSON schema format - building request from test variables');
        parsedBody = {};

        // Build request body from schema properties and test variables
        for (const propName of Object.keys(bodyObj.properties)) {
          // Check webhookTestVariables first
          if (webhookTestVariables[propName] !== undefined && webhookTestVariables[propName] !== '') {
            parsedBody[propName] = webhookTestVariables[propName];
          }
          // Then check custom test variables
          else {
            const customVar = customTestVariables.find(v => v.name === propName);
            if (customVar && customVar.value) {
              parsedBody[propName] = customVar.value;
            } else {
              // Property not found - use a placeholder or null
              parsedBody[propName] = null;
            }
          }
        }

        // Check if any variables are missing
        const missingVars = Object.entries(parsedBody)
          .filter(([key, value]) => value === null)
          .map(([key]) => key);

        if (missingVars.length > 0) {
          toast({
            title: "Warning",
            description: `Missing test values for: ${missingVars.join(', ')}. Please fill in the test variables above.`,
            variant: "destructive"
          });
          setWebhookTestLoading(false);
          return;
        }
      } else {
        // It's a template format with {{variable}} placeholders - replace them
        let body = bodyTemplate || '{}';

        // Replace {{variable}} with test values from extractVariables
        for (const varDef of extractVariables) {
          const varName = varDef.name;
          const testValue = webhookTestVariables[varName] || '';
          body = body.replace(new RegExp(`\\{\\{${varName}\\}\\}`, 'g'), testValue);
        }

        // Replace custom variables
        for (const customVar of customTestVariables) {
          if (customVar.name) {
            body = body.replace(new RegExp(`\\{\\{${customVar.name}\\}\\}`, 'g'), customVar.value || '');
          }
        }

        // Also replace any other common variables
        body = body.replace(/\{\{call_id\}\}/g, 'test_call_123');
        body = body.replace(/\{\{user_message\}\}/g, webhookTestVariables['user_message'] || 'Test message');

        // Parse the body as JSON if it's valid
        try {
          parsedBody = JSON.parse(body);
        } catch {
          parsedBody = body;
        }
      }

      const method = selectedNode.data?.webhook_method || 'POST';
      const timeout = (selectedNode.data?.webhook_timeout || 10) * 1000;

      const startTime = Date.now();

      // Make the request through our backend proxy to avoid CORS
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/webhook-test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          url: webhookUrl,
          method: method,
          body: parsedBody,
          headers: selectedNode.data?.webhook_headers || {},
          timeout: timeout
        })
      });

      const endTime = Date.now();
      const duration = endTime - startTime;

      const result = await response.json();

      setWebhookTestResponse({
        success: result.success,
        status: result.status_code,
        duration: duration,
        data: result.response,
        error: result.error,
        request: {
          url: webhookUrl,
          method: method,
          body: parsedBody
        }
      });

      toast({
        title: result.success ? "Webhook Test Successful" : "Webhook Test Failed",
        description: result.success
          ? `Response received in ${duration}ms`
          : result.error || "Request failed",
        variant: result.success ? "default" : "destructive"
      });

    } catch (error) {
      console.error('Webhook test error:', error);
      setWebhookTestResponse({
        success: false,
        error: error.message,
        request: {
          url: webhookUrl,
          method: selectedNode.data?.webhook_method || 'POST'
        }
      });
      toast({
        title: "Error",
        description: "Failed to test webhook: " + error.message,
        variant: "destructive"
      });
    } finally {
      setWebhookTestLoading(false);
    }
  };

  const nodeTypes = [
    { id: 'start', name: 'Start (Greeting)', icon: Play, color: '#22c55e', description: 'First message users see' },
    { id: 'conversation', name: 'Conversation', icon: MessageSquare, color: '#3b82f6', description: 'Regular response node' },
    { id: 'function', name: 'Function', icon: Zap, color: '#8b5cf6', description: 'Execute a function' },
    { id: 'call_transfer', name: 'Call Transfer', icon: PhoneForwarded, color: '#10b981', description: 'Transfer to another number' },
    { id: 'collect_input', name: 'Collect Input', icon: FormInput, color: '#f59e0b', description: 'Gather structured data' },
    { id: 'send_sms', name: 'Send SMS', icon: MessageSquareText, color: '#14b8a6', description: 'Send text message' },
    { id: 'logic_split', name: 'Logic Split', icon: GitBranch, color: '#ec4899', description: 'Conditional branching' },
    { id: 'press_digit', name: 'Press Digit', icon: Hash, color: '#f59e0b', description: 'DTMF input' },
    { id: 'agent_transfer', name: 'Agent Transfer', icon: UserPlus, color: '#06b6d4', description: 'Transfer to human' },
    { id: 'extract_variable', name: 'Extract Variable', icon: FileText, color: '#f97316', description: 'Capture data' },
    { id: 'ending', name: 'Ending', icon: StopCircle, color: '#ef4444', description: 'End conversation' }
  ];

  const addNode = (type) => {
    let nodeData;

    if (type.id === 'start') {
      nodeData = {
        whoSpeaksFirst: 'user',
        aiSpeaksAfterSilence: true,
        silenceTimeout: 2000,
        transitions: []
      };
    } else if (type.id === 'ending') {
      nodeData = {
        mode: 'script',
        content: 'Thank you for calling. Goodbye!',
        transitions: [] // No transitions for ending nodes
      };
    } else if (type.id === 'function') {
      nodeData = {
        webhook_url: '',
        webhook_method: 'POST',
        webhook_headers: {},
        webhook_body: '',  // Start empty to avoid template issues
        webhook_timeout: 10,
        response_variable: 'webhook_response',
        extract_variables: [],  // Initialize empty array for variable extraction
        speak_during_execution: false,  // NEW: Whether to speak before webhook executes
        dialogue_type: 'static',  // NEW: 'static' or 'prompt' (AI-generated)
        dialogue_text: '',  // NEW: The text to speak (static) or prompt for AI
        wait_for_result: true,  // NEW: Wait for webhook to complete before transitioning
        block_interruptions: true,  // NEW: Prevent user interruptions during dialogue
        transitions: [{ id: '1', condition: 'After webhook completes', nextNode: '' }]
      };
    } else if (type.id === 'call_transfer' || type.id === 'agent_transfer') {
      nodeData = {
        transfer_type: 'cold',  // cold or warm
        destination_type: type.id === 'call_transfer' ? 'phone' : 'agent',
        destination: '',  // phone number or agent name
        transfer_message: 'Please hold while I transfer your call...',
        transitions: []  // No transitions after transfer
      };
    } else if (type.id === 'collect_input') {
      nodeData = {
        variable_name: 'user_input',
        input_type: 'text',  // text, email, phone, number
        prompt_message: 'Please provide the information.',
        error_message: 'That does not look right. Please try again.',
        transitions: [{ id: '1', condition: 'After valid input collected', nextNode: '' }]
      };
    } else if (type.id === 'send_sms') {
      nodeData = {
        phone_number: '',  // Can use variable reference
        sms_message: '',
        transitions: [{ id: '1', condition: 'After SMS sent', nextNode: '' }]
      };
    } else if (type.id === 'logic_split') {
      nodeData = {
        conditions: [
          { id: '1', variable: '', operator: 'equals', value: '', nextNode: '' }
        ],
        default_next_node: ''
      };
    } else if (type.id === 'press_digit') {
      nodeData = {
        prompt_message: 'Please press a digit from 0 to 9.',
        digit_mappings: {},
        transitions: []
      };
    } else if (type.id === 'extract_variable') {
      nodeData = {
        variable_name: 'extracted_data',
        extraction_prompt: 'Extract the relevant information',
        transitions: [{ id: '1', condition: 'After extraction', nextNode: '' }]
      };
    } else {
      nodeData = {
        mode: 'script',
        content: '',
        transitions: [{ id: '1', condition: '', nextNode: '' }]
      };
    }

    const newNode = {
      id: Date.now().toString(),
      type: type.id,
      label: type.name,
      data: nodeData
    };

    setNodes([...nodes, newNode]);
    setSelectedNode(newNode);
    setShowNodePalette(false);
  };

  const updateNode = (nodeId, updates) => {
    setNodes(nodes.map(n => n.id === nodeId ? { ...n, ...updates } : n));
    setSelectedNode({ ...selectedNode, ...updates });
  };

  const addTransition = () => {
    const newTransitions = [
      ...selectedNode.data.transitions,
      { id: Date.now().toString(), condition: '', nextNode: '' }
    ];
    updateNode(selectedNode.id, {
      data: { ...selectedNode.data, transitions: newTransitions }
    });
  };

  const updateTransition = (transitionId, field, value) => {
    const newTransitions = selectedNode.data.transitions.map(t =>
      t.id === transitionId ? { ...t, [field]: value } : t
    );
    updateNode(selectedNode.id, {
      data: { ...selectedNode.data, transitions: newTransitions }
    });
  };

  const deleteTransition = (transitionId) => {
    const newTransitions = selectedNode.data.transitions.filter(t => t.id !== transitionId);
    updateNode(selectedNode.id, {
      data: { ...selectedNode.data, transitions: newTransitions }
    });
  };

  const deleteNode = (nodeId) => {
    if (nodes.length > 1) {
      const newNodes = nodes.filter(n => n.id !== nodeId);
      setNodes(newNodes);
      setSelectedNode(newNodes[0]);
    }
  };

  const handleOptimizeClick = () => {
    setOptimizeContent(selectedNode.data.content || '');
    setShowOptimizeModal(true);
  };

  const handleApplyOptimized = (optimizedContent) => {
    updateNode(selectedNode.id, {
      data: { ...selectedNode.data, content: optimizedContent }
    });
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen bg-gray-900">
        <div className="text-white text-xl">Loading flow...</div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => navigate('/agents')}
              variant="ghost"
              className="text-gray-400 hover:text-white"
              size="sm"
            >
              <ArrowLeft size={20} />
            </Button>
            <Button
              onClick={() => navigate(`/agents/${id}/edit`)}
              variant="ghost"
              className="text-gray-400 hover:text-white"
              size="sm"
            >
              <Settings size={20} className="mr-2" />
              Settings
            </Button>
            <div>
              <h1 className="text-xl font-bold text-white">Call Flow Editor</h1>
              <p className="text-sm text-gray-400">{agent?.name} - Design your conversation flow</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => navigate(`/agents/${id}/test`)}
              variant="outline"
              className="border-green-600 text-green-400 hover:bg-green-600/20 hover:text-green-300"
              size="sm"
            >
              <Play size={16} className="mr-2" />
              Test Agent
            </Button>
            <Button
              onClick={() => setShowNodeTester(true)}
              variant="outline"
              size="sm"
              className="border-purple-500 text-purple-400 hover:bg-purple-500/10"
            >
              <TestTube2 size={16} className="mr-2" />
              Test Nodes
            </Button>
            <Button
              onClick={() => setShowNodeFixer(true)}
              variant="outline"
              size="sm"
              className="border-amber-500 text-amber-400 hover:bg-amber-500/10"
            >
              <Wrench size={16} className="mr-2" />
              AI Fix Nodes
            </Button>
            <Button
              onClick={saveFlow}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              size="sm"
            >
              <Save size={16} className="mr-2" />
              Save
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Node Palette */}
        <div className="w-64 bg-gray-800 border-r border-gray-700 p-4 overflow-y-auto">
          <h2 className="text-white font-semibold mb-4">Node Types</h2>
          <div className="space-y-2">
            {nodeTypes.map((type) => {
              const Icon = type.icon;
              return (
                <button
                  key={type.id}
                  onClick={() => addNode(type)}
                  className="w-full flex items-center gap-3 p-3 bg-gray-900 hover:bg-gray-750 rounded-lg transition-all border border-gray-700 hover:border-gray-600"
                  style={{ borderLeftColor: type.color, borderLeftWidth: '3px' }}
                >
                  <Icon size={18} style={{ color: type.color }} />
                  <span className="text-white text-sm">{type.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Center - Flow Canvas */}
        <div className="flex-1 bg-gray-900 p-6 overflow-auto">
          <div className="space-y-4">
            {nodes.map((node, index) => {
              const nodeType = nodeTypes.find(t => t.id === node.type);
              const Icon = nodeType?.icon || MessageSquare;
              const isSelected = selectedNode?.id === node.id;

              return (
                <div key={node.id} id={`node-item-${node.id}`}>
                  <Card
                    onClick={() => setSelectedNode(node)}
                    className={`p-4 cursor-pointer transition-all ${isSelected
                      ? 'bg-gray-800 border-blue-500 shadow-lg shadow-blue-500/20'
                      : 'bg-gray-800 border-gray-700 hover:border-gray-600'
                      }`}
                    style={{ borderLeftColor: nodeType?.color, borderLeftWidth: '4px' }}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg" style={{ backgroundColor: `${nodeType?.color}20` }}>
                          <Icon size={20} style={{ color: nodeType?.color }} />
                        </div>
                        <div>
                          <h3 className="text-white font-semibold">{node.label}</h3>
                          <p className="text-gray-400 text-xs">{nodeType?.name}</p>
                        </div>
                      </div>
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteNode(node.id);
                        }}
                        variant="ghost"
                        size="sm"
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                    {node.data.prompt && (
                      <p className="text-gray-300 text-sm mt-2 line-clamp-2">{node.data.prompt}</p>
                    )}

                    {/* Show dialogue preview for function nodes with speak_during_execution enabled */}
                    {node.type === 'function' && node.data.speak_during_execution && node.data.dialogue_text && (
                      <div className="mt-3 bg-purple-900/30 border border-purple-600/50 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-semibold text-purple-400">
                            {node.data.dialogue_type === 'static' ? '💬 Static Sentence' : '🤖 AI Prompt'}
                          </span>
                        </div>
                        <p className="text-gray-300 text-sm italic line-clamp-2">{node.data.dialogue_text}</p>
                      </div>
                    )}

                    {node.data.transitions && node.data.transitions.length > 0 && (
                      <div className="mt-3 space-y-1">
                        {node.data.transitions.map((transition) => (
                          <div key={transition.id} className="text-xs text-gray-400">
                            {transition.condition && `→ ${transition.condition}`}
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                  {index < nodes.length - 1 && (
                    <div className="flex items-center justify-center py-2">
                      <div className="w-0.5 h-8 bg-gradient-to-b from-blue-500 to-purple-500"></div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Sidebar - Node Configuration */}
        {selectedNode && (
          <div className="w-96 bg-gray-800 border-l border-gray-700 p-6 overflow-y-auto">
            <h2 className="text-white font-semibold mb-4">Node Settings</h2>

            <div className="space-y-4">
              <div>
                <Label className="text-gray-300">Node Label</Label>
                <Input
                  value={selectedNode.label}
                  onChange={(e) => updateNode(selectedNode.id, { label: e.target.value })}
                  className="bg-gray-900 border-gray-700 text-white mt-2"
                />
              </div>

              {/* Start node settings */}
              {selectedNode.type === 'start' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <h3 className="text-white font-semibold">Begin Settings</h3>

                  <div>
                    <Label className="text-gray-300">Who speaks first</Label>
                    <div className="space-y-2 mt-2">
                      <div
                        onClick={() => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, whoSpeaksFirst: 'ai' }
                        })}
                        className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${selectedNode.data.whoSpeaksFirst === 'ai'
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-gray-700 hover:border-gray-600'
                          }`}
                      >
                        <div className="flex items-center">
                          <div className={`w-5 h-5 rounded-full border-2 mr-3 flex items-center justify-center ${selectedNode.data.whoSpeaksFirst === 'ai' ? 'border-blue-500' : 'border-gray-600'
                            }`}>
                            {selectedNode.data.whoSpeaksFirst === 'ai' && (
                              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                            )}
                          </div>
                          <span className="text-white">AI speaks first</span>
                        </div>
                      </div>

                      <div
                        onClick={() => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, whoSpeaksFirst: 'user' }
                        })}
                        className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${selectedNode.data.whoSpeaksFirst === 'user'
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-gray-700 hover:border-gray-600'
                          }`}
                      >
                        <div className="flex items-center">
                          <div className={`w-5 h-5 rounded-full border-2 mr-3 flex items-center justify-center ${selectedNode.data.whoSpeaksFirst === 'user' ? 'border-blue-500' : 'border-gray-600'
                            }`}>
                            {selectedNode.data.whoSpeaksFirst === 'user' && (
                              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                            )}
                          </div>
                          <span className="text-white">User speaks first</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
                    <div>
                      <Label className="text-gray-300">AI starts speaking after silence</Label>
                      <p className="text-xs text-gray-500 mt-1">
                        When enabled, the AI will automatically speak if the user doesn't start the conversation within the timeout duration.
                      </p>
                    </div>
                    <button
                      onClick={() => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, aiSpeaksAfterSilence: !selectedNode.data.aiSpeaksAfterSilence }
                      })}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${selectedNode.data.aiSpeaksAfterSilence ? 'bg-blue-600' : 'bg-gray-700'
                        }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${selectedNode.data.aiSpeaksAfterSilence ? 'translate-x-6' : 'translate-x-1'
                          }`}
                      />
                    </button>
                  </div>

                  {selectedNode.data.aiSpeaksAfterSilence && (
                    <div>
                      <Label className="text-gray-300">Silence Time</Label>
                      <p className="text-xs text-gray-500 mb-2">
                        Time to wait before the assistant starts speaking if the user stays silent.
                      </p>
                      <div className="flex items-center gap-4">
                        <input
                          type="range"
                          min="500"
                          max="10000"
                          step="500"
                          value={selectedNode.data.silenceTimeout}
                          onChange={(e) => updateNode(selectedNode.id, {
                            data: { ...selectedNode.data, silenceTimeout: parseInt(e.target.value) }
                          })}
                          className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <span className="text-white font-semibold min-w-[3rem]">
                          {(selectedNode.data.silenceTimeout / 1000).toFixed(1)}s
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Function/Webhook node settings */}
              {selectedNode.type === 'function' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <h3 className="text-white font-semibold">Webhook/Function Settings</h3>

                  {/* Function Behavior Controls */}
                  <div className="bg-purple-900/20 border border-purple-700/30 rounded-lg p-4 space-y-4">
                    <h4 className="text-white font-medium">⚙️ Function Behavior</h4>

                    {/* Speak During Execution */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label className="text-gray-300">Speak During Execution</Label>
                        <label className="inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedNode.data?.speak_during_execution === true}
                            onChange={(e) => updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, speak_during_execution: e.target.checked }
                            })}
                            className="sr-only peer"
                          />
                          <div className="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                        </label>
                      </div>
                      <p className="text-xs text-gray-400">Agent will say something before executing the webhook (e.g., "One moment...")</p>
                    </div>

                    {/* Dialogue Configuration - Only show if speak_during_execution is enabled */}
                    {selectedNode.data?.speak_during_execution && (
                      <div className="pl-4 border-l-2 border-purple-600 space-y-3">
                        <div>
                          <Label className="text-gray-300">Dialogue Type</Label>
                          <Select
                            value={selectedNode.data?.dialogue_type || 'static'}
                            onValueChange={(value) => updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, dialogue_type: value }
                            })}
                          >
                            <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="static">Static Sentence</SelectItem>
                              <SelectItem value="prompt">AI Generated (Prompt)</SelectItem>
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-gray-400 mt-1">
                            {selectedNode.data?.dialogue_type === 'static'
                              ? 'Use exact text you specify'
                              : 'AI will generate response based on your prompt'}
                          </p>
                        </div>

                        <div>
                          <Label className="text-gray-300">
                            {selectedNode.data?.dialogue_type === 'static' ? 'Static Text' : 'AI Prompt'}
                          </Label>
                          <Textarea
                            value={selectedNode.data?.dialogue_text || ''}
                            onChange={(e) => updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, dialogue_text: e.target.value }
                            })}
                            className="bg-gray-900 border-gray-700 text-white mt-2"
                            rows={3}
                            placeholder={selectedNode.data?.dialogue_type === 'static'
                              ? 'One moment, let me check that for you...'
                              : 'Tell the user you are checking availability and ask them to wait'}
                          />
                        </div>
                      </div>
                    )}

                    {/* Wait for Result */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label className="text-gray-300">Wait for Result</Label>
                        <label className="inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedNode.data?.wait_for_result !== false}
                            onChange={(e) => updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, wait_for_result: e.target.checked }
                            })}
                            className="sr-only peer"
                          />
                          <div className="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                        </label>
                      </div>
                      <p className="text-xs text-gray-400">Wait for the webhook to finish before transitioning to the next node</p>
                    </div>

                    {/* Block Interruptions */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label className="text-gray-300">Block Interruptions</Label>
                        <label className="inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedNode.data?.block_interruptions !== false}
                            onChange={(e) => updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, block_interruptions: e.target.checked }
                            })}
                            className="sr-only peer"
                          />
                          <div className="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                        </label>
                      </div>
                      <p className="text-xs text-gray-400">Users cannot interrupt while AI is speaking</p>
                    </div>
                  </div>

                  {/* Goal - What to achieve if re-prompt needed */}
                  <div className="bg-yellow-900/20 border border-yellow-700/30 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">🎯 Node Goal (Optional)</h4>
                    <p className="text-xs text-gray-400 mb-3">
                      If required variables are missing, AI uses this goal to guide conversation toward collecting them
                    </p>
                    <Textarea
                      value={selectedNode.data?.goal || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, goal: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white"
                      rows={3}
                      placeholder="e.g., 'Collect the appointment date, time, and customer contact information before booking'"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Leave empty to use auto-generated re-prompts for missing variables
                    </p>
                  </div>

                  {/* Variable Extraction Section */}
                  <div className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">📊 Variables to Extract</h4>
                    <p className="text-xs text-gray-400 mb-3">
                      AI will extract these variables from previous conversation to send to webhook
                    </p>

                    {(selectedNode.data?.extract_variables || []).map((variable, index) => (
                      <div key={index} className="mb-4 p-4 bg-gray-800/50 rounded border border-gray-700">
                        <div className="flex items-start gap-2 mb-3">
                          <input
                            type="text"
                            value={variable.name || ''}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], name: e.target.value };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="bg-gray-900 border border-gray-700 text-white flex-1 px-3 py-2 rounded font-semibold"
                            placeholder="Variable name (e.g., appointment_date)"
                          />
                          <button
                            onClick={() => {
                              const newVars = (selectedNode.data?.extract_variables || []).filter((_, i) => i !== index);
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded"
                          >
                            ✕
                          </button>
                        </div>

                        {/* Description */}
                        <div className="mb-3">
                          <label className="text-xs text-gray-400 mb-1 block">Description</label>
                          <textarea
                            value={variable.description || ''}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], description: e.target.value };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="bg-gray-900 border border-gray-700 text-white text-xs w-full px-3 py-2 rounded"
                            rows={2}
                            placeholder="What to extract (e.g., 'The date mentioned by user for appointment')"
                          />
                        </div>

                        {/* Extraction Hint */}
                        <div className="mb-3">
                          <label className="text-xs text-gray-400 mb-1 block">Extraction Hint (Optional)</label>
                          <input
                            type="text"
                            value={variable.extraction_hint || ''}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], extraction_hint: e.target.value };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="bg-gray-900 border border-gray-700 text-white text-xs w-full px-3 py-2 rounded"
                            placeholder="e.g., 'Look for phrases like tomorrow, next week, specific dates'"
                          />
                          <p className="text-xs text-gray-500 mt-1">Helps AI know what patterns to look for</p>
                        </div>

                        {/* Allow Update Checkbox */}
                        <div className="mb-3 flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={variable.allow_update === true}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], allow_update: e.target.checked };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="w-4 h-4 text-blue-600 bg-gray-900 border-gray-700 rounded"
                          />
                          <label className="text-xs text-gray-300">
                            <span className="font-semibold text-blue-400">Allow Update</span> - Re-extract this variable each time node is visited
                          </label>
                        </div>

                        {/* Required Checkbox */}
                        <div className="mb-3 flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={variable.required === true}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], required: e.target.checked };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="w-4 h-4 text-blue-600 bg-gray-900 border-gray-700 rounded"
                          />
                          <label className="text-xs text-gray-300">
                            <span className="font-semibold text-red-400">Required</span> - Webhook won't execute until this is provided
                          </label>
                        </div>

                        {/* Re-prompt Text (only show if required) */}
                        {variable.required && (
                          <div>
                            <label className="text-xs text-gray-400 mb-1 block">Re-prompt Type</label>
                            <Select
                              value={variable.reprompt_type || 'static'}
                              onValueChange={(value) => {
                                const newVars = [...(selectedNode.data?.extract_variables || [])];
                                newVars[index] = { ...newVars[index], reprompt_type: value };
                                updateNode(selectedNode.id, {
                                  data: { ...selectedNode.data, extract_variables: newVars }
                                });
                              }}
                            >
                              <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1 mb-2">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="static">Static Sentence (Exact Text)</SelectItem>
                                <SelectItem value="prompt">AI Generated (Prompt)</SelectItem>
                              </SelectContent>
                            </Select>

                            <label className="text-xs text-gray-400 mb-1 block">
                              {variable.reprompt_type === 'prompt' ? 'Re-prompt Instruction' : 'Re-prompt Text'} (if missing)
                            </label>
                            <textarea
                              value={variable.reprompt_text || ''}
                              onChange={(e) => {
                                const newVars = [...(selectedNode.data?.extract_variables || [])];
                                newVars[index] = { ...newVars[index], reprompt_text: e.target.value };
                                updateNode(selectedNode.id, {
                                  data: { ...selectedNode.data, extract_variables: newVars }
                                });
                              }}
                              className="bg-gray-900 border border-red-700/50 text-white text-xs w-full px-3 py-2 rounded"
                              rows={2}
                              placeholder={variable.reprompt_type === 'prompt'
                                ? "Tell the user you need the appointment date and ask when they'd like to schedule"
                                : "I need to know the appointment date. When would you like to schedule?"}
                            />
                            <p className="text-xs text-gray-500 mt-1">
                              {variable.reprompt_type === 'prompt'
                                ? 'AI will generate a natural response based on this instruction'
                                : 'Agent will say these exact words if variable is missing'}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}

                    <button
                      onClick={() => {
                        const newVars = [...(selectedNode.data?.extract_variables || []), { name: '', description: '' }];
                        updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, extract_variables: newVars }
                        });
                      }}
                      className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
                    >
                      + Add Variable
                    </button>
                  </div>

                  <div>
                    <Label className="text-gray-300">Webhook URL</Label>
                    <Input
                      value={selectedNode.data?.webhook_url || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, webhook_url: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      placeholder="https://your-api.com/webhook"
                    />
                  </div>

                  <div>
                    <Label className="text-gray-300">HTTP Method</Label>
                    <Select
                      value={selectedNode.data?.webhook_method || 'POST'}
                      onValueChange={(value) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, webhook_method: value }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="GET">GET</SelectItem>
                        <SelectItem value="POST">POST</SelectItem>
                        <SelectItem value="PUT">PUT</SelectItem>
                        <SelectItem value="PATCH">PATCH</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-gray-300">Request Body (JSON)</Label>
                    <Textarea
                      value={selectedNode.data?.webhook_body || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, webhook_body: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2 font-mono text-sm"
                      rows={4}
                      placeholder='{"appointment_date": "{{appointment_date}}", "appointment_time": "{{appointment_time}}"}'
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Use {`{{variable_name}}`} for extracted variables. Available: {`{{user_message}}, {{call_id}}`}, and your custom variables
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-300">Timeout (seconds)</Label>
                    <Input
                      type="number"
                      value={selectedNode.data?.webhook_timeout || 10}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, webhook_timeout: parseInt(e.target.value) || 10 }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      min="1"
                      max="30"
                    />
                  </div>

                  <div>
                    <Label className="text-gray-300">Response Variable Name</Label>
                    <Input
                      value={selectedNode.data?.response_variable || 'webhook_response'}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, response_variable: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      placeholder="webhook_response"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Store webhook response in this variable. Use in transitions to check response values.
                    </p>
                  </div>

                  {/* Example section */}
                  <div className="bg-green-900/20 border border-green-700/30 rounded-lg p-3">
                    <p className="text-xs text-green-400 font-medium mb-1">💡 Example Use Case:</p>
                    <p className="text-xs text-gray-400">
                      1. Extract: appointment_date, appointment_time<br />
                      2. Send to webhook for availability check<br />
                      3. Add transitions: If webhook_response.available == true → confirm, If available == false → ask_different_date
                    </p>
                  </div>

                  {/* Webhook Tester Section */}
                  <div className="border-t border-gray-700 pt-4 mt-4">
                    <button
                      onClick={() => setShowWebhookTester(!showWebhookTester)}
                      className="flex items-center justify-between w-full text-left"
                    >
                      <h3 className="text-white font-semibold flex items-center gap-2">
                        <Play size={16} className="text-blue-400" />
                        Webhook Tester
                      </h3>
                      <span className="text-gray-400 text-sm">{showWebhookTester ? '▼' : '▶'}</span>
                    </button>

                    {showWebhookTester && (
                      <div className="mt-4 space-y-4">
                        <p className="text-xs text-gray-400">
                          Test your webhook with sample variable values before using it in calls.
                        </p>

                        {/* JSON Schema Variables - Detect and show variables from schema */}
                        {(() => {
                          const bodyTemplate = selectedNode.data?.webhook_body || '';
                          let schemaVars = [];
                          try {
                            const bodyObj = JSON.parse(bodyTemplate);
                            if (bodyObj && bodyObj.type === 'object' && bodyObj.properties) {
                              schemaVars = Object.entries(bodyObj.properties).map(([name, def]) => ({
                                name,
                                description: def.description || '',
                                type: def.type || 'string'
                              }));
                            }
                          } catch (e) { /* JSON parse failed - not a schema format */ }

                          if (schemaVars.length > 0) {
                            return (
                              <div className="bg-blue-900/30 rounded-lg p-3 space-y-3 border border-blue-700/50">
                                <Label className="text-blue-300 text-sm">📋 Schema Variables (from webhook body):</Label>
                                <p className="text-xs text-gray-400">Your webhook body uses JSON Schema format. Fill in test values for each property:</p>
                                {schemaVars.map((varDef, idx) => (
                                  <div key={idx} className="space-y-1">
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs text-blue-400 min-w-[100px] font-medium">
                                        {varDef.name}
                                      </span>
                                      <Input
                                        value={webhookTestVariables[varDef.name] || ''}
                                        onChange={(e) => setWebhookTestVariables({
                                          ...webhookTestVariables,
                                          [varDef.name]: e.target.value
                                        })}
                                        className="bg-gray-800 border-gray-700 text-white text-sm flex-1"
                                        placeholder={varDef.description || `Enter test value for ${varDef.name}`}
                                      />
                                    </div>
                                    {varDef.description && (
                                      <p className="text-xs text-gray-500 ml-[108px]">{varDef.description}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            );
                          }
                          return null;
                        })()}

                        {/* Variable inputs from extract_variables (Template format) */}
                        {(selectedNode.data?.extract_variables || []).length > 0 && (
                          <div className="bg-gray-900/50 rounded-lg p-3 space-y-3">
                            <Label className="text-gray-300 text-sm">Test Variables (from Extract Variables):</Label>
                            {(selectedNode.data?.extract_variables || []).map((varDef, idx) => (
                              <div key={idx} className="flex items-center gap-2">
                                <span className="text-xs text-purple-400 min-w-[100px]">
                                  {`{{${varDef.name}}}`}
                                </span>
                                <Input
                                  value={webhookTestVariables[varDef.name] || ''}
                                  onChange={(e) => setWebhookTestVariables({
                                    ...webhookTestVariables,
                                    [varDef.name]: e.target.value
                                  })}
                                  className="bg-gray-800 border-gray-700 text-white text-sm flex-1"
                                  placeholder={`Enter test value for ${varDef.name}`}
                                />
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Additional common variables */}
                        <div className="bg-gray-900/50 rounded-lg p-3 space-y-3">
                          <Label className="text-gray-300 text-sm">Common Variables:</Label>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-purple-400 min-w-[100px]">{`{{user_message}}`}</span>
                            <Input
                              value={webhookTestVariables['user_message'] || ''}
                              onChange={(e) => setWebhookTestVariables({
                                ...webhookTestVariables,
                                user_message: e.target.value
                              })}
                              className="bg-gray-800 border-gray-700 text-white text-sm flex-1"
                              placeholder="Test user message"
                            />
                          </div>
                        </div>

                        {/* Custom variables section */}
                        <div className="bg-gray-900/50 rounded-lg p-3 space-y-3">
                          <div className="flex items-center justify-between">
                            <Label className="text-gray-300 text-sm">Custom Variables:</Label>
                            <button
                              onClick={() => setCustomTestVariables([...customTestVariables, { name: '', value: '' }])}
                              className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
                            >
                              <Plus size={14} />
                              Add Variable
                            </button>
                          </div>

                          {customTestVariables.map((customVar, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <Input
                                value={customVar.name}
                                onChange={(e) => {
                                  const updated = [...customTestVariables];
                                  updated[idx].name = e.target.value;
                                  setCustomTestVariables(updated);
                                }}
                                className="bg-gray-800 border-gray-700 text-purple-400 text-sm w-28"
                                placeholder="var_name"
                              />
                              <span className="text-gray-500">=</span>
                              <Input
                                value={customVar.value}
                                onChange={(e) => {
                                  const updated = [...customTestVariables];
                                  updated[idx].value = e.target.value;
                                  setCustomTestVariables(updated);
                                }}
                                className="bg-gray-800 border-gray-700 text-white text-sm flex-1"
                                placeholder="test value"
                              />
                              <button
                                onClick={() => {
                                  const updated = customTestVariables.filter((_, i) => i !== idx);
                                  setCustomTestVariables(updated);
                                }}
                                className="text-red-400 hover:text-red-300 p-1"
                              >
                                <X size={14} />
                              </button>
                            </div>
                          ))}

                          {customTestVariables.length === 0 && (
                            <p className="text-xs text-gray-500 italic">
                              Click + to add custom variables like {`{{phone_number}}`}, {`{{customer_name}}`}, etc.
                            </p>
                          )}
                        </div>

                        {/* Test button */}
                        <Button
                          onClick={testWebhook}
                          disabled={webhookTestLoading || !selectedNode.data?.webhook_url}
                          className="w-full bg-blue-600 hover:bg-blue-700"
                        >
                          {webhookTestLoading ? (
                            <>
                              <span className="animate-spin mr-2">⏳</span>
                              Testing...
                            </>
                          ) : (
                            <>
                              <Play size={16} className="mr-2" />
                              Send Test Request
                            </>
                          )}
                        </Button>

                        {/* Response display */}
                        {webhookTestResponse && (
                          <div className={`rounded-lg p-3 ${webhookTestResponse.success ? 'bg-green-900/30 border border-green-700/50' : 'bg-red-900/30 border border-red-700/50'}`}>
                            <div className="flex items-center justify-between mb-2">
                              <span className={`text-sm font-medium ${webhookTestResponse.success ? 'text-green-400' : 'text-red-400'}`}>
                                {webhookTestResponse.success ? '✅ Success' : '❌ Failed'}
                              </span>
                              <span className="text-xs text-gray-400">
                                {webhookTestResponse.status && `Status: ${webhookTestResponse.status}`}
                                {webhookTestResponse.duration && ` • ${webhookTestResponse.duration}ms`}
                              </span>
                            </div>

                            {/* Request sent */}
                            <div className="mb-2">
                              <p className="text-xs text-gray-400 mb-1">Request:</p>
                              <pre className="text-xs bg-gray-900 p-2 rounded overflow-auto max-h-20 text-gray-300">
                                {webhookTestResponse.request?.method} {webhookTestResponse.request?.url}
                                {webhookTestResponse.request?.body && '\n\n' + JSON.stringify(webhookTestResponse.request.body, null, 2)}
                              </pre>
                            </div>

                            {/* Response or error */}
                            <div>
                              <p className="text-xs text-gray-400 mb-1">
                                {webhookTestResponse.success ? 'Response:' : 'Error:'}
                              </p>
                              <pre className="text-xs bg-gray-900 p-2 rounded overflow-auto max-h-32 text-gray-300">
                                {webhookTestResponse.success
                                  ? JSON.stringify(webhookTestResponse.data, null, 2)
                                  : webhookTestResponse.error
                                }
                              </pre>
                            </div>

                            {/* Variable mapping hint */}
                            {webhookTestResponse.success && (
                              <p className="text-xs text-gray-500 mt-2">
                                💡 Access response values in transitions using: {selectedNode.data?.response_variable || 'webhook_response'}.field_name
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Transfer Call node settings */}
              {(selectedNode.type === 'call_transfer' || selectedNode.type === 'agent_transfer') && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <h3 className="text-white font-semibold">Transfer Settings</h3>

                  <div>
                    <Label className="text-gray-300">Transfer Type</Label>
                    <Select
                      value={selectedNode.data?.transfer_type || 'cold'}
                      onValueChange={(value) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, transfer_type: value }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="cold">Cold Transfer (Blind)</SelectItem>
                        <SelectItem value="warm">Warm Transfer (Announced)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-gray-300">Destination Type</Label>
                    <Select
                      value={selectedNode.data?.destination_type || 'phone'}
                      onValueChange={(value) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, destination_type: value }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="phone">Phone Number</SelectItem>
                        <SelectItem value="agent">Agent/Queue</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-gray-300">
                      {selectedNode.data?.destination_type === 'phone' ? 'Phone Number' : 'Agent Name'}
                    </Label>
                    <Input
                      value={selectedNode.data?.destination || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, destination: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      placeholder={selectedNode.data?.destination_type === 'phone' ? '+1234567890' : 'sales-team'}
                    />
                  </div>

                  <div>
                    <Label className="text-gray-300">Transfer Message</Label>
                    <Textarea
                      value={selectedNode.data?.transfer_message || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, transfer_message: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      rows={2}
                      placeholder="Please hold while I transfer your call..."
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Message to play before transfer
                    </p>
                  </div>
                </div>
              )}

              {/* Collect Input node settings */}
              {selectedNode.type === 'collect_input' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <h3 className="text-white font-semibold">Collect Input Settings</h3>

                  <div>
                    <Label className="text-gray-300">Variable Name</Label>
                    <Input
                      value={selectedNode.data?.variable_name || 'user_input'}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, variable_name: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      placeholder="user_email"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Name to store the collected value
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-300">Input Type</Label>
                    <Select
                      value={selectedNode.data?.input_type || 'text'}
                      onValueChange={(value) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, input_type: value }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-2">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="text">Text</SelectItem>
                        <SelectItem value="email">Email</SelectItem>
                        <SelectItem value="phone">Phone Number</SelectItem>
                        <SelectItem value="number">Number</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-gray-300">Prompt Message</Label>
                    <Textarea
                      value={selectedNode.data?.prompt_message || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, prompt_message: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      rows={2}
                      placeholder="What to ask the user"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      What to ask the user for this input
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-300">Error Message</Label>
                    <Textarea
                      value={selectedNode.data?.error_message || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, error_message: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      rows={2}
                      placeholder="Message for invalid input"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Message to show when input is invalid
                    </p>
                  </div>
                </div>
              )}

              {/* Send SMS node settings */}
              {selectedNode.type === 'send_sms' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <h3 className="text-white font-semibold">Send SMS Settings</h3>

                  <div>
                    <Label className="text-gray-300">Phone Number</Label>
                    <Input
                      value={selectedNode.data?.phone_number || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, phone_number: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      placeholder="Enter phone or variable name"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Phone number or variable reference (e.g., user_phone)
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-300">SMS Message</Label>
                    <Textarea
                      value={selectedNode.data?.sms_message || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, sms_message: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      rows={4}
                      placeholder="Enter your SMS message here"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Use variables in your message (e.g., user_name)
                    </p>
                  </div>
                </div>
              )}

              {/* Logic Split node settings */}
              {selectedNode.type === 'logic_split' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <h3 className="text-white font-semibold flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-pink-400" />
                    Logic Split Settings
                  </h3>

                  <div className="p-3 bg-blue-900/30 rounded-lg border border-blue-700/50">
                    <p className="text-xs text-blue-300">
                      💡 Create conditions to route calls based on extracted variables.
                      Conditions are evaluated in order - first match wins.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <Label className="text-gray-300">Conditions</Label>
                    {selectedNode.data?.conditions?.map((condition, index) => (
                      <div key={condition.id} className="p-3 bg-gray-800 rounded-lg space-y-3 border border-gray-700">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-pink-400">Condition {index + 1}</span>
                          {selectedNode.data.conditions.length > 1 && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                const newConditions = selectedNode.data.conditions.filter((_, i) => i !== index);
                                updateNode(selectedNode.id, {
                                  data: { ...selectedNode.data, conditions: newConditions }
                                });
                              }}
                              className="text-red-400 hover:text-red-300 h-6 px-2"
                            >
                              <X className="w-3 h-3" />
                            </Button>
                          )}
                        </div>

                        {/* Variable Name - with suggestions from extracted variables */}
                        <div>
                          <Label className="text-xs text-gray-400 mb-1">Variable Name</Label>
                          <div className="flex gap-2">
                            <Input
                              value={condition.variable || ''}
                              onChange={(e) => {
                                const newConditions = [...selectedNode.data.conditions];
                                newConditions[index] = { ...condition, variable: e.target.value };
                                updateNode(selectedNode.id, {
                                  data: { ...selectedNode.data, conditions: newConditions }
                                });
                              }}
                              className="bg-gray-900 border-gray-700 text-white flex-1"
                              placeholder="e.g., Amount_Reference, user_name"
                            />
                            {/* Quick variable picker */}
                            {(() => {
                              // Collect all extracted variables from all nodes
                              const allVars = nodes.flatMap(n =>
                                (n.data?.extract_variables || []).map(v => v.name)
                              ).filter(Boolean);
                              const uniqueVars = [...new Set(allVars)];

                              if (uniqueVars.length > 0) {
                                return (
                                  <Select
                                    value=""
                                    onValueChange={(value) => {
                                      const newConditions = [...selectedNode.data.conditions];
                                      newConditions[index] = { ...condition, variable: value };
                                      updateNode(selectedNode.id, {
                                        data: { ...selectedNode.data, conditions: newConditions }
                                      });
                                    }}
                                  >
                                    <SelectTrigger className="bg-gray-900 border-gray-700 text-white w-24">
                                      <SelectValue placeholder="Pick" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {uniqueVars.map(varName => (
                                        <SelectItem key={varName} value={varName}>{varName}</SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                );
                              }
                              return null;
                            })()}
                          </div>
                        </div>

                        {/* Value Type Selector */}
                        <div>
                          <Label className="text-xs text-gray-400 mb-1">Value Type</Label>
                          <Select
                            value={condition.value_type || 'string'}
                            onValueChange={(value) => {
                              const newConditions = [...selectedNode.data.conditions];
                              // Reset operator to appropriate default when switching types
                              const defaultOperator = value === 'number' ? 'greater_than' : 'equals';
                              newConditions[index] = {
                                ...condition,
                                value_type: value,
                                operator: defaultOperator
                              };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, conditions: newConditions }
                              });
                            }}
                          >
                            <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="string">📝 Text/String</SelectItem>
                              <SelectItem value="number">🔢 Number</SelectItem>
                              <SelectItem value="existence">❓ Check Existence</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Operator - changes based on value type */}
                        <div>
                          <Label className="text-xs text-gray-400 mb-1">Operator</Label>
                          <Select
                            value={condition.operator || 'equals'}
                            onValueChange={(value) => {
                              const newConditions = [...selectedNode.data.conditions];
                              newConditions[index] = { ...condition, operator: value };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, conditions: newConditions }
                              });
                            }}
                          >
                            <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {(condition.value_type === 'number') ? (
                                <>
                                  <SelectItem value="greater_than">&gt; Greater Than</SelectItem>
                                  <SelectItem value="greater_than_or_equal">≥ Greater Than or Equal</SelectItem>
                                  <SelectItem value="less_than">&lt; Less Than</SelectItem>
                                  <SelectItem value="less_than_or_equal">≤ Less Than or Equal</SelectItem>
                                  <SelectItem value="equals">= Equals</SelectItem>
                                  <SelectItem value="not_equals">≠ Not Equals</SelectItem>
                                </>
                              ) : (condition.value_type === 'existence') ? (
                                <>
                                  <SelectItem value="exists">✓ Variable Exists (has value)</SelectItem>
                                  <SelectItem value="not_exists">✗ Variable Does Not Exist</SelectItem>
                                </>
                              ) : (
                                <>
                                  <SelectItem value="equals">= Equals (exact match)</SelectItem>
                                  <SelectItem value="not_equals">≠ Not Equals</SelectItem>
                                  <SelectItem value="contains">⊃ Contains (partial match)</SelectItem>
                                  <SelectItem value="starts_with">▶ Starts With</SelectItem>
                                  <SelectItem value="ends_with">◀ Ends With</SelectItem>
                                </>
                              )}
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Value Input - different based on type */}
                        {condition.value_type !== 'existence' && (
                          <div>
                            <Label className="text-xs text-gray-400 mb-1">
                              {condition.value_type === 'number' ? 'Compare Value (Number)' : 'Compare Value (Text)'}
                            </Label>
                            <Input
                              type={condition.value_type === 'number' ? 'number' : 'text'}
                              value={condition.value || ''}
                              onChange={(e) => {
                                const newConditions = [...selectedNode.data.conditions];
                                newConditions[index] = { ...condition, value: e.target.value };
                                updateNode(selectedNode.id, {
                                  data: { ...selectedNode.data, conditions: newConditions }
                                });
                              }}
                              className="bg-gray-900 border-gray-700 text-white"
                              placeholder={condition.value_type === 'number' ? 'e.g., 8000' : 'e.g., yes, interested'}
                            />
                            {condition.value_type === 'number' && (
                              <p className="text-xs text-gray-500 mt-1">
                                💡 Enter a plain number. Supports: 8000, 10000, etc.
                              </p>
                            )}
                          </div>
                        )}

                        {/* Next Node */}
                        <div>
                          <Label className="text-xs text-gray-400 mb-1">→ Then Go To</Label>
                          <Select
                            value={condition.nextNode || ''}
                            onValueChange={(value) => {
                              const newConditions = [...selectedNode.data.conditions];
                              newConditions[index] = { ...condition, nextNode: value };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, conditions: newConditions }
                              });
                            }}
                          >
                            <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                              <SelectValue placeholder="Select next node" />
                            </SelectTrigger>
                            <SelectContent>
                              {nodes.filter(n => n.id !== selectedNode.id).map(node => (
                                <SelectItem key={node.id} value={node.id}>
                                  {node.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Condition Preview */}
                        <div className="p-2 bg-gray-900/50 rounded text-xs text-gray-400 border border-gray-700/50">
                          <span className="text-gray-500">Preview: </span>
                          <span className="text-purple-400">{condition.variable || '[variable]'}</span>
                          {' '}
                          <span className="text-pink-400">
                            {condition.operator === 'greater_than' ? '>' :
                              condition.operator === 'greater_than_or_equal' ? '>=' :
                                condition.operator === 'less_than' ? '<' :
                                  condition.operator === 'less_than_or_equal' ? '<=' :
                                    condition.operator === 'equals' ? '=' :
                                      condition.operator === 'not_equals' ? '≠' :
                                        condition.operator === 'contains' ? 'contains' :
                                          condition.operator === 'starts_with' ? 'starts with' :
                                            condition.operator === 'ends_with' ? 'ends with' :
                                              condition.operator === 'exists' ? 'exists' :
                                                condition.operator === 'not_exists' ? 'does not exist' :
                                                  condition.operator}
                          </span>
                          {' '}
                          {condition.value_type !== 'existence' && (
                            <span className="text-green-400">{condition.value || '[value]'}</span>
                          )}
                        </div>
                      </div>
                    ))}

                    <Button
                      onClick={() => {
                        const newCondition = {
                          id: Date.now().toString(),
                          variable: '',
                          value_type: 'string',
                          operator: 'equals',
                          value: '',
                          nextNode: ''
                        };
                        updateNode(selectedNode.id, {
                          data: {
                            ...selectedNode.data,
                            conditions: [...(selectedNode.data.conditions || []), newCondition]
                          }
                        });
                      }}
                      size="sm"
                      className="w-full bg-pink-600 hover:bg-pink-700"
                    >
                      <Plus className="w-4 h-4 mr-2" /> Add Condition
                    </Button>
                  </div>

                  <div className="pt-2 border-t border-gray-700">
                    <Label className="text-gray-300">Default Path (No Conditions Match)</Label>
                    <p className="text-xs text-gray-500 mb-2">Where to go if none of the conditions above match</p>
                    <Select
                      value={selectedNode.data?.default_next_node || ''}
                      onValueChange={(value) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, default_next_node: value }
                      })}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                        <SelectValue placeholder="Select default node" />
                      </SelectTrigger>
                      <SelectContent>
                        {nodes.filter(n => n.id !== selectedNode.id).map(node => (
                          <SelectItem key={node.id} value={node.id}>{node.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {/* Press Digit node settings */}
              {selectedNode.type === 'press_digit' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <h3 className="text-white font-semibold">Press Digit (DTMF) Settings</h3>

                  <div>
                    <Label className="text-gray-300">Prompt Message</Label>
                    <Textarea
                      value={selectedNode.data?.prompt_message || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, prompt_message: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      rows={2}
                      placeholder="Please press a digit"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-gray-300">Digit Mappings</Label>
                    <p className="text-xs text-gray-500">Map each digit to a next node</p>

                    {['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '*', '#'].map(digit => (
                      <div key={digit} className="flex items-center gap-2">
                        <span className="text-white font-mono w-8">{digit}</span>
                        <Select
                          value={selectedNode.data?.digit_mappings?.[digit] || 'none'}
                          onValueChange={(value) => {
                            const newMappings = { ...selectedNode.data?.digit_mappings };
                            if (value && value !== 'none') {
                              newMappings[digit] = value;
                            } else {
                              delete newMappings[digit];
                            }
                            updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, digit_mappings: newMappings }
                            });
                          }}
                        >
                          <SelectTrigger className="bg-gray-900 border-gray-700 text-white flex-1">
                            <SelectValue placeholder="Select node" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">None</SelectItem>
                            {nodes.filter(n => n.id !== selectedNode.id).map(node => (
                              <SelectItem key={node.id} value={node.id}>{node.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Extract Variable node settings */}
              {selectedNode.type === 'extract_variable' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <h3 className="text-white font-semibold">Extract Variable Settings</h3>

                  <div>
                    <Label className="text-gray-300">Variable Name</Label>
                    <Input
                      value={selectedNode.data?.variable_name || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, variable_name: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      placeholder="customer_name"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Name to store the extracted value
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-300">Extraction Prompt</Label>
                    <Textarea
                      value={selectedNode.data?.extraction_prompt || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, extraction_prompt: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white mt-2"
                      rows={3}
                      placeholder="Extract the customer name from the message"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Instructions for AI on what to extract
                    </p>
                  </div>
                </div>
              )}

              {/* End Call node settings */}
              {selectedNode.type === 'ending' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                    <p className="text-white font-semibold mb-2">🛑 End Call</p>
                    <p className="text-sm text-gray-400">
                      This node terminates the call. No transitions allowed.
                    </p>
                  </div>

                  <div>
                    <Label className="text-gray-300">Goodbye Message Mode</Label>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div
                        onClick={() => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, mode: 'script' }
                        })}
                        className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${selectedNode.data.mode === 'script'
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-gray-700 hover:border-gray-600'
                          }`}
                      >
                        <div className="text-center">
                          <div className="text-2xl mb-1">📝</div>
                          <div className="text-white font-semibold text-sm">Script</div>
                          <div className="text-gray-400 text-xs mt-1">Exact words</div>
                        </div>
                      </div>
                      <div
                        onClick={() => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, mode: 'prompt' }
                        })}
                        className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${selectedNode.data.mode === 'prompt'
                          ? 'border-purple-500 bg-purple-500/10'
                          : 'border-gray-700 hover:border-gray-600'
                          }`}
                      >
                        <div className="text-center">
                          <div className="text-2xl mb-1">🤖</div>
                          <div className="text-white font-semibold text-sm">Prompt</div>
                          <div className="text-gray-400 text-xs mt-1">AI generates</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-gray-300">
                        {selectedNode.data.mode === 'script' ? 'Goodbye Script' : 'Goodbye Instructions'}
                      </Label>
                      <Button
                        onClick={handleOptimizeClick}
                        size="sm"
                        className="bg-purple-600 hover:bg-purple-700 text-white"
                      >
                        <Sparkles size={14} className="mr-1" />
                        Optimize with AI
                      </Button>
                    </div>
                    <Textarea
                      value={selectedNode.data.content || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, content: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white"
                      rows={4}
                      placeholder={selectedNode.data.mode === 'script'
                        ? "e.g., 'Thank you for calling. Goodbye!'"
                        : "e.g., 'Thank the user and wish them a great day'"}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {selectedNode.data.mode === 'script'
                        ? "AI will say these exact words before ending the call"
                        : "AI will generate a natural goodbye based on these instructions"}
                    </p>
                  </div>
                </div>
              )}

              {/* Conversation node settings */}
              {selectedNode.type === 'conversation' && (
                <div className="space-y-4 border-t border-gray-700 pt-4">
                  <div>
                    <Label className="text-gray-300">Response Mode</Label>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div
                        onClick={() => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, mode: 'script' }
                        })}
                        className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${selectedNode.data.mode === 'script'
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-gray-700 hover:border-gray-600'
                          }`}
                      >
                        <div className="text-center">
                          <div className="text-2xl mb-1">📝</div>
                          <div className="text-white font-semibold text-sm">Script</div>
                          <div className="text-gray-400 text-xs mt-1">Exact words</div>
                        </div>
                      </div>
                      <div
                        onClick={() => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, mode: 'prompt' }
                        })}
                        className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${selectedNode.data.mode === 'prompt'
                          ? 'border-purple-500 bg-purple-500/10'
                          : 'border-gray-700 hover:border-gray-600'
                          }`}
                      >
                        <div className="text-center">
                          <div className="text-2xl mb-1">🤖</div>
                          <div className="text-white font-semibold text-sm">Prompt</div>
                          <div className="text-gray-400 text-xs mt-1">AI generates</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Multi-LLM Processing Toggle */}
                  <div className="border border-purple-700/30 rounded-lg p-4 bg-purple-900/10">
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={selectedNode.data.use_parallel_llm || false}
                        onChange={(e) => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, use_parallel_llm: e.target.checked }
                        })}
                        className="mt-1 w-4 h-4 text-purple-600 bg-gray-900 border-gray-700 rounded focus:ring-purple-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Zap className="w-4 h-4 text-purple-400" />
                          <label className="text-white font-medium text-sm cursor-pointer" onClick={(e) => {
                            e.preventDefault();
                            updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, use_parallel_llm: !selectedNode.data.use_parallel_llm }
                            });
                          }}>
                            Use Multi-LLM Processing
                          </label>
                        </div>
                        <p className="text-xs text-purple-300 leading-relaxed">
                          ⚡ <strong>45% faster</strong> - Uses specialized AI workers in parallel for complex nodes
                          <br />
                          🎯 <strong>Best for:</strong> Objection handling, qualification, KB lookups
                          <br />
                          💰 <strong>Cost:</strong> Same as regular processing
                        </p>
                      </div>
                    </div>
                    {selectedNode.data.use_parallel_llm && (
                      <div className="mt-3 p-2 bg-blue-900/20 rounded border border-blue-700/30">
                        <p className="text-xs text-blue-300">
                          <strong>How it works:</strong> Intent Classifier + DISC Analyzer run simultaneously (~400ms), providing better context to main LLM for faster, more accurate responses.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Q&A Mode - Skip Mandatory Pre-check */}
                  <div className="border border-cyan-700/30 rounded-lg p-4 bg-cyan-900/10">
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={selectedNode.data.skip_mandatory_precheck || false}
                        onChange={(e) => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, skip_mandatory_precheck: e.target.checked }
                        })}
                        className="mt-1 w-4 h-4 text-cyan-600 bg-gray-900 border-gray-700 rounded focus:ring-cyan-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-cyan-400">❓</span>
                          <label className="text-white font-medium text-sm cursor-pointer" onClick={(e) => {
                            e.preventDefault();
                            updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, skip_mandatory_precheck: !selectedNode.data.skip_mandatory_precheck }
                            });
                          }}>
                            Q&A Mode (Answer First)
                          </label>
                        </div>
                        <p className="text-xs text-cyan-300 leading-relaxed">
                          📚 <strong>For Q&A/Knowledge Base nodes</strong> - Answer the user's question first
                          <br />
                          🔄 <strong>Behavior:</strong> Skip mandatory variable checks until transition evaluation
                          <br />
                          ✅ <strong>Use when:</strong> User asks questions that should be answered before collecting info
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Dynamic Rephrase - Only for Script Mode */}
                  {selectedNode.data.mode === 'script' && (
                    <div className="border border-orange-700/30 rounded-lg p-4 bg-orange-900/10">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={selectedNode.data.dynamic_rephrase || false}
                          onChange={(e) => updateNode(selectedNode.id, {
                            data: { ...selectedNode.data, dynamic_rephrase: e.target.checked }
                          })}
                          className="mt-1 w-4 h-4 text-orange-600 bg-gray-900 border-gray-700 rounded focus:ring-orange-500"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-orange-400">🔄</span>
                            <label className="text-white font-medium text-sm cursor-pointer" onClick={(e) => {
                              e.preventDefault();
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, dynamic_rephrase: !selectedNode.data.dynamic_rephrase }
                              });
                            }}>
                              Dynamic Rephrase on Retry
                            </label>
                          </div>
                          <p className="text-xs text-orange-300 leading-relaxed">
                            🔁 <strong>If no transition matches</strong> and agent stays on this node, rephrase the script naturally instead of repeating word-for-word
                            <br />
                            💡 <strong>Best for:</strong> Greetings, confirmations, or any script that might need retrying
                          </p>
                        </div>
                      </div>

                      {/* Rephrase Prompt Guidance - Only shows when checkbox is checked */}
                      {selectedNode.data.dynamic_rephrase && (
                        <div className="mt-3 pt-3 border-t border-orange-700/30">
                          <label className="text-xs text-gray-300 mb-1 block">Rephrase Instructions (Optional)</label>
                          <textarea
                            value={selectedNode.data.rephrase_prompt || ''}
                            onChange={(e) => updateNode(selectedNode.id, {
                              data: { ...selectedNode.data, rephrase_prompt: e.target.value }
                            })}
                            className="bg-gray-900 border border-orange-700/50 text-white text-xs w-full px-3 py-2 rounded"
                            rows={3}
                            placeholder="e.g., 'If user seems confused, ask more directly. Keep the same friendly tone but vary the wording.'"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Guide how the AI rephrases this script when retrying
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-gray-300">
                        {selectedNode.data.mode === 'script' ? 'Script' : 'Instructions for AI'}
                      </Label>
                      <Button
                        onClick={handleOptimizeClick}
                        size="sm"
                        className="bg-purple-600 hover:bg-purple-700 text-white"
                      >
                        <Sparkles size={14} className="mr-1" />
                        Optimize with AI
                      </Button>
                    </div>
                    <Textarea
                      value={selectedNode.data.content || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, content: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white"
                      rows={6}
                      placeholder={selectedNode.data.mode === 'script'
                        ? "Enter the exact words the AI should say..."
                        : "Give instructions to guide the AI's response (e.g., 'Ask about their budget and recommend appropriate plans')"}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {selectedNode.data.mode === 'script'
                        ? "AI will read these exact words"
                        : "AI will use these instructions to generate a natural response"}
                    </p>
                  </div>

                  {/* Goal - What to achieve if transition not met */}
                  <div className="bg-yellow-900/20 border border-yellow-700/30 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">🎯 Node Goal (Optional)</h4>
                    <p className="text-xs text-gray-400 mb-3">
                      If transitions don't match, AI will use this goal to guide the conversation toward meeting the conditions
                    </p>
                    <Textarea
                      value={selectedNode.data.goal || ''}
                      onChange={(e) => updateNode(selectedNode.id, {
                        data: { ...selectedNode.data, goal: e.target.value }
                      })}
                      className="bg-gray-900 border-gray-700 text-white"
                      rows={3}
                      placeholder="e.g., 'Get the user to provide their appointment date and time preference'"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Leave empty if AI should just use node content to generate a response
                    </p>
                  </div>

                  {/* Per-Node Voice Settings (ElevenLabs) */}
                  {agent?.settings?.tts_provider === 'elevenlabs' && (
                    <div className="bg-pink-900/20 border border-pink-700/30 rounded-lg p-4">
                      <h4 className="text-white font-medium mb-2">🎙️ Voice Settings Override</h4>
                      <p className="text-xs text-gray-400 mb-3">
                        Override agent's default voice settings for this node. Leave empty to use agent defaults.
                      </p>

                      {/* Stability */}
                      <div className="mb-4">
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-xs text-gray-300">Stability</label>
                          <span className="text-xs text-pink-400">
                            {selectedNode.data?.voice_settings?.stability ?? 'default'}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={selectedNode.data?.voice_settings?.stability ?? 0.5}
                          onChange={(e) => updateNode(selectedNode.id, {
                            data: {
                              ...selectedNode.data,
                              voice_settings: {
                                ...(selectedNode.data.voice_settings || {}),
                                stability: parseFloat(e.target.value)
                              }
                            }
                          })}
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <p className="text-xs text-gray-500 mt-1">Lower = more expressive, Higher = more consistent</p>
                      </div>

                      {/* Similarity Boost */}
                      <div className="mb-4">
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-xs text-gray-300">Similarity Boost</label>
                          <span className="text-xs text-pink-400">
                            {selectedNode.data?.voice_settings?.similarity_boost ?? 'default'}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={selectedNode.data?.voice_settings?.similarity_boost ?? 0.75}
                          onChange={(e) => updateNode(selectedNode.id, {
                            data: {
                              ...selectedNode.data,
                              voice_settings: {
                                ...(selectedNode.data.voice_settings || {}),
                                similarity_boost: parseFloat(e.target.value)
                              }
                            }
                          })}
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <p className="text-xs text-gray-500 mt-1">Higher = closer to original voice</p>
                      </div>

                      {/* Style */}
                      <div className="mb-4">
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-xs text-gray-300">Style Exaggeration</label>
                          <span className="text-xs text-pink-400">
                            {selectedNode.data?.voice_settings?.style ?? 'default'}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={selectedNode.data?.voice_settings?.style ?? 0}
                          onChange={(e) => updateNode(selectedNode.id, {
                            data: {
                              ...selectedNode.data,
                              voice_settings: {
                                ...(selectedNode.data.voice_settings || {}),
                                style: parseFloat(e.target.value)
                              }
                            }
                          })}
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <p className="text-xs text-gray-500 mt-1">Higher = more dramatic, emotional delivery</p>
                      </div>

                      {/* Speed */}
                      <div className="mb-4">
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-xs text-gray-300">Speed</label>
                          <span className="text-xs text-pink-400">
                            {selectedNode.data?.voice_settings?.speed ?? 'default'}x
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0.5"
                          max="2"
                          step="0.05"
                          value={selectedNode.data?.voice_settings?.speed ?? 1.0}
                          onChange={(e) => updateNode(selectedNode.id, {
                            data: {
                              ...selectedNode.data,
                              voice_settings: {
                                ...(selectedNode.data.voice_settings || {}),
                                speed: parseFloat(e.target.value)
                              }
                            }
                          })}
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <p className="text-xs text-gray-500 mt-1">0.5x = slow, 1.0x = normal, 2.0x = fast</p>
                      </div>

                      {/* Reset Button */}
                      <button
                        onClick={() => updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, voice_settings: undefined }
                        })}
                        className="text-xs text-pink-400 hover:text-pink-300 underline"
                      >
                        Reset to agent defaults
                      </button>
                    </div>
                  )}

                  {/* Extract Variables in Real-Time */}
                  <div className="bg-green-900/20 border border-green-700/30 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">📊 Extract Variables (Real-Time)</h4>
                    <p className="text-xs text-gray-400 mb-3">
                      Extract variables during this conversation - useful for capturing information before webhooks
                    </p>

                    {(selectedNode.data?.extract_variables || []).map((variable, index) => (
                      <div key={index} className="mb-4 p-4 bg-gray-800/50 rounded border border-gray-700">
                        <div className="flex items-start gap-2 mb-3">
                          <input
                            type="text"
                            value={variable.name || ''}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], name: e.target.value };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="bg-gray-900 border border-gray-700 text-white flex-1 px-3 py-2 rounded font-semibold"
                            placeholder="Variable name (e.g., appointment_date)"
                          />
                          <button
                            onClick={() => {
                              const newVars = (selectedNode.data?.extract_variables || []).filter((_, i) => i !== index);
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded"
                          >
                            ✕
                          </button>
                        </div>

                        {/* Description */}
                        <div className="mb-3">
                          <label className="text-xs text-gray-400 mb-1 block">Description</label>
                          <textarea
                            value={variable.description || ''}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], description: e.target.value };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="bg-gray-900 border border-gray-700 text-white text-xs w-full px-3 py-2 rounded"
                            rows={2}
                            placeholder="What to extract (e.g., 'The date mentioned by user for appointment')"
                          />
                        </div>

                        {/* Extraction Hint */}
                        <div className="mb-3">
                          <label className="text-xs text-gray-400 mb-1 block">Extraction Hint (Optional)</label>
                          <input
                            type="text"
                            value={variable.extraction_hint || ''}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], extraction_hint: e.target.value };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="bg-gray-900 border border-gray-700 text-white text-xs w-full px-3 py-2 rounded"
                            placeholder="e.g., 'Look for phrases like tomorrow, next week, specific dates'"
                          />
                          <p className="text-xs text-gray-500 mt-1">Helps AI know what patterns to look for</p>
                        </div>

                        {/* Allow Update Checkbox */}
                        <div className="mb-3 flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={variable.allow_update === true}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], allow_update: e.target.checked };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="w-4 h-4 text-blue-600 bg-gray-900 border-gray-700 rounded"
                          />
                          <label className="text-xs text-gray-300">
                            <span className="font-semibold text-blue-400">Allow Update</span> - Re-extract this variable each time node is visited
                          </label>
                        </div>

                        {/* Mandatory Checkbox */}
                        <div className="mb-3 flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={variable.mandatory === true}
                            onChange={(e) => {
                              const newVars = [...(selectedNode.data?.extract_variables || [])];
                              newVars[index] = { ...newVars[index], mandatory: e.target.checked };
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, extract_variables: newVars }
                              });
                            }}
                            className="w-4 h-4 text-blue-600 bg-gray-900 border-gray-700 rounded"
                          />
                          <label className="text-xs text-gray-300">
                            <span className="font-semibold text-orange-400">Mandatory</span> - Must be collected before transitioning
                          </label>
                        </div>

                        {/* Prompt Message (only show if mandatory) */}
                        {variable.mandatory && (
                          <div>
                            <label className="text-xs text-gray-400 mb-1 block">Prompt Message (if missing)</label>
                            <textarea
                              value={variable.prompt_message || ''}
                              onChange={(e) => {
                                const newVars = [...(selectedNode.data?.extract_variables || [])];
                                newVars[index] = { ...newVars[index], prompt_message: e.target.value };
                                updateNode(selectedNode.id, {
                                  data: { ...selectedNode.data, extract_variables: newVars }
                                });
                              }}
                              className="bg-gray-900 border border-orange-700/50 text-white text-xs w-full px-3 py-2 rounded"
                              rows={2}
                              placeholder="Ask the user to provide their preferred time for the appointment"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                              AI will use this instruction to naturally ask for the missing information
                            </p>
                          </div>
                        )}
                      </div>
                    ))}

                    <button
                      onClick={() => {
                        const newVars = [...(selectedNode.data?.extract_variables || []), { name: '', description: '', extraction_hint: '' }];
                        updateNode(selectedNode.id, {
                          data: { ...selectedNode.data, extract_variables: newVars }
                        });
                      }}
                      className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded text-sm"
                    >
                      + Add Variable to Extract
                    </button>
                  </div>
                </div>
              )}

              {/* Transitions - not for start, ending, transfer, logic_split, or press_digit nodes */}
              {selectedNode.type !== 'start' &&
                selectedNode.type !== 'ending' &&
                selectedNode.type !== 'call_transfer' &&
                selectedNode.type !== 'agent_transfer' &&
                selectedNode.type !== 'logic_split' &&
                selectedNode.type !== 'press_digit' && (
                  <div>
                    {/* Auto-Transition Toggle */}
                    <div className="border border-green-700/30 rounded-lg p-4 bg-green-900/10 mb-4">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={!!selectedNode.data.auto_transition_to}
                          onChange={(e) => {
                            if (e.target.checked) {
                              // Enable auto-transition with first available node
                              const firstAvailableNode = nodes.find(n => n.id !== selectedNode.id);
                              updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, auto_transition_to: firstAvailableNode?.id || '' }
                              });
                            } else {
                              // Disable auto-transition
                              const newData = { ...selectedNode.data };
                              delete newData.auto_transition_to;
                              updateNode(selectedNode.id, { data: newData });
                            }
                          }}
                          className="mt-1 w-4 h-4 text-green-600 bg-gray-900 border-gray-700 rounded focus:ring-green-500"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Zap className="w-4 h-4 text-green-400" />
                            <label className="text-white font-medium text-sm cursor-pointer" onClick={(e) => {
                              e.preventDefault();
                              if (selectedNode.data.auto_transition_to) {
                                const newData = { ...selectedNode.data };
                                delete newData.auto_transition_to;
                                updateNode(selectedNode.id, { data: newData });
                              } else {
                                const firstAvailableNode = nodes.find(n => n.id !== selectedNode.id);
                                updateNode(selectedNode.id, {
                                  data: { ...selectedNode.data, auto_transition_to: firstAvailableNode?.id || '' }
                                });
                              }
                            }}>
                              Auto-Transition (Skip Evaluation)
                            </label>
                          </div>
                          <p className="text-xs text-green-300 leading-relaxed">
                            ⚡ <strong>~574ms faster</strong> - Automatically move to next node without LLM evaluation
                            <br />
                            🎯 <strong>Best for:</strong> Linear flows where next node is always the same
                            <br />
                            ⚠️ <strong>Note:</strong> Disables condition-based transitions below
                          </p>
                        </div>
                      </div>
                      {selectedNode.data.auto_transition_to && (
                        <div className="mt-3">
                          <Label className="text-gray-300 text-sm mb-2 block">Next Node (Auto)</Label>
                          <div className="flex items-center gap-2">
                            <Select
                              value={selectedNode.data.auto_transition_to}
                              onValueChange={(value) => updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, auto_transition_to: value }
                              })}
                            >
                              <SelectTrigger className="bg-gray-800 border-gray-600 text-white text-sm flex-1">
                                <SelectValue placeholder="Select next node..." />
                              </SelectTrigger>
                              <SelectContent>
                                {nodes.filter(n => n.id !== selectedNode.id).map((node) => (
                                  <SelectItem key={node.id} value={node.id}>
                                    {node.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>

                            {/* Jump to selected node button */}
                            {selectedNode.data.auto_transition_to && (
                              <button
                                onClick={() => {
                                  const targetNode = nodes.find(n => n.id === selectedNode.data.auto_transition_to);
                                  if (targetNode) {
                                    setSelectedNode(targetNode);
                                    // Scroll the node into view
                                    setTimeout(() => {
                                      const nodeElement = document.getElementById(`node-item-${targetNode.id}`);
                                      if (nodeElement) {
                                        nodeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                      }
                                    }, 100);
                                  }
                                }}
                                className="p-2 bg-green-600 hover:bg-green-700 rounded text-white transition-colors flex-shrink-0"
                                title={`Jump to "${nodes.find(n => n.id === selectedNode.data.auto_transition_to)?.label}" node`}
                              >
                                <ArrowRight size={16} />
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Auto Transition After Response Toggle */}
                    <div className={`border border-blue-700/30 rounded-lg p-4 bg-blue-900/10 mb-4 ${selectedNode.data.auto_transition_to ? 'opacity-40 pointer-events-none' : ''}`}>
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={!!selectedNode.data.auto_transition_after_response}
                          onChange={(e) => {
                            if (e.target.checked) {
                              // Enable auto-transition after response with first available node
                              const firstAvailableNode = nodes.find(n => n.id !== selectedNode.id);
                              // Clear existing transitions and set the auto_transition_after_response
                              updateNode(selectedNode.id, {
                                data: {
                                  ...selectedNode.data,
                                  auto_transition_after_response: firstAvailableNode?.id || '',
                                  transitions: [] // Clear transitions since only 1 path allowed
                                }
                              });
                            } else {
                              // Disable auto-transition after response and restore default transition
                              const newData = { ...selectedNode.data };
                              delete newData.auto_transition_after_response;
                              newData.transitions = [{ id: Date.now().toString(), condition: '', nextNode: '' }];
                              updateNode(selectedNode.id, { data: newData });
                            }
                          }}
                          className="mt-1 w-4 h-4 text-blue-600 bg-gray-900 border-gray-700 rounded focus:ring-blue-500"
                          disabled={!!selectedNode.data.auto_transition_to}
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <ArrowRight className="w-4 h-4 text-blue-400" />
                            <label className="text-white font-medium text-sm cursor-pointer" onClick={(e) => {
                              e.preventDefault();
                              if (selectedNode.data.auto_transition_to) return; // Disabled if skip evaluation is active
                              if (selectedNode.data.auto_transition_after_response) {
                                const newData = { ...selectedNode.data };
                                delete newData.auto_transition_after_response;
                                newData.transitions = [{ id: Date.now().toString(), condition: '', nextNode: '' }];
                                updateNode(selectedNode.id, { data: newData });
                              } else {
                                const firstAvailableNode = nodes.find(n => n.id !== selectedNode.id);
                                updateNode(selectedNode.id, {
                                  data: {
                                    ...selectedNode.data,
                                    auto_transition_after_response: firstAvailableNode?.id || '',
                                    transitions: []
                                  }
                                });
                              }
                            }}>
                              Auto Transition After Response
                            </label>
                          </div>
                          <p className="text-xs text-blue-300 leading-relaxed">
                            🎤 <strong>Wait for user</strong> - Agent speaks, waits for user response, then auto-transitions
                            <br />
                            📝 <strong>Captures response</strong> - User's message is added to conversation context
                            <br />
                            🎯 <strong>Best for:</strong> When you don't care what user says, just need them to respond
                          </p>
                        </div>
                      </div>
                      {selectedNode.data.auto_transition_after_response && (
                        <div className="mt-3">
                          <Label className="text-gray-300 text-sm mb-2 block">Transition To (After User Responds)</Label>
                          <div className="flex items-center gap-2">
                            <Select
                              value={selectedNode.data.auto_transition_after_response}
                              onValueChange={(value) => updateNode(selectedNode.id, {
                                data: { ...selectedNode.data, auto_transition_after_response: value }
                              })}
                            >
                              <SelectTrigger className="bg-gray-800 border-gray-600 text-white text-sm flex-1">
                                <SelectValue placeholder="Select next node..." />
                              </SelectTrigger>
                              <SelectContent>
                                {nodes.filter(n => n.id !== selectedNode.id).map((node) => (
                                  <SelectItem key={node.id} value={node.id}>
                                    {node.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>

                            {/* Jump to selected node button */}
                            {selectedNode.data.auto_transition_after_response && (
                              <button
                                onClick={() => {
                                  const targetNode = nodes.find(n => n.id === selectedNode.data.auto_transition_after_response);
                                  if (targetNode) {
                                    setSelectedNode(targetNode);
                                    // Scroll the node into view
                                    setTimeout(() => {
                                      const nodeElement = document.getElementById(`node-item-${targetNode.id}`);
                                      if (nodeElement) {
                                        nodeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                      }
                                    }, 100);
                                  }
                                }}
                                className="p-2 bg-blue-600 hover:bg-blue-700 rounded text-white transition-colors flex-shrink-0"
                                title={`Jump to "${nodes.find(n => n.id === selectedNode.data.auto_transition_after_response)?.label}" node`}
                              >
                                <ArrowRight size={16} />
                              </button>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 mt-2">
                            Flow: Agent speaks → User says anything → Auto-transition to this node
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-gray-300">
                        {selectedNode.data.auto_transition_to
                          ? 'Transitions (Disabled - Auto-Transition Active)'
                          : selectedNode.data.auto_transition_after_response
                            ? 'Transitions (Disabled - Auto After Response Active)'
                            : 'Transitions'}
                      </Label>
                      {!selectedNode.data.auto_transition_to && !selectedNode.data.auto_transition_after_response && (
                        <Button
                          onClick={addTransition}
                          size="sm"
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          <Plus size={14} className="mr-1" />
                          Add
                        </Button>
                      )}
                    </div>

                    <div className={`space-y-3 ${(selectedNode.data.auto_transition_to || selectedNode.data.auto_transition_after_response) ? 'opacity-40 pointer-events-none' : ''}`}>
                      {selectedNode.data.transitions?.map((transition) => (
                        <div key={transition.id} className="p-3 bg-gray-900 rounded-lg border border-gray-700">
                          <div className="space-y-2">
                            <div className="flex items-start gap-2">
                              <Textarea
                                value={transition.condition}
                                onChange={(e) => updateTransition(transition.id, 'condition', e.target.value)}
                                placeholder="Describe when to take this path (e.g., 'If user asks about pricing or wants to know costs' or 'If user needs technical support')"
                                className="bg-gray-800 border-gray-600 text-white text-sm flex-1"
                                rows={2}
                              />
                              {transition.condition && (
                                <button
                                  onClick={() => {
                                    setCurrentTransitionId(transition.id);
                                    setTransitionContent(transition.condition);
                                    setShowTransitionModal(true);
                                  }}
                                  className="p-2 bg-yellow-600 hover:bg-yellow-700 rounded text-white transition-colors flex-shrink-0"
                                  title="Optimize transition for faster evaluation"
                                >
                                  <Zap size={16} />
                                </button>
                              )}
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              AI will analyze the conversation and decide if this condition is met
                            </p>
                            <div className="flex items-center gap-2">
                              <Select
                                value={transition.nextNode}
                                onValueChange={(value) => updateTransition(transition.id, 'nextNode', value)}
                              >
                                <SelectTrigger className="bg-gray-800 border-gray-600 text-white text-sm flex-1">
                                  <SelectValue placeholder="Next node..." />
                                </SelectTrigger>
                                <SelectContent>
                                  {nodes.filter(n => n.id !== selectedNode.id).map((node) => (
                                    <SelectItem key={node.id} value={node.id}>
                                      {node.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>

                              {/* Jump to selected node button */}
                              {transition.nextNode && (
                                <button
                                  onClick={() => {
                                    const targetNode = nodes.find(n => n.id === transition.nextNode);
                                    if (targetNode) {
                                      setSelectedNode(targetNode);
                                      // Scroll the node into view in the sidebar
                                      setTimeout(() => {
                                        const nodeElement = document.getElementById(`node-item-${targetNode.id}`);
                                        if (nodeElement) {
                                          nodeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        }
                                      }, 100);
                                    }
                                  }}
                                  className="p-2 bg-blue-600 hover:bg-blue-700 rounded text-white transition-colors flex-shrink-0"
                                  title={`Jump to "${nodes.find(n => n.id === transition.nextNode)?.label}" node`}
                                >
                                  <ArrowRight size={16} />
                                </button>
                              )}
                            </div>

                            {/* Variable Checks - Optional */}
                            <div className="mt-3 p-3 bg-gray-800/50 rounded border border-gray-700">
                              <label className="text-xs text-gray-400 mb-2 block font-medium">
                                🔍 Variable Checks (Optional)
                              </label>
                              <p className="text-xs text-gray-500 mb-2">
                                Require specific variables to have values before this transition can be taken
                              </p>

                              {/* Collect all variables from all nodes in the flow */}
                              {(() => {
                                const allVariables = new Set();
                                nodes.forEach(node => {
                                  const extractVars = node.data?.extract_variables || [];
                                  extractVars.forEach(v => {
                                    if (v.name) allVariables.add(v.name);
                                  });
                                });

                                if (allVariables.size === 0) {
                                  return (
                                    <p className="text-xs text-gray-500 italic">
                                      No variables defined in any nodes yet
                                    </p>
                                  );
                                }

                                const checkVariables = transition.check_variables || [];

                                return (
                                  <div className="space-y-2">
                                    {Array.from(allVariables).map((varName) => (
                                      <label key={varName} className="flex items-center gap-2 cursor-pointer hover:bg-gray-700/30 p-1 rounded">
                                        <input
                                          type="checkbox"
                                          checked={checkVariables.includes(varName)}
                                          onChange={(e) => {
                                            let newCheckVars = [...(checkVariables || [])];
                                            if (e.target.checked) {
                                              newCheckVars.push(varName);
                                            } else {
                                              newCheckVars = newCheckVars.filter(v => v !== varName);
                                            }
                                            updateTransition(transition.id, 'check_variables', newCheckVars);
                                          }}
                                          className="w-3 h-3 text-blue-600 bg-gray-900 border-gray-600 rounded"
                                        />
                                        <span className="text-xs text-gray-300">
                                          {varName}
                                        </span>
                                      </label>
                                    ))}
                                  </div>
                                );
                              })()}
                            </div>

                            {selectedNode.data.transitions.length > 1 && (
                              <Button
                                onClick={() => deleteTransition(transition.id)}
                                size="sm"
                                variant="ghost"
                                className="w-full text-red-400 hover:text-red-300 mt-2"
                              >
                                <Trash2 size={14} className="mr-2" />
                                Remove
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Analyze All Transitions Button */}
                    {!selectedNode.data.auto_transition_to && !selectedNode.data.auto_transition_after_response && selectedNode.data.transitions && selectedNode.data.transitions.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-700">
                        <button
                          onClick={() => setShowAnalysisModal(true)}
                          className="w-full bg-purple-600 hover:bg-purple-700 text-white py-2.5 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                        >
                          <Brain size={18} />
                          Analyze All Transitions (Detect Confusion & Overlap)
                        </button>
                        <p className="text-xs text-gray-400 mt-2 text-center">
                          See how the LLM interprets your transitions and identify potential issues
                        </p>
                      </div>
                    )}
                  </div>
                )}
            </div>
          </div>
        )}
      </div>

      {/* Optimize Node Modal */}
      <OptimizeNodeModal
        isOpen={showOptimizeModal}
        onClose={() => setShowOptimizeModal(false)}
        agentId={id}
        originalContent={optimizeContent}
        onApply={handleApplyOptimized}
      />

      <OptimizeTransitionModal
        isOpen={showTransitionModal}
        onClose={() => setShowTransitionModal(false)}
        agentId={id}
        originalCondition={transitionContent}
        onApply={(optimized) => {
          if (currentTransitionId) {
            updateTransition(currentTransitionId, 'condition', optimized);
          }
        }}
      />

      <TransitionAnalysisModal
        isOpen={showAnalysisModal}
        onClose={() => setShowAnalysisModal(false)}
        agentId={id}
        transitions={selectedNode.data.transitions || []}
        onAnalysisComplete={(result) => {
          // Could show a toast with overall assessment
          if (result.confusion_warnings && result.confusion_warnings.length > 0) {
            toast({
              title: "Potential Issues Found",
              description: `${result.confusion_warnings.length} confusion/overlap warning(s) detected`,
              variant: "warning"
            });
          } else {
            toast({
              title: "Analysis Complete",
              description: "No confusion or overlap detected",
            });
          }
        }}
      />

      {/* Node Sequence Tester Modal */}
      <NodeSequenceTester
        agentId={id}
        isOpen={showNodeTester}
        onClose={() => setShowNodeTester(false)}
      />

      {/* AI Node Fixer Modal */}
      <AINodeFixer
        agentId={id}
        isOpen={showNodeFixer}
        onClose={() => setShowNodeFixer(false)}
        onNodesFixed={(result) => {
          toast({
            title: "Nodes Fixed",
            description: result.message,
          });
          fetchAgentFlow(); // Reload the flow to show fixed nodes
        }}
      />
    </div>
  );
};

export default FlowBuilder;
