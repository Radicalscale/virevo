import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`; // Add /api to baseURL

// DEBUG: Log environment variables
console.log('🔍 API Service Configuration:');
console.log('  BACKEND_URL:', BACKEND_URL);
console.log('  API baseURL:', API);
console.log('  Expected: https://api.li-ai.org/api');

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Include cookies for authentication
});

// Agent APIs
export const agentAPI = {
  create: (data) => apiClient.post('/agents', data),
  list: () => apiClient.get('/agents'),
  get: (id) => apiClient.get(`/agents/${id}`),
  update: (id, data) => apiClient.put(`/agents/${id}`, data),
  delete: (id) => apiClient.delete(`/agents/${id}`),
  duplicate: (id) => apiClient.post(`/agents/${id}/duplicate`),
  updateFlow: (id, flow) => apiClient.put(`/agents/${id}/flow`, flow),
  getFlow: (id) => apiClient.get(`/agents/${id}/flow`),
  getKBItems: (id) => apiClient.get(`/agents/${id}/kb`),
  optimizeNode: (id, content, guidelines, model, fileContext = null, useKB = true) => 
    apiClient.post(`/agents/${id}/optimize-node`, { content, guidelines, model, file_context: fileContext, use_kb: useKB }),
  enhanceScript: (id, script, model) => apiClient.post(`/agents/${id}/enhance-script`, { script, model }),
  optimizeTransition: (id, condition, model) => apiClient.post(`/agents/${id}/optimize-transition`, { condition, model }),
  analyzeTransitions: (id, data) => apiClient.post(`/agents/${id}/analyze-transitions`, data),
  extractContextFromFile: (id, formData) => apiClient.post(`/agents/${id}/extract-context`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
};

// Call APIs
export const callAPI = {
  create: (data) => apiClient.post('/calls', data),
  list: (limit = 100) => apiClient.get('/calls', { params: { limit } }),
  get: (id) => apiClient.get(`/calls/${id}`),
  end: (id, data) => apiClient.post(`/calls/${id}/end`, data),
};

// QC Enhanced APIs
export const qcEnhancedAPI = {
  // Call data fetching - pass campaign_id to get results from campaign_calls collection
  fetchCallForQC: (callId, campaignId = null) => apiClient.post('/qc/enhanced/calls/fetch', { 
    call_id: callId,
    campaign_id: campaignId 
  }),
  
  // Campaign management
  createCampaign: (data) => apiClient.post('/qc/enhanced/campaigns', data),
  listCampaigns: () => apiClient.get('/qc/enhanced/campaigns'),
  getCampaign: (id) => apiClient.get(`/qc/enhanced/campaigns/${id}`),
  updateCampaign: (id, data) => apiClient.put(`/qc/enhanced/campaigns/${id}`, data),
  deleteCampaign: (id) => apiClient.delete(`/qc/enhanced/campaigns/${id}`),
  
  // Campaign call management
  addCallToCampaign: (campaignId, data) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/add-call`, data),
  getCampaignCalls: (campaignId) => apiClient.get(`/qc/enhanced/campaigns/${campaignId}/calls`),
  deleteCampaignCalls: (campaignId, callIds) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/delete-calls`, { call_ids: callIds }),
  
  // Training calls
  uploadTrainingCall: (campaignId, formData) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/training-calls`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getTrainingCalls: (campaignId) => apiClient.get(`/qc/enhanced/campaigns/${campaignId}/training-calls`),
  getTrainingCall: (campaignId, trainingCallId) => apiClient.get(`/qc/enhanced/campaigns/${campaignId}/training-calls/${trainingCallId}`),
  deleteTrainingCall: (campaignId, trainingCallId) => apiClient.delete(`/qc/enhanced/campaigns/${campaignId}/training-calls/${trainingCallId}`),
  updateTrainingCallOutcome: (campaignId, trainingCallId, outcomeData) => apiClient.put(
    `/qc/enhanced/campaigns/${campaignId}/training-calls/${trainingCallId}/outcome`, 
    outcomeData
  ),
  analyzeTrainingCall: (campaignId, trainingCallId, data = {}) => apiClient.post(
    `/qc/enhanced/campaigns/${campaignId}/training-calls/${trainingCallId}/analyze`,
    data
  ),
  analyzeAllTrainingCalls: (campaignId, data = {}) => apiClient.post(
    `/qc/enhanced/campaigns/${campaignId}/training-calls/analyze-all`,
    data
  ),
  
  // Custom calls (not from agents)
  uploadCustomCall: (campaignId, data) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/custom-calls`, data),
  
  // Campaign KB
  uploadCampaignKB: (campaignId, formData) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/kb`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getCampaignKB: (campaignId) => apiClient.get(`/qc/enhanced/campaigns/${campaignId}/kb`),
  
  // Campaign agents configuration
  updateCampaignAgents: (campaignId, data) => apiClient.put(`/qc/enhanced/campaigns/${campaignId}/agents`, data),
  
  // Campaign analysis
  analyzePatterns: (campaignId) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/analyze-patterns`),
  generateReport: (campaignId) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/generate-report`),
  
  // Batch analysis - Analyze all pending calls
  analyzeAllCalls: (campaignId, data) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/analyze-all`, data),
  
  // Reset analysis
  resetAllAnalysis: (campaignId) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/reset-all-analysis`),
  resetCallAnalysis: (campaignId, callId) => apiClient.post(`/qc/enhanced/campaigns/${campaignId}/calls/${encodeURIComponent(callId)}/reset-analysis`),
  
  // Campaign auto settings
  getCampaignAutoSettings: (campaignId) => apiClient.get(`/qc/enhanced/campaigns/${campaignId}/auto-settings`),
  
  // Campaign QC Results - get all analyzed calls and their results
  getCampaignQCResults: (campaignId) => apiClient.get(`/qc/enhanced/campaigns/${campaignId}/qc-results`),
  
  // QC Analysis
  analyzeTech: (data) => apiClient.post('/qc/enhanced/analyze/tech', data),
  analyzeScript: (data) => apiClient.post('/qc/enhanced/analyze/script', data),
  analyzeTonality: (data) => apiClient.post('/qc/enhanced/analyze/tonality', data),
  analyzeAudioTonality: (data) => apiClient.post('/qc/enhanced/analyze/audio-tonality', data),
  
  // Auto QC Settings
  getAgentAutoQCSettings: (agentId) => apiClient.get(`/qc/enhanced/agents/${agentId}/auto-qc-settings`),
  updateAgentAutoQCSettings: (agentId, settings) => apiClient.put(`/qc/enhanced/agents/${agentId}/auto-qc-settings`, settings),
  
  // Process QC (manual trigger or background)
  processCallQC: (data) => apiClient.post('/qc/enhanced/process-call-qc', data),
  triggerAutoQC: (callId) => apiClient.post(`/qc/enhanced/trigger-auto-qc/${callId}`),
  
  // Node Optimization
  optimizeNode: (data) => apiClient.post('/qc/enhanced/optimize/node', data),
  applyNodeOptimization: (data) => apiClient.post('/qc/enhanced/optimize/node/apply', data),
};

// QC Agents API
export const qcAgentsAPI = {
  // CRUD
  create: (data) => apiClient.post('/qc/agents', data),
  list: (agentType = null) => apiClient.get('/qc/agents', { params: agentType ? { agent_type: agentType } : {} }),
  listByType: (agentType) => apiClient.get(`/qc/agents/by-type/${agentType}`),
  get: (id) => apiClient.get(`/qc/agents/${id}`),
  update: (id, data) => apiClient.put(`/qc/agents/${id}`, data),
  delete: (id) => apiClient.delete(`/qc/agents/${id}`),
  
  // Knowledge Base
  uploadKB: (agentId, formData) => apiClient.post(`/qc/agents/${agentId}/kb`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  listKB: (agentId) => apiClient.get(`/qc/agents/${agentId}/kb`),
  deleteKB: (agentId, kbItemId) => apiClient.delete(`/qc/agents/${agentId}/kb/${kbItemId}`),
  
  // Pattern MD
  uploadPatternMD: (agentId, patternMd) => apiClient.post(`/qc/agents/${agentId}/pattern-md`, { pattern_md: patternMd }),
  
  // Assignments
  assign: (data) => apiClient.post('/qc/agents/assign', data),
  listAssignments: (params = {}) => apiClient.get('/qc/agents/assignments', { params }),
  deleteAssignment: (assignmentId) => apiClient.delete(`/qc/agents/assignments/${assignmentId}`),
  
  // Emotional Directions (for tonality agents)
  generateEmotionalDirections: (agentId, data) => apiClient.post(`/qc/agents/${agentId}/emotional-directions`, data),
  
  // Tech Issues Analysis
  analyzeTechIssues: (agentId, data) => apiClient.post(`/qc/agents/${agentId}/analyze-tech-issues`, data),
  
  // Interruption System
  checkInterruption: (data) => apiClient.post('/qc/agents/interruption/check', data),
  getInterruptionPhrases: () => apiClient.get('/qc/agents/interruption/phrases'),
  updateInterruptionPhrases: (data) => apiClient.put('/qc/agents/interruption/phrases', data),
};

// QC Learning API (Memory & Playbook System)
export const qcLearningAPI = {
  // Playbook Management
  getPlaybook: (agentId) => apiClient.get(`/qc/learning/agents/${agentId}/playbook`),
  updatePlaybook: (agentId, data) => apiClient.put(`/qc/learning/agents/${agentId}/playbook`, data),
  getPlaybookHistory: (agentId) => apiClient.get(`/qc/learning/agents/${agentId}/playbook/history`),
  getPlaybookVersion: (agentId, version) => apiClient.get(`/qc/learning/agents/${agentId}/playbook/version/${version}`),
  restorePlaybookVersion: (agentId, version) => apiClient.post(`/qc/learning/agents/${agentId}/playbook/restore/${version}`),
  
  // Learning Control
  getLearningConfig: (agentId) => apiClient.get(`/qc/learning/agents/${agentId}/config`),
  updateLearningConfig: (agentId, config) => apiClient.put(`/qc/learning/agents/${agentId}/config`, config),
  triggerLearning: (agentId) => apiClient.post(`/qc/learning/agents/${agentId}/learn`),
  getLearningStats: (agentId) => apiClient.get(`/qc/learning/agents/${agentId}/stats`),
  
  // Analysis Logs
  getAnalysisLogs: (agentId, params = {}) => apiClient.get(`/qc/learning/agents/${agentId}/analysis-logs`, { params }),
  updateLogOutcome: (agentId, logId, outcome) => apiClient.put(`/qc/learning/agents/${agentId}/analysis-logs/${logId}/outcome`, outcome),
  
  // Patterns
  getPatterns: (agentId, params = {}) => apiClient.get(`/qc/learning/agents/${agentId}/patterns`, { params }),
  deletePattern: (agentId, patternId) => apiClient.delete(`/qc/learning/agents/${agentId}/patterns/${patternId}`),
  
  // Learning Sessions
  getLearningSessions: (agentId, limit = 20) => apiClient.get(`/qc/learning/agents/${agentId}/sessions`, { params: { limit } }),
  
  // Brain Prompts
  getBrainPrompts: (agentId) => apiClient.get(`/qc/learning/agents/${agentId}/brain-prompts`),
  updateBrainPrompts: (agentId, prompts) => apiClient.put(`/qc/learning/agents/${agentId}/brain-prompts`, prompts),
  previewBrainPrompts: (agentId, data) => apiClient.post(`/qc/learning/agents/${agentId}/brain-prompts/preview`, data),
};

// Analytics API (merged QC and general analytics)
export const analyticsAPI = {
  // QC Analytics
  getCampaignAnalytics: (campaignId) => apiClient.get(`/qc/enhanced/campaigns/${campaignId}/analytics`),
  getAggregatedAnalytics: (params = {}) => apiClient.get('/crm/analytics', { params }),
  getLeadsByCategory: (category) => apiClient.get(`/crm/leads/by-category/${category}`),
  getLeadCallHistory: (leadId) => apiClient.get(`/crm/leads/${leadId}/call-history`),
  // General Analytics
  callHistory: (params) => apiClient.get('/call-history', { params }),
  callAnalytics: () => apiClient.get('/call-analytics'),
  callDetail: (callId) => apiClient.get(`/call-history/${callId}`),
  dashboardAnalytics: () => apiClient.get('/dashboard/analytics'),
};

// Phone Number APIs
export const phoneNumberAPI = {
  create: (data) => apiClient.post('/phone-numbers', data),
  list: () => apiClient.get('/phone-numbers'),
  assign: (id, agentId) => apiClient.put(`/phone-numbers/${id}`, { agent_id: agentId }),
};

// Knowledge Base APIs
export const kbAPI = {
  list: (agentId) => apiClient.get(`/agents/${agentId}/kb`),
  upload: (agentId, formData) => apiClient.post(`/agents/${agentId}/kb/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  addUrl: (agentId, url) => apiClient.post(`/agents/${agentId}/kb/url?url=${encodeURIComponent(url)}`),
  delete: (agentId, kbId) => apiClient.delete(`/agents/${agentId}/kb/${kbId}`),
};

// Warmup APIs - Call before initiating calls to reduce latency
export const warmupAPI = {
  tts: () => apiClient.post('/warmup/tts'),
};

// Telnyx APIs
export const telnyxAPI = {
  outboundCall: (data) => apiClient.post('/telnyx/call/outbound', data),
};

// Test APIs
export const testAPI = {
  createRoom: (agentId) => apiClient.post('/test/create-room', { agent_id: agentId }),
  health: () => apiClient.get('/health'),
};

export default apiClient;
