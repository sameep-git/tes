import { FC } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import ChatPanel from './chat-panel';

export default function Dashboard() {
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Left Side: Data Dashboard */}
      <div className="flex-1 flex flex-col min-w-0 border-r border-gray-200">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">TES System</h1>
            <p className="text-sm text-gray-500">TCU Econ Scheduler</p>
          </div>
          <div className="flex items-center space-x-4 text-sm font-medium">
            <span className="text-gray-500 flex items-center gap-1">
              <Clock className="w-4 h-4" /> Next Term: Fall 2025
            </span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Tabs defaultValue="inbox" className="w-full h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-4 max-w-2xl mb-6">
              <TabsTrigger value="inbox">Preferences Inbox</TabsTrigger>
              <TabsTrigger value="professors">Professors</TabsTrigger>
              <TabsTrigger value="courses">Courses</TabsTrigger>
              <TabsTrigger value="schedules">Schedules</TabsTrigger>
            </TabsList>

            {/* Inbox Tab Placeholder */}
            <TabsContent value="inbox" className="flex-1 mt-0">
              <Card>
                <CardHeader>
                  <CardTitle>Preference Inbox</CardTitle>
                  <CardDescription>Review and approve professor requests before running the solver.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 p-4 mb-4 bg-amber-50 text-amber-900 border border-amber-200 rounded-lg">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <div>
                      <p className="font-medium">Pre-flight Blocked</p>
                      <p className="text-sm opacity-90">1 professor has not submitted preferences yet.</p>
                    </div>
                  </div>
                  
                  {/* Placeholder table - we will wire this to FastAPI soon */}
                  <div className="border rounded-md">
                    <table className="w-full text-sm text-left">
                      <thead className="text-xs text-gray-700 bg-gray-50 uppercase border-b">
                        <tr>
                          <th className="px-6 py-3">Professor</th>
                          <th className="px-6 py-3">Status</th>
                          <th className="px-6 py-3">Confidence</th>
                          <th className="px-6 py-3 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b bg-white">
                          <td className="px-6 py-4 font-medium">Prof. Shah</td>
                          <td className="px-6 py-4"><Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Approved</Badge></td>
                          <td className="px-6 py-4">90%</td>
                          <td className="px-6 py-4 text-right"><span className="text-blue-600 hover:underline cursor-pointer">View</span></td>
                        </tr>
                        <tr className="bg-gray-50 text-gray-500">
                          <td className="px-6 py-4 font-medium">Dr. Smith</td>
                          <td className="px-6 py-4"><Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Missing</Badge></td>
                          <td className="px-6 py-4">-</td>
                          <td className="px-6 py-4 text-right"><span className="text-blue-600 hover:underline cursor-pointer">Follow Up</span></td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Other tabs placeholders */}
            <TabsContent value="professors">
              <Card><CardHeader><CardTitle>Faculty Roster</CardTitle></CardHeader></Card>
            </TabsContent>
            <TabsContent value="courses">
              <Card><CardHeader><CardTitle>Course Catalog</CardTitle></CardHeader></Card>
            </TabsContent>
            <TabsContent value="schedules">
              <Card><CardHeader><CardTitle>Generated Schedules</CardTitle></CardHeader></Card>
            </TabsContent>
          </Tabs>
        </main>
      </div>

      {/* Right Side: AI Agent Chat */}
      <div className="w-[450px] flex-shrink-0 bg-white shadow-xl z-10 flex flex-col">
        <ChatPanel />
      </div>
    </div>
  );
}