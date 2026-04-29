'use client';

// Shared interfaces — moved from dashboard.tsx so they're reusable across the app

export interface Professor {
    id: number;
    tcu_id: string | null;
    name: string;
    email: string;
    office: string | null;
    rank: string;
    fall_count: number;
    spring_count: number;
    active: boolean;
}

export interface Course {
    id: number;
    code: string;
    name: string;
    semester: string;
    year: number;
    credits: number;
    level: number;
    min_sections: number;
    max_sections: number;
    capacity: number;
    core_ssc: boolean;
    core_ht: boolean;
    core_ga: boolean;
    core_wem: boolean;
    is_timeless: boolean;
}

export interface Section {
    id: number;
    course_code: string | null;
    course_name: string | null;
    professor_name: string | null;
    timeslot_label: string | null;
    room_building: string | null;
    room_number: string | null;
    days: string | null;
    start_time: string | null;
    end_time: string | null;
    status: string;
    section_number: string | null;
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

export interface Room {
    id: number;
    building: string;
    room_number: string;
    capacity: number;
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

export interface InsightsResponse {
    summary: {
        trPreferencePercent: number | null;
        peakTime: { label: string; count: number } | null;
        mostAvoidedTime: { label: string; count: number } | null;
        readiness: { approved: number; total: number };
    };
    timeslotData: Array<{
        id: number;
        label: string;
        days: string;
        startTime: string;
        preferred: number;
        avoided: number;
    }>;
    courseData: Array<{
        code: string;
        name: string;
        preferred: number;
        avoided: number;
    }>;
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
    courses: (semester: string, year: number) => ['courses', semester, year] as const,
    timeslots: ['timeslots'] as const,
    rooms: ['rooms'] as const,
    schedules: (semester: string, year: number) => ['schedules', semester, year] as const,
    preferences: (semester: string, year: number) => ['preferences', semester, year] as const,
    insights: (semester: string, year: number) => ['insights', semester, year] as const,
};

// ---------------------------------------------------------------------------
// Fetch functions
// ---------------------------------------------------------------------------

async function jsonOrThrow<T>(res: Response): Promise<T> {
    if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
    return res.json() as Promise<T>;
}

export const fetchProfessors = (): Promise<Professor[]> => fetch(`${API}/professors/`).then(r => jsonOrThrow<Professor[]>(r));
export const fetchCourses = (semester?: string, year?: number): Promise<Course[]> => {
    const params = new URLSearchParams();
    if (semester) params.append('semester', semester);
    if (year !== undefined && year !== null) params.append('year', year.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetch(`${API}/courses/${query}`).then(r => jsonOrThrow<Course[]>(r));
};
export const fetchTimeslots = (): Promise<TimeSlot[]> => fetch(`${API}/timeslots/`).then(r => jsonOrThrow<TimeSlot[]>(r));
export const fetchRooms = (): Promise<Room[]> => fetch(`${API}/rooms/`).then(r => jsonOrThrow<Room[]>(r));

export const fetchSchedules = (semester: string, year: number): Promise<Schedule[]> =>
    fetch(`${API}/schedules/?semester=${encodeURIComponent(semester)}&year=${year}`).then(r => jsonOrThrow<Schedule[]>(r));

export const fetchPreferences = (semester: string, year: number): Promise<Preference[]> =>
    fetch(`${API}/preferences/?semester=${encodeURIComponent(semester)}&year=${year}`).then(r => jsonOrThrow<Preference[]>(r));

export const fetchInsights = (semester: string, year: number): Promise<InsightsResponse> =>
    fetch(`${API}/insights/?semester=${encodeURIComponent(semester)}&year=${year}`).then(r => jsonOrThrow<InsightsResponse>(r));

export const fetchCourseHistory = (courseId: number, semester?: string, year?: number): Promise<Section[]> => {
    let url = `${API}/courses/${courseId}/history`;
    const params = new URLSearchParams();
    if (semester) params.append('semester', semester);
    if (year) params.append('year', year.toString());

    const queryString = params.toString();
    if (queryString) url += `?${queryString}`;

    return fetch(url).then(r => jsonOrThrow<Section[]>(r));
};

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export async function approvePreference(prefId: number): Promise<Preference> {
    const res = await fetch(`${API}/preferences/${prefId}/approve/`, { method: 'PUT' });
    return jsonOrThrow<Preference>(res);
}

export async function updatePreferenceParsedJson(
    prefId: number,
    parsedJson: Record<string, unknown>,
): Promise<Preference> {
    const res = await fetch(`${API}/preferences/${prefId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parsed_json: parsedJson }),
    });
    return jsonOrThrow<Preference>(res);
}

export async function initializeCourses(semester: string, year: number): Promise<Course[]> {
    const res = await fetch(
        `${API}/courses/initialize/?semester=${encodeURIComponent(semester)}&year=${year}`,
        { method: 'POST' },
    );
    return jsonOrThrow<Course[]>(res);
}

export async function exportScheduleExcel(scheduleId: number): Promise<void> {
    const res = await fetch(`${API}/schedules/${scheduleId}/export`);
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    // Extract filename from Content-Disposition header or use a fallback
    const disposition = res.headers.get('Content-Disposition');
    const match = disposition?.match(/filename="?(.+?)"?$/);
    a.download = match?.[1] ?? `ECON_Schedule_${scheduleId}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
