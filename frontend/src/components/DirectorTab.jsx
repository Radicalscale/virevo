import React, { useState, useEffect } from 'react';
import { Play, Activity, GitBranch, Mic, Save, Shield } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';

// Mock API for frontend demo (replacing backend calls for now)
const mockBackend = {
    evolveNode: async (nodeId) => {
        await new Promise(r => setTimeout(r, 2000)); // Sim delay
        return {
            generations: 3,
            winner: {
                id: "variant_b",
                score: 9.2,
                changes: { prompt: "Reworded for empathy", voice: "Stability -10%" },
                metrics: { human_connection: 9.5, latency: "200ms" }
            },
            variants: [
                { id: "variant_a", score: 8.5, type: "Diplomat" },
                { id: "variant_b", score: 9.2, type: "The Closer" },
                { id: "variant_c", score: 7.8, type: "High Energy" }
            ]
        };
    }
};

const DirectorTab = () => {
    const [selectedAgent, setSelectedAgent] = useState(null);
    const [sandboxId, setSandboxId] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const [evolving, setEvolving] = useState(false);
    const [evolutionResult, setEvolutionResult] = useState(null);

    // Mock Agent List
    const agents = [
        { id: '1', name: 'Sales Agent V3' },
        { id: '2', name: 'Support Bot' }
    ];

    // Mock Nodes for the selected agent
    const nodes = [
        { id: 'node_intro', label: 'Introduction', text: 'Hi, this is Alex from Solar.' },
        { id: 'node_price', label: 'Price Objection', text: 'I understand, but our value is...' },
        { id: 'node_close', label: 'Closing', text: 'Can we schedule a time?' }
    ];

    const handleAgentSelect = (agent) => {
        setSelectedAgent(agent);
        // Simulate Sandbox Creation
        setSandboxId(`sandbox_${agent.id}_temp`);
        setEvolutionResult(null);
    };

    const handleEvolve = async () => {
        if (!selectedNode) return;
        setEvolving(true);
        try {
            const result = await mockBackend.evolveNode(selectedNode.id);
            setEvolutionResult(result);
        } catch (e) {
            console.error(e);
        } finally {
            setEvolving(false);
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
                        <span className="text-sm font-mono">SANDBOX ACTIVE: {sandboxId}</span>
                    </div>
                )}
            </div>

            {/* 1. Agent Selection */}
            <Card className="bg-gray-800 border-gray-700 p-6">
                <h2 className="text-xl font-semibold mb-4">1. Select Target Agent</h2>
                <div className="flex gap-4">
                    {agents.map(agent => (
                        <Button
                            key={agent.id}
                            onClick={() => handleAgentSelect(agent)}
                            variant={selectedAgent?.id === agent.id ? "default" : "outline"}
                            className={`${selectedAgent?.id === agent.id ? 'bg-blue-600' : 'bg-gray-700'}`}
                        >
                            {agent.name}
                        </Button>
                    ))}
                </div>
            </Card>

            {selectedAgent && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                    {/* 2. Node Inspector */}
                    <Card className="bg-gray-800 border-gray-700 p-6">
                        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                            <GitBranch className="text-purple-400" />
                            2. Select Node to Evolve
                        </h2>
                        <div className="space-y-2">
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
                                    <div className="text-sm text-gray-400 mt-1">"{node.text}"</div>
                                </div>
                            ))}
                        </div>
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
                                    {">"} Director: GPT-5.2 (Online)<br />
                                    {">"} Scripter: Grok 4.1 (Online)<br />
                                    {">"} Mutation Strategy: Genetic A/B
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
                                    <Activity className="animate-pulse" /> Evolving Variants...
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
            {evolutionResult && (
                <Card className="bg-gray-800 border-green-500/50 p-6 animate-in fade-in slide-in-from-bottom-4">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                <Shield className="text-green-500" />
                                Evolution Complete
                            </h2>
                            <p className="text-green-400 mt-1">Found superior variant (Score: {evolutionResult.winner.score}/10)</p>
                        </div>
                        <Button className="bg-green-600 hover:bg-green-700 text-white">
                            <Save size={18} className="mr-2" />
                            Promote to Live
                        </Button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {evolutionResult.variants.map((variant) => (
                            <div
                                key={variant.id}
                                className={`p-4 rounded-lg border ${variant.id === evolutionResult.winner.id
                                        ? 'bg-green-900/20 border-green-500 relative overflow-hidden'
                                        : 'bg-gray-900 border-gray-700 opacity-60'
                                    }`}
                            >
                                {variant.id === evolutionResult.winner.id && (
                                    <div className="absolute top-0 right-0 bg-green-500 text-black text-xs font-bold px-2 py-1">
                                        WINNER
                                    </div>
                                )}
                                <h3 className="font-bold text-lg mb-1">{variant.type}</h3>
                                <div className="text-2xl font-mono mb-2">{variant.score}</div>

                                {variant.id === evolutionResult.winner.id && (
                                    <div className="text-sm space-y-1 text-gray-300 mt-3 border-t border-gray-700 pt-3">
                                        <p>Changes: <span className="text-green-300">{evolutionResult.winner.changes.prompt}</span></p>
                                        <p>Latency: <span className="text-blue-300">{evolutionResult.winner.metrics.latency}</span></p>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </Card>
            )}
        </div>
    );
};

export default DirectorTab;
