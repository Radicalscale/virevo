import React from 'react';
import { 
  X, 
  AlertTriangle, 
  CheckCircle, 
  Info, 
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Target,
  Lightbulb,
  Award,
  BarChart3,
  Calendar,
  Clock,
  FileText
} from 'lucide-react';
import { Button } from './ui/button';

const CampaignReportModal = ({ report, onClose }) => {
  if (!report) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getQualityColor = (score) => {
    if (score >= 3.5) return 'text-green-400';
    if (score >= 2.5) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getQualityLabel = (score) => {
    if (score >= 3.5) return 'Excellent';
    if (score >= 3.0) return 'Good';
    if (score >= 2.5) return 'Fair';
    return 'Needs Improvement';
  };

  const getInsightIcon = (type) => {
    switch (type) {
      case 'critical': return <AlertCircle className="text-red-400" size={20} />;
      case 'warning': return <AlertTriangle className="text-yellow-400" size={20} />;
      case 'positive': return <CheckCircle className="text-green-400" size={20} />;
      case 'info': return <Info className="text-blue-400" size={20} />;
      default: return <Info className="text-gray-400" size={20} />;
    }
  };

  const getInsightBg = (type) => {
    switch (type) {
      case 'critical': return 'bg-red-900/20 border-red-700/30';
      case 'warning': return 'bg-yellow-900/20 border-yellow-700/30';
      case 'positive': return 'bg-green-900/20 border-green-700/30';
      case 'info': return 'bg-blue-900/20 border-blue-700/30';
      default: return 'bg-gray-800 border-gray-700';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical': return 'bg-red-600';
      case 'high': return 'bg-orange-600';
      case 'medium': return 'bg-yellow-600';
      default: return 'bg-gray-600';
    }
  };

  // Deduplicate patterns by description
  const uniquePatterns = report.patterns?.details?.reduce((acc, pattern) => {
    const key = pattern.description;
    if (!acc.find(p => p.description === key)) {
      acc.push(pattern);
    }
    return acc;
  }, []) || [];

  // Group unique patterns by type
  const patternsByType = uniquePatterns.reduce((acc, pattern) => {
    const type = pattern.pattern_type || 'unknown';
    if (!acc[type]) acc[type] = [];
    acc[type].push(pattern);
    return acc;
  }, {});

  const summary = report.summary || {};
  const qualityDist = summary.quality_distribution || {};
  const totalQuality = Object.values(qualityDist).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="text-purple-400" size={24} />
            <div>
              <h2 className="text-xl font-bold text-white">{report.campaign_name} - QC Report</h2>
              <p className="text-sm text-gray-400">Generated {formatDate(report.generated_at)}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X size={20} />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Executive Summary */}
          <section>
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <BarChart3 size={20} className="text-purple-400" />
              Executive Summary
            </h3>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-3xl font-bold text-white">{summary.total_calls_analyzed || 0}</div>
                <div className="text-sm text-gray-400">Calls Analyzed</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-3xl font-bold text-white">{summary.total_conversation_turns || 0}</div>
                <div className="text-sm text-gray-400">Total Turns</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className={`text-3xl font-bold ${getQualityColor(summary.average_quality_score)}`}>
                  {summary.average_quality_score?.toFixed(1) || 'N/A'}/4.0
                </div>
                <div className="text-sm text-gray-400">Quality Score</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-xl font-bold text-white">{getQualityLabel(summary.average_quality_score)}</div>
                <div className="text-sm text-gray-400">Overall Rating</div>
              </div>
            </div>

            {/* Quality Distribution Bar */}
            <div className="mt-4 bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-2">Quality Distribution</div>
              <div className="flex rounded-full overflow-hidden h-4">
                {qualityDist.good > 0 && (
                  <div 
                    className="bg-green-500" 
                    style={{ width: `${(qualityDist.good / totalQuality) * 100}%` }}
                    title={`Good: ${qualityDist.good}`}
                  />
                )}
                {qualityDist.needs_improvement > 0 && (
                  <div 
                    className="bg-yellow-500" 
                    style={{ width: `${(qualityDist.needs_improvement / totalQuality) * 100}%` }}
                    title={`Needs Improvement: ${qualityDist.needs_improvement}`}
                  />
                )}
                {qualityDist.poor > 0 && (
                  <div 
                    className="bg-red-500" 
                    style={{ width: `${(qualityDist.poor / totalQuality) * 100}%` }}
                    title={`Poor: ${qualityDist.poor}`}
                  />
                )}
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Good ({qualityDist.good || 0})
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                  Needs Work ({qualityDist.needs_improvement || 0})
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                  Poor ({qualityDist.poor || 0})
                </span>
              </div>
            </div>
          </section>

          {/* Key Insights */}
          {report.insights && report.insights.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Lightbulb size={20} className="text-yellow-400" />
                Key Insights
              </h3>
              <div className="space-y-3">
                {report.insights.map((insight, idx) => (
                  <div key={idx} className={`rounded-lg p-4 border ${getInsightBg(insight.type)}`}>
                    <div className="flex items-start gap-3">
                      {getInsightIcon(insight.type)}
                      <div>
                        <div className="font-medium text-white">{insight.title}</div>
                        <div className="text-sm text-gray-300 mt-1">{insight.description}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Recommendations */}
          {report.recommendations && report.recommendations.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Target size={20} className="text-green-400" />
                Recommendations
              </h3>
              <div className="space-y-3">
                {report.recommendations.map((rec, idx) => (
                  <div key={idx} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                    <div className="flex items-start gap-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium text-white ${getPriorityColor(rec.priority)}`}>
                        {rec.priority?.toUpperCase()}
                      </span>
                      <div className="flex-1">
                        <div className="font-medium text-white">{rec.title}</div>
                        <div className="text-sm text-gray-300 mt-1">{rec.action}</div>
                        {rec.estimated_impact && (
                          <div className="text-xs text-gray-500 mt-2">
                            Expected Impact: <span className="text-purple-400">{rec.estimated_impact}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Patterns Summary */}
          {uniquePatterns.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <TrendingUp size={20} className="text-blue-400" />
                Detected Patterns ({uniquePatterns.length})
              </h3>
              
              {/* Bottlenecks */}
              {patternsByType.bottleneck && patternsByType.bottleneck.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-red-400 mb-2 flex items-center gap-2">
                    <TrendingDown size={16} />
                    Bottlenecks ({patternsByType.bottleneck.length})
                  </h4>
                  <div className="bg-red-900/10 border border-red-900/30 rounded-lg p-3">
                    <ul className="space-y-2">
                      {patternsByType.bottleneck.slice(0, 5).map((pattern, idx) => (
                        <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                          <span className="text-red-400 mt-1">•</span>
                          <span>{pattern.description}</span>
                        </li>
                      ))}
                      {patternsByType.bottleneck.length > 5 && (
                        <li className="text-xs text-gray-500">
                          ...and {patternsByType.bottleneck.length - 5} more
                        </li>
                      )}
                    </ul>
                  </div>
                </div>
              )}

              {/* Improvement Opportunities */}
              {patternsByType.improvement_opportunity && patternsByType.improvement_opportunity.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-yellow-400 mb-2 flex items-center gap-2">
                    <Lightbulb size={16} />
                    Improvement Opportunities ({patternsByType.improvement_opportunity.length})
                  </h4>
                  <div className="bg-yellow-900/10 border border-yellow-900/30 rounded-lg p-3">
                    <ul className="space-y-2">
                      {patternsByType.improvement_opportunity.map((pattern, idx) => (
                        <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                          <span className="text-yellow-400 mt-1">•</span>
                          <span>{pattern.description}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Successes */}
              {patternsByType.success && patternsByType.success.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-green-400 mb-2 flex items-center gap-2">
                    <Award size={16} />
                    Success Patterns ({patternsByType.success.length})
                  </h4>
                  <div className="bg-green-900/10 border border-green-900/30 rounded-lg p-3">
                    <ul className="space-y-2">
                      {patternsByType.success.map((pattern, idx) => (
                        <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                          <span className="text-green-400 mt-1">•</span>
                          <span>{pattern.description}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Report Footer */}
          <section className="border-t border-gray-800 pt-4">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center gap-2">
                <Calendar size={14} />
                <span>Analysis Period: {formatDate(report.date_range?.start)} - {formatDate(report.date_range?.end)}</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock size={14} />
                <span>Report ID: {report.campaign_id?.slice(0, 8)}...</span>
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-800 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>Close</Button>
          <Button 
            onClick={() => {
              const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `campaign-${report.campaign_name}-report.json`;
              a.click();
            }}
          >
            Download JSON
          </Button>
        </div>
      </div>
    </div>
  );
};

export default CampaignReportModal;
