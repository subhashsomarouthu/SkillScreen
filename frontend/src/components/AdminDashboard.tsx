'use client';

import React, { useState, useEffect } from 'react';
import { Building2, Users, FileText, TrendingUp, Filter, LogOut, ClipboardCheck } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';

interface AdminStats {
    total_interviews: number;
    completed_interviews: number;
    in_progress_interviews: number;
    scheduled_interviews: number;
    total_organizations: number;
    total_candidates: number;
}

interface Organization {
    id: string;
    name: string;
    domain: string;
    created_at: string;
}

interface Interview {
    id: string;
    candidate_name?: string;
    candidate_email?: string;
    organization_id: string;
    status: string;
    created_at: string;
}

interface Candidate {
    id: string;
    full_name: string;
    email: string;
    organization_id: string;
    created_at: string;
}

interface Assessment {
    id: string;
    interview_id: string;
    candidate_id?: string;
    organization_id: string;
    overall_score: number;
    recommendation: string;
    technical_score?: number;
    communication_score?: number;
    soft_skills_score?: number;
    proctoring_risk_score?: number;
    created_at: string;
}


export default function AdminDashboard() {
    const { logout } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<'organizations' | 'interviews' | 'candidates' | 'assessments'>('organizations');
    const [stats, setStats] = useState<AdminStats | null>(null);
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [interviews, setInterviews] = useState<Interview[]>([]);
    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [assessments, setAssessments] = useState<Assessment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedOrg, setSelectedOrg] = useState<string>('');

    const handleLogout = () => {
        logout();
        router.push('/');
    };

    useEffect(() => {
        fetchAdminData();
    }, []);

    useEffect(() => {
        if (activeTab === 'interviews') {
            fetchInterviews();
        } else if (activeTab === 'candidates') {
            fetchCandidates();
        } else if (activeTab === 'assessments') {
            fetchAssessments();
        }
    }, [activeTab, selectedOrg]);

    const getAuthHeaders = (): Record<string, string> => {
        const storedAuth = localStorage.getItem('intervuai_auth_token');
        if (storedAuth) {
            const authData = JSON.parse(storedAuth);
            return {
                'Authorization': `Bearer ${authData.token}`,
                'Content-Type': 'application/json'
            };
        }
        return { 'Content-Type': 'application/json' };
    };

    const fetchAdminData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch organizations from user service
            const orgsRes = await fetch('http://localhost:5001/user/admin/organizations', {
                headers: getAuthHeaders()
            });

            if (orgsRes.ok) {
                const orgsData = await orgsRes.json();
                console.log('Organizations response:', orgsData);
                setOrganizations(orgsData.organizations || []);
            } else {
                console.error('Failed to fetch organizations:', orgsRes.status, await orgsRes.text());
            }

            // Try to fetch stats from interview service
            try {
                const statsRes = await fetch('http://localhost:5001/interview/admin/dashboard/stats', {
                    headers: getAuthHeaders()
                });

                if (statsRes.ok) {
                    const statsData = await statsRes.json();
                    setStats(statsData.data);
                }
            } catch (e) {
                console.log('Stats endpoint not available');
            }
        } catch (err) {
            console.error('Failed to fetch admin data:', err);
            setError('Failed to load admin data');
        } finally {
            setLoading(false);
        }
    };

    const fetchInterviews = async () => {
        try {
            const params = selectedOrg ? `?organization_id=${selectedOrg}` : '';
            const res = await fetch(`http://localhost:5001/interview/admin/interviews${params}`, {
                headers: getAuthHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                setInterviews(data.data?.interviews || []);
            }
        } catch (err) {
            console.error('Failed to fetch interviews:', err);
        }
    };

    const fetchCandidates = async () => {
        try {
            const params = selectedOrg ? `?organization_id=${selectedOrg}` : '';
            const res = await fetch(`http://localhost:5001/interview/admin/candidates${params}`, {
                headers: getAuthHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                setCandidates(data.data?.candidates || []);
            }
        } catch (err) {
            console.error('Failed to fetch candidates:', err);
        }
    };

    const fetchAssessments = async () => {
        try {
            const params = selectedOrg ? `?organization_id=${selectedOrg}` : '';
            const res = await fetch(`http://localhost:5001/assessment/v1/admin/assessments${params}`, {
                headers: getAuthHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                setAssessments(data.assessments || []);
            }
        } catch (err) {
            console.error('Failed to fetch assessments:', err);
        }
    };

    const StatCard = ({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) => (
        <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm text-gray-600">{label}</p>
                    <p className="text-3xl font-bold mt-2 text-gray-900">{value}</p>
                </div>
                <div className={`p-3 rounded-full ${color}`}>
                    <Icon className="w-6 h-6 text-white" />
                </div>
            </div>
        </div>
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading admin dashboard...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 p-8 pt-24">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
                    <p className="text-gray-600 mt-2">Platform-wide overview and management</p>
                </div>

                {/* Error message */}
                {error && (
                    <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-lg">
                        {error}
                    </div>
                )}

                {/* Stats Grid */}
                {stats && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                        <StatCard
                            icon={Building2}
                            label="Total Organizations"
                            value={stats.total_organizations}
                            color="bg-blue-500"
                        />
                        <StatCard
                            icon={FileText}
                            label="Total Interviews"
                            value={stats.total_interviews}
                            color="bg-green-500"
                        />
                        <StatCard
                            icon={Users}
                            label="Total Candidates"
                            value={stats.total_candidates}
                            color="bg-purple-500"
                        />
                        <StatCard
                            icon={TrendingUp}
                            label="Completed"
                            value={stats.completed_interviews}
                            color="bg-emerald-500"
                        />
                        <StatCard
                            icon={TrendingUp}
                            label="In Progress"
                            value={stats.in_progress_interviews}
                            color="bg-yellow-500"
                        />
                        <StatCard
                            icon={TrendingUp}
                            label="Scheduled"
                            value={stats.scheduled_interviews}
                            color="bg-indigo-500"
                        />
                    </div>
                )}

                {/* Tabs */}
                <div className="bg-white rounded-lg shadow">
                    <div className="border-b border-gray-200">
                        <nav className="flex -mb-px">
                            <button
                                onClick={() => setActiveTab('organizations')}
                                className={`px-6 py-4 text-sm font-medium border-b-2 ${activeTab === 'organizations'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                <Building2 className="w-4 h-4 inline mr-2" />
                                Organizations
                            </button>
                            <button
                                onClick={() => setActiveTab('interviews')}
                                className={`px-6 py-4 text-sm font-medium border-b-2 ${activeTab === 'interviews'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                <FileText className="w-4 h-4 inline mr-2" />
                                Interviews
                            </button>
                            <button
                                onClick={() => setActiveTab('candidates')}
                                className={`px-6 py-4 text-sm font-medium border-b-2 ${activeTab === 'candidates'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                <Users className="w-4 h-4 inline mr-2" />
                                Candidates
                            </button>
                            <button
                                onClick={() => setActiveTab('assessments')}
                                className={`px-6 py-4 text-sm font-medium border-b-2 ${activeTab === 'assessments'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                <ClipboardCheck className="w-4 h-4 inline mr-2" />
                                Assessments
                            </button>
                        </nav>
                    </div>

                    {/* Filter Bar */}
                    {(activeTab === 'interviews' || activeTab === 'candidates' || activeTab === 'assessments') && (
                        <div className="p-4 bg-gray-50 border-b">
                            <div className="flex items-center gap-4">
                                <Filter className="w-4 h-4 text-gray-500" />
                                <select
                                    value={selectedOrg}
                                    onChange={(e) => setSelectedOrg(e.target.value)}
                                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                                >
                                    <option value="">All Organizations</option>
                                    {organizations.map((org) => (
                                        <option key={org.id} value={org.id}>
                                            {org.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    )}

                    {/* Tab Content */}
                    <div className="p-6">
                        {activeTab === 'organizations' && (
                            <div className="overflow-x-auto">
                                {organizations.length === 0 ? (
                                    <p className="text-gray-500 text-center py-8">No organizations found</p>
                                ) : (
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Name
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Domain
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Created At
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    ID
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {organizations.map((org) => (
                                                <tr key={org.id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                        {org.name}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {org.domain || 'N/A'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {org.created_at ? new Date(org.created_at).toLocaleDateString() : 'N/A'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400 font-mono">
                                                        {org.id.substring(0, 8)}...
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        )}

                        {activeTab === 'interviews' && (
                            <div className="overflow-x-auto">
                                {interviews.length === 0 ? (
                                    <p className="text-gray-500 text-center py-8">No interviews found</p>
                                ) : (
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Candidate
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Email
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Status
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Created At
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {interviews.map((interview) => (
                                                <tr key={interview.id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                        {interview.candidate_name || 'N/A'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {interview.candidate_email || 'N/A'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className={`px-2 py-1 text-xs rounded-full ${interview.status === 'completed' ? 'bg-green-100 text-green-800' :
                                                            interview.status === 'in_progress' ? 'bg-yellow-100 text-yellow-800' :
                                                                'bg-gray-100 text-gray-800'
                                                            }`}>
                                                            {interview.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {interview.created_at ? new Date(interview.created_at).toLocaleDateString() : 'N/A'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        )}

                        {activeTab === 'candidates' && (
                            <div className="overflow-x-auto">
                                {candidates.length === 0 ? (
                                    <p className="text-gray-500 text-center py-8">No candidates found</p>
                                ) : (
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Name
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Email
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Created At
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {candidates.map((candidate) => (
                                                <tr key={candidate.id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                        {candidate.full_name}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {candidate.email}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {candidate.created_at ? new Date(candidate.created_at).toLocaleDateString() : 'N/A'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        )}

                        {activeTab === 'assessments' && (
                            <div className="overflow-x-auto">
                                {assessments.length === 0 ? (
                                    <p className="text-gray-500 text-center py-8">No assessments found</p>
                                ) : (
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Interview ID
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Overall Score
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Recommendation
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Technical
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Communication
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Created At
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {assessments.map((assessment) => (
                                                <tr key={assessment.id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                        {assessment.interview_id.slice(0, 8)}...
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className={`text-sm font-semibold ${assessment.overall_score >= 70 ? 'text-green-600' :
                                                            assessment.overall_score >= 50 ? 'text-yellow-600' :
                                                                'text-red-600'
                                                            }`}>
                                                            {assessment.overall_score?.toFixed(1) || 'N/A'}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${assessment.recommendation?.toLowerCase().includes('hire') && !assessment.recommendation?.toLowerCase().includes('no')
                                                            ? 'bg-green-100 text-green-800'
                                                            : assessment.recommendation?.toLowerCase().includes('no') || assessment.recommendation?.toLowerCase().includes('reject')
                                                                ? 'bg-red-100 text-red-800'
                                                                : 'bg-yellow-100 text-yellow-800'
                                                            }`}>
                                                            {assessment.recommendation || 'Pending'}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {assessment.technical_score?.toFixed(1) || 'N/A'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {assessment.communication_score?.toFixed(1) || 'N/A'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {assessment.created_at ? new Date(assessment.created_at).toLocaleDateString() : 'N/A'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
