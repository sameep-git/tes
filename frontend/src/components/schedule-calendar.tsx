'use client';

import React, { useMemo, useState } from 'react';
import { Section } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription 
} from '@/components/ui/dialog';
import { Clock, User, BookOpen, AlertCircle } from 'lucide-react';

interface ScheduleCalendarProps {
    sections: Section[];
}

const DAYS = ['M', 'T', 'W', 'R', 'F'];
const DAY_LABELS: Record<string, string> = {
    'M': 'Monday',
    'T': 'Tuesday',
    'W': 'Wednesday',
    'R': 'Thursday',
    'F': 'Friday'
};

// Helper to generate a stable color based on course code
const getCourseColor = (courseCode: string | null) => {
    if (!courseCode) return 'hsl(0, 0%, 95%)';
    
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < courseCode.length; i++) {
        hash = courseCode.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    // Use HSL for better control over vibrancy and lightness
    const h = Math.abs(hash % 360);
    const s = 60 + (Math.abs(hash % 20)); // 60-80% saturation
    const l = 85 + (Math.abs(hash % 10)); // 85-95% lightness (pastel)
    
    return `hsl(${h}, ${s}%, ${l}%)`;
};

const getCourseDarkColor = (courseCode: string | null) => {
    if (!courseCode) return 'hsl(0, 0%, 40%)';
    let hash = 0;
    for (let i = 0; i < courseCode.length; i++) {
        hash = courseCode.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h = Math.abs(hash % 360);
    return `hsl(${h}, 70%, 30%)`;
};

export default function ScheduleCalendar({ sections }: ScheduleCalendarProps) {
    const [selectedSection, setSelectedSection] = useState<Section | null>(null);

    // 1. Determine time range
    const timeRange = useMemo(() => {
        let minHour = 8;
        let maxHour = 21;

        sections.forEach(s => {
            if (s.start_time) {
                const h = parseInt(s.start_time.split(':')[0]);
                if (h < minHour) minHour = h;
            }
            if (s.end_time) {
                const h = parseInt(s.end_time.split(':')[0]);
                if (h > maxHour) maxHour = h;
            }
        });

        return { min: minHour, max: maxHour + 1 };
    }, [sections]);

    const hours = useMemo(() => {
        const h = [];
        for (let i = timeRange.min; i <= timeRange.max; i++) {
            h.push(i);
        }
        return h;
    }, [timeRange]);

    // 2. Map sections to days and handle overlaps
    const calendarData = useMemo(() => {
        const daysMap: Record<string, Section[]> = {
            'M': [], 'T': [], 'W': [], 'R': [], 'F': []
        };

        sections.forEach(s => {
            if (!s.days || !s.start_time || !s.end_time) return;
            
            // Split "MWF" into ["M", "W", "F"]
            const dayChars = s.days.split('');
            dayChars.forEach(char => {
                if (daysMap[char]) {
                    daysMap[char].push(s);
                }
            });
        });

        return daysMap;
    }, [sections]);

    const getTimePosition = (timeStr: string) => {
        const [h, m] = timeStr.split(':').map(Number);
        const totalMinutes = (h - timeRange.min) * 60 + m;
        return (totalMinutes / 60) * 100; // Percentage of an hour slot
    };

    const getDurationHeight = (startTime: string, endTime: string) => {
        const [sh, sm] = startTime.split(':').map(Number);
        const [eh, em] = endTime.split(':').map(Number);
        const durationMinutes = (eh * 60 + em) - (sh * 60 + sm);
        return (durationMinutes / 60) * 100;
    };

    return (
        <div className="flex flex-col h-full min-h-[600px] bg-white rounded-lg border shadow-sm overflow-hidden">
            {/* Calendar Header */}
            <div className="grid grid-cols-[80px_1fr_1fr_1fr_1fr_1fr] border-b bg-gray-50/50">
                <div className="p-3 border-r"></div>
                {DAYS.map(day => (
                    <div key={day} className="p-3 text-center font-semibold text-sm border-r last:border-r-0">
                        <span className="hidden sm:inline">{DAY_LABELS[day]}</span>
                        <span className="sm:hidden">{day}</span>
                    </div>
                ))}
            </div>

            {/* Calendar Body */}
            <div className="flex-1 overflow-y-auto relative">
                <div className="grid grid-cols-[80px_1fr_1fr_1fr_1fr_1fr] h-full min-h-full">
                    {/* Time Gutter */}
                    <div className="bg-gray-50/30 border-r relative">
                        {hours.map(hour => (
                            <div 
                                key={hour} 
                                className="absolute left-0 right-0 text-[10px] text-gray-400 text-center -translate-y-1/2"
                                style={{ top: `${(hour - timeRange.min) * 100}px` }}
                            >
                                {hour > 12 ? `${hour-12} PM` : hour === 12 ? '12 PM' : `${hour} AM`}
                            </div>
                        ))}
                    </div>

                    {/* Day Columns */}
                    {DAYS.map(day => (
                        <div key={day} className="border-r last:border-r-0 relative min-h-full bg-grid-slate-100">
                            {/* Hour Grid Lines */}
                            {hours.map(hour => (
                                <div 
                                    key={hour} 
                                    className="absolute left-0 right-0 border-b border-gray-100"
                                    style={{ 
                                        top: `${(hour - timeRange.min) * 100}px`,
                                        height: '100px'
                                    }}
                                />
                            ))}

                            {/* Section Blocks */}
                            {calendarData[day].map((s, idx) => {
                                const topPx = getTimePosition(s.start_time!);
                                const heightPx = getDurationHeight(s.start_time!, s.end_time!);
                                const bgColor = getCourseColor(s.course_code);
                                const borderColor = getCourseDarkColor(s.course_code);
                                
                                // Basic overlap adjustment: if multiple items start at the same time, shift them
                                const sameStartTime = calendarData[day].filter(other => other.start_time === s.start_time);
                                const order = sameStartTime.indexOf(s);
                                const width = 100 / sameStartTime.length;
                                const left = order * width;

                                return (
                                    <div
                                        key={`${s.id}-${idx}`}
                                        className="absolute rounded-md p-1.5 text-[10px] sm:text-xs overflow-hidden cursor-pointer transition-all hover:ring-2 hover:ring-offset-1 hover:z-20 border-l-4 shadow-sm"
                                        style={{ 
                                            top: `${topPx}px`,
                                            height: `${heightPx}px`,
                                            left: `${left}%`,
                                            width: `${width}%`,
                                            backgroundColor: bgColor,
                                            borderLeftColor: borderColor,
                                            color: borderColor,
                                            zIndex: 10 + order
                                        }}
                                        onClick={() => setSelectedSection(s)}
                                    >
                                        <div className="font-bold truncate leading-tight">{s.course_code}</div>
                                        <div className="truncate opacity-80 leading-tight">{s.professor_name || 'Unassigned'}</div>
                                    </div>
                                );
                            })}
                        </div>
                    ))}
                </div>
            </div>

            {/* Detail Dialog */}
            <Dialog open={!!selectedSection} onOpenChange={(open) => !open && setSelectedSection(null)}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <BookOpen className="w-5 h-5 text-blue-600" />
                            {selectedSection?.course_code}
                        </DialogTitle>
                        <DialogDescription>
                            {selectedSection?.course_name}
                        </DialogDescription>
                    </DialogHeader>
                    
                    <div className="grid gap-4 py-4">
                        <div className="flex items-center gap-3 text-sm">
                            <User className="w-4 h-4 text-gray-400" />
                            <span className="font-medium">Professor:</span>
                            <span>{selectedSection?.professor_name || 'Not assigned'}</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                            <Clock className="w-4 h-4 text-gray-400" />
                            <span className="font-medium">Time:</span>
                            <span>{selectedSection?.timeslot_label}</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                            <AlertCircle className="w-4 h-4 text-gray-400" />
                            <span className="font-medium">Status:</span>
                            <Badge variant={selectedSection?.status === 'Approved' ? 'default' : 'outline'}>
                                {selectedSection?.status}
                            </Badge>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            <style jsx>{`
                .bg-grid-slate-100 {
                    background-image: linear-gradient(to bottom, #f1f5f9 1px, transparent 1px);
                    background-size: 100% 100px;
                }
            `}</style>
        </div>
    );
}
