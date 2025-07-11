import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [botStatus, setBotStatus] = useState(null);
  const [servers, setServers] = useState([]);
  const [commands, setCommands] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    fetchBotStatus();
    fetchServers();
    fetchCommands();
    fetchLogs();
  }, []);

  const fetchBotStatus = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/bot/status`);
      const data = await response.json();
      setBotStatus(data);
    } catch (error) {
      console.error('Error fetching bot status:', error);
    }
  };

  const fetchServers = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/servers`);
      const data = await response.json();
      setServers(data.servers || []);
    } catch (error) {
      console.error('Error fetching servers:', error);
    }
  };

  const fetchCommands = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/commands`);
      const data = await response.json();
      setCommands(data.commands || []);
    } catch (error) {
      console.error('Error fetching commands:', error);
    }
  };

  const fetchLogs = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/logs`);
      const data = await response.json();
      setLogs(data.logs || []);
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  };

  const toggleBot = async (action) => {
    setLoading(true);
    try {
      const response = await fetch(`${backendUrl}/api/bot/${action}`, {
        method: 'POST',
      });
      const data = await response.json();
      
      // Wait a moment then refresh status
      setTimeout(() => {
        fetchBotStatus();
        setLoading(false);
      }, 2000);
    } catch (error) {
      console.error(`Error ${action}ing bot:`, error);
      setLoading(false);
    }
  };

  const filteredCommands = selectedCategory === 'all' 
    ? commands 
    : commands.filter(cmd => cmd.category === selectedCategory);

  const getUniqueCategories = () => {
    const categories = [...new Set(commands.map(cmd => cmd.category))];
    return categories.sort();
  };

  const StatusBadge = ({ status }) => (
    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
      status === 'running' 
        ? 'bg-green-100 text-green-800' 
        : 'bg-red-100 text-red-800'
    }`}>
      {status === 'running' ? '🟢 Online' : '🔴 Offline'}
    </span>
  );

  const CategoryBadge = ({ category }) => {
    const colors = {
      moderation: 'bg-red-100 text-red-800',
      server: 'bg-blue-100 text-blue-800',
      roles: 'bg-purple-100 text-purple-800',
      channels: 'bg-green-100 text-green-800',
      users: 'bg-yellow-100 text-yellow-800',
      utility: 'bg-gray-100 text-gray-800',
      fun: 'bg-pink-100 text-pink-800',
      economy: 'bg-indigo-100 text-indigo-800',
      logging: 'bg-orange-100 text-orange-800',
      automod: 'bg-cyan-100 text-cyan-800',
      advanced: 'bg-teal-100 text-teal-800'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[category] || 'bg-gray-100 text-gray-800'}`}>
        {category}
      </span>
    );
  };

  const DashboardTab = () => (
    <div className="space-y-6">
      {/* Bot Status Card */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-blue-500">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-2xl font-bold text-gray-800 mb-2">Discord Bot Status</h3>
            <div className="flex items-center space-x-4 mb-4">
              <StatusBadge status={botStatus?.status || 'stopped'} />
              <span className="text-gray-600">
                {botStatus?.servers || 0} servers connected
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-blue-600">
              {botStatus?.commands_executed || 0}
            </div>
            <div className="text-sm text-gray-500">Commands Executed</div>
          </div>
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={() => toggleBot('start')}
            disabled={loading || botStatus?.status === 'running'}
            className="bg-green-500 hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {loading ? 'Starting...' : 'Start Bot'}
          </button>
          <button
            onClick={() => toggleBot('stop')}
            disabled={loading || botStatus?.status === 'stopped'}
            className="bg-red-500 hover:bg-red-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {loading ? 'Stopping...' : 'Stop Bot'}
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-lg p-6 text-center">
          <div className="text-3xl font-bold text-blue-600 mb-2">
            {commands.length}
          </div>
          <div className="text-gray-600">Total Commands</div>
        </div>
        
        <div className="bg-white rounded-xl shadow-lg p-6 text-center">
          <div className="text-3xl font-bold text-green-600 mb-2">
            {servers.length}
          </div>
          <div className="text-gray-600">Active Servers</div>
        </div>
        
        <div className="bg-white rounded-xl shadow-lg p-6 text-center">
          <div className="text-3xl font-bold text-purple-600 mb-2">
            {getUniqueCategories().length}
          </div>
          <div className="text-gray-600">Command Categories</div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {logs.slice(0, 5).map((log, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${log.success ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="font-medium text-gray-800">{log.command_name}</span>
                <span className="text-sm text-gray-500">by User {log.user_id}</span>
              </div>
              <span className="text-xs text-gray-400">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const CommandsTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-2xl font-bold text-gray-800">
            Available Commands ({filteredCommands.length})
          </h3>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Categories</option>
            {getUniqueCategories().map(category => (
              <option key={category} value={category}>
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCommands.map((command, index) => (
            <div key={index} className="bg-gray-50 rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-gray-800">!{command.name}</h4>
                <CategoryBadge category={command.category} />
              </div>
              <p className="text-sm text-gray-600">{command.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const ServersTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-2xl font-bold text-gray-800 mb-6">
          Connected Servers ({servers.length})
        </h3>
        
        {servers.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">🏢</div>
            <h4 className="text-xl font-semibold text-gray-600 mb-2">No Servers Connected</h4>
            <p className="text-gray-500">
              Once your bot joins servers, they will appear here.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {servers.map((server, index) => (
              <div key={index} className="bg-gray-50 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-gray-800">{server.server_name}</h4>
                  <span className="text-xs text-gray-500">ID: {server.server_id}</span>
                </div>
                <div className="text-sm text-gray-600 mb-2">
                  Prefix: <code className="bg-gray-200 px-1 rounded">{server.prefix}</code>
                </div>
                <div className="text-xs text-gray-500">
                  Added: {new Date(server.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const LogsTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-2xl font-bold text-gray-800 mb-6">
          Command Logs ({logs.length})
        </h3>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-800">Status</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-800">Command</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-800">User</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-800">Server</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-800">Time</th>
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 20).map((log, index) => (
                <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <span className={`w-3 h-3 rounded-full inline-block ${log.success ? 'bg-green-500' : 'bg-red-500'}`}></span>
                  </td>
                  <td className="py-3 px-4 font-medium text-gray-800">{log.command_name}</td>
                  <td className="py-3 px-4 text-gray-600">{log.user_id}</td>
                  <td className="py-3 px-4 text-gray-600">{log.server_id}</td>
                  <td className="py-3 px-4 text-gray-500">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="text-2xl">🤖</div>
              <h1 className="text-2xl font-bold text-gray-900">Discord Bot Manager</h1>
            </div>
            <div className="flex items-center space-x-4">
              <StatusBadge status={botStatus?.status || 'stopped'} />
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: '📊' },
              { id: 'commands', label: 'Commands', icon: '⚡' },
              { id: 'servers', label: 'Servers', icon: '🏢' },
              { id: 'logs', label: 'Logs', icon: '📋' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && <DashboardTab />}
        {activeTab === 'commands' && <CommandsTab />}
        {activeTab === 'servers' && <ServersTab />}
        {activeTab === 'logs' && <LogsTab />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">
              Discord Bot Manager - Managing 100+ server commands
            </div>
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <span>Bot ID: 1162053379313381528</span>
              <span>•</span>
              <span>Total Commands: {commands.length}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;