import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './APIKeyManager.css';

const API_SERVICES = [
  {
    name: 'deepgram',
    label: 'Deepgram',
    description: 'Speech-to-Text (STT) service',
    placeholder: 'Enter your Deepgram API key',
    getKeyUrl: 'https://console.deepgram.com/',
    required: true
  },
  {
    name: 'openai',
    label: 'OpenAI',
    description: 'Large Language Model (LLM) provider',
    placeholder: 'sk-proj-...',
    getKeyUrl: 'https://platform.openai.com/api-keys',
    required: true
  },
  {
    name: 'elevenlabs',
    label: 'ElevenLabs',
    description: 'Text-to-Speech (TTS) service',
    placeholder: 'Enter your ElevenLabs API key',
    getKeyUrl: 'https://elevenlabs.io/app/settings/api-keys',
    required: true
  },
  {
    name: 'grok',
    label: 'Grok (xAI)',
    description: 'Alternative LLM provider',
    placeholder: 'xai-...',
    getKeyUrl: 'https://x.ai/',
    required: false
  },
  {
    name: 'hume',
    label: 'Hume AI',
    description: 'Alternative TTS provider with emotional voices',
    placeholder: 'Enter your Hume API key',
    getKeyUrl: 'https://platform.hume.ai/',
    required: false
  },
  {
    name: 'soniox',
    label: 'Soniox',
    description: 'Alternative STT provider',
    placeholder: 'Enter your Soniox API key',
    getKeyUrl: 'https://soniox.com/',
    required: false
  },
  {
    name: 'assemblyai',
    label: 'AssemblyAI',
    description: 'Alternative STT provider',
    placeholder: 'Enter your AssemblyAI API key',
    getKeyUrl: 'https://www.assemblyai.com/app/account',
    required: false
  },
  {
    name: 'telnyx',
    label: 'Telnyx',
    description: 'Phone calling service (REQUIRED for calls)',
    placeholder: 'KEY...',
    getKeyUrl: 'https://portal.telnyx.com/#/app/api-keys',
    required: true
  },
  {
    name: 'telnyx_connection_id',
    label: 'Telnyx Connection ID',
    description: 'Your Telnyx TeXML or SIP Connection ID (REQUIRED for calls)',
    placeholder: 'your-connection-id-here',
    getKeyUrl: 'https://portal.telnyx.com/#/app/connections',
    required: true
  },
  {
    name: 'webhook',
    label: 'Webhook API Key',
    description: 'API key for external services (n8n, Zapier, Make) to trigger calls',
    placeholder: 'Create any secret key (e.g., my-secret-key-12345)',
    getKeyUrl: null,
    required: false
  }
];

function APIKeyManager() {
  const [apiKeys, setApiKeys] = useState({});
  const [editingKey, setEditingKey] = useState(null);
  const [keyValue, setKeyValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState({});
  const [qcModel, setQcModel] = useState('gpt-4o');
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    fetchConfiguredKeys();
    fetchQCConfig();
  }, []);

  const loadAPIKeys = async () => {
    try {
      const response = await api.get('/settings/api-keys');
      const keysMap = {};
      response.data.forEach(key => {
        keysMap[key.service_name] = {
          has_key: key.has_key,
          is_active: key.is_active
        };
      });
      setApiKeys(keysMap);
    } catch (error) {
      console.error('Failed to load API keys:', error);
      showMessage('error', 'Failed to load API keys');
    }
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 5000);
  };

  const fetchConfiguredKeys = async () => {
    // This function can be used to fetch additional configuration
    // For now, it calls the existing loadAPIKeys function
    await loadAPIKeys();
  };

  const fetchQCConfig = async () => {
    try {
      const response = await api.get('/settings/qc-config');
      if (response.data && response.data.model) {
        setQcModel(response.data.model);
      }
    } catch (error) {
      console.error('Failed to load QC config:', error);
      // Don't show error message as this might be expected for new installations
    }
  };

  const handleQCModelChange = async (newModel) => {
    setQcModel(newModel);
    try {
      await api.post('/settings/qc-config', { model: newModel });
      showMessage('success', `QC model updated to ${newModel}`);
    } catch (error) {
      console.error('Failed to save QC config:', error);
      showMessage('error', 'Failed to save QC configuration');
    }
  };

  const handleAddKey = (serviceName) => {
    setEditingKey(serviceName);
    setKeyValue('');
  };

  const handleSaveKey = async (serviceName) => {
    if (!keyValue.trim()) {
      showMessage('error', 'Please enter an API key');
      return;
    }

    setLoading(true);
    try {
      await api.post('/settings/api-keys', {
        service_name: serviceName,
        api_key: keyValue
      });

      showMessage('success', `${serviceName} API key saved successfully`);
      setEditingKey(null);
      setKeyValue('');
      loadAPIKeys();
    } catch (error) {
      console.error('Failed to save API key:', error);
      showMessage('error', error.response?.data?.detail || 'Failed to save API key');
    } finally {
      setLoading(false);
    }
  };

  const handleTestKey = async (serviceName) => {
    setTesting(prev => ({ ...prev, [serviceName]: true }));
    try {
      const response = await api.post(`/settings/api-keys/test/${serviceName}`);
      if (response.data.valid) {
        showMessage('success', `${serviceName} API key is valid ✓`);
      } else {
        showMessage('error', `${serviceName} API key is invalid: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Failed to test API key:', error);
      showMessage('error', error.response?.data?.detail || 'Failed to test API key');
    } finally {
      setTesting(prev => ({ ...prev, [serviceName]: false }));
    }
  };

  const handleDeleteKey = async (serviceName) => {
    if (!window.confirm(`Are you sure you want to delete your ${serviceName} API key?`)) {
      return;
    }

    setLoading(true);
    try {
      await api.delete(`/settings/api-keys/${serviceName}`);
      showMessage('success', `${serviceName} API key deleted`);
      loadAPIKeys();
    } catch (error) {
      console.error('Failed to delete API key:', error);
      showMessage('error', 'Failed to delete API key');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="api-keys-container">
      <div className="api-keys-header">
        <h1>API Keys</h1>
        <p className="subtitle">Manage your API keys for various AI services. All keys are encrypted and stored securely.</p>
      </div>

      {message.text && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="api-keys-info">
        <h3>⚠️ Important</h3>
        <ul>
          <li><strong>Required Keys:</strong> You must add Deepgram, OpenAI, ElevenLabs, and Telnyx keys to make calls.</li>
          <li><strong>Optional Keys:</strong> Additional providers can be used as alternatives.</li>
          <li><strong>Security:</strong> All keys are encrypted before storage.</li>
          <li><strong>Usage:</strong> Your keys are only used for your agents and calls.</li>
        </ul>
      </div>

      <div className="api-services-grid">
        {API_SERVICES.map(service => {
          const hasKey = apiKeys[service.name]?.has_key;
          const isEditing = editingKey === service.name;

          return (
            <div key={service.name} className={`api-service-card ${service.required ? 'required' : ''}`}>
              <div className="service-header">
                <div>
                  <h3>{service.label} {service.required && <span className="required-badge">REQUIRED</span>}</h3>
                  <p className="service-description">{service.description}</p>
                </div>
                <div className={`status-indicator ${hasKey ? 'active' : 'inactive'}`}>
                  {hasKey ? '✓ Active' : '⚠ Not Set'}
                </div>
              </div>

              {isEditing ? (
                <div className="key-input-section">
                  <input
                    type="password"
                    value={keyValue}
                    onChange={(e) => setKeyValue(e.target.value)}
                    placeholder={service.placeholder}
                    className="key-input"
                    disabled={loading}
                  />
                  <div className="button-group">
                    <button
                      onClick={() => handleSaveKey(service.name)}
                      disabled={loading}
                      className="btn btn-primary"
                    >
                      {loading ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => {
                        setEditingKey(null);
                        setKeyValue('');
                      }}
                      disabled={loading}
                      className="btn btn-secondary"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="key-actions">
                  <button
                    onClick={() => handleAddKey(service.name)}
                    className="btn btn-primary"
                  >
                    {hasKey ? 'Update Key' : 'Add Key'}
                  </button>

                  {hasKey && (
                    <>
                      <button
                        onClick={() => handleTestKey(service.name)}
                        disabled={testing[service.name]}
                        className="btn btn-secondary"
                      >
                        {testing[service.name] ? 'Testing...' : 'Test Key'}
                      </button>
                      <button
                        onClick={() => handleDeleteKey(service.name)}
                        className="btn btn-danger"
                      >
                        Delete
                      </button>
                    </>
                  )}

                  {service.getKeyUrl && (
                    <a
                      href={service.getKeyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-link"
                    >
                      Get API Key →
                    </a>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* QC Agent Configuration */}
      <div className="qc-config-section" style={{ marginTop: '40px', padding: '24px', background: '#1a1a2e', borderRadius: '8px', border: '1px solid #333' }}>
        <h2 style={{ color: '#fff', marginBottom: '8px' }}>🎯 QC Agent Configuration</h2>
        <p style={{ color: '#888', marginBottom: '24px' }}>Configure the AI model used for post-call quality analysis</p>

        <div style={{ display: 'grid', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', color: '#fff', marginBottom: '8px', fontWeight: '500' }}>
              LLM Model for QC Analysis
            </label>
            <select
              value={qcModel}
              onChange={(e) => handleQCModelChange(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                background: '#0f0f1e',
                border: '1px solid #333',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '14px'
              }}
            >
              <option value="gpt-4o">GPT-4o (Recommended - Fast & Accurate)</option>
              <option value="gpt-4o-mini">GPT-4o Mini (Faster, Lower Cost)</option>
              <option value="gpt-4-turbo">GPT-4 Turbo (More Detailed)</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Budget Option)</option>
            </select>
            <p style={{ color: '#666', fontSize: '12px', marginTop: '8px' }}>
              Model used by all 3 QC agents: Commitment Detector, Conversion Pathfinder, Excellence Replicator
            </p>
          </div>

          <div style={{ padding: '16px', background: '#0f0f1e', borderRadius: '6px', border: '1px solid #333' }}>
            <h4 style={{ color: '#fff', marginBottom: '8px', fontSize: '14px' }}>💰 Estimated Cost Per Analysis</h4>
            <div style={{ color: '#888', fontSize: '13px' }}>
              {qcModel === 'gpt-4o' && '~$0.03-0.05 per call'}
              {qcModel === 'gpt-4o-mini' && '~$0.01-0.02 per call'}
              {qcModel === 'gpt-4-turbo' && '~$0.05-0.08 per call'}
              {qcModel === 'gpt-3.5-turbo' && '~$0.005-0.01 per call'}
            </div>
          </div>
        </div>
      </div>

      <div className="api-keys-help">
        <h3>Need Help?</h3>
        <ul>
          <li><strong>Deepgram:</strong> Sign up at deepgram.com and create an API key in the console</li>
          <li><strong>OpenAI:</strong> Create an account at openai.com and generate a key in API settings</li>
          <li><strong>ElevenLabs:</strong> Sign up at elevenlabs.io and find your key in profile settings</li>
          <li><strong>Telnyx:</strong> Create an account at telnyx.com, buy a phone number, and generate API key</li>
          <li><strong>Other services:</strong> Click "Get API Key" next to each service for registration</li>
        </ul>
      </div>
    </div>
  );
}

export default APIKeyManager;
