import Link from 'next/link';
import { Home, BarChart2, MessageSquare, Settings } from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 text-gray-300 flex flex-col h-screen fixed">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-white tracking-wider flex items-center gap-2">
          <span className="bg-blue-600 p-1.5 rounded-lg text-white">
            <BarChart2 size={24} />
          </span>
          HERMES
        </h1>
      </div>
      <nav className="flex-1 px-4 space-y-2 mt-4">
        <Link href="/" className="flex items-center gap-3 px-4 py-3 bg-gray-800 text-white rounded-xl transition-colors">
          <Home size={20} />
          Overview
        </Link>
        <Link href="/opportunities" className="flex items-center gap-3 px-4 py-3 hover:bg-gray-800 rounded-xl transition-colors">
          <BarChart2 size={20} />
          Opportunities
        </Link>
        <Link href="/ai-chat" className="flex items-center gap-3 px-4 py-3 hover:bg-gray-800 rounded-xl transition-colors">
          <MessageSquare size={20} />
          AI Assistant
        </Link>
        <Link href="/settings" className="flex items-center gap-3 px-4 py-3 hover:bg-gray-800 rounded-xl transition-colors">
          <Settings size={20} />
          Settings
        </Link>
      </nav>
      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-500 text-center">Hermes AI Dashboard v1.0</div>
      </div>
    </aside>
  );
}
