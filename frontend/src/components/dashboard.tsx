'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import ChatPanel from './chat-panel';

const API = 'http://localhost:8000/api';

interface Professor {
  id: number;
  name: string;
  email: string;
  office: string | null;
  rank: string;
  max_sections: number;
  active: boolean;
}

interface Course {
  id: number;
  code: string;
  name: string;
  credits: number;
  level: number;
  min_sections: number;
  max_sections: number;
  requires_lab: boolean;
  core_ssc: boolean;
  core_ht: boolean;
  core_ga: boolean;
  core_wem: boolean;
}

interface Section {
  id: number;
  course_code: string | null;
  course_name: string | null;
  professor_name: string | null;
  timeslot_label: string | null;
  status: string;
}

interface Schedule {
  id: number;
  semester: string;
  year: number;
  status: string;
  finalized_at: string | null;
  sections: Section[];
}

interface Preference {
  id: number;
  professor_id: number;
  semester: string;
  year: number;
  raw_email: string | null;
  parsed_json: Record<string, unknown> | null;
  confidence: number | null;
  admin_approved: boolean;
  received_at: string;
  professor: { id: number; name: string; email: string } | null;
}

export default function Dashboard() {
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [loading, setLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<number | null>(null);

  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      try {
        const [profRes, courseRes, schedRes, prefRes] = await Promise.all([
          fetch(`${API}/professors`),
          fetch(`${API}/courses`),
          fetch(`${API}/schedules`),
          fetch(`${API}/preferences`),
        ]);
        setProfessors(await profRes.json());
        setCourses(await courseRes.json());
        setSchedules(await schedRes.json());
        setPreferences(await prefRes.json());
      } catch (err) {
        console.error('Failed to fetch data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, []);

  const handleApprove = async (prefId: number) => {
    setApprovingId(prefId);
    try {
      const res = await fetch(`${API}/preferences/${prefId}/approve`, { method: 'PUT' });
      if (res.ok) {
        const updated = await res.json();
        setPreferences(prev => prev.map(p => (p.id === prefId ? updated : p)));
      }
    } catch (err) {
      console.error('Failed to approve:', err);
    } finally {
      setApprovingId(null);
    }
  };

  const pendingCount = preferences.filter(p => !p.admin_approved).length;

  function coreTags(course: Course) {
    const tags: string[] = [];
    if (course.core_ssc) tags.push('SSC');
    if (course.core_ht) tags.push('HT');
    if (course.core_ga) tags.push('GA');
    if (course.core_wem) tags.push('WEM');
    return tags;
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Left Side: Data Dashboard */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 border-r border-gray-200">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center flex-shrink-0">
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

        <main className="flex-1 overflow-y-auto p-6 min-h-0">
          <Tabs defaultValue="inbox" className="w-full h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-4 max-w-2xl mb-6 flex-shrink-0">
              <TabsTrigger value="inbox">
                Preferences Inbox
                {pendingCount > 0 && (
                  <span className="ml-1.5 bg-amber-500 text-white text-[10px] font-bold rounded-full w-5 h-5 inline-flex items-center justify-center">
                    {pendingCount}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="professors">Professors</TabsTrigger>
              <TabsTrigger value="courses">Courses</TabsTrigger>
              <TabsTrigger value="schedules">Schedules</TabsTrigger>
            </TabsList>

            {/* ========== Inbox Tab ========== */}
            <TabsContent value="inbox" className="flex-1 mt-0">
              <Card>
                <CardHeader>
                  <CardTitle>Preference Inbox</CardTitle>
                  <CardDescription>Review and approve professor requests before running the solver.</CardDescription>
                </CardHeader>
                <CardContent>
                  {pendingCount > 0 && (
                    <div className="flex items-center gap-4 p-4 mb-4 bg-amber-50 text-amber-900 border border-amber-200 rounded-lg">
                      <AlertCircle className="w-5 h-5 flex-shrink-0" />
                      <div>
                        <p className="font-medium">Pre-flight Blocked</p>
                        <p className="text-sm opacity-90">{pendingCount} preference(s) pending approval.</p>
                      </div>
                    </div>
                  )}
                  {!loading && preferences.length === 0 && (
                    <div className="text-center py-12 text-gray-400">
                      <p className="text-lg font-medium">No preferences received yet</p>
                      <p className="text-sm mt-1">Preference emails from professors will appear here once polled.</p>
                    </div>
                  )}
                  {preferences.length > 0 && (
                    <div className="border rounded-md">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Professor</TableHead>
                            <TableHead>Semester</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Confidence</TableHead>
                            <TableHead>Received</TableHead>
                            <TableHead className="text-right">Action</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {preferences.map(pref => (
                            <TableRow key={pref.id}>
                              <TableCell className="font-medium">{pref.professor?.name ?? `Prof #${pref.professor_id}`}</TableCell>
                              <TableCell>{pref.semester} {pref.year}</TableCell>
                              <TableCell>
                                {pref.admin_approved ? (
                                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                    <CheckCircle2 className="w-3 h-3 mr-1" /> Approved
                                  </Badge>
                                ) : (
                                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                                    Pending
                                  </Badge>
                                )}
                              </TableCell>
                              <TableCell>{pref.confidence != null ? `${Math.round(pref.confidence * 100)}%` : '—'}</TableCell>
                              <TableCell className="text-xs text-gray-500">{new Date(pref.received_at).toLocaleDateString()}</TableCell>
                              <TableCell className="text-right">
                                {!pref.admin_approved && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="text-green-700 border-green-300 hover:bg-green-50"
                                    disabled={approvingId === pref.id}
                                    onClick={() => handleApprove(pref.id)}
                                  >
                                    {approvingId === pref.id ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                                    Approve
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* ========== Professors Tab ========== */}
            <TabsContent value="professors" className="flex-1 mt-0">
              <Card>
                <CardHeader>
                  <CardTitle>Faculty Roster</CardTitle>
                  <CardDescription>{professors.length} professors in the system</CardDescription>
                </CardHeader>
                <CardContent>
                  {loading ? (
                    <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
                  ) : (
                    <div className="border rounded-md">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead>Office</TableHead>
                            <TableHead>Rank</TableHead>
                            <TableHead>Max Sections</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {professors.map(prof => (
                            <TableRow key={prof.id}>
                              <TableCell className="font-medium">{prof.name}</TableCell>
                              <TableCell className="text-gray-500">{prof.email}</TableCell>
                              <TableCell>{prof.office ?? '—'}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className={
                                  prof.rank === 'Tenured' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                                    prof.rank === 'Tenure-Track' ? 'bg-indigo-50 text-indigo-700 border-indigo-200' :
                                      prof.rank === 'Visiting' ? 'bg-purple-50 text-purple-700 border-purple-200' :
                                        'bg-gray-50 text-gray-700 border-gray-200'
                                }>
                                  {prof.rank}
                                </Badge>
                              </TableCell>
                              <TableCell>{prof.max_sections}</TableCell>
                              <TableCell>
                                <span className={`inline-flex items-center gap-1 text-xs font-medium ${prof.active ? 'text-green-600' : 'text-gray-400'}`}>
                                  <span className={`w-1.5 h-1.5 rounded-full ${prof.active ? 'bg-green-500' : 'bg-gray-300'}`} />
                                  {prof.active ? 'Active' : 'Inactive'}
                                </span>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* ========== Courses Tab ========== */}
            <TabsContent value="courses" className="flex-1 mt-0">
              <Card>
                <CardHeader>
                  <CardTitle>Course Catalog</CardTitle>
                  <CardDescription>{courses.length} courses in the system</CardDescription>
                </CardHeader>
                <CardContent>
                  {loading ? (
                    <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
                  ) : (
                    <div className="border rounded-md">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Code</TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead>Level</TableHead>
                            <TableHead>Credits</TableHead>
                            <TableHead>Sections</TableHead>
                            <TableHead>Core</TableHead>
                            <TableHead>Lab</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {courses.map(course => (
                            <TableRow key={course.id}>
                              <TableCell className="font-medium font-mono">{course.code}</TableCell>
                              <TableCell>{course.name}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className={
                                  course.level >= 400 ? 'bg-red-50 text-red-700 border-red-200' :
                                    course.level >= 300 ? 'bg-orange-50 text-orange-700 border-orange-200' :
                                      'bg-green-50 text-green-700 border-green-200'
                                }>
                                  {course.level}
                                </Badge>
                              </TableCell>
                              <TableCell>{course.credits}</TableCell>
                              <TableCell className="text-gray-500">{course.min_sections}–{course.max_sections}</TableCell>
                              <TableCell>
                                <div className="flex gap-1">
                                  {coreTags(course).map(tag => (
                                    <Badge key={tag} variant="outline" className="text-[10px] px-1.5 py-0 bg-indigo-50 text-indigo-600 border-indigo-200">{tag}</Badge>
                                  ))}
                                  {coreTags(course).length === 0 && <span className="text-gray-300">—</span>}
                                </div>
                              </TableCell>
                              <TableCell>{course.requires_lab ? '✓' : ''}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* ========== Schedules Tab ========== */}
            <TabsContent value="schedules" className="flex-1 mt-0">
              <Card>
                <CardHeader>
                  <CardTitle>Generated Schedules</CardTitle>
                  <CardDescription>{schedules.length} schedule(s) in the system</CardDescription>
                </CardHeader>
                <CardContent>
                  {loading ? (
                    <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
                  ) : schedules.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <p className="text-lg font-medium">No schedules generated yet</p>
                      <p className="text-sm mt-1">Ask the TES Agent to run the solver to generate a schedule.</p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {schedules.map(sched => (
                        <div key={sched.id} className="border rounded-lg overflow-hidden">
                          <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-b">
                            <div className="flex items-center gap-3">
                              <span className="font-semibold text-gray-900">{sched.semester} {sched.year}</span>
                              <Badge variant="outline" className={
                                sched.status === 'Finalized' ? 'bg-green-50 text-green-700 border-green-200' :
                                  'bg-amber-50 text-amber-700 border-amber-200'
                              }>
                                {sched.status}
                              </Badge>
                            </div>
                            <span className="text-xs text-gray-400">{sched.sections.length} section(s)</span>
                          </div>
                          {sched.sections.length > 0 && (
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Course</TableHead>
                                  <TableHead>Professor</TableHead>
                                  <TableHead>Time Slot</TableHead>
                                  <TableHead>Status</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {sched.sections.map(sec => (
                                  <TableRow key={sec.id}>
                                    <TableCell className="font-medium">{sec.course_code} — {sec.course_name}</TableCell>
                                    <TableCell>{sec.professor_name ?? <span className="text-gray-300">Unassigned</span>}</TableCell>
                                    <TableCell>{sec.timeslot_label ?? <span className="text-gray-300">TBD</span>}</TableCell>
                                    <TableCell>
                                      <Badge variant="outline" className="text-xs">{sec.status}</Badge>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </main>
      </div>

      {/* Right Side: AI Agent Chat */}
      <div className="w-[450px] flex-shrink-0 bg-white shadow-xl z-10 flex flex-col overflow-hidden">
        <ChatPanel />
      </div>
    </div>
  );
}