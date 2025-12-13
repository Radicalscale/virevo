import React, { useState, useEffect } from 'react';
import { Phone, Plus, Edit2, Trash2, X, Check } from 'lucide-react';
import { phoneNumberAPI, agentAPI } from '../services/api';

const PhoneNumbers = () => {
  const [phoneNumbers, setPhoneNumbers] = useState([]);
  const [agents, setAgents] = useState([]);
  const [selectedNumber, setSelectedNumber] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newNumber, setNewNumber] = useState('');
  const [editingNumber, setEditingNumber] = useState(false);
  const [tempNumberValue, setTempNumberValue] = useState('');

  // Fetch phone numbers and agents
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [numbersRes, agentsRes] = await Promise.all([
        phoneNumberAPI.list(),
        agentAPI.list()
      ]);
      
      setPhoneNumbers(numbersRes.data);
      setAgents(agentsRes.data);
      
      // Select first number by default
      if (numbersData.length > 0 && !selectedNumber) {
        setSelectedNumber(numbersData[0]);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddNumber = async () => {
    if (!newNumber.trim()) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/phone-numbers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ number: newNumber })
      });
      
      if (response.ok) {
        const addedNumber = await response.json();
        setPhoneNumbers([...phoneNumbers, addedNumber]);
        setSelectedNumber(addedNumber);
        setNewNumber('');
        setShowAddModal(false);
      }
    } catch (error) {
      console.error('Error adding number:', error);
    }
  };

  const handleUpdateNumber = async (numberId, field, value) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/phone-numbers/${numberId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value })
      });
      
      if (response.ok) {
        const updated = await response.json();
        setPhoneNumbers(phoneNumbers.map(n => n.id === numberId ? updated : n));
        setSelectedNumber(updated);
      }
    } catch (error) {
      console.error('Error updating number:', error);
    }
  };

  const handleDeleteNumber = async (numberId) => {
    if (!window.confirm('Are you sure you want to delete this phone number?')) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/phone-numbers/${numberId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        const remaining = phoneNumbers.filter(n => n.id !== numberId);
        setPhoneNumbers(remaining);
        setSelectedNumber(remaining.length > 0 ? remaining[0] : null);
      }
    } catch (error) {
      console.error('Error deleting number:', error);
    }
  };

  const startEditingNumber = () => {
    setEditingNumber(true);
    setTempNumberValue(selectedNumber.number);
  };

  const saveNumberEdit = async () => {
    if (tempNumberValue.trim()) {
      await handleUpdateNumber(selectedNumber.id, 'number', tempNumberValue);
      setEditingNumber(false);
    }
  };

  const cancelNumberEdit = () => {
    setEditingNumber(false);
    setTempNumberValue('');
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Phone Numbers</h1>
          <p className="text-gray-400">Manage phone number assignments</p>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Left Sidebar - Phone Numbers List */}
        <div className="w-80 bg-gray-800 border border-gray-700 rounded-lg">
          <div className="p-4 border-b border-gray-700 flex justify-between items-center">
            <h2 className="text-white font-semibold flex items-center gap-2">
              <Phone className="w-5 h-5" />
              Phone Numbers
            </h2>
            <button
              onClick={() => setShowAddModal(true)}
              className="p-1 hover:bg-gray-700 rounded"
              title="Add number"
            >
              <Plus className="w-5 h-5 text-gray-400" />
            </button>
          </div>
          
          <div className="overflow-y-auto max-h-[calc(100vh-250px)]">
            {loading ? (
              <div className="p-8 text-center text-gray-400">Loading...</div>
            ) : phoneNumbers.length === 0 ? (
              <div className="p-8 text-center">
                <Phone className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400 text-sm mb-4">No phone numbers</p>
                <button
                  onClick={() => setShowAddModal(true)}
                  className="text-blue-400 hover:text-blue-300 text-sm"
                >
                  Add your first number
                </button>
              </div>
            ) : (
              phoneNumbers.map((number) => (
                <button
                  key={number.id}
                  onClick={() => setSelectedNumber(number)}
                  className={`w-full text-left p-4 border-b border-gray-700 hover:bg-gray-750 transition-colors ${
                    selectedNumber?.id === number.id ? 'bg-gray-750 border-l-4 border-blue-500' : ''
                  }`}
                >
                  <div className="text-white font-medium">{number.number}</div>
                  <div className="text-sm text-gray-400 mt-1">
                    {number.inbound_agent_name || number.outbound_agent_name ? (
                      <>
                        {number.inbound_agent_name && <div>In: {number.inbound_agent_name}</div>}
                        {number.outbound_agent_name && <div>Out: {number.outbound_agent_name}</div>}
                      </>
                    ) : (
                      'No agents assigned'
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right Panel - Number Details */}
        <div className="flex-1 bg-gray-800 border border-gray-700 rounded-lg p-6">
          {selectedNumber ? (
            <div className="space-y-6">
              {/* Number Header with Edit */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Phone Number</label>
                <div className="flex items-center gap-3">
                  {editingNumber ? (
                    <>
                      <input
                        type="text"
                        value={tempNumberValue}
                        onChange={(e) => setTempNumberValue(e.target.value)}
                        className="flex-1 px-4 py-2 bg-gray-900 border border-gray-600 rounded text-white text-xl focus:outline-none focus:border-blue-500"
                      />
                      <button
                        onClick={saveNumberEdit}
                        className="p-2 bg-green-600 hover:bg-green-700 rounded text-white"
                      >
                        <Check className="w-5 h-5" />
                      </button>
                      <button
                        onClick={cancelNumberEdit}
                        className="p-2 bg-gray-600 hover:bg-gray-700 rounded text-white"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </>
                  ) : (
                    <>
                      <div className="flex-1 text-2xl font-bold text-white">{selectedNumber.number}</div>
                      <button
                        onClick={startEditingNumber}
                        className="p-2 hover:bg-gray-700 rounded text-gray-400"
                      >
                        <Edit2 className="w-5 h-5" />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Number Info */}
              <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
                <div className="text-sm text-gray-400">
                  <div className="flex items-center gap-2">
                    <span>ID: {selectedNumber.id}</span>
                    <button
                      onClick={() => navigator.clipboard.writeText(selectedNumber.id)}
                      className="text-blue-400 hover:text-blue-300"
                      title="Copy ID"
                    >
                      📋
                    </button>
                  </div>
                  <div className="mt-1">Provider: Custom telephony</div>
                </div>
              </div>

              {/* Inbound Agent Assignment */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Inbound call agent
                </label>
                <select
                  value={selectedNumber.inbound_agent_id || ''}
                  onChange={(e) => handleUpdateNumber(selectedNumber.id, 'inbound_agent_id', e.target.value || null)}
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">None (disable inbound)</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Outbound Agent Assignment */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Outbound call agent
                </label>
                <select
                  value={selectedNumber.outbound_agent_id || ''}
                  onChange={(e) => handleUpdateNumber(selectedNumber.id, 'outbound_agent_id', e.target.value || null)}
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">None (disable outbound)</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Advanced Add-Ons */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Advanced Add-Ons</h3>
                <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium text-white">SMS</div>
                      <div className="text-sm text-gray-400 mt-1">The ability to send SMS</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Delete Button */}
              <div className="pt-4 border-t border-gray-700">
                <button
                  onClick={() => handleDeleteNumber(selectedNumber.id)}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600/10 hover:bg-red-600/20 text-red-400 rounded-lg border border-red-600/30 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Phone Number
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <Phone className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Select a phone number to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Number Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-4">Add Phone Number</h2>
            <input
              type="text"
              value={newNumber}
              onChange={(e) => setNewNumber(e.target.value)}
              placeholder="+1 (555) 123-4567"
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded text-white mb-4 focus:outline-none focus:border-blue-500"
              onKeyPress={(e) => e.key === 'Enter' && handleAddNumber()}
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setNewNumber('');
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleAddNumber}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
              >
                Add Number
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PhoneNumbers;
