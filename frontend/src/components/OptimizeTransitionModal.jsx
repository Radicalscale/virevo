import React, { useState } from 'react';
import { X, Zap, Loader2, Copy, Check } from 'lucide-react';
import { agentAPI } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

const OptimizeTransitionModal = ({ isOpen, onClose, agentId, originalCondition, onApply }) => {
  const { toast } = useToast();
  const [condition, setCondition] = useState(originalCondition);
  const [optimized, setOptimized] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [model, setModel] = useState('grok-4-0709');

  React.useEffect(() => {
    if (isOpen) {
      setCondition(originalCondition);
      setOptimized('');
      setCopied(false);
      setModel('grok-4-0709');
    }
  }, [isOpen, originalCondition]);

  const handleOptimize = async () => {
    if (!condition.trim()) {
      toast({
        title: "Error",
        description: "Please enter a transition condition to optimize",
        variant: "destructive"
      });
      return;
    }

    setLoading(true);
    try {
      const response = await agentAPI.optimizeTransition(agentId, condition, model);
      setOptimized(response.data.optimized);
      
      // Calculate reduction
      const reduction = ((condition.length - response.data.optimized.length) / condition.length * 100).toFixed(1);
      
      toast({
        title: "Success",
        description: `Transition optimized (${reduction}% reduction)`
      });
    } catch (error) {
      console.error('Error optimizing transition:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to optimize transition. Make sure you have added your Grok API key in Settings.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (optimized) {
      onApply(optimized);
      onClose();
      toast({
        title: "Success",
        description: "Optimized transition applied"
      });
    }
  };

  const handleCopy = () => {
    if (optimized) {
      navigator.clipboard.writeText(optimized);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast({
        title: "Copied",
        description: "Optimized transition copied to clipboard"
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <Zap className="text-yellow-400" size={24} />
            <div>
              <h2 className="text-2xl font-bold text-white">Optimize Transition</h2>
              <p className="text-sm text-gray-400 mt-1">Reduce LLM evaluation time while preserving all logic</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-4">
            <div>
              <Label className="text-white mb-2">Grok Model</Label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-700">
                  <SelectItem value="grok-4-0709">Grok 4 (Default - Best Balance)</SelectItem>
                  <SelectItem value="grok-3">Grok 3 (Reliable & Fast)</SelectItem>
                  <SelectItem value="grok-2-1212">Grok 2 (Dec 2024)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-400 mt-1">
                Select which Grok model to use for optimization
              </p>
            </div>

            <div>
              <Label className="text-white mb-2">Original Transition Condition</Label>
              <Textarea
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                placeholder="Paste your transition condition here..."
                className="min-h-[120px] bg-gray-900 text-white border-gray-700 font-mono text-sm"
              />
              <p className="text-xs text-gray-400 mt-1">
                {condition.length} characters
              </p>
            </div>

            <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4">
              <h4 className="text-blue-300 font-semibold mb-2 flex items-center gap-2">
                <Zap size={16} />
                What This Does
              </h4>
              <ul className="text-sm text-blue-200 space-y-1">
                <li>• Reduces verbose sentences to compact structure</li>
                <li>• Uses pipes (|) for OR conditions, colons (:) for IF-THEN logic</li>
                <li>• Preserves ALL conditions, examples, and rules</li>
                <li>• Makes LLM evaluation 2-3x faster (reduces 100-300ms latency)</li>
                <li>• Maintains exact same decision logic</li>
              </ul>
            </div>

            <Button
              onClick={handleOptimize}
              disabled={loading}
              className="w-full bg-gradient-to-r from-yellow-600 to-orange-600 hover:from-yellow-700 hover:to-orange-700"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 animate-spin" size={16} />
                  Optimizing with Grok...
                </>
              ) : (
                <>
                  <Zap className="mr-2" size={16} />
                  Optimize Transition
                </>
              )}
            </Button>

            {optimized && (
              <div className="mt-6">
                <Label className="text-white mb-2 flex items-center justify-between">
                  <span>Optimized Condition</span>
                  <span className="text-xs text-green-400">
                    {((condition.length - optimized.length) / condition.length * 100).toFixed(1)}% reduction
                  </span>
                </Label>
                <div className="relative">
                  <Textarea
                    value={optimized}
                    readOnly
                    className="min-h-[120px] bg-gray-900 text-white border-green-600 border-2 font-mono text-sm"
                  />
                  <button
                    onClick={handleCopy}
                    className="absolute top-2 right-2 p-2 bg-gray-800 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
                  >
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {optimized.length} characters
                </p>
              </div>
            )}

            {optimized && (
              <div className="bg-green-900/20 border border-green-700 rounded-lg p-4">
                <h4 className="text-green-300 font-semibold mb-2">✅ Optimization Complete</h4>
                <p className="text-sm text-green-200">
                  The optimized condition will evaluate {((condition.length - optimized.length) / condition.length * 100).toFixed(0)}% faster 
                  while preserving all logic. This reduces latency by approximately {Math.round((condition.length - optimized.length) * 0.15)}ms per evaluation.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-700">
          <Button
            onClick={onClose}
            variant="ghost"
            className="text-gray-400 hover:text-white"
          >
            Cancel
          </Button>
          {optimized && (
            <Button
              onClick={handleApply}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              Apply to Transition
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default OptimizeTransitionModal;
