'use client';

import { useQuery } from '@tanstack/react-query';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, TrendingUp, AlertTriangle, CheckCircle2, Info, AlertOctagon } from 'lucide-react';
import { fetchInsights, queryKeys, Course } from '@/lib/api';
import { useState, useMemo, useEffect } from 'react';
import { MultiSelect } from './ui/multi-select';

interface InsightsTabProps {
    semester: string;
    year: number;
    courses: Course[];
    chatWidth?: number;
}

export default function InsightsTab({ semester, year, courses, chatWidth = 450 }: InsightsTabProps) {
    const isCompact = chatWidth >= 600;
    const { data, isLoading, isError } = useQuery({
        queryKey: queryKeys.insights(semester, year),
        queryFn: () => fetchInsights(semester, year),
    });

    const [selectedCourseKeys, setSelectedCourseKeys] = useState<string[]>([]);
    const [selectedDays, setSelectedDays] = useState<string>('All');

    // Extract unique day combinations from the timeslot data
    const availableDays = useMemo(() => {
        if (!data) return [];
        const daysSet = new Set<string>();
        data.timeslotData.forEach(ts => daysSet.add(ts.days));
        return Array.from(daysSet).sort();
    }, [data]);

    // Reset filter when the data changes and the selected day pattern is no longer available
    useEffect(() => {
        if (selectedDays !== 'All' && availableDays.length > 0 && !availableDays.includes(selectedDays)) {
            setSelectedDays('All');
        }
    }, [availableDays, selectedDays]);

    const groupedTimeslotData = useMemo(() => {
        if (!data?.timeslotData) return [];

        // 1. Filter by selected days
        const filteredData = selectedDays === 'All' 
            ? data.timeslotData 
            : data.timeslotData.filter(ts => ts.days === selectedDays);

        // 2. Map and Sort
        // If "All" is selected, we group by hour so the chart isn't overly crowded
        // If a specific day combination is selected, we can show exact times (e.g. 9:00, 9:30)
        if (selectedDays === 'All') {
            const hourGroups = new Map<string, { label: string; preferred: number; avoided: number; sortKey: number }>();
            
            filteredData.forEach(ts => {
                const hourStr = ts.startTime.split(':')[0];
                const hourInt = parseInt(hourStr, 10);
                
                let label = "12 AM";
                if (hourInt === 12) label = "12 PM";
                else if (hourInt > 12) label = `${hourInt - 12} PM`;
                else if (hourInt > 0) label = `${hourInt} AM`;

                const existing = hourGroups.get(label);
                if (existing) {
                    existing.preferred += ts.preferred;
                    existing.avoided += ts.avoided;
                } else {
                    hourGroups.set(label, { label, preferred: ts.preferred, avoided: ts.avoided, sortKey: hourInt });
                }
            });

            return Array.from(hourGroups.values()).sort((a, b) => a.sortKey - b.sortKey);
        } else {
            // Specific Day selected -> Show exact times
            return filteredData.map(ts => {
                const hourStr = ts.startTime.split(':')[0];
                const minStr = ts.startTime.split(':')[1] || '00';
                const hourInt = parseInt(hourStr, 10);

                const h12 = hourInt % 12 === 0 ? 12 : hourInt % 12;
                const period = hourInt < 12 ? 'AM' : 'PM';
                const timeLabel = `${h12}:${minStr} ${period}`;

                return {
                    label: timeLabel,
                    preferred: ts.preferred,
                    avoided: ts.avoided,
                    sortKey: hourInt * 60 + parseInt(minStr, 10)
                };
            }).sort((a, b) => a.sortKey - b.sortKey);
        }
    }, [data, selectedDays]);

    const filteredCourseData = useMemo(() => {
        if (!data) return [];
        // Map data to include a nice display label for the Y-axis
        const dataWithLabels = data.courseData.map(c => {
            const fullName = `${c.code}: ${c.name}`;
            return {
                ...c,
                key: `${c.code} | ${c.name}`,
                displayLabel: fullName.length > 25 ? fullName.substring(0, 25) + '...' : fullName
            };
        });

        if (selectedCourseKeys.length === 0) {
            // Default to top 5 most preferred
            return dataWithLabels.sort((a, b) => b.preferred - a.preferred).slice(0, 5);
        }
        return dataWithLabels.filter(c => selectedCourseKeys.includes(c.key));
    }, [data, selectedCourseKeys]);

    if (isLoading) {
        return (
            <div className="flex justify-center py-24">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
        );
    }

    if (isError) {
        return (
            <Card className="border-red-200 bg-red-50">
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                    <AlertOctagon className="w-12 h-12 text-red-400 mb-4" />
                    <h3 className="text-lg font-medium text-red-900">Failed to load insights</h3>
                    <p className="text-sm text-red-700 max-w-sm mt-1">
                        There was an error communicating with the server. Please try refreshing the page.
                    </p>
                </CardContent>
            </Card>
        );
    }

    if (!data || (data.timeslotData.length === 0 && data.courseData.length === 0)) {
        return (
            <Card className="border-dashed">
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                    <Info className="w-12 h-12 text-gray-200 mb-4" />
                    <h3 className="text-lg font-medium text-gray-900">No Insights Available</h3>
                    <p className="text-sm text-gray-500 max-w-sm mt-1">
                        Aggregated demand data will appear here once professors start submitting preferences for {semester} {year}.
                    </p>
                </CardContent>
            </Card>
        );
    }

    const totalProfs = data?.summary.readiness.total ?? 0;
    const readinessPercent = totalProfs > 0
        ? Math.round((data!.summary.readiness.approved / totalProfs) * 100)
        : 0;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Summary Highlights */}
            <div className={`grid gap-4 ${isCompact ? 'grid-cols-2' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'}`}>
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs uppercase font-semibold">Readiness Score</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <span className="text-2xl font-bold">{readinessPercent}%</span>
                            <CheckCircle2 className={readinessPercent > 80 ? "text-green-500" : "text-amber-500"} />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{data!.summary.readiness.approved} of {totalProfs} approved</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs uppercase font-semibold">T/Th Preference</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <span className="text-xl font-bold truncate pr-2">
                                {data!.summary.trPreferencePercent != null ? `${data!.summary.trPreferencePercent}%` : '—'}
                            </span>
                            <TrendingUp className="text-blue-500 flex-shrink-0" />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">of professors prefer T/Th</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs uppercase font-semibold">Peak Demand Time</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-bold truncate pr-2">{data!.summary.peakTime?.label || '—'}</span>
                            <TrendingUp className="text-red-500 flex-shrink-0" />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{data!.summary.peakTime?.count || 0} requests for this slot</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs uppercase font-semibold">Most Avoided</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-bold truncate pr-2">{data!.summary.mostAvoidedTime?.label || '—'}</span>
                            <AlertTriangle className="text-amber-500 flex-shrink-0" />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{data!.summary.mostAvoidedTime?.count || 0} professors avoid this</p>
                    </CardContent>
                </Card>
            </div>

            <div className={`grid gap-6 ${isCompact ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-5'}`}>
                {/* Timeslot Heatmap */}
                <Card className={isCompact ? "col-span-1" : "lg:col-span-3"}>
                    <CardHeader className="flex flex-row items-start justify-between pb-2">
                        <div>
                            <CardTitle className="text-base">Demand Heatmap</CardTitle>
                            <CardDescription>Comparison of preferred vs. avoided start times</CardDescription>
                        </div>
                        <Select value={selectedDays} onValueChange={setSelectedDays}>
                            <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="Filter by Days" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="All">All Days</SelectItem>
                                {availableDays.map(day => (
                                    <SelectItem key={day} value={day}>{day} Only</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[350px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={groupedTimeslotData} margin={{ top: 20, right: 30, left: 0, bottom: 60 }} barCategoryGap="20%">
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis
                                        dataKey="label"
                                        angle={-45}
                                        textAnchor="end"
                                        height={60}
                                        interval={0}
                                        tick={{ fontSize: 10 }}
                                        tickMargin={10}
                                    />
                                    <YAxis style={{ fontSize: '12px' }} />
                                    <Tooltip
                                        allowEscapeViewBox={{ x: false, y: true }}
                                        wrapperStyle={{ zIndex: 1000 }}
                                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                                    />
                                    <Legend verticalAlign="top" height={36} />
                                    <Bar dataKey="preferred" name="Preferred" fill="#10b981" stackId="a" />
                                    <Bar dataKey="avoided" name="Avoided" fill="#ef4444" stackId="a" />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>

                {/* Course Comparison */}
                <Card className={isCompact ? "col-span-1" : "lg:col-span-2"}>
                    <CardHeader>
                        <CardTitle className="text-base">Course Comparison Tool</CardTitle>
                        <CardDescription>Select specific courses to compare faculty interest</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <MultiSelect
                            selected={selectedCourseKeys}
                            options={courses.map(c => ({
                                value: `${c.code} | ${c.name}`,
                                label: `${c.code}: ${c.name}`
                            }))}
                            onChange={setSelectedCourseKeys}
                            placeholder="Search courses to compare..."
                        />

                        <div className="h-[250px] w-full mt-4 flex items-center justify-center">
                            {filteredCourseData.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart layout="vertical" data={filteredCourseData} margin={{ top: 5, right: 30, left: 40, bottom: 5 }} barCategoryGap="20%">
                                        <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                                        <XAxis type="number" hide />
                                        <YAxis
                                            dataKey="displayLabel"
                                            type="category"
                                            style={{ fontSize: '11px', fontWeight: 'bold' }}
                                            width={140}
                                        />
                                        <Tooltip
                                            allowEscapeViewBox={{ x: false, y: true }}
                                            wrapperStyle={{ zIndex: 1000 }}
                                            cursor={{ fill: '#f9fafb' }}
                                            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: '12px' }}
                                        />
                                        <Bar dataKey="preferred" name="Preferred" fill="#3b82f6" stackId="a" />
                                        <Bar dataKey="avoided" name="Avoided" fill="#94a3b8" stackId="a" />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="text-center p-8 bg-gray-50 rounded-lg border border-dashed w-full">
                                    <p className="text-sm text-gray-500">
                                        {selectedCourseKeys.length > 0
                                            ? "No preference data for selected courses."
                                            : "No course preference data available yet."}
                                    </p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
