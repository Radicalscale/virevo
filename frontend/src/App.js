import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import PrivateRoute from "./components/PrivateRoute";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import Agents from "./components/Agents";
import AgentForm from "./components/AgentForm";
import FlowBuilder from "./components/FlowBuilder";
import OutboundCallTester from "./components/OutboundCallTester";
import APIKeyManager from "./components/APIKeyManager";
import Calls from "./components/Calls";
import Analytics from "./components/AnalyticsNew";
import PhoneNumbers from "./components/PhoneNumbers";
import CRM from "./components/CRM";
import LeadDetail from "./components/LeadDetail";
import LeadEdit from "./components/LeadEdit";
import QCAgentTester from "./components/QCAgentTester";
import AgentTester from "./components/AgentTester";
import QCDashboard from "./components/QCDashboard";
import CampaignManager from "./components/CampaignManager";
import CampaignDetailsPage from "./components/CampaignDetailsPage";
import CampaignSettingsPage from "./components/CampaignSettingsPage";
import QCAgents from "./components/QCAgents";
import QCAgentEditor from "./components/QCAgentEditor";
import QCAnalyticsDashboard from "./components/QCAnalyticsDashboard";
import DirectorTab from "./components/DirectorTab";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import { Toaster } from "./components/ui/toaster";
import DebugInfo from "./components/DebugInfo";

function App() {
  return (
    <div className="App bg-gray-900 min-h-screen">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Protected routes */}
            <Route
              path="/*"
              element={
                <PrivateRoute>
                  <div className="flex">
                    <Sidebar />
                    <div className="ml-64 flex-1">
                      <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/agents" element={<Agents />} />
                        <Route path="/agents/new" element={<AgentForm />} />
                        <Route path="/agents/:id/edit" element={<AgentForm />} />
                        <Route path="/agents/:id/flow" element={<FlowBuilder />} />
                        <Route path="/agents/:id/test" element={<AgentTester />} />
                        <Route path="/test-call" element={<OutboundCallTester />} />
                        <Route path="/calls" element={<Calls />} />
                        <Route path="/numbers" element={<PhoneNumbers />} />
                        <Route path="/crm" element={<CRM />} />
                        <Route path="/crm/leads/:leadId" element={<LeadDetail />} />
                        <Route path="/crm/leads/:leadId/edit" element={<LeadEdit />} />
                        <Route path="/qc-tester" element={<QCAgentTester />} />
                        <Route path="/qc/calls/:callId" element={<QCDashboard />} />
                        <Route path="/qc/campaigns" element={<CampaignManager />} />
                        <Route path="/qc/campaigns/:campaignId" element={<CampaignDetailsPage />} />
                        <Route path="/qc/campaigns/:campaignId/settings" element={<CampaignSettingsPage />} />
                        {/* QC Agents Routes */}
                        <Route path="/qc/agents" element={<QCAgents />} />
                        <Route path="/qc/agents/new" element={<QCAgentEditor />} />
                        <Route path="/qc/agents/:agentId" element={<QCAgentEditor />} />
                        <Route path="/qc/agents/:agentId/edit" element={<QCAgentEditor />} />
                        {/* QC Analytics Dashboard */}
                        <Route path="/qc/analytics" element={<QCAnalyticsDashboard />} />
                        <Route path="/analytics" element={<Analytics />} />
                        <Route path="/settings" element={<APIKeyManager />} />
                        <Route path="/director" element={<DirectorTab />} />
                      </Routes>
                    </div>
                  </div>
                </PrivateRoute>
              }
            />
          </Routes>
          <Toaster />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
