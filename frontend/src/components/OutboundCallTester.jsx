import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Card } from './ui/card';
import { useToast } from '../hooks/use-toast';
import { Phone, Loader2, Activity, CheckCircle, TrendingUp } from 'lucide-react';
import { agentAPI, telnyxAPI } from '../services/api';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const OutboundCallTester = () => {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [toNumber, setToNumber] = useState('');
  const [fromNumber, setFromNumber] = useState('+18722778634');
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // QC Tracking
  const [enableQCTracking, setEnableQCTracking] = useState(true);
  const [createLead, setCreateLead] = useState(false);
  const [leadSource, setLeadSource] = useState('test_call');
  const [trackKeywords, setTrackKeywords] = useState('');
  const [expectedCommitment, setExpectedCommitment] = useState('not_specified');

  // Call tracking
  const [activeCallId, setActiveCallId] = useState(null);
  const [qcResults, setQcResults] = useState(null);
  const [checkingQC, setCheckingQC] = useState(false);

  const { toast } = useToast();

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await agentAPI.list();
      setAgents(response.data);
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

  const handleMakeCall = async () => {
    if (!selectedAgent || !toNumber) {
      toast({
        title: "Missing Information",
        description: "Please select an agent and enter a phone number",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    setQcResults(null); // Clear previous results

    try {
      // Step 1: Create lead if enabled
      let leadId = null;
      if (createLead && customerName && customerEmail) {
        try {
          const leadResponse = await axios.post(
            `${BACKEND_URL}/api/crm/leads`,
            {
              name: customerName,
              email: customerEmail,
              phone: toNumber,
              source: leadSource,
              tags: ['test_call'],
              notes: 'Created from test call'
            },
            { withCredentials: true }
          );
          leadId = leadResponse.data.id;
          toast({
            title: "Lead Created",
            description: `Lead ${customerName} created for tracking`,
          });
        } catch (error) {
          console.error('Error creating lead:', error);
        }
      }

      // Step 2: Make the call with custom variables
      const customVariables = {
        lead_id: leadId,
        qc_tracking_enabled: enableQCTracking,
        track_keywords: trackKeywords,
        expected_commitment: expectedCommitment
      };
      if (customerName) customVariables.customer_name = customerName;
      if (customerEmail) customVariables.customer_email = customerEmail;

      const response = await telnyxAPI.outboundCall({
        agent_id: selectedAgent,
        to_number: toNumber,
        from_number: fromNumber,
        custom_variables: customVariables
      });

      const data = response.data;

      if (data.success) {
        const callId = data.call_id || data.call_control_id; // Backend returns call_id
        setActiveCallId(callId);

        toast({
          title: "Call Initiated! 📞",
          description: enableQCTracking
            ? `Calling ${toNumber}. QC analysis will run when call ends.`
            : `Calling ${toNumber} from ${data.from_number}`,
        });

        // If QC tracking enabled, start polling for results
        if (enableQCTracking && callId) {
          setTimeout(() => checkForQCResults(callId, leadId), 10000); // Check after 10 seconds
        }
      } else {
        toast({
          title: "Call Failed",
          description: data.detail || data.error || "Failed to initiate call",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error making call:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to initiate call. Check console for details.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const checkForQCResults = async (callId, leadId, attempts = 0) => {
    // Max 30 minutes of checking (180 attempts × 10 seconds = 30 min)
    // Allows for long calls + processing time
    if (attempts > 180) {
      toast({
        title: "QC Analysis Pending",
        description: "Analysis is taking longer than expected. Check CRM later for results.",
        variant: "warning"
      });
      setCheckingQC(false);
      return;
    }

    setCheckingQC(true);

    try {
      // Check if call has ended and QC analysis is complete
      const response = await axios.get(
        `${BACKEND_URL}/api/crm/analytics/call/${callId}`,
        { withCredentials: true }
      );

      if (response.data && response.data.aggregated_scores) {
        setQcResults(response.data);
        setCheckingQC(false);

        toast({
          title: "QC Analysis Complete! 🎯",
          description: "Scroll down to see detailed scores and recommendations",
        });
        return;
      }
    } catch (error) {
      // Not found yet or still processing, continue polling
      if (error.response?.status === 404 || error.response?.status === 400) {
        setTimeout(() => checkForQCResults(callId, leadId, attempts + 1), 10000);
        return;
      }

      // Other errors - log and stop
      console.error('Error checking QC results:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to check QC results. Check CRM later.",
        variant: "destructive"
      });
    }

    setCheckingQC(false);
  };

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <Card className="p-6 bg-gray-900 border-gray-800">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-white mb-2">
            📞 Outbound Call Tester
          </h2>
          <p className="text-gray-400 text-sm">
            Test your AI agents with real phone calls via Telnyx
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <Label className="text-gray-300">Select Agent</Label>
            <Select value={selectedAgent} onValueChange={setSelectedAgent}>
              <SelectTrigger className="bg-gray-800 border-gray-700 text-white mt-2">
                <SelectValue placeholder="Choose an agent" />
              </SelectTrigger>
              <SelectContent>
                {agents.map((agent) => (
                  <SelectItem key={agent.id} value={agent.id}>
                    {agent.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-gray-300">To Number (Phone to Call)</Label>
            <Input
              type="tel"
              value={toNumber}
              onChange={(e) => setToNumber(e.target.value)}
              placeholder="+1234567890"
              className="bg-gray-800 border-gray-700 text-white mt-2"
            />
            <p className="text-xs text-gray-500 mt-1">E.164 format (e.g., +15551234567)</p>
          </div>

          <div>
            <Label className="text-gray-300">From Number (Optional)</Label>
            <Input
              type="tel"
              value={fromNumber}
              onChange={(e) => setFromNumber(e.target.value)}
              placeholder="+14048000152"
              className="bg-gray-800 border-gray-700 text-white mt-2"
            />
          </div>

          <div className="border-t border-gray-700 pt-4">
            <h3 className="text-white font-semibold mb-3">Custom Variables (Optional)</h3>

            <div className="space-y-3">
              <div>
                <Label className="text-gray-300">Customer Name</Label>
                <Input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="John Smith"
                  className="bg-gray-800 border-gray-700 text-white mt-2"
                />
              </div>

              <div>
                <Label className="text-gray-300">Email</Label>
                <Input
                  type="email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  placeholder="john@example.com"
                  className="bg-gray-800 border-gray-700 text-white mt-2"
                />
              </div>
            </div>
          </div>

          {/* QC Tracking Section */}
          <div className="border-t border-gray-700 pt-4">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="text-blue-400" size={20} />
              <h3 className="text-white font-semibold">QC Agent Tracking</h3>
            </div>

            <div className="space-y-3">
              {/* Enable QC Tracking */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableQCTracking}
                  onChange={(e) => setEnableQCTracking(e.target.checked)}
                  className="w-4 h-4 bg-gray-800 border-gray-700 rounded focus:ring-blue-500"
                />
                <span className="text-gray-300 text-sm">
                  Enable QC Analysis (analyze call quality when it ends)
                </span>
              </label>

              {/* Create Lead */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={createLead}
                  onChange={(e) => setCreateLead(e.target.checked)}
                  className="w-4 h-4 bg-gray-800 border-gray-700 rounded focus:ring-blue-500"
                />
                <span className="text-gray-300 text-sm">
                  Create CRM lead from this call
                </span>
              </label>

              {createLead && (
                <div className="ml-6 space-y-2">
                  <div>
                    <Label className="text-gray-300 text-sm">Lead Source</Label>
                    <Input
                      type="text"
                      value={leadSource}
                      onChange={(e) => setLeadSource(e.target.value)}
                      placeholder="test_call"
                      className="bg-gray-800 border-gray-700 text-white mt-1 text-sm"
                    />
                  </div>
                </div>
              )}

              {enableQCTracking && (
                <div className="ml-6 space-y-2 pt-2 border-t border-gray-700">
                  <div>
                    <Label className="text-gray-300 text-sm">Track Keywords (comma-separated)</Label>
                    <Input
                      type="text"
                      value={trackKeywords}
                      onChange={(e) => setTrackKeywords(e.target.value)}
                      placeholder="price, cost, deadline, objection"
                      className="bg-gray-800 border-gray-700 text-white mt-1 text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-300 text-sm">Expected Commitment Level</Label>
                    <Select value={expectedCommitment} onValueChange={setExpectedCommitment}>
                      <SelectTrigger className="bg-gray-800 border-gray-700 text-white mt-1">
                        <SelectValue placeholder="Not specified" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="not_specified">Not specified</SelectItem>
                        <SelectItem value="high">High (75-100)</SelectItem>
                        <SelectItem value="medium">Medium (50-74)</SelectItem>
                        <SelectItem value="low">Low (0-49)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}
            </div>
          </div>

          <Button
            onClick={handleMakeCall}
            disabled={isLoading || !selectedAgent || !toNumber}
            className="w-full bg-green-600 hover:bg-green-700 text-white"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Calling...
              </>
            ) : (
              <>
                <Phone className="mr-2 h-4 w-4" />
                Make Call
              </>
            )}
          </Button>

          {/* QC Checking Status */}
          {checkingQC && (
            <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4 flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
              <div>
                <p className="text-white font-medium">Waiting for QC Analysis...</p>
                <p className="text-gray-400 text-sm">Analysis will start when the call ends</p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
          <h4 className="text-white font-semibold mb-2">How it works:</h4>
          <ul className="text-sm text-gray-400 space-y-1">
            <li>1. Select an AI agent</li>
            <li>2. Enter the phone number to call</li>
            <li>3. (Optional) Enable QC tracking to analyze call quality</li>
            <li>4. (Optional) Create a CRM lead to track this contact</li>
            <li>5. Click "Make Call" - the agent will call the number!</li>
            <li>6. Answer the phone and talk to your AI agent</li>
            <li>7. After call ends, QC agents will analyze the conversation</li>
          </ul>
        </div>
      </Card>

      {/* QC Results Section */}
      {qcResults && (
        <Card className="p-6 bg-gray-900 border-gray-800 mt-6">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="text-green-400" size={24} />
            <h2 className="text-2xl font-bold text-white">
              QC Analysis Results
            </h2>
          </div>

          {/* Overall Scores */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {/* Commitment Score */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <p className="text-gray-400 text-sm mb-1">Commitment Score</p>
              <p className={`text-3xl font-bold ${(qcResults.aggregated_scores?.commitment_score || 0) >= 75 ? 'text-green-400' :
                  (qcResults.aggregated_scores?.commitment_score || 0) >= 50 ? 'text-yellow-400' :
                    'text-red-400'
                }`}>
                {qcResults.aggregated_scores?.commitment_score || 'N/A'}
              </p>
              <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                <div
                  className={`h-2 rounded-full ${(qcResults.aggregated_scores?.commitment_score || 0) >= 75 ? 'bg-green-500' :
                      (qcResults.aggregated_scores?.commitment_score || 0) >= 50 ? 'bg-yellow-500' :
                        'bg-red-500'
                    }`}
                  style={{ width: `${qcResults.aggregated_scores?.commitment_score || 0}%` }}
                ></div>
              </div>
            </div>

            {/* Conversion Score */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <p className="text-gray-400 text-sm mb-1">Conversion Score</p>
              <p className={`text-3xl font-bold ${(qcResults.aggregated_scores?.conversion_score || 0) >= 75 ? 'text-green-400' :
                  (qcResults.aggregated_scores?.conversion_score || 0) >= 50 ? 'text-yellow-400' :
                    'text-red-400'
                }`}>
                {qcResults.aggregated_scores?.conversion_score || 'N/A'}
              </p>
              <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                <div
                  className={`h-2 rounded-full ${(qcResults.aggregated_scores?.conversion_score || 0) >= 75 ? 'bg-green-500' :
                      (qcResults.aggregated_scores?.conversion_score || 0) >= 50 ? 'bg-yellow-500' :
                        'bg-red-500'
                    }`}
                  style={{ width: `${qcResults.aggregated_scores?.conversion_score || 0}%` }}
                ></div>
              </div>
            </div>

            {/* Excellence Score */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <p className="text-gray-400 text-sm mb-1">Excellence Score</p>
              <p className={`text-3xl font-bold ${(qcResults.aggregated_scores?.excellence_score || 0) >= 75 ? 'text-green-400' :
                  (qcResults.aggregated_scores?.excellence_score || 0) >= 50 ? 'text-yellow-400' :
                    'text-red-400'
                }`}>
                {qcResults.aggregated_scores?.excellence_score || 'N/A'}
              </p>
              <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                <div
                  className={`h-2 rounded-full ${(qcResults.aggregated_scores?.excellence_score || 0) >= 75 ? 'bg-green-500' :
                      (qcResults.aggregated_scores?.excellence_score || 0) >= 50 ? 'bg-yellow-500' :
                        'bg-red-500'
                    }`}
                  style={{ width: `${qcResults.aggregated_scores?.excellence_score || 0}%` }}
                ></div>
              </div>
            </div>

            {/* Show-Up Probability */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <p className="text-gray-400 text-sm mb-1">Show-Up Probability</p>
              <p className={`text-3xl font-bold ${(qcResults.aggregated_scores?.show_up_probability || 0) >= 75 ? 'text-green-400' :
                  (qcResults.aggregated_scores?.show_up_probability || 0) >= 50 ? 'text-yellow-400' :
                    'text-red-400'
                }`}>
                {qcResults.aggregated_scores?.show_up_probability || 'N/A'}%
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Risk: <span className={`font-semibold uppercase ${qcResults.aggregated_scores?.risk_level === 'low' ? 'text-green-400' :
                    qcResults.aggregated_scores?.risk_level === 'medium' ? 'text-yellow-400' :
                      'text-red-400'
                  }`}>
                  {qcResults.aggregated_scores?.risk_level || 'N/A'}
                </span>
              </p>
            </div>
          </div>

          {/* Overall Quality Score */}
          <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-blue-700 rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-300 text-sm mb-1">Overall Quality Score</p>
                <p className={`text-5xl font-bold ${(qcResults.aggregated_scores?.overall_quality_score || 0) >= 75 ? 'text-green-400' :
                    (qcResults.aggregated_scores?.overall_quality_score || 0) >= 50 ? 'text-yellow-400' :
                      'text-red-400'
                  }`}>
                  {qcResults.aggregated_scores?.overall_quality_score || 'N/A'}
                </p>
              </div>
              <CheckCircle className="text-green-400" size={48} />
            </div>
          </div>

          {/* Recommendations */}
          {qcResults.recommendations && qcResults.recommendations.length > 0 && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <h3 className="text-white font-semibold mb-3">Recommendations</h3>
              <ul className="space-y-2">
                {qcResults.recommendations.slice(0, 5).map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-gray-300 text-sm">
                    <span className="text-yellow-400 mt-1">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* View in CRM */}
          {qcResults.lead_id && (
            <div className="mt-4">
              <Button
                onClick={() => window.location.href = `/crm/leads/${qcResults.lead_id}`}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                View Lead in CRM
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default OutboundCallTester;
