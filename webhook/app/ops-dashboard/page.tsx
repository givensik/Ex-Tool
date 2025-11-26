'use client';

import { useEffect, useState } from 'react';

type Log = {
    id: number;
    method: string;
    path: string;
    headers: string;
    queryParams: string;
    body: string | null;
    ip: string | null;
    createdAt: string;
};

export default function Dashboard() {
    const [logs, setLogs] = useState<Log[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchLogs = async () => {
        try {
            const res = await fetch('/api/logs');
            if (res.ok) {
                const data = await res.json();
                setLogs(data);
            }
        } catch (error) {
            console.error('Failed to fetch logs', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
        const interval = setInterval(fetchLogs, 2000); // Poll every 2 seconds
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <h1 className="text-3xl font-bold mb-6 text-red-500">🚨 OOB Interaction Logs</h1>

            {loading && logs.length === 0 ? (
                <p>Loading...</p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-gray-700 text-gray-400">
                                <th className="p-3">Time</th>
                                <th className="p-3">Method</th>
                                <th className="p-3">Path</th>
                                <th className="p-3">IP</th>
                                <th className="p-3">Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.map((log) => (
                                <tr key={log.id} className="border-b border-gray-800 hover:bg-gray-800 font-mono text-sm">
                                    <td className="p-3 whitespace-nowrap">{new Date(log.createdAt).toLocaleString()}</td>
                                    <td className="p-3">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${log.method === 'GET' ? 'bg-blue-900 text-blue-200' :
                                                log.method === 'POST' ? 'bg-green-900 text-green-200' :
                                                    'bg-gray-700'
                                            }`}>
                                            {log.method}
                                        </span>
                                    </td>
                                    <td className="p-3 text-yellow-300">{log.path}</td>
                                    <td className="p-3 text-gray-400">{log.ip}</td>
                                    <td className="p-3">
                                        <details>
                                            <summary className="cursor-pointer text-blue-400 hover:text-blue-300">View Payload</summary>
                                            <div className="mt-2 p-2 bg-black rounded border border-gray-700 overflow-auto max-w-2xl">
                                                <p className="text-xs text-gray-500 mb-1">Query Params:</p>
                                                <pre className="text-xs text-green-400 mb-2">{JSON.stringify(JSON.parse(log.queryParams), null, 2)}</pre>

                                                <p className="text-xs text-gray-500 mb-1">Body:</p>
                                                <pre className="text-xs text-orange-400 mb-2">{log.body || '(empty)'}</pre>

                                                <p className="text-xs text-gray-500 mb-1">Headers:</p>
                                                <pre className="text-xs text-gray-400">{JSON.stringify(JSON.parse(log.headers), null, 2)}</pre>
                                            </div>
                                        </details>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {logs.length === 0 && (
                        <div className="text-center py-10 text-gray-500">No interactions captured yet. Waiting for prey... 🕷️</div>
                    )}
                </div>
            )}
        </div>
    );
}
