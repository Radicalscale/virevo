import React, { useState, useEffect } from 'react';
import { Play, Activity, GitBranch, Mic, Save, Shield, AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';

const API_BASE = process.env.REACT_APP_API_URL || '';

const DirectorTab = () => {
    // State
    const [agents, setAgents] = useState([]);
    const [agentsLoading, setAgentsLoading] = useState(true);
    const [agentsError, setAgentsError] = useState(null);

    const [selectedAgent, setSelectedAgent] = useState(null);
    const [sandboxId, setSandboxId] = useState(null);
    const [sandboxLoading, setSandboxLoading] = useState(false);

    const [nodes, setNodes] = useState([]);
    const [nodesLoading, setNodesLoading] = useState(false);
    const [selectedNode, setSelectedNode] = useState(null);

    const [evolving, setEvolving] = useState(false);
    const [evolutionResult, setEvolutionResult] = useState(null);
    const [evolutionError, setEvolutionError] = useState(null);

    const [promoting, setPromoting] = useState(false);

    // Fetch real agents on mount
    useEffect(() => {
        fetchAgents();
    }, []);

    const fetchAgents = async () => {
        setAgentsLoading(true);
        setAgentsError(null);
        try {
            const res = await fetch(`${API_BASE}/api/agents`, {
                credentials: 'include'
            });
            if (!res.ok) throw new Error('Failed to fetch agents');
            const data = await res.json();
            setAgents(data || []);
        } catch (e) {
            console.error('Error fetching agents:', e);
            setAgentsError(e.message);
        } finally {
            setAgentsLoading(false);
        }
    };

    const handleAgentSelect = async (agent) => {
        setSelectedAgent(agent);
        setEvolutionResult(null);
        setSelectedNode(null);
        setNodes([]);
        setSandboxId(null);

        // Create sandbox via real API
        setSandboxLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/director/sandbox`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agent.id })
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create sandbox');
            }
            const data = await res.json();
            setSandboxId(data.sandbox_id);

            // Now fetch nodes for this sandbox
            await fetchNodes(data.sandbox_id);
        } catch (e) {
            console.error('Error creating sandbox:', e);
            setAgentsError(e.message);
        } finally {
            setSandboxLoading(false);
        }
    };

    const fetchNodes = async (sbId) => {
        setNodesLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/director/sandbox/${sbId}/nodes`, {
                credentials: 'include'
            });
            if (!res.ok) throw new Error('Failed to fetch nodes');
            const data = await res.json();
            setNodes(data.nodes || []);
        } catch (e) {
            console.error('Error fetching nodes:', e);
        } finally {
            setNodesLoading(false);
        }
    };

    const handleEvolve = async () => {
        if (!selectedNode || !sandboxId) return;
        setEvolving(true);
        setEvolutionError(null);
        setEvolutionResult(null);

        try {
            const res = await fetch(`${API_BASE}/api/director/evolve`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sandbox_id: sandboxId,
                    node_id: selectedNode.id,
                    generations: 3
                })
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Evolution failed');
            }
            const data = await res.json();
            setEvolutionResult(data);
        } catch (e) {
            console.error('Evolution error:', e);
            setEvolutionError(e.message);
        } finally {
            setEvolving(false);
        }
    };

    const handlePromote = async () => {
        if (!sandboxId) return;
        setPromoting(true);
        try {
            const res = await fetch(`${API_BASE}/api/director/promote`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sandbox_id: sandboxId })
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Promotion failed');
            }
            alert('✅ Sandbox promoted to live agent!');
            setSandboxId(null);
            setSelectedAgent(null);
            setEvolutionResult(null);
        } catch (e) {
            console.error('Promote error:', e);
            alert('❌ Failed: ' + e.message);
        } finally {
            setPromoting(false);
        }
    };

    return (
        <div className="p-8 space-y-8 bg-gray-900 min-h-screen text-gray-100">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Activity className="text-blue-500" />
                        Director Studio
                    </h1>
                    <p className="text-gray-400 mt-1">Automated Evolutionary Optimization Engine</p>
                </div>
                {sandboxId && (
                    <div className="flex items-center gap-2 px-4 py-2 bg-green-900/30 border border-green-500/50 rounded-full text-green-400">
                        <Shield size={16} />
                        <span className="text-sm font-mono">SANDBOX ACTIVE</span>
                    </div>
                )}
            </div>

            {/* 1. Agent Selection */}
            <Card className="bg-gray-800 border-gray-700 p-6">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold">1. Select Target Agent</h2>
                    <Button variant="outline" size="sm" onClick={fetchAgents} disabled={agentsLoading}>
                        <RefreshCw size={14} className={agentsLoading ? 'animate-spin' : ''} />
                    </Button>
                </div>

                {agentsLoading ? (
                    <div className="flex items-center gap-2 text-gray-400">
                        <Loader2 className="animate-spin" size={18} />
                        Loading agents...
                    </div>
                ) : agentsError ? (
                    <div className="flex items-center gap-2 text-red-400">
                        <AlertCircle size={18} />
                        {agentsError}
                    </div>
                ) : agents.length === 0 ? (
                    <p className="text-gray-400">No agents found. Create an agent first.</p>
                ) : (
                    <div className="flex flex-wrap gap-3">
                        {agents.map(agent => (
                            <Button
                                key={agent.id}
                                onClick={() => handleAgentSelect(agent)}
                                disabled={sandboxLoading}
                                variant={selectedAgent?.id === agent.id ? "default" : "outline"}
                                className={`${selectedAgent?.id === agent.id ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
                            >
                                {sandboxLoading && selectedAgent?.id === agent.id ? (
                                    <Loader2 className="animate-spin mr-2" size={14} />
                                ) : null}
                                {agent.name}
                            </Button>
                        ))}
                    </div>
                )}
            </Card>

            {selectedAgent && sandboxId && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                    {/* 2. Node Inspector */}
                    <Card className="bg-gray-800 border-gray-700 p-6">
                        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                            <GitBranch className="text-purple-400" />
                            2. Select Node to Evolve
                        </h2>

                        {nodesLoading ? (
                            <div className="flex items-center gap-2 text-gray-400">
                                <Loader2 className="animate-spin" size={18} />
                                Loading nodes...
                            </div>
                        ) : nodes.length === 0 ? (
                            <p className="text-gray-400">No nodes found in this agent's call flow.</p>
                        ) : (
                            <div className="space-y-2 max-h-80 overflow-y-auto">
                                {nodes.map(node => (
                                    <div
                                        key={node.id}
                                        onClick={() => setSelectedNode(node)}
                                        className={`p-4 rounded-lg cursor-pointer border transition-all ${selectedNode?.id === node.id
                                            ? 'bg-purple-900/40 border-purple-500'
                                            : 'bg-gray-900 border-gray-700 hover:border-gray-600'
                                            }`}
                                    >
                                        <div className="font-medium text-white">{node.label}</div>
                                        <div className="text-xs text-gray-500 mt-1">Mode: {node.mode}</div>
                                        {node.content_preview && (
                                            <div className="text-sm text-gray-400 mt-1 truncate">
                                                "{node.content_preview}"
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>

                    {/* 3. Evolution Controls */}
                    <Card className="bg-gray-800 border-gray-700 p-6 flex flex-col justify-between">
                        <div>
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <Mic className="text-red-400" />
                                3. The Evolution Engine
                            </h2>
                            <p className="text-gray-400 mb-6">
                                Current State: <span className="text-white">{selectedNode ? 'Ready' : 'Waiting for selection...'}</span>
                            </p>

                            {selectedNode && (
                                <div className="bg-black/30 p-4 rounded-lg mb-6 font-mono text-sm text-green-300">
                                    {">"} Target: {selectedNode.label}<br />
                                    {">"} Director: GPT-4o (Judgment)<br />
                                    {">"} Scripter: Grok 4 (Chaos)<br />
                                    {">"} Sandbox: {sandboxId}
                                </div>
                            )}

                            {evolutionError && (
                                <div className="bg-red-900/30 border border-red-500/50 p-3 rounded-lg mb-4 text-red-300 text-sm flex items-center gap-2">
                                    <AlertCircle size={16} />
                                    {evolutionError}
                                </div>
                            )}
                        </div>

                        <Button
                            onClick={handleEvolve}
                            disabled={!selectedNode || evolving}
                            className={`w-full py-6 text-lg font-bold shadow-lg shadow-purple-900/20 ${evolving ? 'bg-purple-800/50' : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500'
                                }`}
                        >
                            {evolving ? (
                                <span className="flex items-center gap-2">
                                    <Loader2 className="animate-spin" /> Evolving Variants...
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    <Play fill="currentColor" /> Run Evolution Loop
                                </span>
                            )}
                        </Button>
                    </Card>
                </div>
            )}

            {/* 4. Results (Gene Browser) */}
            {evolutionResult && evolutionResult.success && (
                <Card className="bg-gray-800 border-green-500/50 p-6 animate-in fade-in slide-in-from-bottom-4">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                <Shield className="text-green-500" />
                                Evolution Complete
                            </h2>
                            <p className="text-green-400 mt-1">
                                Best Score: {evolutionResult.best_score}/10
                            </p>
                        </div>
                        <Button
                            className="bg-green-600 hover:bg-green-700 text-white"
                            onClick={handlePromote}
                            disabled={promoting}
                        >
                            {promoting ? (
                                <Loader2 className="animate-spin mr-2" size={18} />
                            ) : (
                                <Save size={18} className="mr-2" />
                            )}
                            Promote to Live
                        </Button>
                    </div>

                    <div className="bg-gray-900 p-4 rounded-lg">
                        <h3 className="font-semibold text-lg mb-2">Winning Variant: {evolutionResult.best_variant?.type}</h3>
                        <p className="text-gray-400 text-sm mb-2">
                            Content: "{evolutionResult.best_variant?.content_preview}"
                        </p>
                        {evolutionResult.best_variant?.voice_settings && (
                            <div className="text-xs text-gray-500">
                                Voice: Stability {evolutionResult.best_variant.voice_settings.stability || 'default'},
                                Speed {evolutionResult.best_variant.voice_settings.speed || 'default'}
                            </div>
                        )}
                    </div>
                </Card>
            )}
        </div>
    );
};

export default DirectorTab;
