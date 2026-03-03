'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import { AlertCircle, CheckCircle2, Clock, Eye, Loader2 } from 'lucide-react';
import ChatPanel from './chat-panel';
import {
  queryKeys,
  fetchProfessors,
  fetchCourses,
  fetchSchedules,
  fetchPreferences,
  approvePreference,
  type Professor,
  type Course,
  type Schedule,
  type Preference,
} from '@/lib/api';

// ---- Preference Detail Dialog ----
function PreferenceDetailDialog({
  pref,
  onClose,
}: {
  pref: Preference | null;
  onClose: () => void;
}) {
  if (!pref) return null;

  const profName = pref.professor?.name ?? `Prof #${pref.professor_id}`;
  const parsed = pref.parsed_json as Record<string, unknown> | null;

  const Field = ({ label, value }: { label: string; value: unknown }) => {
    if (value === null || value === undefined) return null;
    if (Array.isArray(value) && value.length === 0) return null;
    return (
      <div className="flex gap-3 py-1.5 border-b border-gray-100 last:border-0">
        <span className="w-44 flex-shrink-0 text-xs font-medium text-gray-500 uppercase tracking-wide">
          {label}
        </span>
        <span className="text-sm text-gray-900 break-words">
          {Array.isArray(value) ? value.join(', ') : String(value)}
        </span>
      </div>
    );
  };

  return (
    <Dialog open={!!pref} onOpenChange={open => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg">{profName} — Preference</DialogTitle>
          <DialogDescription>
            {pref.semester} {pref.year} &middot;{' '}
            {pref.admin_approved ? (
              <span className="text-green-600 font-medium">Approved</span>
            ) : (
              <span className="text-amber-600 font-medium">Pending approval</span>
            )}
            {pref.confidence != null && (
              <> &middot; Confidence: {Math.round(pref.confidence * 100)}%</>
            )}
          </DialogDescription>
        </DialogHeader>

        {parsed ? (
          <div className="mt-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Extracted Preferences</h3>
            <div className="bg-gray-50 rounded-lg px-4 py-2 border border-gray-200">
              <Field label="Requested Load" value={parsed.requested_load} />
              <Field label="Max Load" value={parsed.max_load} />
              <Field label="Preferred Courses" value={parsed.preferred_courses} />
              <Field label="Avoid Courses" value={parsed.avoid_courses} />
              <Field label="Preferred Levels" value={parsed.preferred_levels} />
              <Field label="Preferred Timeslots" value={parsed.preferred_timeslots} />
              <Field label="Avoid Timeslots" value={parsed.avoid_timeslots} />
              <Field label="Avoid Days" value={parsed.avoid_days} />
              <Field label="Back-to-Back" value={
                parsed.wants_back_to_back === true ? 'Prefers back-to-back'
                  : parsed.wants_back_to_back === false ? 'Avoid back-to-back'
                    : null
              } />
              <Field label="On Leave" value={parsed.on_leave === true ? '⚠️ On Leave' : null} />
              <Field label="Notes for Admin" value={parsed.notes_for_admin} />
            </div>
          </div>
        ) : (
          <div className="mt-4 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
            ⚠️ No parsed JSON yet. Ask the TES Agent to run{' '}
            <code className="font-mono text-xs">extract_and_save_preference_json({pref.id})</code>.
          </div>
        )}

        {pref.raw_email && (
          <div className="mt-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Raw Email</h3>
            <pre className="bg-gray-900 text-gray-100 text-xs rounded-lg p-4 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
              {pref.raw_email}
            </pre>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ---- Main Dashboard ----
export default function Dashboard() {
  const queryClient = useQueryClient();
  const [viewingPref, setViewingPref] = useState<Preference | null>(null);

  // ---- TanStack Query hooks — each tab has its own independent loading state ----
  const { data: professors = [], isLoading: profsLoading } = useQuery({ queryKey: queryKeys.professors, queryFn: fetchProfessors });
  const { data: courses = [], isLoading: coursesLoading } = useQuery({ queryKey: queryKeys.courses, queryFn: fetchCourses });
  const { data: schedules = [], isLoading: schedsLoading } = useQuery({ queryKey: queryKeys.schedules, queryFn: fetchSchedules });
  const { data: preferences = [], isLoading: prefsLoading } = useQuery({ queryKey: queryKeys.preferences, queryFn: fetchPreferences });

  // ---- Mutation: approve preference ----
  const approveMutation = useMutation({
    mutationFn: approvePreference,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.preferences });
    },
  });

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
      {/* Preference Detail Dialog */}
      <PreferenceDetailDialog pref={viewingPref} onClose={() => setViewingPref(null)} />

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
                  {prefsLoading ? (
                    <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
                  ) : preferences.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <p className="text-lg font-medium">No preferences received yet</p>
                      <p className="text-sm mt-1">Preference emails from professors will appear here once polled.</p>
                    </div>
                  ) : (
                    <div className="border rounded-md">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Professor</TableHead>
                            <TableHead>Semester</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Confidence</TableHead>
                            <TableHead>Received</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
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
                                <div className="flex items-center justify-end gap-2">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                                    onClick={() => setViewingPref(pref)}
                                  >
                                    <Eye className="w-3.5 h-3.5 mr-1" />
                                    View
                                  </Button>
                                  {!pref.admin_approved && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="text-green-700 border-green-300 hover:bg-green-50"
                                      disabled={approveMutation.isPending}
                                      onClick={() => approveMutation.mutate(pref.id)}
                                    >
                                      {approveMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                                      Approve
                                    </Button>
                                  )}
                                </div>
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
                  {profsLoading ? (
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
                  {coursesLoading ? (
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
                  {schedsLoading ? (
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

      {/* Right Side: AI Agent Chat — no more onDone prop needed */}
      <div className="w-[450px] flex-shrink-0 bg-white shadow-xl z-10 flex flex-col overflow-hidden">
        <ChatPanel />
      </div>
    </div>
  );
}