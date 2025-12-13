import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { agentAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { ArrowLeft, Send, RotateCcw, Download, Loader2, Play, GitBranch, Square, Search, RefreshCw } from 'lucide-react';

// Searchable Node Select Component
const SearchableNodeSelect = ({ nodes, value, onValueChange, placeholder, disabled, className }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);
  
  // Filter nodes based on search term
  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return nodes;
    const term = searchTerm.toLowerCase();
    return nodes.filter(node => {
      const label = (node.label || node.id || '').toLowerCase();
      const type = (node.type || '').toLowerCase();
      return label.includes(term) || type.includes(term);
    });
  }, [nodes, searchTerm]);
  
  // Get selected node label
  const selectedLabel = useMemo(() => {
    if (!value) return '';
    const node = nodes.find(n => n.id === value);
    return node ? `${node.label || node.id} (${node.type})` : value;
  }, [nodes, value]);
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  // Focus input when opening
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);
  
  return (
    <div className={`relative ${className || ''}`} ref={dropdownRef}>
      <div
        onClick={() => !disabled && setIsOpen(!isOpen)}
        className={`flex items-center justify-between px-3 py-2 border rounded cursor-pointer bg-white text-sm h-9 ${
          disabled ? 'opacity-50 cursor-not-allowed bg-gray-100' : 'hover:border-gray-400'
        }`}
      >
        <span className={value ? 'text-gray-900' : 'text-gray-500'}>
          {value ? selectedLabel : placeholder || 'Select node...'}
        </span>
        <Search className="h-4 w-4 text-gray-400" />
      </div>
      
      {isOpen && !disabled && (
        <div className="absolute z-50 w-full mt-1 bg-white border rounded-md shadow-lg">
          <div className="p-2 border-b">
            <Input
              ref={inputRef}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Type to search nodes..."
              className="h-8 text-sm"
            />
          </div>
          <div className="max-h-60 overflow-y-auto">
            {filteredNodes.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500">No nodes found</div>
            ) : (
              filteredNodes.map((node) => (
                <div
                  key={node.id}
                  onClick={() => {
                    onValueChange(node.id);
                    setIsOpen(false);
                    setSearchTerm('');
                  }}
                  className={`px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 ${
                    value === node.id ? 'bg-blue-100 text-blue-900' : 'text-gray-900'
                  }`}
                >
                  <span className="font-medium">{node.label || node.id}</span>
                  <span className="text-gray-500 ml-2">({node.type})</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Safe fetch using XMLHttpRequest to avoid rrweb-recorder "body already used" error
const safeFetch = (url, options = {}) => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(options.method || 'GET', url, true);
    
    // Set headers
    if (options.headers) {
      Object.entries(options.headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });
    }
    
    // Enable cookies for cross-origin requests
    xhr.withCredentials = options.credentials === 'include';
    
    xhr.onload = function() {
      const responseText = xhr.responseText;
      resolve({
        ok: xhr.status >= 200 && xhr.status < 300,
        status: xhr.status,
        statusText: xhr.statusText,
        text: responseText,
        json: () => {
          try {
            return JSON.parse(responseText);
          } catch (e) {
            throw new Error(`Invalid JSON response: ${responseText}`);
          }
        }
      });
    };
    
    xhr.onerror = function() {
      reject(new Error('Network request failed'));
    };
    
    xhr.ontimeout = function() {
      reject(new Error('Request timeout'));
    };
    
    // Send request body if provided
    if (options.body) {
      xhr.send(options.body);
    } else {
      xhr.send();
    }
  });
};

export default function AgentTester() {
  const { id: agentId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const messagesEndRef = useRef(null);
  
  // Get URL params for pre-filling from QC
  const urlNodeId = searchParams.get('nodeId');
  const urlSuggestion = searchParams.get('suggestion');

  const [agent, setAgent] = useState(null);
  const [callFlow, setCallFlow] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [conversation, setConversation] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [metrics, setMetrics] = useState({
    total_turns: 0,
    total_latency: 0,
    avg_latency: 0
  });
  const [currentNodeId, setCurrentNodeId] = useState(null);
  const [nodeTransitions, setNodeTransitions] = useState([]);
  const [variables, setVariables] = useState({});
  const [shouldEndCall, setShouldEndCall] = useState(false);
  const [measureRealTTS, setMeasureRealTTS] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [startNodeId, setStartNodeId] = useState('');
  const [expectedNextNode, setExpectedNextNode] = useState('');
  const [transitionTestResult, setTransitionTestResult] = useState(null);
  const [editingNodeId, setEditingNodeId] = useState(null);
  const [tempNodePrompt, setTempNodePrompt] = useState('');
  const [nodeOverrides, setNodeOverrides] = useState({}); // Store temporary prompt overrides
  const [qcSuggestionMode, setQcSuggestionMode] = useState(false); // Track if we came from QC with a suggestion

  // AI Auto-Test State
  const [autoTestMode, setAutoTestMode] = useState(false);
  const [autoTestSessionId, setAutoTestSessionId] = useState(null);
  const [autoTestStatus, setAutoTestStatus] = useState(null); // running, completed, stopped, error
  const [autoTestDifficulty, setAutoTestDifficulty] = useState('compliant');
  const [autoTestCustomInstructions, setAutoTestCustomInstructions] = useState('');
  const [autoTestMaxTurns, setAutoTestMaxTurns] = useState(15);
  const [autoTestConversation, setAutoTestConversation] = useState([]);
  const [autoTestPolling, setAutoTestPolling] = useState(null);

  // Load agent details
  useEffect(() => {
    loadAgent();
  }, [agentId]);

  // Handle URL params from QC (pre-fill edit mode with suggestion)
  useEffect(() => {
    // urlSuggestion is already decoded by useSearchParams, no need to decode again
    if (urlNodeId && callFlow.length > 0) {
      console.log('QC Integration: Looking for node', urlNodeId, 'in call flow with', callFlow.length, 'nodes');
      
      // Find the node in call flow - try by ID first, then by label/name
      let targetNode = callFlow.find(n => n.id === urlNodeId);
      
      // If not found by ID, try to find by label/name (QC might use node name instead of ID)
      if (!targetNode) {
        targetNode = callFlow.find(n => 
          (n.label && n.label === urlNodeId) || 
          (n.data?.label && n.data.label === urlNodeId) ||
          (n.data?.name && n.data.name === urlNodeId)
        );
        if (targetNode) {
          console.log('QC Integration: Found node by label instead of ID:', targetNode.id);
        }
      }
      
      if (targetNode) {
        const nodeId = targetNode.id;
        console.log('QC Integration: Setting up edit mode for node', nodeId);
        
        // Set up the edit mode with the QC suggestion
        setEditingNodeId(nodeId);
        
        // Use the suggestion from URL if provided, otherwise use the node's current prompt
        if (urlSuggestion) {
          setTempNodePrompt(urlSuggestion);
          setQcSuggestionMode(true);
          
          toast({
            title: '📝 QC Suggestion Loaded',
            description: `Edit prompt ready for node: ${targetNode.label || targetNode.data?.label || 'Unknown'}`,
          });
        } else {
          // No suggestion, just select the node for editing
          const currentPrompt = targetNode.data?.prompt || targetNode.data?.script || targetNode.data?.content || '';
          setTempNodePrompt(currentPrompt);
          
          toast({
            title: '📝 Node Selected',
            description: `Editing node: ${targetNode.label || targetNode.data?.label || 'Unknown'}`,
          });
        }
      } else {
        console.warn(`QC Integration: Node ${urlNodeId} not found in call flow. Available nodes:`, 
          callFlow.map(n => ({ id: n.id, label: n.label || n.data?.label }))
        );
        
        // Even if node not found, still show the suggestion if provided
        if (urlSuggestion) {
          setTempNodePrompt(urlSuggestion);
          setQcSuggestionMode(true);
          toast({
            title: '📝 QC Suggestion Loaded',
            description: `Suggestion loaded but node "${urlNodeId}" not found. Please select the correct node.`,
            variant: 'default'
          });
        }
      }
    }
  }, [urlNodeId, urlSuggestion, callFlow, toast]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  // Clear expected node when start node changes
  useEffect(() => {
    setExpectedNextNode('');
    setTransitionTestResult(null);
  }, [startNodeId]);

  const loadAgent = async () => {
    try {
      const response = await agentAPI.get(agentId);
      setAgent(response.data);
      
      // Load call flow for node selection in test mode
      if (response.data.call_flow) {
        setCallFlow(response.data.call_flow);
      }
    } catch (error) {
      console.error('Error loading agent:', error);
      toast({
        title: 'Error',
        description: 'Failed to load agent',
        variant: 'destructive'
      });
    }
  };

  const startSession = async () => {
    setIsLoading(true);
    try {
      // Build request body - include start_node_id if in transition test mode
      const requestBody = {};
      if (testMode && startNodeId) {
        requestBody.start_node_id = startNodeId;
      }
      
      const response = await safeFetch(`${process.env.REACT_APP_BACKEND_URL}/api/agents/${agentId}/test/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        throw new Error(response.text || 'Failed to start test session');
      }

      const data = response.json();
      setSessionId(data.session_id);
      
      // If starting from a specific node, update current node
      if (testMode && startNodeId) {
        setCurrentNodeId(startNodeId);
        setNodeTransitions([startNodeId]);
      }
      
      toast({
        title: 'Test Session Started',
        description: testMode && startNodeId 
          ? `Testing from node: ${getNodeLabel(startNodeId)}`
          : `Testing: ${data.agent_name}`
      });
    } catch (error) {
      console.error('Error starting session:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to start test session',
        variant: 'destructive'
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Reset conversation while keeping all settings (agent, test mode, start node, etc.)
  const resetConversation = async () => {
    // Clear conversation and metrics
    setConversation([]);
    setMetrics({ total_turns: 0, total_latency: 0, avg_latency: 0 });
    setCurrentNodeId(null);
    setNodeTransitions([]);
    setVariables({});
    setShouldEndCall(false);
    setTransitionTestResult(null);
    setSessionId(null);
    
    // Clear auto-test conversation if any
    setAutoTestConversation([]);
    setAutoTestStatus(null);
    
    toast({
      title: '🔄 Conversation Reset',
      description: 'Chat cleared. Your settings are preserved. Start a new test!',
    });
  };

  // Get available transitions from a selected node
  const getAvailableTransitions = (nodeId) => {
    if (!nodeId || !callFlow) return [];
    
    const sourceNode = callFlow.find(n => n.id === nodeId);
    if (!sourceNode) return [];
    
    // Get transitions from node data
    const transitions = sourceNode.data?.transitions || [];
    
    // Collect all target node IDs from transitions
    // Handle both field names: nextNode (from FlowBuilder) and target_node_id
    const targetNodeIds = new Set();
    transitions.forEach(t => {
      const targetId = t.nextNode || t.target_node_id;
      if (targetId) {
        targetNodeIds.add(targetId);
      }
    });
    
    // Also check for auto_transition_to
    if (sourceNode.data?.auto_transition_to) {
      targetNodeIds.add(sourceNode.data.auto_transition_to);
    }
    
    // Return the actual node objects for those IDs
    return callFlow.filter(n => targetNodeIds.has(n.id));
  };

  // Helper function to get node label/name from ID
  const getNodeLabel = useCallback((nodeId) => {
    if (!nodeId || !callFlow) return nodeId;
    
    const node = callFlow.find(n => n.id === nodeId);
    if (node) {
      // Try different field names for the label
      return node.data?.label || node.data?.name || node.name || node.label || nodeId;
    }
    return nodeId;
  }, [callFlow]);

  const availableTransitions = startNodeId ? getAvailableTransitions(startNodeId) : [];

  const sendMessage = async (e) => {
    e.preventDefault();
    
    if (!currentMessage.trim()) return;
    
    if (!sessionId) {
      await startSession();
      // Will send message after session is created
      return;
    }

    const userMessage = currentMessage;
    setCurrentMessage('');
    setIsLoading(true);

    // Add user message to UI immediately
    setConversation(prev => [...prev, {
      role: 'user',
      message: userMessage,
      timestamp: new Date().toISOString()
    }]);

    try {
      const response = await safeFetch(`${process.env.REACT_APP_BACKEND_URL}/api/agents/${agentId}/test/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          measure_real_tts: measureRealTTS,
          start_node_id: testMode ? startNodeId : null,
          expected_next_node: testMode ? expectedNextNode : null,
          node_overrides: nodeOverrides
        })
      });

      if (!response.ok) {
        throw new Error(response.text || 'Failed to send message');
      }

      // Parse JSON from response
      const data = response.json();

      // Add agent response to UI
      setConversation(prev => [...prev, {
        role: 'agent',
        message: data.agent_response || '(No response)',
        timestamp: new Date().toISOString(),
        latency: data.latency,
        node_id: data.current_node_id,
        node_label: data.current_node_label,
        detailed_timing: data.detailed_timing
      }]);

      // Update state
      setCurrentNodeId(data.current_node_id);
      setNodeTransitions(data.node_transitions || []);
      setVariables(data.variables || {});
      setMetrics(data.metrics || {});
      setShouldEndCall(data.should_end_call || false);
      
      // Handle transition test result
      if (data.transition_test) {
        // Use labels from backend if available, otherwise fallback to getNodeLabel
        const result = {
          ...data.transition_test,
          expected_label: data.transition_test.expected_label || getNodeLabel(data.transition_test.expected_node),
          actual_label: data.transition_test.actual_label || getNodeLabel(data.transition_test.actual_node),
          start_label: data.transition_test.start_label || getNodeLabel(data.transition_test.start_node)
        };
        
        setTransitionTestResult(result);
        toast({
          title: result.success ? 'Transition Test Passed ✅' : 'Transition Test Failed ❌',
          description: result.message,
          variant: result.success ? 'default' : 'destructive'
        });
      }

      if (data.should_end_call) {
        toast({
          title: 'Call Ended',
          description: 'Agent indicated the call should end'
        });
      }

      if (data.error) {
        toast({
          title: 'Error in Agent Response',
          description: data.error,
          variant: 'destructive'
        });
      }

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Check if session expired/not found - auto-restart session
      const errorMessage = error.message || '';
      if (errorMessage.includes('session not found') || errorMessage.includes('Test session not found')) {
        toast({
          title: 'Session Expired',
          description: 'Restarting test session...',
          variant: 'default'
        });
        
        // Clear old session and restart
        setSessionId(null);
        setConversation([]);
        setNodeTransitions([]);
        setMetrics({});
        setTransitionTestResult(null);
        
        // Auto-restart the session after a brief delay
        setTimeout(async () => {
          await startSession();
          toast({
            title: 'Session Restarted',
            description: 'Please send your message again',
            variant: 'default'
          });
        }, 500);
      } else {
        toast({
          title: 'Error',
          description: 'Failed to send message',
          variant: 'destructive'
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const resetSession = async () => {
    setIsLoading(true);
    try {
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/agents/${agentId}/test/reset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          session_id: sessionId
        })
      });

      // Clear local state
      setConversation([]);
      setNodeTransitions([]);
      setVariables({});
      setMetrics({ total_turns: 0, total_latency: 0, avg_latency: 0 });
      setCurrentNodeId(null);
      setShouldEndCall(false);
      setCurrentMessage('');

      toast({
        title: 'Session Reset',
        description: 'Test session has been reset'
      });
    } catch (error) {
      console.error('Error resetting session:', error);
      toast({
        title: 'Error',
        description: 'Failed to reset session',
        variant: 'destructive'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const exportResults = () => {
    const results = {
      agent: {
        id: agentId,
        name: agent?.name,
        type: agent?.agent_type
      },
      session_id: sessionId,
      conversation,
      metrics,
      node_transitions: nodeTransitions,
      variables,
      timestamp: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agent-test-${agentId}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: 'Exported',
      description: 'Test results downloaded'
    });
  };

  // ============================================================================
  // AI AUTO-TEST FUNCTIONS
  // ============================================================================

  const startAutoTest = async () => {
    try {
      setIsLoading(true);
      setAutoTestMode(true);
      setAutoTestConversation([]);
      setAutoTestStatus('starting');

      const response = await safeFetch(
        `${process.env.REACT_APP_BACKEND_URL || ''}/api/agents/${agentId}/auto-test/start`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            difficulty: autoTestDifficulty,
            custom_instructions: autoTestCustomInstructions || null,
            max_turns: autoTestMaxTurns,
            llm_provider: 'grok',
            start_node_id: startNodeId && startNodeId !== 'default' ? startNodeId : null
          })
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to start auto-test: ${response.status}`);
      }

      const data = response.json();
      setAutoTestSessionId(data.session_id);
      setAutoTestStatus('running');

      toast({
        title: '🤖 Auto-Test Started',
        description: `Running ${autoTestDifficulty} caller simulation...`
      });

      // Start polling for updates
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await safeFetch(
            `${process.env.REACT_APP_BACKEND_URL || ''}/api/agents/${agentId}/auto-test/status/${data.session_id}`,
            {
              method: 'GET',
              credentials: 'include'
            }
          );

          if (statusResponse.ok) {
            const statusData = statusResponse.json();
            setAutoTestConversation(statusData.conversation || []);
            setAutoTestStatus(statusData.status);
            setNodeTransitions(statusData.node_transitions || []);

            // Stop polling if completed
            if (statusData.status !== 'running') {
              clearInterval(pollInterval);
              setAutoTestPolling(null);
              setIsLoading(false);

              toast({
                title: statusData.status === 'completed' ? '✅ Auto-Test Complete' : '🛑 Auto-Test Stopped',
                description: `${statusData.conversation?.length || 0} messages exchanged. ${statusData.end_reason || ''}`
              });
            }
          }
        } catch (error) {
          console.error('Error polling auto-test status:', error);
        }
      }, 1000);

      setAutoTestPolling(pollInterval);

    } catch (error) {
      console.error('Error starting auto-test:', error);
      setAutoTestStatus('error');
      setIsLoading(false);
      toast({
        title: 'Error',
        description: error.message,
        variant: 'destructive'
      });
    }
  };

  const stopAutoTest = async () => {
    try {
      if (autoTestPolling) {
        clearInterval(autoTestPolling);
        setAutoTestPolling(null);
      }

      if (autoTestSessionId) {
        await safeFetch(
          `${process.env.REACT_APP_BACKEND_URL || ''}/api/agents/${agentId}/auto-test/stop`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ session_id: autoTestSessionId })
          }
        );
      }

      setAutoTestStatus('stopped');
      setIsLoading(false);

      toast({
        title: '🛑 Auto-Test Stopped',
        description: 'The simulated conversation was stopped.'
      });

    } catch (error) {
      console.error('Error stopping auto-test:', error);
    }
  };

  const resetAutoTest = () => {
    if (autoTestPolling) {
      clearInterval(autoTestPolling);
      setAutoTestPolling(null);
    }
    setAutoTestMode(false);
    setAutoTestSessionId(null);
    setAutoTestStatus(null);
    setAutoTestConversation([]);
    setIsLoading(false);
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (autoTestPolling) {
        clearInterval(autoTestPolling);
      }
    };
  }, [autoTestPolling]);

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={() => navigate(`/agents/${agentId}/edit`)}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Agent
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{agent.name}</h1>
              <p className="text-sm text-gray-500">Agent Tester - {agent.agent_type}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => navigate(`/agents/${agentId}/flow`)}
              className="border-purple-600 text-purple-600 hover:bg-purple-50"
            >
              <GitBranch className="h-4 w-4 mr-2" />
              Edit Flow
            </Button>
            <Button
              variant="outline"
              onClick={resetSession}
              disabled={isLoading || conversation.length === 0}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset
            </Button>
            <Button
              variant="outline"
              onClick={exportResults}
              disabled={conversation.length === 0}
            >
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-3 gap-6">
        {/* Conversation Panel - 2 columns */}
        <Card className="col-span-2 p-6 flex flex-col" style={{ height: 'calc(100vh - 200px)' }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Conversation</h2>
            <Button
              variant="outline"
              size="sm"
              onClick={resetConversation}
              disabled={isLoading}
              title="Clear chat and restart (keeps settings)"
              className="text-orange-600 border-orange-300 hover:bg-orange-50"
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              Clear & Restart
            </Button>
          </div>
          
          {/* Messages */}
          <div className="flex-1 overflow-y-auto mb-4 space-y-4">
            {conversation.length === 0 && (
              <div className="text-center text-gray-400 py-12">
                <p>No messages yet. Start typing to test the agent!</p>
              </div>
            )}
            
            {conversation.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-xs font-semibold opacity-70">
                      {msg.role === 'user' ? 'You' : 'Agent'}
                    </span>
                    {msg.latency && (
                      <span className="text-xs opacity-70">
                        {msg.latency.toFixed(2)}s
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap">{msg.message}</p>
                  
                  {/* Detailed timing for agent responses */}
                  {msg.role === 'agent' && msg.detailed_timing && (
                    <div className="mt-2 pt-2 border-t border-gray-300 text-xs opacity-70 space-y-1">
                      <div className="flex justify-between">
                        <span>LLM:</span>
                        <span>{msg.detailed_timing.llm_time?.toFixed(3)}s</span>
                      </div>
                      <div className="flex justify-between">
                        <span>TTS ({msg.detailed_timing.tts_method || 'formula'}):</span>
                        <span>{msg.detailed_timing.tts_time?.toFixed(3)}s</span>
                      </div>
                      {msg.detailed_timing.ttfb && (
                        <div className="flex justify-between text-[10px]">
                          <span className="ml-2">└─ TTFB:</span>
                          <span>{msg.detailed_timing.ttfb?.toFixed(3)}s</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span>System:</span>
                        <span>{msg.detailed_timing.system_overhead?.toFixed(3)}s</span>
                      </div>
                      <div className="flex justify-between font-semibold border-t border-gray-400 pt-1 mt-1">
                        <span>Total Latency:</span>
                        <span>{msg.detailed_timing.total_latency?.toFixed(3)}s</span>
                      </div>
                    </div>
                  )}
                  
                  {/* Node info with label */}
                  {msg.node_id && (
                    <p className="text-xs opacity-70 mt-2">
                      <span className="font-semibold">{msg.node_label || 'Node'}</span>
                      <br />
                      <span className="opacity-60">ID: {msg.node_id}</span>
                    </p>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* TTS Measurement Settings */}
          <div className="mb-3 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input 
                type="checkbox" 
                checked={measureRealTTS}
                onChange={(e) => setMeasureRealTTS(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-gray-600">
                Measure Real TTS (costs ~$0.001/turn, 100% accurate)
              </span>
            </label>
            
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input 
                type="checkbox" 
                checked={testMode}
                onChange={(e) => {
                  setTestMode(e.target.checked);
                  if (!e.target.checked) {
                    setStartNodeId('');
                    setExpectedNextNode('');
                    setTransitionTestResult(null);
                  }
                }}
                className="rounded border-gray-300"
              />
              <span className="text-gray-600">
                🎯 Transition Test Mode (test specific node transitions)
              </span>
            </label>
            
            {testMode && (
              <div className="ml-6 space-y-2 p-3 bg-blue-50 border border-blue-200 rounded">
                <div>
                  <label className="text-xs text-gray-600 block mb-1">Start From Node (type to search):</label>
                  <SearchableNodeSelect
                    nodes={callFlow}
                    value={startNodeId}
                    onValueChange={setStartNodeId}
                    placeholder="Search and select node..."
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600 block mb-1">Expected Next Node:</label>
                  <SearchableNodeSelect
                    nodes={availableTransitions}
                    value={expectedNextNode}
                    onValueChange={setExpectedNextNode}
                    placeholder={startNodeId ? "Search expected destination..." : "Select start node first..."}
                    disabled={!startNodeId}
                  />
                  {startNodeId && availableTransitions.length === 0 && (
                    <p className="text-xs text-amber-600 mt-1">
                      ⚠️ No transitions defined from this node. Add transitions in the flow builder.
                    </p>
                  )}
                </div>
                <p className="text-xs text-gray-500">
                  Select nodes to test if a transition works correctly. The system will start from your specified node and validate it transitions to the expected node.
                </p>
                {transitionTestResult && (
                  <div className={`mt-2 p-3 rounded text-xs ${
                    transitionTestResult.success 
                      ? 'bg-green-100 border border-green-300 text-green-800' 
                      : 'bg-red-100 border border-red-300 text-red-800'
                  }`}>
                    <div className="font-semibold text-sm mb-2">
                      {transitionTestResult.success ? '✅ Transition Test Passed' : '❌ Transition Test Failed'}
                    </div>
                    <div className="space-y-1">
                      <div><span className="font-medium">From Node:</span> {transitionTestResult.start_label || transitionTestResult.start_node}</div>
                      <div><span className="font-medium">User Said:</span> &quot;{transitionTestResult.user_message}&quot;</div>
                      <div><span className="font-medium">Expected Transition To:</span> {transitionTestResult.expected_label}</div>
                      <div><span className="font-medium">Actual Transition To:</span> {transitionTestResult.actual_label || 'No transition matched'}</div>
                      {transitionTestResult.matched_condition && (
                        <div className="mt-1 text-xs opacity-75">
                          <span className="font-medium">Matched Condition:</span> {transitionTestResult.matched_condition}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* AI Auto-Test Mode */}
            <div className="mt-3 pt-3 border-t border-gray-200">
              <label className="flex items-center gap-2 cursor-pointer text-sm mb-2">
                <input 
                  type="checkbox" 
                  checked={autoTestMode}
                  onChange={(e) => {
                    if (!e.target.checked) {
                      resetAutoTest();
                    } else {
                      setAutoTestMode(true);
                    }
                  }}
                  className="rounded border-gray-300"
                  disabled={isLoading && autoTestStatus === 'running'}
                />
                <span className="text-gray-600 font-medium">
                  🤖 AI Auto-Test (Simulated Caller)
                </span>
              </label>

              {autoTestMode && (
                <div className="ml-6 space-y-3 p-3 bg-purple-50 border border-purple-200 rounded">
                  {/* Difficulty Selection */}
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Caller Difficulty:</label>
                    <Select 
                      value={autoTestDifficulty} 
                      onValueChange={setAutoTestDifficulty}
                      disabled={autoTestStatus === 'running'}
                    >
                      <SelectTrigger className="bg-white text-sm h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="compliant">
                          <span className="flex items-center gap-2">
                            <span className="text-green-500">😊</span> Compliant - Friendly, cooperative
                          </span>
                        </SelectItem>
                        <SelectItem value="skeptical">
                          <span className="flex items-center gap-2">
                            <span className="text-yellow-500">🤔</span> Skeptical - Cautious, questioning
                          </span>
                        </SelectItem>
                        <SelectItem value="hostile">
                          <span className="flex items-center gap-2">
                            <span className="text-red-500">😠</span> Hostile - Confrontational, difficult
                          </span>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Max Turns */}
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Max Conversation Turns: {autoTestMaxTurns}</label>
                    <input
                      type="range"
                      min="5"
                      max="30"
                      value={autoTestMaxTurns}
                      onChange={(e) => setAutoTestMaxTurns(parseInt(e.target.value))}
                      className="w-full"
                      disabled={autoTestStatus === 'running'}
                    />
                  </div>

                  {/* Custom Instructions */}
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Custom Instructions (Optional):</label>
                    <textarea
                      value={autoTestCustomInstructions}
                      onChange={(e) => setAutoTestCustomInstructions(e.target.value)}
                      placeholder="E.g., 'Ask about pricing twice', 'Mention a competitor', 'Be interested in the premium plan'..."
                      className="w-full text-sm p-2 border rounded bg-white h-16 resize-none"
                      disabled={autoTestStatus === 'running'}
                    />
                  </div>

                  {/* Start Node (Optional) */}
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Start From Node (type to search):</label>
                    <SearchableNodeSelect
                      nodes={[{ id: 'default', label: 'Default', type: 'start node' }, ...callFlow]}
                      value={startNodeId || 'default'}
                      onValueChange={(val) => setStartNodeId(val === 'default' ? '' : val)}
                      placeholder="Search nodes..."
                      disabled={autoTestStatus === 'running'}
                    />
                  </div>

                  {/* Status Display */}
                  {autoTestStatus && (
                    <div className={`p-2 rounded text-sm ${
                      autoTestStatus === 'running' ? 'bg-blue-100 text-blue-800' :
                      autoTestStatus === 'completed' ? 'bg-green-100 text-green-800' :
                      autoTestStatus === 'stopped' ? 'bg-yellow-100 text-yellow-800' :
                      autoTestStatus === 'error' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {autoTestStatus === 'running' && '🔄 Running... '}
                      {autoTestStatus === 'completed' && '✅ Completed - '}
                      {autoTestStatus === 'stopped' && '🛑 Stopped - '}
                      {autoTestStatus === 'error' && '❌ Error - '}
                      {autoTestConversation.length > 0 && `${autoTestConversation.length} messages`}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    {autoTestStatus !== 'running' ? (
                      <Button
                        onClick={startAutoTest}
                        disabled={isLoading}
                        className="flex-1 bg-purple-600 hover:bg-purple-700"
                      >
                        {isLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Play className="h-4 w-4 mr-2" />
                        )}
                        Start Auto-Test
                      </Button>
                    ) : (
                      <Button
                        onClick={stopAutoTest}
                        variant="destructive"
                        className="flex-1"
                      >
                        <Square className="h-4 w-4 mr-2" />
                        Stop
                      </Button>
                    )}
                    {(autoTestStatus === 'completed' || autoTestStatus === 'stopped') && (
                      <Button
                        onClick={resetAutoTest}
                        variant="outline"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  <p className="text-xs text-gray-500">
                    AI will simulate a {autoTestDifficulty} caller going through your agent&apos;s flow. Watch the conversation appear in real-time.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Show Auto-Test Conversation if active */}
          {autoTestMode && autoTestConversation.length > 0 && (
            <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded">
              <h4 className="text-sm font-semibold text-purple-800 mb-2">🤖 Auto-Test Conversation</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {autoTestConversation.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`text-sm p-2 rounded ${
                      msg.role === 'user' 
                        ? 'bg-purple-100 text-purple-900 ml-8' 
                        : 'bg-white text-gray-900 mr-8 border'
                    }`}
                  >
                    <span className="font-medium">
                      {msg.role === 'user' ? '👤 Caller: ' : '🤖 Agent: '}
                    </span>
                    {msg.content}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <form onSubmit={sendMessage} className="flex gap-2">
            <Input
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              placeholder="Type your message..."
              disabled={isLoading || shouldEndCall}
              className="flex-1"
            />
            <Button type="submit" disabled={isLoading || shouldEndCall || !currentMessage.trim()}>
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>

          {shouldEndCall && (
            <div className="mt-2 text-sm text-amber-600 text-center">
              ⚠️ Agent indicated call should end
            </div>
          )}
        </Card>

        {/* Metrics Panel - 1 column */}
        <div className="space-y-6">
          {/* Metrics Card */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Metrics</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Total Turns:</span>
                <span className="font-medium">{metrics.total_turns || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Avg Latency:</span>
                <span className="font-medium">
                  {metrics.avg_latency ? `${metrics.avg_latency.toFixed(2)}s` : '0s'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total Latency:</span>
                <span className="font-medium">
                  {metrics.total_latency ? `${metrics.total_latency.toFixed(2)}s` : '0s'}
                </span>
              </div>
            </div>
          </Card>

          {/* Current Node Card */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Current Node</h3>
            <div className="text-sm">
              {currentNodeId ? (
                <div className="bg-gray-100 px-3 py-2 rounded">
                  <div className="font-medium text-gray-800">{getNodeLabel(currentNodeId)}</div>
                  <div className="text-xs text-gray-500 mt-1">ID: {currentNodeId}</div>
                </div>
              ) : (
                <span className="text-gray-400">Not started</span>
              )}
            </div>
          </Card>

          {/* Node Transitions Card */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Node Transitions</h3>
            <div className="space-y-2 text-xs max-h-40 overflow-y-auto">
              {nodeTransitions.length > 0 ? (
                nodeTransitions.map((transition, idx) => {
                  // Handle both old format (string nodeId) and new format (object with node_id)
                  const nodeId = typeof transition === 'object' ? transition.node_id : transition;
                  const turn = typeof transition === 'object' ? transition.turn : null;
                  return (
                    <div key={idx} className="flex items-center gap-2 bg-gray-50 px-2 py-1.5 rounded">
                      <span className="text-gray-400 w-5">{idx + 1}.</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-800 truncate">
                          {getNodeLabel(nodeId)}
                          {turn !== null && <span className="text-gray-400 ml-2">(turn {turn})</span>}
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <span className="text-gray-400">No transitions yet</span>
              )}
            </div>
          </Card>

          {/* Variables Card */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Variables Extracted</h3>
            <div className="space-y-2 text-xs max-h-60 overflow-y-auto">
              {Object.keys(variables).length > 0 ? (
                Object.entries(variables).map(([key, value]) => (
                  <div key={key} className="border-b border-gray-100 pb-2">
                    <div className="font-medium text-gray-700">{key}:</div>
                    <div className="text-gray-600 mt-1 break-all">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </div>
                  </div>
                ))
              ) : (
                <span className="text-gray-400">No variables extracted</span>
              )}
            </div>
          </Card>

          {/* Node Prompt Editor Card */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">📝 Edit Node Prompts (Temporary)</h3>
            <p className="text-xs text-gray-500 mb-3">
              Edit prompts to test changes without affecting your live agent. 
              Changes only apply to this test session.
            </p>
            
            <div className="space-y-3">
              <SearchableNodeSelect
                nodes={callFlow.map(node => ({
                  ...node,
                  label: nodeOverrides[node.id] ? `* ${node.label || node.id}` : (node.label || node.id)
                }))}
                value={editingNodeId || ''}
                onValueChange={(value) => {
                  setEditingNodeId(value);
                  // Load existing override or original prompt
                  if (nodeOverrides[value]) {
                    setTempNodePrompt(nodeOverrides[value]);
                  } else {
                    const node = callFlow.find(n => n.id === value);
                    setTempNodePrompt(node?.data?.prompt || '');
                  }
                }}
                placeholder="Search and select node to edit..."
              />

              {editingNodeId && (
                <>
                  <textarea
                    value={tempNodePrompt}
                    onChange={(e) => setTempNodePrompt(e.target.value)}
                    placeholder="Enter modified prompt..."
                    className="w-full h-40 text-xs border border-gray-300 rounded p-2 font-mono resize-y"
                  />
                  
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => {
                        setNodeOverrides(prev => ({
                          ...prev,
                          [editingNodeId]: tempNodePrompt
                        }));
                        toast({
                          title: 'Prompt Override Saved',
                          description: `Temporary prompt saved for node. Test to see changes.`
                        });
                      }}
                      className="flex-1 bg-purple-600 hover:bg-purple-700"
                    >
                      Save Override
                    </Button>
                    <Button
                      size="sm"
                      onClick={async () => {
                        // Save the override first
                        setNodeOverrides(prev => ({
                          ...prev,
                          [editingNodeId]: tempNodePrompt
                        }));
                        
                        // Start a new session if needed
                        let currentSessionId = sessionId;
                        if (!currentSessionId) {
                          try {
                            const response = await safeFetch(`${process.env.REACT_APP_BACKEND_URL}/api/agents/${agentId}/test/start`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              credentials: 'include',
                              body: JSON.stringify({ start_node_id: editingNodeId })
                            });
                            if (response.ok) {
                              const data = response.json();
                              currentSessionId = data.session_id;
                              setSessionId(currentSessionId);
                            }
                          } catch (err) {
                            console.error('Error starting session:', err);
                          }
                        }
                        
                        if (!currentSessionId) {
                          toast({
                            title: 'Error',
                            description: 'Could not start test session',
                            variant: 'destructive'
                          });
                          return;
                        }
                        
                        // Send a test message to trigger the node
                        setIsLoading(true);
                        try {
                          const testResponse = await safeFetch(`${process.env.REACT_APP_BACKEND_URL}/api/agents/${agentId}/test/message`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'include',
                            body: JSON.stringify({
                              message: 'Test prompt response',
                              session_id: currentSessionId,
                              start_node_id: editingNodeId,
                              node_overrides: { [editingNodeId]: tempNodePrompt }
                            })
                          });
                          
                          if (testResponse.ok) {
                            const data = testResponse.json();
                            // Add the test result to conversation
                            setConversation([{
                              role: 'system',
                              message: `🧪 Testing node: ${getNodeLabel(editingNodeId)}`,
                              timestamp: new Date().toISOString()
                            }, {
                              role: 'agent',
                              message: data.agent_response || '(No response)',
                              timestamp: new Date().toISOString(),
                              latency: data.latency,
                              node_id: data.current_node_id,
                              node_label: data.current_node_label
                            }]);
                            
                            setCurrentNodeId(data.current_node_id);
                            toast({
                              title: '✅ Node Tested',
                              description: 'Check the conversation for the agent response'
                            });
                          }
                        } catch (err) {
                          console.error('Error testing node:', err);
                          toast({
                            title: 'Error',
                            description: 'Failed to test node',
                            variant: 'destructive'
                          });
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                      className="flex-1 bg-green-600 hover:bg-green-700"
                      disabled={isLoading || !tempNodePrompt.trim()}
                    >
                      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 mr-1" />}
                      Test Now
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const newOverrides = {...nodeOverrides};
                        delete newOverrides[editingNodeId];
                        setNodeOverrides(newOverrides);
                        const node = callFlow.find(n => n.id === editingNodeId);
                        setTempNodePrompt(node?.data?.prompt || '');
                        toast({
                          title: 'Reset to Original',
                          description: 'Prompt reset to original version'
                        });
                      }}
                    >
                      Reset
                    </Button>
                  </div>
                  
                  {/* Save to Flow Builder Button */}
                  <div className="flex gap-2 pt-2 border-t border-gray-700">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        // Copy the prompt to clipboard
                        navigator.clipboard.writeText(tempNodePrompt);
                        const node = callFlow.find(n => n.id === editingNodeId);
                        toast({
                          title: '📋 Prompt Copied!',
                          description: `Prompt for "${node?.label || 'node'}" copied. Opening Flow Builder...`,
                        });
                        // Open flow builder in new tab
                        setTimeout(() => {
                          window.open(`/agents/${agentId}/flow`, '_blank');
                        }, 500);
                      }}
                      className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
                      disabled={!tempNodePrompt.trim()}
                    >
                      📋 Copy & Open Flow Builder ↗
                    </Button>
                  </div>
                  
                  {qcSuggestionMode && (
                    <div className="text-xs text-blue-600 bg-blue-50 p-2 rounded border border-blue-200">
                      <strong>💡 QC Suggestion Loaded</strong>
                      <p className="mt-1 text-blue-700">This prompt was suggested by the QC system. Test it first, then click &quot;Copy &amp; Open Flow Builder&quot; to make it permanent.</p>
                    </div>
                  )}

                  {Object.keys(nodeOverrides).length > 0 && (
                    <div className="text-xs text-yellow-600 bg-yellow-50 p-2 rounded">
                      <strong>Active Overrides:</strong>
                      <div className="mt-1 space-y-1">
                        {Object.keys(nodeOverrides).map(nodeId => {
                          const node = callFlow.find(n => n.id === nodeId);
                          return (
                            <div key={nodeId}>
                              • {node?.label || nodeId.slice(0, 8)}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
