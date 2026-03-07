'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { AlertCircle, CheckCircle2, Clock, Eye, History, Loader2, Save, X, Plus, ChevronDown } from 'lucide-react';
import ChatPanel from './chat-panel';
import { CourseHistoryDialog } from './course-history-dialog';
import {
  queryKeys,
  fetchProfessors,
  fetchCourses,
  fetchSchedules,
  fetchPreferences,
  fetchTimeslots,
  approvePreference,
  updatePreferenceParsedJson,
  type Professor,
  type Course,
  type Schedule,
  type TimeSlot,
  type Preference,
} from '@/lib/api';

// ---------------------------------------------------------------------------
// Semester options
// ---------------------------------------------------------------------------
const SEMESTERS = ['Fall', 'Spring', 'Summer'] as const;
const currentYear = new Date().getFullYear();
const YEARS = [currentYear + 1, currentYear, currentYear - 1];

function defaultSemester(): { semester: string; year: number } {
  const month = new Date().getMonth(); // 0-indexed
  // If after August → target next Spring; otherwise target next Fall
  if (month >= 8) return { semester: 'Spring', year: currentYear + 1 };
  if (month >= 3) return { semester: 'Fall', year: currentYear };
  return { semester: 'Spring', year: currentYear };
}

// ---------------------------------------------------------------------------
// Multi-select chip component (for courses, timeslots, etc.)
// ---------------------------------------------------------------------------
function ChipSelect({
  selected,
  options,
  onChange,
}: {
  selected: string[];
  options: { value: string; label: string }[];
  onChange: (val: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const available = options.filter(o => !selected.includes(o.value));

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1.5">
        {selected.map(v => {
          const opt = options.find(o => o.value === v);
          return (
            <Badge key={v} variant="outline" className="text-xs gap-1 pr-1">
              {opt?.label ?? v}
              <button
                type="button"
                className="ml-0.5 hover:text-red-500 transition-colors"
                onClick={() => onChange(selected.filter(s => s !== v))}
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          );
        })}
      </div>
      {available.length > 0 && (
        <div className="relative">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="text-xs h-7 gap-1"
            onClick={() => setOpen(!open)}
          >
            <Plus className="w-3 h-3" /> Add <ChevronDown className="w-3 h-3" />
          </Button>
          {open && (
            <div className="absolute z-50 mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-48 overflow-y-auto w-72">
              {available.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  className="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50 transition-colors"
                  onClick={() => {
                    onChange([...selected, opt.value]);
                    setOpen(false);
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Day toggle chips
// ---------------------------------------------------------------------------
const ALL_DAYS = ['M', 'T', 'W', 'R', 'F'] as const;

function DayToggle({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (val: string[]) => void;
}) {
  return (
    <div className="flex gap-1.5">
      {ALL_DAYS.map(day => {
        const active = selected.includes(day);
        return (
          <button
            key={day}
            type="button"
            className={`w-8 h-8 rounded-full text-xs font-semibold border transition-all ${active
              ? 'bg-red-100 text-red-700 border-red-300'
              : 'bg-gray-50 text-gray-400 border-gray-200 hover:bg-gray-100'
              }`}
            onClick={() =>
              onChange(active ? selected.filter(d => d !== day) : [...selected, day])
            }
          >
            {day}
          </button>
        );
      })}
    </div>
  );
}

const ReadonlyField = ({
  label,
  value,
}: {
  label: string;
  value: string | string[] | undefined | null;
}) => {
  if (value == null || (Array.isArray(value) && value.length === 0)) return null;
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

const EditableField = ({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) => (
  <div className="flex gap-3 py-2 border-b border-gray-100 last:border-0 items-start">
    <span className="w-44 flex-shrink-0 text-xs font-medium text-gray-500 uppercase tracking-wide pt-1">
      {label}
    </span>
    <div className="flex-1">{children}</div>
  </div>
);

// ---------------------------------------------------------------------------
// Editable Preference Detail Dialog
// ---------------------------------------------------------------------------
function PreferenceDetailDialog({
  pref,
  courses,
  timeslots,
  onClose,
  onSave,
  isSaving,
}: {
  pref: Preference | null;
  courses: Course[];
  timeslots: TimeSlot[];
  onClose: () => void;
  onSave: (prefId: number, parsed: Record<string, unknown>) => void;
  isSaving: boolean;
}) {
  const [editMode, setEditMode] = useState(false);
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  // Reset draft when pref changes

  useEffect(() => {
    if (pref?.parsed_json) {
      setDraft({ ...pref.parsed_json });
      setEditMode(false);
    }
  }, [pref?.parsed_json]);

  if (!pref) return null;

  const profName = pref.professor?.name ?? `Prof #${pref.professor_id}`;
  const parsed = editMode ? draft : (pref.parsed_json as Record<string, unknown> | null);

  const courseOptions = courses.map(c => ({ value: `${c.code} | ${c.name}`, label: `${c.code} — ${c.name}` }));
  const timeslotOptions = timeslots
    .filter(t => t.active)
    .map(t => ({ value: t.label, label: t.label }));

  const updateDraft = (key: string, value: unknown) => {
    setDraft(prev => ({ ...prev, [key]: value }));
  };

  return (
    <Dialog open={!!pref} onOpenChange={open => !open && onClose()}>
      <DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg">{profName} — Preference</DialogTitle>
          <DialogDescription>
            {pref.semester ? pref.semester.charAt(0).toUpperCase() + pref.semester.slice(1) : ''} {pref.year} &middot;{' '}
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
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">
                {editMode ? 'Editing Preferences' : 'Extracted Preferences'}
              </h3>
              {!editMode && (
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs h-7"
                  onClick={() => {
                    setDraft({ ...pref.parsed_json! });
                    setEditMode(true);
                  }}
                >
                  Edit
                </Button>
              )}
            </div>

            {editMode ? (
              <div className="bg-gray-50 rounded-lg px-4 py-2 border border-gray-200 space-y-1">
                <EditableField label="Requested Load">
                  <Input
                    type="number"
                    className="h-8 w-24 text-sm"
                    value={String(draft.requested_load ?? '')}
                    onChange={e => updateDraft('requested_load', e.target.value ? Number(e.target.value) : null)}
                  />
                </EditableField>
                <EditableField label="Max Load">
                  <Input
                    type="number"
                    className="h-8 w-24 text-sm"
                    value={String(draft.max_load ?? '')}
                    onChange={e => updateDraft('max_load', e.target.value ? Number(e.target.value) : null)}
                  />
                </EditableField>
                <EditableField label="Preferred Courses">
                  <ChipSelect
                    selected={(draft.preferred_courses as string[]) ?? []}
                    options={courseOptions}
                    onChange={val => updateDraft('preferred_courses', val)}
                  />
                </EditableField>
                <EditableField label="Avoid Courses">
                  <ChipSelect
                    selected={(draft.avoid_courses as string[]) ?? []}
                    options={courseOptions}
                    onChange={val => updateDraft('avoid_courses', val)}
                  />
                </EditableField>
                <EditableField label="Preferred Timeslots">
                  <ChipSelect
                    selected={(draft.preferred_timeslots as string[]) ?? []}
                    options={timeslotOptions}
                    onChange={val => updateDraft('preferred_timeslots', val)}
                  />
                </EditableField>
                <EditableField label="Avoid Timeslots">
                  <ChipSelect
                    selected={(draft.avoid_timeslots as string[]) ?? []}
                    options={timeslotOptions}
                    onChange={val => updateDraft('avoid_timeslots', val)}
                  />
                </EditableField>
                <EditableField label="Avoid Days">
                  <DayToggle
                    selected={(draft.avoid_days as string[]) ?? []}
                    onChange={val => updateDraft('avoid_days', val)}
                  />
                </EditableField>
                <EditableField label="Back-to-Back">
                  <div className="flex gap-2">
                    {(['Prefers', 'Avoid', 'No preference'] as const).map(opt => {
                      const val = opt === 'Prefers' ? true : opt === 'Avoid' ? false : null;
                      const active = draft.wants_back_to_back === val;
                      return (
                        <button
                          key={opt}
                          type="button"
                          className={`px-3 py-1 rounded-full text-xs border transition-all ${active
                            ? 'bg-blue-100 text-blue-700 border-blue-300'
                            : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'
                            }`}
                          onClick={() => updateDraft('wants_back_to_back', val)}
                        >
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                </EditableField>
                <EditableField label="On Leave">
                  <button
                    type="button"
                    className={`px-3 py-1 rounded-full text-xs border transition-all ${draft.on_leave === true
                      ? 'bg-red-100 text-red-700 border-red-300'
                      : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'
                      }`}
                    onClick={() => updateDraft('on_leave', draft.on_leave === true ? false : true)}
                  >
                    {draft.on_leave === true ? '⚠️ On Leave' : 'Not on leave'}
                  </button>
                </EditableField>
                <EditableField label="Notes for Admin">
                  <textarea
                    className="w-full border border-gray-200 rounded-md p-2 text-sm resize-none h-20"
                    value={String(draft.notes_for_admin ?? '')}
                    onChange={e => updateDraft('notes_for_admin', e.target.value || null)}
                  />
                </EditableField>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg px-4 py-2 border border-gray-200">
                <ReadonlyField label="Requested Load" value={parsed.requested_load as string} />
                <ReadonlyField label="Max Load" value={parsed.max_load as string} />
                <ReadonlyField label="Preferred Courses" value={parsed.preferred_courses as string[]} />
                <ReadonlyField label="Avoid Courses" value={parsed.avoid_courses as string[]} />
                <ReadonlyField label="Preferred Levels" value={parsed.preferred_levels as string[]} />
                <ReadonlyField label="Preferred Timeslots" value={parsed.preferred_timeslots as string[]} />
                <ReadonlyField label="Avoid Timeslots" value={parsed.avoid_timeslots as string[]} />
                <ReadonlyField label="Avoid Days" value={parsed.avoid_days as string[]} />
                <ReadonlyField
                  label="Back-to-Back"
                  value={
                    parsed.wants_back_to_back === true
                      ? 'Prefers back-to-back classes'
                      : parsed.wants_back_to_back === false
                        ? 'Avoid back-to-back classes'
                        : 'No preference specified'
                  }
                />
                <ReadonlyField
                  label="On Leave"
                  value={
                    parsed.on_leave === true
                      ? 'Yes'
                      : parsed.on_leave === false
                        ? 'No'
                        : '—/Unknown'
                  }
                />
                <ReadonlyField label="Notes for Admin" value={parsed.notes_for_admin as string} />
              </div>
            )}

            {editMode && (
              <div className="flex gap-2 mt-4 justify-end">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setEditMode(false)}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                  disabled={isSaving}
                  onClick={() => onSave(pref.id, draft)}
                >
                  {isSaving ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Save className="w-3 h-3 mr-1" />}
                  Save Changes
                </Button>
              </div>
            )}
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

  // ---- Semester/year selector ----
  const defaults = defaultSemester();
  const [semester, setSemester] = useState(defaults.semester);
  const [year, setYear] = useState(defaults.year);
  const termLabel = `${semester} ${year}`;

  // ---- TanStack Query hooks ----
  const { data: professors = [], isLoading: profsLoading } = useQuery({ queryKey: queryKeys.professors, queryFn: fetchProfessors });
  const { data: courses = [], isLoading: coursesLoading } = useQuery({ queryKey: queryKeys.courses, queryFn: fetchCourses });
  const { data: timeslots = [] } = useQuery({ queryKey: queryKeys.timeslots, queryFn: fetchTimeslots });
  const { data: schedules = [], isLoading: schedsLoading } = useQuery({
    queryKey: queryKeys.schedules(semester, year),
    queryFn: () => fetchSchedules(semester, year),
  });
  const { data: preferences = [], isLoading: prefsLoading } = useQuery({
    queryKey: ['preferences', semester, year],
    queryFn: () => fetchPreferences(semester, year),
  });

  const [viewingHistoryCourse, setViewingHistoryCourse] = useState<Course | null>(null);
  const approveMutation = useMutation({
    mutationFn: approvePreference,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.preferences(semester, year) });
    },
  });

  // ---- Mutation: update preference parsed_json ----
  const updatePrefMutation = useMutation({
    mutationFn: ({ prefId, parsed }: { prefId: number; parsed: Record<string, unknown> }) =>
      updatePreferenceParsedJson(prefId, parsed),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.preferences(semester, year) });
      setViewingPref(null);
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
      {/* Sub-components / Modals */}
      {viewingPref && (
        <PreferenceDetailDialog
          pref={viewingPref}
          courses={courses}
          timeslots={timeslots}
          onClose={() => setViewingPref(null)}
          onSave={(prefId, parsed) => updatePrefMutation.mutate({ prefId, parsed })}
          isSaving={updatePrefMutation.isPending}
        />
      )}

      {/* Course History Modal */}
      <CourseHistoryDialog
        course={viewingHistoryCourse}
        open={viewingHistoryCourse !== null}
        onOpenChange={(open) => {
          if (!open) setViewingHistoryCourse(null);
        }}
      />

      {/* Left Side: Data Dashboard */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 border-r border-gray-200">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center flex-shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">TES System</h1>
            <p className="text-sm text-gray-500">TCU Econ Scheduler</p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-gray-400" />
            <Select value={semester} onValueChange={setSemester}>
              <SelectTrigger className="w-[110px] h-8 bg-white">
                <SelectValue placeholder="Semester" />
              </SelectTrigger>
              <SelectContent>
                {SEMESTERS.map(s => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={year.toString()} onValueChange={v => setYear(Number(v))}>
              <SelectTrigger className="w-[90px] h-8 bg-white">
                <SelectValue placeholder="Year" />
              </SelectTrigger>
              <SelectContent>
                {YEARS.map(y => (
                  <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
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
                  <CardTitle>Preference Inbox — {termLabel}</CardTitle>
                  <CardDescription>Review and approve professor requests before running the solver.</CardDescription>
                </CardHeader>
                <CardContent>
                  {pendingCount > 0 && (
                    <div className="flex items-center gap-4 p-4 mb-4 bg-amber-50 text-amber-900 border border-amber-200 rounded-lg">
                      <AlertCircle className="w-5 h-5 flex-shrink-0" />
                      <div>
                        <p className="font-medium">Pending Approvals</p>
                        <p className="text-sm opacity-90">{pendingCount} preference(s) pending approval.</p>
                      </div>
                    </div>
                  )}
                  {prefsLoading ? (
                    <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
                  ) : preferences.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <p className="text-lg font-medium">No preferences for {termLabel}</p>
                      <p className="text-sm mt-1">Preference emails from professors will appear here once polled.</p>
                    </div>
                  ) : (
                    <div className="border rounded-md">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Professor</TableHead>
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
                                  prof.rank.includes('Visiting') ? 'bg-purple-50 text-purple-700 border-purple-200' :
                                    prof.rank.includes('Assistant Professor') ? 'bg-violet-50 text-violet-700 border-violet-200' :
                                      prof.rank.includes('Associate Professor') ? 'bg-indigo-50 text-indigo-700 border-indigo-200' :
                                        prof.rank.includes('Professor') ? 'bg-blue-50 text-blue-700 border-blue-200' :
                                          prof.rank.includes('Instructor') ? 'bg-amber-50 text-amber-700 border-amber-200' :
                                            'bg-gray-50 text-gray-700 border-gray-200'
                                }>
                                  {prof.rank}
                                </Badge>
                              </TableCell>
                              <TableCell>{prof.max_sections}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className={
                                  prof.active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-gray-100 text-gray-500 border-gray-200'
                                }>
                                  {prof.active ? 'Active' : 'Inactive'}
                                </Badge>
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
                            <TableHead className="text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {courses.map(course => (
                            <TableRow key={course.id}>
                              <TableCell className="font-mono font-medium text-sm">{course.code}</TableCell>
                              <TableCell>{course.name}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className={
                                  course.level >= 40000 ? 'bg-red-50 text-red-700 border-red-200' :
                                    course.level >= 30000 ? 'bg-orange-50 text-orange-700 border-orange-200' :
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
                                    <Badge key={tag} variant="outline" className={`text-[10px] px-1.5 py-0 ${tag === 'SSC' ? 'bg-blue-50 text-blue-600 border-blue-200' :
                                      tag === 'HT' ? 'bg-amber-50 text-amber-600 border-amber-200' :
                                        tag === 'GA' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' :
                                          'bg-violet-50 text-violet-600 border-violet-200'
                                      }`}>{tag}</Badge>
                                  ))}
                                  {coreTags(course).length === 0 && <span className="text-gray-300">—</span>}
                                </div>
                              </TableCell>
                              <TableCell>{course.requires_lab ? '✓' : ''}</TableCell>
                              <TableCell className="text-right">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-8 w-8 p-0 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50"
                                  title="View Course History"
                                  onClick={() => setViewingHistoryCourse(course)}
                                >
                                  <History className="h-4 w-4" />
                                </Button>
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

            {/* ========== Schedules Tab ========== */}
            <TabsContent value="schedules" className="flex-1 mt-0">
              <Card>
                <CardHeader>
                  <CardTitle>Schedules — {termLabel}</CardTitle>
                  <CardDescription>{schedules.length} schedule(s) for {termLabel}</CardDescription>
                </CardHeader>
                <CardContent>
                  {schedsLoading ? (
                    <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
                  ) : schedules.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <p className="text-lg font-medium">No schedules for {termLabel}</p>
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