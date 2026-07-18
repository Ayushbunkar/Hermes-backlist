'use client';
import { useEffect, useState } from 'react';
import { Globe, Plus, AlertCircle, Link as LinkIcon, Tag } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState('');
  const [niche, setNiche] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [adding, setAdding] = useState(false);

  const fetchProjects = async () => {
    try {
      const res = await fetch('/api/projects');
      const data = await res.json();
      setProjects(data.data || []);
      setLoading(false);
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !niche) return;
    
    setAdding(true);
    setMessage('');
    setError('');

    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, niche })
      });
      const data = await res.json();

      if (res.ok) {
        setMessage('Project added successfully! The orchestrator will begin scanning shortly.');
        setUrl('');
        setNiche('');
        fetchProjects(); // refresh list
      } else {
        setError(data.error || 'Failed to add project');
      }
    } catch (e: any) {
      setError(e.message);
    }
    setAdding(false);
  };

  const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
  const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
          <Globe className="text-blue-500" size={28} />
          Projects Management
        </h1>
        <p className="text-gray-400">Add websites for Hermes to scan and discover backlink opportunities.</p>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-white mb-4">Track New Project</h2>
        
        {message && (
          <div className="mb-4 bg-green-900/30 border border-green-800 text-green-400 px-4 py-3 rounded-lg flex items-center gap-2">
            <AlertCircle size={18} /> {message}
          </div>
        )}
        
        {error && (
          <div className="mb-4 bg-red-900/30 border border-red-800 text-red-400 px-4 py-3 rounded-lg flex items-center gap-2">
            <AlertCircle size={18} /> {error}
          </div>
        )}

        <form onSubmit={handleAdd} className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
            <input 
              type="url"
              required
              placeholder="https://yourwebsite.com"
              value={url}
              onChange={e => setUrl(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 text-white pl-10 pr-4 py-3 rounded-xl focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          <div className="flex-1 relative">
            <Tag className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
            <input 
              type="text"
              required
              placeholder="Project Niche (e.g. AI Tools, SaaS)"
              value={niche}
              onChange={e => setNiche(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 text-white pl-10 pr-4 py-3 rounded-xl focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          <button 
            type="submit" 
            disabled={adding}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white px-6 py-3 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors min-w-[140px]"
          >
            {adding ? 'Adding...' : <><Plus size={20} /> Add Project</>}
          </button>
        </form>
      </div>

      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Active Projects</h2>
        
        <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-400">
              <thead className="bg-gray-950/50 text-gray-300 uppercase font-medium">
                <tr>
                  <th className="px-6 py-4">URL</th>
                  <th className="px-6 py-4">Niche</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Added On</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={4} className="text-center py-8">Loading projects...</td></tr>
                ) : projects.length === 0 ? (
                  <tr><td colSpan={4} className="text-center py-8 text-gray-500">No projects found. Add one above!</td></tr>
                ) : (
                  projects.map((proj) => (
                    <tr key={proj.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                      <td className="px-6 py-4">
                        <span className="font-medium text-white block">{proj.project_url}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-gray-800 px-3 py-1 rounded-full text-xs text-blue-400 border border-gray-700">
                          {proj.niche}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-green-400 text-xs flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                          Active
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {new Date(proj.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
