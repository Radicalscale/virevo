import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  TrendingUp,
  Users,
  Phone,
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  Filter,
  Download,
  RefreshCw,
  ChevronDown,
  Activity,
  Target,
  Percent
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { useToast } from '../hooks/use-toast';
import { qcEnhancedAPI, analyticsAPI } from '../services/api';

// Lead category display names
const CATEGORY_LABELS = {
  training_call: 'Training Call',
  new_first_call: 'New/First Call',
  new_non_answered: 'New/Non-Answered',
  called_delayed: 'Called - Delayed',
  called_refused: 'Called - Refused',
  '1_appointment_pre_date': '1 Appt - Pre Date',
  '1_appointment_showed': '1 Appt - Showed',
  '1_appointment_no_show_call_2_non_answered': '1 Appt No-Show - Call 2 No Answer',
  '1_appointment_no_show_call_2_delayed': '1 Appt No-Show - Call 2 Delayed',
  '1_appointment_no_show_call_2_refused': '1 Appt No-Show - Call 2 Refused',
  '1_appointment_no_show_call_2_new_appointment': '1 Appt No-Show - Call 2 New Appt',
  '2_appointment_showed': '2 Appt - Showed',
  '3_plus_appointment_showed': '3+ Appt - Showed'
};

/**
 * Metric Card Component
 */
const MetricCard = ({ title, value, icon: Icon, color, subtitle, trend }) => (
  <Card className="bg-gray-900 border-gray-800">
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-400">{title}</p>
          <p className={`text-2xl font-bold ${color || 'text-white'}`}>{value}</p>
          {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-full ${color?.replace('text-', 'bg-').replace('400', '900/30') || 'bg-gray-800'}`}>
          <Icon size={20} className={color || 'text-gray-400'} />
        </div>
      </div>
      {trend !== undefined && (
        <div className="mt-2 flex items-center gap-1 text-xs">
          <TrendingUp size={12} className={trend >= 0 ? 'text-green-400' : 'text-red-400'} />
          <span className={trend >= 0 ? 'text-green-400' : 'text-red-400'}>
            {trend >= 0 ? '+' : ''}{trend}%
          </span>
          <span className="text-gray-500">vs last period</span>
        </div>
      )}
    </CardContent>
  </Card>
);

/**
 * Ratio Display Component
 */
const RatioDisplay = ({ label, value, total, color }) => {
  const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
  
  return (
    <div className="bg-gray-800/50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">{label}</span>
        <span className={`text-lg font-bold ${color}`}>{percentage}%</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div 
          className={`h-2 rounded-full ${color?.replace('text-', 'bg-')}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 mt-1">{value} / {total}</p>
    </div>
  );
};

/**
 * Category Distribution Chart (simple bar chart)
 */
const CategoryChart = ({ data }) => {
  const maxValue = Math.max(...Object.values(data), 1);
  
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([category, count]) => (
        <div key={category} className="flex items-center gap-3">
          <span className="text-xs text-gray-400 w-40 truncate">
            {CATEGORY_LABELS[category] || category}
          </span>
          <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
            <div 
              className="h-full bg-purple-500 rounded-full transition-all"
              style={{ width: `${(count / maxValue) * 100}%` }}
            />
          </div>
          <span className="text-sm text-white w-12 text-right">{count}</span>
        </div>
      ))}
    </div>
  );
};

/**
 * QC Analytics Dashboard Page
 */
const QCAnalyticsDashboard = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [loading, setLoading] = useState(true);
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState('all');
  const [dateRange, setDateRange] = useState('7d'); // 7d, 30d, 90d, all
  const [activeTab, setActiveTab] = useState('overview');
  
  // Analytics data
  const [analytics, setAnalytics] = useState({
    totalCalls: 0,
    totalLeads: 0,
    appointmentsSet: 0,
    appointmentsShowed: 0,
    noShows: 0,
    categoryBreakdown: {},
    ratios: {
      callsToAnswer: 0,
      callsToBook: 0,
      showRate: 0,
      noShowRate: 0,
      noShowToFollowup: 0,
      noShowToShowed: 0
    },
    trends: {
      calls: 0,
      appointments: 0,
      showRate: 0
    }
  });
  
  // Fetch campaigns
  useEffect(() => {
    fetchCampaigns();
  }, []);
  
  // Fetch analytics when campaign or date range changes
  useEffect(() => {
    fetchAnalytics();
  }, [selectedCampaign, dateRange]);
  
  const fetchCampaigns = async () => {
    try {
      const response = await qcEnhancedAPI.listCampaigns();
      setCampaigns(response.data || []);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
    }
  };
  
  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      
      // Fetch campaign-specific or aggregated analytics
      // For now, we'll compute from campaigns data
      let totalCalls = 0;
      let totalLeads = 0;
      let appointmentsSet = 0;
      let appointmentsShowed = 0;
      let noShows = 0;
      let categoryBreakdown = {};
      
      const campaignsToAnalyze = selectedCampaign === 'all' 
        ? campaigns 
        : campaigns.filter(c => c.id === selectedCampaign);
      
      for (const campaign of campaignsToAnalyze) {
        const stats = campaign.stats || {};
        totalCalls += stats.total_calls || 0;
        totalLeads += stats.total_leads || 0;
        appointmentsSet += stats.appointments_set || 0;
        appointmentsShowed += stats.appointments_showed || 0;
        noShows += stats.no_shows || 0;
        
        // Aggregate category breakdown
        if (stats.category_breakdown) {
          Object.entries(stats.category_breakdown).forEach(([cat, count]) => {
            categoryBreakdown[cat] = (categoryBreakdown[cat] || 0) + count;
          });
        }
      }
      
      // Calculate ratios
      const showRate = appointmentsSet > 0 ? (appointmentsShowed / appointmentsSet) * 100 : 0;
      const noShowRate = appointmentsSet > 0 ? (noShows / appointmentsSet) * 100 : 0;
      
      setAnalytics({
        totalCalls,
        totalLeads,
        appointmentsSet,
        appointmentsShowed,
        noShows,
        categoryBreakdown,
        ratios: {
          callsToAnswer: totalLeads > 0 ? (totalCalls / totalLeads).toFixed(1) : 0,
          callsToBook: appointmentsSet > 0 ? (totalCalls / appointmentsSet).toFixed(1) : 0,
          showRate: showRate.toFixed(1),
          noShowRate: noShowRate.toFixed(1),
          noShowToFollowup: 0, // Would need more detailed tracking
          noShowToShowed: 0
        },
        trends: {
          calls: 5, // Placeholder - would calculate from historical data
          appointments: 12,
          showRate: -3
        }
      });
      
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast({
        title: 'Error',
        description: 'Failed to load analytics',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleExport = () => {
    const exportData = {
      generatedAt: new Date().toISOString(),
      campaign: selectedCampaign === 'all' ? 'All Campaigns' : campaigns.find(c => c.id === selectedCampaign)?.name,
      dateRange,
      ...analytics
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qc-analytics-${dateRange}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    toast({
      title: 'Exported',
      description: 'Analytics data exported successfully'
    });
  };
  
  if (loading && campaigns.length === 0) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading analytics...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">QC Analytics Dashboard</h1>
            <p className="text-gray-400">Campaign performance and lead metrics</p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Campaign Filter */}
            <Select value={selectedCampaign} onValueChange={setSelectedCampaign}>
              <SelectTrigger className="w-48 bg-gray-900 border-gray-700">
                <SelectValue placeholder="Select Campaign" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Campaigns</SelectItem>
                {campaigns.map(campaign => (
                  <SelectItem key={campaign.id} value={campaign.id}>
                    {campaign.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {/* Date Range Filter */}
            <Select value={dateRange} onValueChange={setDateRange}>
              <SelectTrigger className="w-32 bg-gray-900 border-gray-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 90 days</SelectItem>
                <SelectItem value="all">All time</SelectItem>
              </SelectContent>
            </Select>
            
            <Button variant="outline" size="sm" onClick={fetchAnalytics}>
              <RefreshCw size={16} className="mr-1" />
              Refresh
            </Button>
            
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download size={16} className="mr-1" />
              Export
            </Button>
          </div>
        </div>
        
        {/* Main Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <MetricCard
            title="Total Calls"
            value={analytics.totalCalls}
            icon={Phone}
            color="text-blue-400"
            trend={analytics.trends.calls}
          />
          <MetricCard
            title="Total Leads"
            value={analytics.totalLeads}
            icon={Users}
            color="text-green-400"
          />
          <MetricCard
            title="Appointments Set"
            value={analytics.appointmentsSet}
            icon={Calendar}
            color="text-purple-400"
            trend={analytics.trends.appointments}
          />
          <MetricCard
            title="Showed Up"
            value={analytics.appointmentsShowed}
            icon={CheckCircle}
            color="text-emerald-400"
          />
          <MetricCard
            title="No Shows"
            value={analytics.noShows}
            icon={XCircle}
            color="text-red-400"
          />
        </div>
        
        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-gray-900 border border-gray-800 mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="ratios">Ratio Metrics</TabsTrigger>
            <TabsTrigger value="categories">Lead Categories</TabsTrigger>
            <TabsTrigger value="campaigns">By Campaign</TabsTrigger>
          </TabsList>
          
          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Key Ratios */}
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Percent size={20} className="text-purple-400" />
                    Key Performance Ratios
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <RatioDisplay
                    label="Show Rate"
                    value={analytics.appointmentsShowed}
                    total={analytics.appointmentsSet}
                    color="text-green-400"
                  />
                  <RatioDisplay
                    label="No Show Rate"
                    value={analytics.noShows}
                    total={analytics.appointmentsSet}
                    color="text-red-400"
                  />
                  <RatioDisplay
                    label="Booking Rate"
                    value={analytics.appointmentsSet}
                    total={analytics.totalCalls}
                    color="text-purple-400"
                  />
                </CardContent>
              </Card>
              
              {/* Quick Stats */}
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity size={20} className="text-blue-400" />
                    Call Efficiency
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded">
                    <span className="text-gray-400">Avg Calls to Answer</span>
                    <span className="text-xl font-bold text-white">{analytics.ratios.callsToAnswer}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded">
                    <span className="text-gray-400">Avg Calls to Book</span>
                    <span className="text-xl font-bold text-white">{analytics.ratios.callsToBook}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded">
                    <span className="text-gray-400">Calls per Lead</span>
                    <span className="text-xl font-bold text-white">
                      {analytics.totalLeads > 0 ? (analytics.totalCalls / analytics.totalLeads).toFixed(1) : 0}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* Ratio Metrics Tab */}
          <TabsContent value="ratios">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-lg">Calls to Answer</CardTitle>
                  <CardDescription>How many calls before leads answer</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold text-blue-400">
                    {analytics.ratios.callsToAnswer}
                  </div>
                  <p className="text-sm text-gray-500 mt-2">calls average</p>
                </CardContent>
              </Card>
              
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-lg">Calls to Book</CardTitle>
                  <CardDescription>How many calls before booking</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold text-purple-400">
                    {analytics.ratios.callsToBook}
                  </div>
                  <p className="text-sm text-gray-500 mt-2">calls average</p>
                </CardContent>
              </Card>
              
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-lg">Show Rate</CardTitle>
                  <CardDescription>Appointments that showed up</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold text-green-400">
                    {analytics.ratios.showRate}%
                  </div>
                  <p className="text-sm text-gray-500 mt-2">
                    {analytics.appointmentsShowed} of {analytics.appointmentsSet}
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-lg">No Show Rate</CardTitle>
                  <CardDescription>Appointments that didn't show</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold text-red-400">
                    {analytics.ratios.noShowRate}%
                  </div>
                  <p className="text-sm text-gray-500 mt-2">
                    {analytics.noShows} of {analytics.appointmentsSet}
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-lg">No-Show to Follow-up Booked</CardTitle>
                  <CardDescription>No-shows that rebooked</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold text-yellow-400">
                    {analytics.ratios.noShowToFollowup}%
                  </div>
                  <p className="text-sm text-gray-500 mt-2">recovery rate</p>
                </CardContent>
              </Card>
              
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader>
                  <CardTitle className="text-lg">No-Show Recovery to Showed</CardTitle>
                  <CardDescription>Rebooked no-shows that showed</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold text-emerald-400">
                    {analytics.ratios.noShowToShowed}%
                  </div>
                  <p className="text-sm text-gray-500 mt-2">final show rate</p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* Categories Tab */}
          <TabsContent value="categories">
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target size={20} className="text-purple-400" />
                  Lead Category Distribution
                </CardTitle>
                <CardDescription>
                  Breakdown of leads by their current status in the sales funnel
                </CardDescription>
              </CardHeader>
              <CardContent>
                {Object.keys(analytics.categoryBreakdown).length > 0 ? (
                  <CategoryChart data={analytics.categoryBreakdown} />
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Target size={48} className="mx-auto mb-4 text-gray-600" />
                    <p>No category data available</p>
                    <p className="text-sm">Lead categorization data will appear here once calls are analyzed</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* By Campaign Tab */}
          <TabsContent value="campaigns">
            <div className="space-y-4">
              {campaigns.length === 0 ? (
                <Card className="bg-gray-900 border-gray-800 p-12 text-center">
                  <BarChart3 size={48} className="mx-auto mb-4 text-gray-600" />
                  <h3 className="text-lg font-medium mb-2">No Campaigns Yet</h3>
                  <p className="text-gray-500 mb-4">Create campaigns to see per-campaign analytics</p>
                  <Button onClick={() => navigate('/qc/campaigns')}>
                    Go to Campaigns
                  </Button>
                </Card>
              ) : (
                campaigns.map(campaign => {
                  const stats = campaign.stats || {};
                  return (
                    <Card key={campaign.id} className="bg-gray-900 border-gray-800">
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <h3 className="font-medium text-white">{campaign.name}</h3>
                            <p className="text-sm text-gray-500">{campaign.description || 'No description'}</p>
                          </div>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => navigate(`/qc/campaigns/${campaign.id}`)}
                          >
                            View Details
                          </Button>
                        </div>
                        
                        <div className="grid grid-cols-5 gap-4">
                          <div className="text-center">
                            <p className="text-2xl font-bold text-blue-400">{stats.total_calls || 0}</p>
                            <p className="text-xs text-gray-500">Calls</p>
                          </div>
                          <div className="text-center">
                            <p className="text-2xl font-bold text-green-400">{stats.total_leads || 0}</p>
                            <p className="text-xs text-gray-500">Leads</p>
                          </div>
                          <div className="text-center">
                            <p className="text-2xl font-bold text-purple-400">{stats.appointments_set || 0}</p>
                            <p className="text-xs text-gray-500">Appts Set</p>
                          </div>
                          <div className="text-center">
                            <p className="text-2xl font-bold text-emerald-400">{stats.appointments_showed || 0}</p>
                            <p className="text-xs text-gray-500">Showed</p>
                          </div>
                          <div className="text-center">
                            <p className="text-2xl font-bold text-red-400">{stats.no_shows || 0}</p>
                            <p className="text-xs text-gray-500">No Shows</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default QCAnalyticsDashboard;
