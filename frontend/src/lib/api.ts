'use client';

// Shared interfaces — moved from dashboard.tsx so they're reusable across the app

export interface Professor {
    id: number;
    name: string;
    email: string;
    office: string | null;
    rank: string;
    max_sections: number;
    active: boolean;
}

export interface Course {
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

export interface Section {
    id: number;
    course_code: string | null;
    course_name: string | null;
    professor_name: string | null;
    timeslot_label: string | null;
    status: string;
    semester?: string;
    year?: number;
}

export interface Schedule {
    id: number;
    semester: string;
    year: number;
    status: string;
    finalized_at: string | null;
    sections: Section[];
}

export interface TimeSlot {
    id: number;
    days: string;
    start_time: string;
    end_time: string;
    label: string;
    section_number: string;
    max_classes: number;
    active: boolean;
}

export interface Preference {
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

// ---------------------------------------------------------------------------
// API base URL
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const API = `${API_BASE}/api`;

// ---------------------------------------------------------------------------
// Query keys — used for cache identity and targeted invalidation
// ---------------------------------------------------------------------------

export const queryKeys = {
    professors: ['professors'] as const,
    courses: ['courses'] as const,
    timeslots: ['timeslots'] as const,
    schedules: (semester: string, year: number) => ['schedules', semester, year] as const,
    preferences: (semester: string, year: number) => ['preferences', semester, year] as const,
};

// ---------------------------------------------------------------------------
// Fetch functions
// ---------------------------------------------------------------------------

async function jsonOrThrow<T>(res: Response): Promise<T> {
    if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
    return res.json() as Promise<T>;
}

export const fetchProfessors = (): Promise<Professor[]> => fetch(`${API}/professors`).then(r => jsonOrThrow<Professor[]>(r));
export const fetchCourses = (): Promise<Course[]> => fetch(`${API}/courses`).then(r => jsonOrThrow<Course[]>(r));
export const fetchTimeslots = (): Promise<TimeSlot[]> => fetch(`${API}/timeslots`).then(r => jsonOrThrow<TimeSlot[]>(r));

export const fetchSchedules = (semester: string, year: number): Promise<Schedule[]> =>
    fetch(`${API}/schedules?semester=${encodeURIComponent(semester)}&year=${year}`).then(r => jsonOrThrow<Schedule[]>(r));

export const fetchPreferences = (semester: string, year: number): Promise<Preference[]> =>
    fetch(`${API}/preferences?semester=${encodeURIComponent(semester)}&year=${year}`).then(r => jsonOrThrow<Preference[]>(r));

export const fetchCourseHistory = (courseId: number, semester?: string, year?: number): Promise<Section[]> => {
    let url = `${API}/courses/${courseId}/history`;
    const params = new URLSearchParams();
    if (semester) params.append('semester', semester);
    if (year) params.append('year', year.toString());

    const qty = params.toString();
    if (qty) url += `?${qty}`;

    return fetch(url).then(r => jsonOrThrow<Section[]>(r));
};

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export async function approvePreference(prefId: number): Promise<Preference> {
    const res = await fetch(`${API}/preferences/${prefId}/approve`, { method: 'PUT' });
    return jsonOrThrow<Preference>(res);
}

export async function updatePreferenceParsedJson(
    prefId: number,
    parsedJson: Record<string, unknown>,
): Promise<Preference> {
    const res = await fetch(`${API}/preferences/${prefId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parsed_json: parsedJson }),
    });
    return jsonOrThrow<Preference>(res);
}
