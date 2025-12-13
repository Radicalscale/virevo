import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from './ui/collapsible';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Play,
  Plus,
  Trash2,
  Variable,
  Webhook,
  ArrowRight,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import api from '../services/api';

/**
 * NodeSequenceTester - Test node flows with exact same code paths as live calls
 */
const NodeSequenceTester = ({ agentId, isOpen, onClose }) => {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState(null);
  
  // Test configuration
  const [selectedNodes, setSelectedNodes] = useState([]);
  const [responses, setResponses] = useState([]);
  const [initialVariables, setInitialVariables] = useState([
    { key: 'customer_name', value: '' }
  ]);
  
  // Test results
  const [testResult, setTestResult] = useState(null);

  // Load nodes when modal opens
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
  }, [isOpen, agentId, loadNodes]);

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

  const runTest = async () => {
    if (selectedNodes.length === 0) {
      setError('Please select at least one node to test');
      return;
    }

    if (responses.some(r => !r.trim())) {
      setError('Please provide a response for each node');
      return;
    }

    setTesting(true);
    setError(null);
    setTestResult(null);

    try {
      // Convert initial variables array to object
      const varsObj = {};
      initialVariables.forEach(v => {
        if (v.key.trim()) {
          varsObj[v.key.trim()] = v.value;
        }
      });

      const payload = {
        node_ids: selectedNodes.map(n => n.id),
        responses: responses,
        initial_variables: Object.keys(varsObj).length > 0 ? varsObj : null
      };

      const response = await api.post(`/agents/${agentId}/test-sequence`, payload);
      setTestResult(response.data);
    } catch (err) {
      setError('Test failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setTesting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <CardHeader className="flex-shrink-0">
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="text-xl">Node Sequence Tester</CardTitle>
              <CardDescription>
                Test node flows with exact same logic as live calls
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>×</Button>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-hidden flex gap-4">
          {/* Left Panel - Configuration */}
          <div className="w-1/2 flex flex-col gap-4 overflow-hidden">
            {/* Node Selector */}
            <div className="flex-shrink-0">
              <Label className="text-sm font-medium mb-2 block">Add Node to Sequence</Label>
              <Select onValueChange={addNodeToSequence}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a node..." />
                </SelectTrigger>
                <SelectContent>
                  {nodes.map(node => (
                    <SelectItem key={node.id} value={node.id}>
                      <div className="flex items-center gap-2">
                        <span>{node.label || node.id}</span>
                        {node.has_extraction && (
                          <Badge variant="outline" className="text-xs">
                            <Variable className="w-3 h-3 mr-1" />
                            {node.extract_variables?.length || 0}
                          </Badge>
                        )}
                        {node.has_webhook && (
                          <Badge variant="outline" className="text-xs">
                            <Webhook className="w-3 h-3" />
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Selected Nodes & Responses */}
            <ScrollArea className="flex-1">
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
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                    
                    {node.content_preview && (
                      <p className="text-xs text-muted-foreground mb-2 italic">
                        &ldquo;{node.content_preview}&rdquo;
                      </p>
                    )}
                    
                    <div className="flex gap-2 mb-2 flex-wrap">
                      {node.has_extraction && (
                        <Badge variant="outline" className="text-xs">
                          Extracts: {node.extract_variables?.join(', ')}
                        </Badge>
                      )}
                      {node.has_webhook && (
                        <Badge variant="outline" className="text-xs">
                          <Webhook className="w-3 h-3 mr-1" />
                          Webhook
                        </Badge>
                      )}
                    </div>
                    
                    <Textarea
                      placeholder="Simulated user response..."
                      value={responses[index]}
                      onChange={(e) => updateResponse(index, e.target.value)}
                      className="text-sm"
                      rows={2}
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
                    Select nodes above to build your test sequence
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Initial Variables */}
            <div className="flex-shrink-0">
              <div className="flex justify-between items-center mb-2">
                <Label className="text-sm font-medium">Initial Variables</Label>
                <Button variant="ghost" size="sm" onClick={addVariable}>
                  <Plus className="w-4 h-4 mr-1" /> Add
                </Button>
              </div>
              <div className="space-y-2">
                {initialVariables.map((v, i) => (
                  <div key={i} className="flex gap-2">
                    <Input
                      placeholder="Variable name"
                      value={v.key}
                      onChange={(e) => updateVariable(i, 'key', e.target.value)}
                      className="flex-1"
                    />
                    <Input
                      placeholder="Value"
                      value={v.value}
                      onChange={(e) => updateVariable(i, 'value', e.target.value)}
                      className="flex-1"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeVariable(i)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            {/* Run Button */}
            <Button
              className="w-full"
              onClick={runTest}
              disabled={testing || selectedNodes.length === 0}
            >
              {testing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Running Test...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run Test
                </>
              )}
            </Button>

            {error && (
              <div className="flex items-center gap-2 text-destructive text-sm">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}
          </div>

          {/* Right Panel - Results */}
          <div className="w-1/2 flex flex-col overflow-hidden border-l pl-4">
            <Label className="text-sm font-medium mb-2">Test Results</Label>
            
            {loading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin" />
              </div>
            )}

            {!testResult && !loading && (
              <div className="flex-1 flex items-center justify-center text-muted-foreground">
                Run a test to see results
              </div>
            )}

            {testResult && (
              <ScrollArea className="flex-1">
                <div className="space-y-4 pr-4">
                  {/* Summary */}
                  <Card className={testResult.success ? 'border-green-500' : 'border-red-500'}>
                    <CardContent className="p-3">
                      <div className="flex items-center gap-2 mb-2">
                        {testResult.success ? (
                          <CheckCircle2 className="w-5 h-5 text-green-500" />
                        ) : (
                          <AlertCircle className="w-5 h-5 text-red-500" />
                        )}
                        <span className="font-medium">
                          {testResult.success ? 'All Tests Passed' : 'Issues Found'}
                        </span>
                      </div>
                      
                      {testResult.summary && (
                        <div className="text-sm text-muted-foreground">
                          {testResult.summary.total_steps} steps • 
                          {testResult.summary.variables_extracted} extractions • 
                          {testResult.summary.webhooks_tested} webhooks • 
                          {testResult.summary.issues_count} issues
                        </div>
                      )}
                      
                      {testResult.issues_found?.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {testResult.issues_found.map((issue, i) => (
                            <div key={i} className="text-sm text-red-600 flex items-start gap-1">
                              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                              {issue}
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Step Details */}
                  {testResult.steps?.map((step, index) => (
                    <StepResult key={index} step={step} />
                  ))}

                  {/* Final Variables */}
                  {testResult.final_variables && Object.keys(testResult.final_variables).length > 0 && (
                    <Card>
                      <CardHeader className="py-2 px-3">
                        <CardTitle className="text-sm">Final Variables</CardTitle>
                      </CardHeader>
                      <CardContent className="p-3 pt-0">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {Object.entries(testResult.final_variables).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="font-mono text-muted-foreground">{key}:</span>
                              <span className="font-medium">{String(value)}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </ScrollArea>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

/**
 * Individual step result component
 */
const StepResult = ({ step }) => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card className={step.success ? '' : 'border-amber-500'}>
        <CollapsibleTrigger className="w-full">
          <CardHeader className="py-2 px-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <Badge variant="outline">{step.step_number}</Badge>
              <span className="font-medium text-sm">{step.node_label}</span>
            </div>
            {step.success ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            )}
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="p-3 pt-0 space-y-3">
            {/* User Response */}
            <div>
              <Label className="text-xs text-muted-foreground">User Said</Label>
              <p className="text-sm italic">&ldquo;{step.user_response}&rdquo;</p>
            </div>

            {/* Extraction */}
            {step.extraction && (
              <div>
                <Label className="text-xs text-muted-foreground">Extraction</Label>
                {step.extraction.extracted && Object.keys(step.extraction.extracted).length > 0 ? (
                  <div className="space-y-1">
                    {Object.entries(step.extraction.extracted).map(([key, value]) => (
                      <div key={key} className="flex items-center gap-2 text-sm">
                        <Badge variant="secondary" className="font-mono">{key}</Badge>
                        <span>=</span>
                        <span className="font-medium">{String(value)}</span>
                      </div>
                    ))}
                    {step.extraction.calculations_shown?.map((calc, i) => (
                      <div key={i} className="text-xs text-muted-foreground">
                        📊 {calc}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No variables extracted</p>
                )}
                {step.extraction.errors?.length > 0 && (
                  <div className="text-sm text-red-600 mt-1">
                    {step.extraction.errors.join(', ')}
                  </div>
                )}
              </div>
            )}

            {/* Transition */}
            {step.transition && (
              <div>
                <Label className="text-xs text-muted-foreground">Transition Logic</Label>
                <div className="space-y-1">
                  {step.transition.conditions_evaluated?.map((cond, i) => (
                    <div key={i} className="text-sm">
                      <div className="flex items-center gap-2">
                        {cond.result === true ? (
                          <CheckCircle2 className="w-3 h-3 text-green-500" />
                        ) : cond.result === 'default' ? (
                          <span className="w-3 h-3 text-xs">⚡</span>
                        ) : (
                          <span className="w-3 h-3 text-xs text-muted-foreground">○</span>
                        )}
                        <code className="text-xs bg-muted px-1 rounded">
                          {cond.condition || 'default'}
                        </code>
                        <ArrowRight className="w-3 h-3" />
                        <span className="text-xs">{cond.target_node_label || cond.target_node}</span>
                      </div>
                      {cond.condition_after_substitution && (
                        <div className="text-xs text-muted-foreground ml-5">
                          → {cond.condition_after_substitution}
                        </div>
                      )}
                    </div>
                  ))}
                  {step.transition.next_node_id && (
                    <div className="text-sm font-medium text-green-600">
                      Next: {step.transition.next_node_label || step.transition.next_node_id}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Webhook Execution */}
            {step.webhook && (
              <div>
                <Label className="text-xs text-muted-foreground">Webhook Executed</Label>
                <div className="space-y-2">
                  {/* Request */}
                  <div className="text-xs">
                    <span className="font-medium">{step.webhook.method || 'POST'}</span>
                    <span className="text-muted-foreground ml-2 break-all">{step.webhook.url}</span>
                  </div>
                  
                  {/* Payload Sent */}
                  <div>
                    <span className="text-xs text-muted-foreground">Payload Sent:</span>
                    <div className="bg-muted p-2 rounded text-xs font-mono overflow-x-auto max-h-24">
                      {JSON.stringify(step.webhook.payload_sent, null, 2)}
                    </div>
                  </div>
                  
                  {/* Response */}
                  {step.webhook.executed && (
                    <div>
                      <span className="text-xs text-muted-foreground">
                        Response: 
                        <Badge 
                          variant={step.webhook.response_status < 400 ? 'default' : 'destructive'}
                          className="ml-2"
                        >
                          {step.webhook.response_status}
                        </Badge>
                      </span>
                      <div className="bg-muted p-2 rounded text-xs font-mono overflow-x-auto max-h-32 mt-1">
                        {typeof step.webhook.response_data === 'object' 
                          ? JSON.stringify(step.webhook.response_data, null, 2)
                          : step.webhook.response}
                      </div>
                    </div>
                  )}
                  
                  {/* Error */}
                  {step.webhook.error && (
                    <div className="text-sm text-red-600 flex items-center gap-1">
                      <AlertCircle className="w-4 h-4" />
                      {step.webhook.error}
                    </div>
                  )}
                  
                  {/* Missing Variables */}
                  {step.webhook.missing_variables?.length > 0 && (
                    <div className="text-sm text-amber-600 flex items-center gap-1">
                      <AlertTriangle className="w-4 h-4" />
                      Missing: {step.webhook.missing_variables.map(m => m.expected_variable).join(', ')}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Legacy webhook_preview support */}
            {step.webhook_preview && !step.webhook && (
              <div>
                <Label className="text-xs text-muted-foreground">Webhook Preview</Label>
                <div className="bg-muted p-2 rounded text-xs font-mono overflow-x-auto">
                  {JSON.stringify(step.webhook_preview.body, null, 2)}
                </div>
                {step.webhook_preview.missing_variables?.length > 0 && (
                  <div className="text-sm text-amber-600 mt-1 flex items-center gap-1">
                    <AlertTriangle className="w-4 h-4" />
                    Missing: {step.webhook_preview.missing_variables.map(m => m.expected_variable).join(', ')}
                  </div>
                )}
              </div>
            )}

            {/* Warnings */}
            {step.warnings?.length > 0 && (
              <div className="space-y-1">
                {step.warnings.map((warning, i) => (
                  <div key={i} className="text-sm text-amber-600 flex items-start gap-1">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    {warning}
                  </div>
                ))}
              </div>
            )}

            {/* Errors */}
            {step.errors?.length > 0 && (
              <div className="space-y-1">
                {step.errors.map((error, i) => (
                  <div key={i} className="text-sm text-red-600 flex items-start gap-1">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
};

export default NodeSequenceTester;
