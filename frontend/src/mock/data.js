// Mock data for Andromeda Voice AI Platform

export const mockAgents = [
  {
    id: 'agent_1',
    name: 'Customer Support Agent',
    description: 'Handles customer inquiries and support tickets',
    voice: 'Rachel',
    language: 'English',
    model: 'gpt-4-turbo',
    status: 'active',
    callsHandled: 1247,
    avgLatency: 1.8,
    successRate: 94.2,
    createdAt: '2024-01-15T10:30:00Z',
    lastUsed: '2024-03-20T14:22:00Z'
  },
  {
    id: 'agent_2',
    name: 'Sales Qualifier',
    description: 'Qualifies leads and schedules appointments',
    voice: 'Joseph',
    language: 'English',
    model: 'gpt-4-turbo',
    status: 'active',
    callsHandled: 856,
    avgLatency: 1.6,
    successRate: 91.5,
    createdAt: '2024-02-10T09:15:00Z',
    lastUsed: '2024-03-20T16:45:00Z'
  },
  {
    id: 'agent_3',
    name: 'Appointment Scheduler',
    description: 'Books and manages appointments',
    voice: 'Emily',
    language: 'English',
    model: 'gpt-4-turbo',
    status: 'inactive',
    callsHandled: 432,
    avgLatency: 1.9,
    successRate: 88.7,
    createdAt: '2024-03-01T11:00:00Z',
    lastUsed: '2024-03-18T10:30:00Z'
  }
];

export const mockCalls = [
  {
    id: 'call_1',
    agentId: 'agent_1',
    agentName: 'Customer Support Agent',
    phoneNumber: '+1 (555) 123-4567',
    direction: 'inbound',
    duration: 245,
    status: 'completed',
    sentiment: 'positive',
    latency: 1.7,
    timestamp: '2024-03-20T16:45:00Z',
    transcript: 'Customer called about order status...'
  },
  {
    id: 'call_2',
    agentId: 'agent_2',
    agentName: 'Sales Qualifier',
    phoneNumber: '+1 (555) 987-6543',
    direction: 'outbound',
    duration: 180,
    status: 'completed',
    sentiment: 'neutral',
    latency: 1.5,
    timestamp: '2024-03-20T16:30:00Z',
    transcript: 'Reached out to qualify lead...'
  },
  {
    id: 'call_3',
    agentId: 'agent_1',
    agentName: 'Customer Support Agent',
    phoneNumber: '+1 (555) 456-7890',
    direction: 'inbound',
    duration: 320,
    status: 'completed',
    sentiment: 'negative',
    latency: 2.1,
    timestamp: '2024-03-20T16:00:00Z',
    transcript: 'Customer complaint about billing...'
  }
];

export const mockPhoneNumbers = [
  {
    id: 'phone_1',
    number: '+1 (555) 100-0001',
    assignedAgent: 'agent_1',
    agentName: 'Customer Support Agent',
    status: 'active',
    callsReceived: 1247
  },
  {
    id: 'phone_2',
    number: '+1 (555) 100-0002',
    assignedAgent: 'agent_2',
    agentName: 'Sales Qualifier',
    status: 'active',
    callsReceived: 856
  },
  {
    id: 'phone_3',
    number: '+1 (555) 100-0003',
    assignedAgent: null,
    agentName: null,
    status: 'unassigned',
    callsReceived: 0
  }
];

export const mockVoices = [
  { id: 'rachel', name: 'Rachel', gender: 'female', accent: 'American' },
  { id: 'joseph', name: 'Joseph', gender: 'male', accent: 'American' },
  { id: 'emily', name: 'Emily', gender: 'female', accent: 'British' },
  { id: 'daniel', name: 'Daniel', gender: 'male', accent: 'British' },
  { id: 'aria', name: 'Aria', gender: 'female', accent: 'Australian' }
];

export const mockFlowNodes = [
  {
    id: 'node_1',
    type: 'conversation',
    label: 'Greeting',
    position: { x: 100, y: 100 },
    data: {
      prompt: 'Hello! I\'m an AI assistant. How can I help you today?',
      transitions: [
        { condition: 'customer needs support', nextNode: 'node_2' },
        { condition: 'customer wants sales', nextNode: 'node_3' }
      ]
    }
  },
  {
    id: 'node_2',
    type: 'conversation',
    label: 'Support Flow',
    position: { x: 300, y: 100 },
    data: {
      prompt: 'I can help you with that. Can you provide your order number?',
      transitions: [
        { condition: 'order number provided', nextNode: 'node_4' }
      ]
    }
  }
];

export const nodeTypes = [
  { id: 'conversation', name: 'Conversation', icon: 'MessageSquare', color: '#3b82f6' },
  { id: 'function', name: 'Function', icon: 'Zap', color: '#8b5cf6' },
  { id: 'call_transfer', name: 'Call Transfer', icon: 'PhoneForwarded', color: '#10b981' },
  { id: 'press_digit', name: 'Press Digit', icon: 'Hash', color: '#f59e0b' },
  { id: 'logic_split', name: 'Logic Split Node', icon: 'GitBranch', color: '#ec4899' },
  { id: 'agent_transfer', name: 'Agent Transfer', icon: 'UserPlus', color: '#06b6d4' },
  { id: 'sms', name: 'SMS', icon: 'MessageCircle', color: '#14b8a6' },
  { id: 'extract_variable', name: 'Extract Variable', icon: 'FileText', color: '#f97316' },
  { id: 'ending', name: 'Ending', icon: 'StopCircle', color: '#ef4444' }
];
