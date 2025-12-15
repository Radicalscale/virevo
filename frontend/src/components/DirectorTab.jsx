import React, { useState, useEffect } from 'react';
import { Play, Activity, GitBranch, Mic, Save, Shield, AlertCircle, Loader2, RefreshCw, Zap } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

// XHR-based fetch to bypass rrweb's fetch wrapper
const safeFetch = (url, options = {}) => {
    return new Promise((resolve) => {
        const xhr = new XMLHttpRequest();
        xhr.open(options.method || 'GET', url, true);
        xhr.withCredentials = true;

        // Set headers
        if (options.headers) {
            Object.entries(options.headers).forEach(([key, value]) => {
                xhr.setRequestHeader(key, value);
            });
        }

        xhr.onload = () => {
            let data = {};
            try {
                data = JSON.parse(xhr.responseText);
            } catch (e) {
                data = { detail: 'Invalid JSON response' };
            }
            resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, data });
        };

        xhr.onerror = () => {
            resolve({ ok: false, status: 0, data: { detail: 'Network error' } });
        };

        xhr.send(options.body || null);
    });
};

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
    const [evolvingAll, setEvolvingAll] = useState(false);
    const [evolutionProgress, setEvolutionProgress] = useState('');
    const [evolutionResults, setEvolutionResults] = useState([]);
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
            const { ok, status, data } = await safeFetch(`${API_BASE}/api/agents`, {
                credentials: 'include'
            });
            if (!ok) {
                throw new Error(`Failed to fetch agents (${status})`);
            }
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
        setEvolutionResults([]);
        setSelectedNode(null);
        setNodes([]);
        setSandboxId(null);
        setEvolutionError(null);

        // Create sandbox via real API
        setSandboxLoading(true);
        try {
            const { ok, data } = await safeFetch(`${API_BASE}/api/director/sandbox`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agent.id })
            });
            if (!ok) {
                throw new Error(data.detail || 'Failed to create sandbox');
            }
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
            const { ok, data } = await safeFetch(`${API_BASE}/api/director/sandbox/${sbId}/nodes`, {
                credentials: 'include'
            });
            if (!ok) {
                throw new Error(data.detail || 'Failed to fetch nodes');
            }
            setNodes(data.nodes || []);
        } catch (e) {
            console.error('Error fetching nodes:', e);
        } finally {
            setNodesLoading(false);
        }
    };

    const evolveNode = async (nodeId, nodeName) => {
        const { ok, data } = await safeFetch(`${API_BASE}/api/director/evolve`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sandbox_id: sandboxId,
                node_id: nodeId,
                generations: 3
            })
        });
        if (!ok) {
            throw new Error(data.detail || `Evolution failed for ${nodeName}`);
        }
        return { nodeId, nodeName, ...data };
    };

    const handleEvolveSingle = async () => {
        if (!selectedNode || !sandboxId) return;
        setEvolving(true);
        setEvolutionError(null);
        setEvolutionResults([]);
        setEvolutionProgress(`Evolving ${selectedNode.label}...`);

        try {
            const result = await evolveNode(selectedNode.id, selectedNode.label);
            setEvolutionResults([result]);
        } catch (e) {
            console.error('Evolution error:', e);
            setEvolutionError(e.message);
        } finally {
            setEvolving(false);
            setEvolutionProgress('');
        }
    };

    const handleEvolveAll = async () => {
        if (!sandboxId || nodes.length === 0) return;
        setEvolvingAll(true);
        setEvolutionError(null);
        setEvolutionResults([]);

        const results = [];

        try {
            for (let i = 0; i < nodes.length; i++) {
                const node = nodes[i];
                setEvolutionProgress(`Evolving node ${i + 1}/${nodes.length}: ${node.label}`);

                try {
                    const result = await evolveNode(node.id, node.label);
                    results.push(result);
                } catch (nodeErr) {
                    results.push({
                        nodeId: node.id,
                        nodeName: node.label,
                        success: false,
                        error: nodeErr.message
                    });
                }
            }
            setEvolutionResults(results);
        } catch (e) {
            console.error('Evolve all error:', e);
            setEvolutionError(e.message);
        } finally {
            setEvolvingAll(false);
            setEvolutionProgress('');
        }
    };

    const handlePromote = async () => {
        if (!sandboxId) return;
        setPromoting(true);
        try {
            const { ok, data } = await safeFetch(`${API_BASE}/api/director/promote`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sandbox_id: sandboxId })
            });
            if (!ok) {
                throw new Error(data.detail || 'Promotion failed');
            }
            alert('✅ Sandbox promoted to live agent!');
            setSandboxId(null);
            setSelectedAgent(null);
            setEvolutionResults([]);
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
                <>
                    {/* Evolution Mode Selection */}
                    <Card className="bg-gray-800 border-gray-700 p-6">
                        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                            <Mic className="text-red-400" />
                            2. Evolution Controls
                        </h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Evolve All Button */}
                            <Button
                                onClick={handleEvolveAll}
                                disabled={evolvingAll || evolving || nodes.length === 0}
                                className="py-8 text-lg font-bold bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500"
                            >
                                {evolvingAll ? (
                                    <span className="flex items-center gap-2">
                                        <Loader2 className="animate-spin" /> {evolutionProgress}
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-2">
                                        <Zap /> Evolve ALL Nodes ({nodes.length})
                                    </span>
                                )}
                            </Button>

                            {/* Evolve Single Button */}
                            <Button
                                onClick={handleEvolveSingle}
                                disabled={!selectedNode || evolving || evolvingAll}
                                variant="outline"
                                className="py-8 text-lg"
                            >
                                {evolving ? (
                                    <span className="flex items-center gap-2">
                                        <Loader2 className="animate-spin" /> {evolutionProgress}
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-2">
                                        <Play /> Evolve Selected Node
                                    </span>
                                )}
                            </Button>
                        </div>

                        {evolutionError && (
                            <div className="mt-4 bg-red-900/30 border border-red-500/50 p-3 rounded-lg text-red-300 text-sm flex items-center gap-2">
                                <AlertCircle size={16} />
                                {evolutionError}
                            </div>
                        )}
                    </Card>

                    {/* Node Selector (for single-node evolution) */}
                    <Card className="bg-gray-800 border-gray-700 p-6">
                        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                            <GitBranch className="text-purple-400" />
                            3. Select Node (for single evolution)
                        </h2>

                        {nodesLoading ? (
                            <div className="flex items-center gap-2 text-gray-400">
                                <Loader2 className="animate-spin" size={18} />
                                Loading nodes...
                            </div>
                        ) : nodes.length === 0 ? (
                            <p className="text-gray-400">No nodes found in this agent's call flow.</p>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-64 overflow-y-auto">
                                {nodes.map(node => (
                                    <div
                                        key={node.id}
                                        onClick={() => setSelectedNode(node)}
                                        className={`p-3 rounded-lg cursor-pointer border transition-all ${selectedNode?.id === node.id
                                            ? 'bg-purple-900/40 border-purple-500'
                                            : 'bg-gray-900 border-gray-700 hover:border-gray-600'
                                            }`}
                                    >
                                        <div className="font-medium text-white text-sm">{node.label}</div>
                                        <div className="text-xs text-gray-500">Mode: {node.mode}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>
                </>
            )}

            {/* Results */}
            {evolutionResults.length > 0 && (
                <Card className="bg-gray-800 border-green-500/50 p-6">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                <Shield className="text-green-500" />
                                Evolution Complete
                            </h2>
                            <p className="text-green-400 mt-1">
                                {evolutionResults.length} node(s) optimized
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

                    <div className="space-y-3 max-h-96 overflow-y-auto">
                        {evolutionResults.map((result, idx) => (
                            <div key={idx} className={`p-4 rounded-lg border ${result.success === false ? 'bg-red-900/20 border-red-500/50' : 'bg-green-900/20 border-green-500/50'}`}>
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h3 className="font-semibold">{result.nodeName || result.nodeId}</h3>
                                        {result.success === false ? (
                                            <p className="text-red-400 text-sm">{result.error}</p>
                                        ) : (
                                            <>
                                                <p className="text-green-400 text-sm">
                                                    Score: {result.best_score}/10 | Variant: {result.best_variant?.type}
                                                </p>
                                                {result.best_variant?.content_preview && (
                                                    <p className="text-gray-400 text-xs mt-1 truncate max-w-md">
                                                        "{result.best_variant.content_preview}"
                                                    </p>
                                                )}
                                            </>
                                        )}
                                    </div>
                                    {result.success !== false && (
                                        <span className="bg-green-500 text-black text-xs font-bold px-2 py-1 rounded">
                                            ✓
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            )}
        </div>
    );
};

export default DirectorTab;
