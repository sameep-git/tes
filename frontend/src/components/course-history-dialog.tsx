import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { fetchCourseHistory } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { Course } from "@/lib/api";
import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface CourseHistoryDialogProps {
    course: Course | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function CourseHistoryDialog({ course, open, onOpenChange }: CourseHistoryDialogProps) {
    const [selectedSemester, setSelectedSemester] = useState<string>("all");
    const [selectedYear, setSelectedYear] = useState<string>("all");

    const { data: historySections = [], isLoading } = useQuery({
        queryKey: ['courseHistory', course?.id, selectedSemester, selectedYear],
        queryFn: () => fetchCourseHistory(
            course!.id,
            selectedSemester === 'all' ? undefined : selectedSemester,
            selectedYear === 'all' ? undefined : parseInt(selectedYear)
        ),
        enabled: !!course && open,
    });

    const uniqueYears = Array.from(new Set(historySections.map(s => s.year).filter((y): y is number => y !== undefined))).sort((a, b) => b - a);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>Course History: {course?.code}</DialogTitle>
                    <DialogDescription>
                        {course?.name} - View past instructors and timeslots.
                    </DialogDescription>
                </DialogHeader>

                <div className="flex items-center gap-4 py-4">
                    <div className="flex flex-col gap-1.5 w-40">
                        <label className="text-xs font-medium text-gray-500">Semester</label>
                        <Select value={selectedSemester} onValueChange={setSelectedSemester}>
                            <SelectTrigger>
                                <SelectValue placeholder="All Semesters" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Semesters</SelectItem>
                                <SelectItem value="Fall">Fall</SelectItem>
                                <SelectItem value="Spring">Spring</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="flex flex-col gap-1.5 w-40">
                        <label className="text-xs font-medium text-gray-500">Year</label>
                        <Select value={selectedYear} onValueChange={setSelectedYear}>
                            <SelectTrigger>
                                <SelectValue placeholder="All Years" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Years</SelectItem>
                                {/* Dynamically list years from the data and fallback years */}
                                {uniqueYears.map(y => (
                                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                                ))}
                                {uniqueYears.length === 0 && (
                                    <>
                                        <SelectItem value="2026">2026</SelectItem>
                                        <SelectItem value="2025">2025</SelectItem>
                                        <SelectItem value="2024">2024</SelectItem>
                                    </>
                                )}
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto border rounded-md">
                    {isLoading ? (
                        <div className="flex justify-center p-12">
                            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                        </div>
                    ) : historySections.length === 0 ? (
                        <div className="text-center p-12 text-gray-500">
                            No historical data found for {course?.code} matching these filters.
                        </div>
                    ) : (
                        <Table>
                            <TableHeader className="bg-gray-50 sticky top-0">
                                <TableRow>
                                    <TableHead className="w-[120px]">Term</TableHead>
                                    <TableHead>Professor</TableHead>
                                    <TableHead>TimeSlot</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {historySections.map(section => (
                                    <TableRow key={section.id}>
                                        <TableCell className="font-medium">
                                            {section.semester} {section.year}
                                        </TableCell>
                                        <TableCell>
                                            {section.professor_name || <span className="text-gray-400">TBA</span>}
                                        </TableCell>
                                        <TableCell>
                                            {section.timeslot_label || <span className="text-gray-400">TBA</span>}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </div>
            </DialogContent>
        </Dialog >
    );
}
