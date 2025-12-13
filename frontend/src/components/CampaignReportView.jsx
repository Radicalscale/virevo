import React from 'react';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Info,
  BarChart3,
  Target,
  Lightbulb,
  Download,
  Calendar,
  Phone,
  MessageSquare,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from './ui/dialog';

const CampaignReportView = ({ report, isOpen, onClose, onDownload }) => {
  if (!report) return null;

  const {
    campaign_name,
    generated_at,
    date_range,
    summary,
    patterns,
    insights,
    recommendations,
    high_impact_suggestions
  } = report;

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  // Get quality score color
  const getQualityScoreColor = (score) => {
    if (score >= 3.5) return 'text-green-400';
    if (score >= 2.5) return 'text-yellow-400';
    return 'text-red-400';
  };

  // Get quality score label
  const getQualityScoreLabel = (score) => {
    if (score >= 3.5) return 'Excellent';
    if (score >= 3.0) return 'Good';
    if (score >= 2.5) return 'Average';
    return 'Needs Improvement';
  };

  // Get insight icon based on type
  const getInsightIcon = (type) => {
    switch (type) {
      case 'positive':
        return <CheckCircle className="text-green-400" size={20} />;
      case 'warning':
        return <AlertTriangle className="text-yellow-400" size={20} />;
      case 'critical':
        return <AlertTriangle className="text-red-400" size={20} />;
      case 'info':
      default:
        return <Info className="text-blue-400" size={20} />;
    }
  };

  // Get insight background color
  const getInsightBgColor = (type) => {
    switch (type) {
      case 'positive':
        return 'bg-green-900/30 border-green-800';
      case 'warning':
        return 'bg-yellow-900/30 border-yellow-800';
      case 'critical':
        return 'bg-red-900/30 border-red-800';
      case 'info':
      default:
        return 'bg-blue-900/30 border-blue-800';
    }
  };

  // Get priority badge color
  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-600';
      case 'high':
        return 'bg-orange-600';
      case 'medium':
        return 'bg-yellow-600';
      default:
        return 'bg-gray-600';
    }
  };

  // Get quality distribution chart
  const renderQualityDistribution = (distribution) => {
    const total = Object.values(distribution).reduce((a, b) => a + b, 0);
    if (total === 0) return <p className="text-gray-500 text-sm">No data</p>;

    const items = [
      { key: 'excellent', label: 'Excellent', color: 'bg-green-500' },
      { key: 'good', label: 'Good', color: 'bg-blue-500' },
      { key: 'needs_improvement', label: 'Needs Work', color: 'bg-yellow-500' },
      { key: 'poor', label: 'Poor', color: 'bg-red-500' }
    ];

    return (
      <div className="space-y-2">
        {items.map(({ key, label, color }) => {
          const count = distribution[key] || 0;
          const percentage = total > 0 ? (count / total) * 100 : 0;
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="text-gray-400 text-sm w-24">{label}</span>
              <div className="flex-1 h-4 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full ${color} transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <span className="text-gray-300 text-sm w-16 text-right">
                {count} ({percentage.toFixed(0)}%)
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-gray-900 border-gray-800 text-white">
        <DialogHeader className="border-b border-gray-800 pb-4">
          <DialogTitle className="text-2xl font-bold text-white flex items-center gap-3">
            <BarChart3 className="text-purple-400" size={28} />
            Campaign Report
          </DialogTitle>
          <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-gray-400">
            <span className="font-medium text-white">{campaign_name}</span>
            <span className="flex items-center gap-1">
              <Calendar size={14} />
              Generated: {formatDate(generated_at)}
            </span>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Summary Section */}
          <section>
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Target className="text-blue-400" size={20} />
              Summary
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="bg-gray-800 border-gray-700">
                <CardContent className="p-4 text-center">
                  <Phone className="mx-auto mb-2 text-blue-400" size={24} />
                  <div className="text-2xl font-bold text-white">
                    {summary?.total_calls_analyzed || 0}
                  </div>
                  <div className="text-sm text-gray-400">Calls Analyzed</div>
                </CardContent>
              </Card>
              
              <Card className="bg-gray-800 border-gray-700">
                <CardContent className="p-4 text-center">
                  <MessageSquare className="mx-auto mb-2 text-green-400" size={24} />
                  <div className="text-2xl font-bold text-white">
                    {summary?.total_conversation_turns || 0}
                  </div>
                  <div className="text-sm text-gray-400">Total Turns</div>
                </CardContent>
              </Card>
              
              <Card className="bg-gray-800 border-gray-700">
                <CardContent className="p-4 text-center">
                  <TrendingUp className={`mx-auto mb-2 ${getQualityScoreColor(summary?.average_quality_score)}`} size={24} />
                  <div className={`text-2xl font-bold ${getQualityScoreColor(summary?.average_quality_score)}`}>
                    {summary?.average_quality_score?.toFixed(2) || 'N/A'}/4.0
                  </div>
                  <div className="text-sm text-gray-400">
                    {getQualityScoreLabel(summary?.average_quality_score)}
                  </div>
                </CardContent>
              </Card>
              
              <Card className="bg-gray-800 border-gray-700">
                <CardContent className="p-4 text-center">
                  <Zap className="mx-auto mb-2 text-purple-400" size={24} />
                  <div className="text-2xl font-bold text-white">
                    {patterns?.total_patterns || 0}
                  </div>
                  <div className="text-sm text-gray-400">Patterns Found</div>
                </CardContent>
              </Card>
            </div>
          </section>

          {/* Quality Distribution */}
          {summary?.quality_distribution && Object.keys(summary.quality_distribution).length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <BarChart3 className="text-green-400" size={20} />
                Quality Distribution
              </h3>
              <Card className="bg-gray-800 border-gray-700">
                <CardContent className="p-4">
                  {renderQualityDistribution(summary.quality_distribution)}
                </CardContent>
              </Card>
            </section>
          )}

          {/* Insights Section */}
          {insights && insights.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Lightbulb className="text-yellow-400" size={20} />
                Key Insights
              </h3>
              <div className="space-y-3">
                {insights.map((insight, idx) => (
                  <Card
                    key={idx}
                    className={`border ${getInsightBgColor(insight.type)}`}
                  >
                    <CardContent className="p-4 flex items-start gap-3">
                      {getInsightIcon(insight.type)}
                      <div>
                        <h4 className="font-semibold text-white">{insight.title}</h4>
                        <p className="text-gray-300 text-sm mt-1">{insight.description}</p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          )}

          {/* Patterns Breakdown */}
          {patterns && patterns.by_type && (
            <section>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <BarChart3 className="text-purple-400" size={20} />
                Patterns Breakdown
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-gray-800 border-gray-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">
                      {patterns.by_type.successes || 0}
                    </div>
                    <div className="text-sm text-gray-400">Success Patterns</div>
                  </CardContent>
                </Card>
                <Card className="bg-gray-800 border-gray-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-yellow-400">
                      {patterns.by_type.improvements || 0}
                    </div>
                    <div className="text-sm text-gray-400">Improvements</div>
                  </CardContent>
                </Card>
                <Card className="bg-gray-800 border-gray-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-orange-400">
                      {patterns.by_type.bottlenecks || 0}
                    </div>
                    <div className="text-sm text-gray-400">Bottlenecks</div>
                  </CardContent>
                </Card>
                <Card className="bg-gray-800 border-gray-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-red-400">
                      {patterns.by_type.recurring_issues || 0}
                    </div>
                    <div className="text-sm text-gray-400">Recurring Issues</div>
                  </CardContent>
                </Card>
              </div>
            </section>
          )}

          {/* Recommendations Section */}
          {recommendations && recommendations.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <CheckCircle className="text-blue-400" size={20} />
                Recommendations
              </h3>
              <div className="space-y-3">
                {recommendations.map((rec, idx) => (
                  <Card key={idx} className="bg-gray-800 border-gray-700">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge className={`${getPriorityColor(rec.priority)} text-white`}>
                              {rec.priority?.toUpperCase()}
                            </Badge>
                            <h4 className="font-semibold text-white">{rec.title}</h4>
                          </div>
                          <p className="text-gray-300 text-sm">{rec.action}</p>
                        </div>
                        {rec.estimated_impact && (
                          <Badge variant="outline" className="border-gray-600 text-gray-300">
                            Impact: {rec.estimated_impact}
                          </Badge>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          )}

          {/* High Impact Suggestions */}
          {high_impact_suggestions && high_impact_suggestions.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="text-orange-400" size={20} />
                High Impact Areas
              </h3>
              <Card className="bg-gray-800 border-gray-700">
                <CardContent className="p-4">
                  <div className="space-y-3">
                    {high_impact_suggestions.map((sugg, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0"
                      >
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="border-gray-600 text-gray-300">
                            {sugg.type?.replace(/_/g, ' ')}
                          </Badge>
                          {sugg.node !== 'general' && (
                            <span className="text-gray-400 text-sm">Node: {sugg.node}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-gray-300 text-sm">
                            {sugg.frequency} occurrences
                          </span>
                          <Badge className={sugg.impact === 'high' ? 'bg-red-600' : 'bg-yellow-600'}>
                            {sugg.impact} impact
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </section>
          )}

          {/* Date Range */}
          {date_range && (date_range.start || date_range.end) && (
            <section className="text-center text-sm text-gray-500 pt-4 border-t border-gray-800">
              <span>Analysis Period: </span>
              <span>{formatDate(date_range.start)} - {formatDate(date_range.end)}</span>
            </section>
          )}
        </div>

        <DialogFooter className="border-t border-gray-800 pt-4 flex justify-between items-center">
          <Button
            onClick={onDownload}
            variant="outline"
            className="border-gray-600 text-gray-300 hover:bg-gray-800"
          >
            <Download className="mr-2" size={16} />
            Download JSON
          </Button>
          <Button
            onClick={onClose}
            className="bg-purple-600 hover:bg-purple-700 text-white"
          >
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CampaignReportView;
