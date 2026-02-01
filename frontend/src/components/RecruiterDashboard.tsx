'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { FileUploadDemo } from '@/components/ui/file-upload-demo';
import { apiClient } from '@/lib/api';
import { FileText, User, Users, TrendingUp, Clock, Award, ThumbsUp, AlertCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface CodingQuestion {
  id: string;
  title: string;
  difficulty: string;
  language?: string;
  description?: string;
}

interface JobPosition {
  id: string;
  title: string;
  department: string;
  description: string;
  required_skills?: string[];
  interview_settings?: {
    has_coding_round?: boolean;
    coding_question_ids?: string[];
    coding_time_limit?: number;
    allowed_languages?: string[];
    qa_question_count?: number;
    qa_time_per_question?: number;
  };
}

interface DashboardStats {
  total_interviews: number;
  completed_interviews: number;
  assessed_count: number;
  pending_count: number;
  in_progress_count: number;
  recommendations: {
    hire: number;
    no_hire: number;
    maybe: number;
    needs_review: number;
  };
  average_scores: {
    overall: number | null;
    technical: number | null;
    communication: number | null;
    soft_skills: number | null;
  };
}

interface DashboardCandidate {
  interview_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  job_position_id: string;
  job_title: string;
  status: string;
  interview_completed_at: string;
  assessment: {
    id: string;
    overall_score: number;
    recommendation: string;
    technical_score: number;
    communication_score: number;
    soft_skills_score: number;
    proctoring_risk_score: number;
    created_at: string;
  } | null;
}

export default function RecruiterDashboard() {
  const router = useRouter();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'interviews' | 'candidates' | 'jobs'>('interviews');

  // Dashboard data state
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [dashboardCandidates, setDashboardCandidates] = useState<DashboardCandidate[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingCandidates, setLoadingCandidates] = useState(true);

  // Job Positions state
  const [jobPositions, setJobPositions] = useState<JobPosition[]>([]);
  const [loadingJobPositions, setLoadingJobPositions] = useState(true);
  const [templateTitle, setTemplateTitle] = useState('');
  const [templateDepartment, setTemplateDepartment] = useState('');
  const [templateContent, setTemplateContent] = useState('');
  const [templateSkills, setTemplateSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');
  const [editingJobPositionId, setEditingJobPositionId] = useState<string | null>(null);
  const [savingJobPosition, setSavingJobPosition] = useState(false);

  // Interview Settings state
  const [hasCodingRound, setHasCodingRound] = useState(false);
  const [codingTimeLimit, setCodingTimeLimit] = useState(60); // in minutes
  const [allowedLanguages, setAllowedLanguages] = useState<string[]>(['python', 'javascript']);
  const [qaQuestionCount, setQaQuestionCount] = useState(5);
  const [qaTimePerQuestion, setQaTimePerQuestion] = useState(2); // in minutes
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium');
  const [hasCodingAccess, setHasCodingAccess] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  // Coding questions state
  const [availableCodingQuestions, setAvailableCodingQuestions] = useState<CodingQuestion[]>([]);
  const [selectedCodingQuestionIds, setSelectedCodingQuestionIds] = useState<string[]>([]);
  const [loadingCodingQuestions, setLoadingCodingQuestions] = useState(false);

  // Candidate filter state
  const [candidateFilter, setCandidateFilter] = useState<'all' | 'hire' | 'assessed' | 'pending'>('all');

  // Fetch dashboard data - each call is independent so one failure doesn't block others
  useEffect(() => {
    if (!user?.organizationId) return;

    // Fetch stats
    const fetchStats = async () => {
      try {
        setLoadingStats(true);
        const statsResponse: any = await apiClient.getDashboardStats();
        console.log('Dashboard stats raw response:', statsResponse);
        const statsData = statsResponse?.success ? statsResponse.data : statsResponse;
        if (statsData?.total_interviews !== undefined) {
          setDashboardStats(statsData as DashboardStats);
        }
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
      } finally {
        setLoadingStats(false);
      }
    };

    // Fetch candidates
    const fetchCandidates = async () => {
      try {
        setLoadingCandidates(true);
        const candidatesResponse: any = await apiClient.getDashboardCandidates({
          page_size: 50,
          sort_by: 'created_at',
          sort_order: 'desc'
        });
        console.log('Dashboard candidates raw response:', candidatesResponse);
        const candidatesData = candidatesResponse?.success
          ? candidatesResponse.data
          : candidatesResponse;
        if (candidatesData?.candidates) {
          setDashboardCandidates(candidatesData.candidates || []);
        }
      } catch (error) {
        console.error('Failed to fetch dashboard candidates:', error);
      } finally {
        setLoadingCandidates(false);
      }
    };

    // Fetch job positions
    const fetchJobs = async () => {
      try {
        setLoadingJobPositions(true);
        if (user?.organizationId) {
          const jobsResponse: any = await apiClient.getJobPositions(user.organizationId);
          const jobsData = jobsResponse?.success ? jobsResponse.data : jobsResponse;
          if (jobsData?.job_positions) {
            setJobPositions(jobsData.job_positions || []);
          }
        }
      } catch (error) {
        console.error('Failed to fetch job positions:', error);
      } finally {
        setLoadingJobPositions(false);
      }
    };

    fetchStats();
    fetchCandidates();
    fetchJobs();

    // Fetch user profile to check feature flags
    apiClient.getMe().then((res: any) => {
      if (res.success && res.data?.user?.organization) {
        setHasCodingAccess(res.data.user.role === 'admin' || !!res.data.user.organization.has_coding_access);
      } else if (res.success && res.data?.user?.role === 'admin') {
        setHasCodingAccess(true);
      }
    }).catch(err => console.error('Failed to fetch user profile', err));

  }, [user?.organizationId]);

  // Fetch coding questions when coding round is enabled
  useEffect(() => {
    if (!hasCodingRound) return;
    const fetchCodingQuestions = async () => {
      setLoadingCodingQuestions(true);
      try {
        const response = await apiClient.getCodingQuestions();
        if (response.success) {
          // Handle both array and object with questions key
          const questions = Array.isArray(response.data) ? response.data : (response.data?.questions || []);
          setAvailableCodingQuestions(questions);
        }
      } catch (error) {
        console.error('Failed to fetch coding questions:', error);
      } finally {
        setLoadingCodingQuestions(false);
      }
    };
    fetchCodingQuestions();
  }, [hasCodingRound]);

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Invalid Date';
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return 'Unknown';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'assessed': return 'bg-green-500/20 text-green-300';
      case 'scheduled': return 'bg-blue-500/20 text-blue-300';
      case 'pending': return 'bg-yellow-500/20 text-yellow-300';
      case 'in_progress':
      case 'coding_in_progress': return 'bg-purple-500/20 text-purple-300';
      case 'rejected':
      case 'no_hire': return 'bg-red-500/20 text-red-300';
      default: return 'bg-gray-500/20 text-gray-300';
    }
  };

  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation?.toLowerCase()) {
      case 'hire': return 'bg-green-500/30 text-green-300 border-green-500/50';
      case 'no_hire': return 'bg-red-500/30 text-red-300 border-red-500/50';
      case 'maybe': return 'bg-yellow-500/30 text-yellow-300 border-yellow-500/50';
      default: return 'bg-gray-500/30 text-gray-300 border-gray-500/50';
    }
  };

  const resetJobPositionForm = () => {
    setTemplateTitle('');
    setTemplateDepartment('');
    setTemplateContent('');
    setTemplateSkills([]);
    setSkillInput('');
    setEditingJobPositionId(null);
    // Reset interview settings
    setHasCodingRound(false);
    setCodingTimeLimit(60);
    setAllowedLanguages(['python', 'javascript']);
    setQaQuestionCount(5);
    setQaTimePerQuestion(2);
    setDifficulty('medium');
    setSelectedCodingQuestionIds([]);
  };

  const saveJobPosition = async () => {
    if (!user?.organizationId) return;

    const trimmedTitle = templateTitle.trim();
    const trimmedDept = templateDepartment.trim();
    const trimmedContent = templateContent.trim();
    if (!trimmedTitle) return;

    setSavingJobPosition(true);
    try {
      // Step 1: Create the job position
      const response = await apiClient.createJobPosition({
        organization_id: user.organizationId,
        title: trimmedTitle,
        department: trimmedDept || undefined,
        description: trimmedContent || undefined,
        required_skills: templateSkills.length > 0 ? templateSkills : undefined,
      });

      if (response.success && response.data?.id) {
        const jobPositionId = response.data.id;

        // Step 2: Save interview settings via separate PATCH call
        const interviewSettings: Record<string, any> = {
          has_coding_round: hasCodingRound,
          coding_time_limit: codingTimeLimit * 60, // convert to seconds
          allowed_languages: allowedLanguages,
          qa_question_count: qaQuestionCount,
          qa_time_per_question: qaTimePerQuestion * 60, // convert to seconds
          difficulty: difficulty,
        };

        // Include selected coding question IDs if coding round is enabled
        if (hasCodingRound && selectedCodingQuestionIds.length > 0) {
          interviewSettings.coding_question_ids = selectedCodingQuestionIds;
        }

        await apiClient.updateInterviewSettings(jobPositionId, interviewSettings);

        // Refresh job positions
        const jobsResponse = await apiClient.getJobPositions(user.organizationId);
        if (jobsResponse.success) {
          setJobPositions(jobsResponse.data.job_positions || []);
        }
        resetJobPositionForm();
      }
    } catch (error) {
      console.error('Failed to save job position:', error);
    } finally {
      setSavingJobPosition(false);
    }
  };

  const deleteJobPosition = async (id: string) => {
    if (!user?.organizationId) return;

    try {
      await apiClient.deleteJobPosition(id);
      // Refresh job positions
      const jobsResponse = await apiClient.getJobPositions(user.organizationId);
      if (jobsResponse.success) {
        setJobPositions(jobsResponse.data.job_positions || []);
      }
    } catch (error) {
      console.error('Failed to delete job position:', error);
    }
  };

  const editJobPosition = (job: JobPosition) => {
    setTemplateTitle(job.title);
    setTemplateDepartment(job.department || '');
    setTemplateContent(job.description || '');
    setTemplateSkills(job.required_skills || []);
    setEditingJobPositionId(job.id);
  };

  const addSkill = () => {
    const trimmedSkill = skillInput.trim();
    if (trimmedSkill && !templateSkills.includes(trimmedSkill)) {
      setTemplateSkills(prev => [...prev, trimmedSkill]);
      setSkillInput('');
    }
  };

  const removeSkill = (skillToRemove: string) => {
    setTemplateSkills(prev => prev.filter(skill => skill !== skillToRemove));
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSkill();
    }
  };

  // Filter candidates based on selected filter
  const filteredCandidates = dashboardCandidates.filter(c => {
    if (candidateFilter === 'all') return true;
    if (candidateFilter === 'hire') return c.assessment?.recommendation?.toLowerCase() === 'hire';
    if (candidateFilter === 'assessed') return c.status === 'assessed' && c.assessment;
    if (candidateFilter === 'pending') return c.status === 'pending' || !c.assessment;
    return true;
  });

  // Hirable candidates (those with 'hire' recommendation)
  const hirableCandidates = dashboardCandidates.filter(c =>
    c.assessment?.recommendation?.toLowerCase() === 'hire'
  );

  return (
    <div className="min-h-screen p-6">
      <div className="breathing-circle"></div>

      <div className="relative z-10 max-w-7xl mx-auto">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Recruiter Dashboard</h1>
          <p className="text-primary-100">
            {user?.organizationName ? `${user.organizationName} - ` : ''}
            Manage candidates, interviews, and hiring pipeline
          </p>
        </div>

        {/* Stats Overview - Now with real data */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-5 border border-primary-200/30">
            <div className="flex items-center gap-3 mb-2">
              <Users className="w-5 h-5 text-blue-400" />
              <span className="text-primary-100 text-sm">Total Interviews</span>
            </div>
            <div className="text-3xl font-bold text-white">
              {loadingStats ? '...' : dashboardStats?.total_interviews || 0}
            </div>
          </div>

          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-5 border border-primary-200/30">
            <div className="flex items-center gap-3 mb-2">
              <Clock className="w-5 h-5 text-yellow-400" />
              <span className="text-primary-100 text-sm">Scheduled / Pending</span>
            </div>
            <div className="text-3xl font-bold text-yellow-400">
              {loadingStats ? '...' : (dashboardStats ? (dashboardStats.in_progress_count || 0) + (dashboardStats.pending_count || 0) : 0)}
            </div>
          </div>

          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-5 border border-primary-200/30">
            <div className="flex items-center gap-3 mb-2">
              <ThumbsUp className="w-5 h-5 text-green-400" />
              <span className="text-primary-100 text-sm">Hire</span>
            </div>
            <div className="text-3xl font-bold text-green-400">
              {loadingStats ? '...' : dashboardStats?.recommendations?.hire || 0}
            </div>
          </div>

          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-5 border border-primary-200/30">
            <div className="flex items-center gap-3 mb-2">
              <AlertCircle className="w-5 h-5 text-yellow-500" />
              <span className="text-primary-100 text-sm">Maybe</span>
            </div>
            <div className="text-3xl font-bold text-yellow-500">
              {loadingStats ? '...' : dashboardStats?.recommendations?.maybe || 0}
            </div>
          </div>

          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-5 border border-primary-200/30">
            <div className="flex items-center gap-3 mb-2">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-primary-100 text-sm">No Hire</span>
            </div>
            <div className="text-3xl font-bold text-red-400">
              {loadingStats ? '...' : dashboardStats?.recommendations?.no_hire || 0}
            </div>
          </div>

          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-5 border border-primary-200/30">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="w-5 h-5 text-purple-400" />
              <span className="text-primary-100 text-sm">Avg. Score</span>
            </div>
            <div className="text-3xl font-bold text-white">
              {loadingStats ? '...' : dashboardStats?.average_scores?.overall
                ? `${Math.round(dashboardStats.average_scores.overall)}%`
                : '-'}
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 mb-8 bg-primary-200/10 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('interviews')}
            className={`px-6 py-3 rounded-md font-semibold transition-colors ${activeTab === 'interviews'
              ? 'bg-white text-primary-300'
              : 'text-white hover:bg-primary-200/20'
              }`}
          >
            Interviews
          </button>
          <button
            onClick={() => setActiveTab('candidates')}
            className={`px-6 py-3 rounded-md font-semibold transition-colors ${activeTab === 'candidates'
              ? 'bg-white text-primary-300'
              : 'text-white hover:bg-primary-200/20'
              }`}
          >
            Candidates
            {hirableCandidates.length > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-green-500 text-white text-xs rounded-full">
                {hirableCandidates.length} hirable
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('jobs')}
            className={`px-6 py-3 rounded-md font-semibold transition-colors ${activeTab === 'jobs'
              ? 'bg-white text-primary-300'
              : 'text-white hover:bg-primary-200/20'
              }`}
          >
            Job Positions
          </button>
        </div>

        {/* Interviews Tab */}
        {activeTab === 'interviews' && (
          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-6 border border-primary-200/30">
            <div className="mb-8">
              <FileUploadDemo />
            </div>

            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
                <FileText className="w-6 h-6" />
                All Candidates
              </h2>
              <span className="text-primary-100">
                {dashboardCandidates.length} total
              </span>
            </div>

            {loadingCandidates ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : dashboardCandidates.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="w-16 h-16 text-white/30 mx-auto mb-4" />
                <p className="text-white/60">No interviews yet</p>
                <p className="text-white/40 text-sm">Upload resumes above to start scheduling interviews</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Candidate</th>
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Position</th>
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Date</th>
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Score</th>
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Status</th>
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Recommendation</th>
                      <th className="text-left py-3 px-4 text-white/80 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardCandidates.map((candidate) => (
                      <tr key={candidate.interview_id} className="border-b border-white/5 hover:bg-white/5">
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-3">
                            <div className="bg-blue-500/20 rounded-full p-2">
                              <User className="w-5 h-5 text-blue-300" />
                            </div>
                            <div>
                              <span className="text-white font-medium block">{candidate.candidate_name || 'Unknown'}</span>
                              <span className="text-white/50 text-sm break-all">{candidate.candidate_email}</span>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-white/80">{candidate.job_title || '-'}</td>
                        <td className="py-4 px-4 text-white/80">{formatDate(candidate.interview_completed_at)}</td>
                        <td className="py-4 px-4">
                          {candidate.assessment?.overall_score !== undefined ? (
                            <span className="text-white font-semibold">
                              {Math.round(candidate.assessment.overall_score)}%
                            </span>
                          ) : (
                            <span className="text-white/50">-</span>
                          )}
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(candidate.status)}`}>
                            {candidate.status}
                          </span>
                        </td>
                        <td className="py-4 px-4">
                          {candidate.assessment?.recommendation ? (
                            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getRecommendationColor(candidate.assessment.recommendation)}`}>
                              {candidate.assessment.recommendation}
                            </span>
                          ) : (
                            <span className="text-white/50">-</span>
                          )}
                        </td>
                        <td className="py-4 px-4">
                          <button
                            onClick={() => router.push(`/interview-summary?id=${candidate.interview_id}`)}
                            className="text-blue-400 hover:text-blue-300 font-medium"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Candidates Tab - Hirable Focus */}
        {activeTab === 'candidates' && (
          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-6 border border-primary-200/30">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
                <Award className="w-6 h-6 text-green-400" />
                Potential Hires
              </h2>
              <div className="flex gap-2">
                {(['all', 'hire', 'assessed', 'pending'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setCandidateFilter(filter)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${candidateFilter === filter
                      ? 'bg-white text-primary-300'
                      : 'bg-white/10 text-white hover:bg-white/20'
                      }`}
                  >
                    {filter === 'all' ? 'All' : filter === 'hire' ? 'Recommended' : filter.charAt(0).toUpperCase() + filter.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {loadingCandidates ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : filteredCandidates.length === 0 ? (
              <div className="text-center py-12">
                <Award className="w-16 h-16 text-white/30 mx-auto mb-4" />
                <p className="text-white/60">No candidates match this filter</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredCandidates.map((candidate) => (
                  <div
                    key={candidate.interview_id}
                    className="bg-primary-200/10 rounded-xl p-5 border border-primary-200/20 hover:border-primary-200/40 transition-colors cursor-pointer"
                    onClick={() => router.push(`/interview-summary?id=${candidate.interview_id}`)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="bg-blue-500/20 rounded-full p-2">
                          <User className="w-5 h-5 text-blue-300" />
                        </div>
                        <div>
                          <h4 className="text-white font-semibold">{candidate.candidate_name || 'Unknown'}</h4>
                          <p className="text-white/50 text-sm">{candidate.job_title || 'No position'}</p>
                        </div>
                      </div>
                      {candidate.assessment?.recommendation && (
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getRecommendationColor(candidate.assessment.recommendation)}`}>
                          {candidate.assessment.recommendation}
                        </span>
                      )}
                    </div>

                    {candidate.assessment && (
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-white/60">Overall Score</span>
                          <span className="text-white font-semibold">{Math.round(candidate.assessment.overall_score)}%</span>
                        </div>
                        <div className="w-full bg-primary-300/30 rounded-full h-2">
                          <div
                            className="bg-green-400 h-2 rounded-full transition-all"
                            style={{ width: `${candidate.assessment.overall_score}%` }}
                          ></div>
                        </div>
                        <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
                          <div className="text-center">
                            <div className="text-white/60">Technical</div>
                            <div className="text-white font-medium">{Math.round(candidate.assessment.technical_score || 0)}%</div>
                          </div>
                          <div className="text-center">
                            <div className="text-white/60">Comm.</div>
                            <div className="text-white font-medium">{Math.round(candidate.assessment.communication_score || 0)}%</div>
                          </div>
                          <div className="text-center">
                            <div className="text-white/60">Soft Skills</div>
                            <div className="text-white font-medium">{Math.round(candidate.assessment.soft_skills_score || 0)}%</div>
                          </div>
                        </div>
                      </div>
                    )}

                    {!candidate.assessment && (
                      <div className="text-center py-4">
                        <span className={`px-3 py-1 rounded-full text-sm ${getStatusColor(candidate.status)}`}>
                          {candidate.status}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Job Positions Tab */}
        {activeTab === 'jobs' && (
          <div className="bg-primary-200/20 backdrop-blur-sm rounded-xl p-6 border border-primary-200/30">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-white">Job Position Management</h2>
              <p className="text-primary-100 text-sm">
                Create job positions before uploading resumes to match candidates
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Job Position Form */}
              <div className="lg:col-span-1 bg-primary-200/10 rounded-xl p-5 border border-primary-200/20">
                <h3 className="text-lg font-semibold text-white mb-4">
                  {editingJobPositionId ? 'Edit Position' : 'Add New Position'}
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-primary-100 mb-1">Title *</label>
                    <input
                      value={templateTitle}
                      onChange={(e) => setTemplateTitle(e.target.value)}
                      placeholder="e.g., Senior Backend Engineer"
                      className="w-full rounded-lg bg-transparent border border-primary-200/40 text-white px-3 py-2 focus:outline-none focus:border-white/60"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-primary-100 mb-1">Department</label>
                    <input
                      value={templateDepartment}
                      onChange={(e) => setTemplateDepartment(e.target.value)}
                      placeholder="e.g., Engineering"
                      className="w-full rounded-lg bg-transparent border border-primary-200/40 text-white px-3 py-2 focus:outline-none focus:border-white/60"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-primary-100 mb-1">Description</label>
                    <textarea
                      value={templateContent}
                      onChange={(e) => setTemplateContent(e.target.value)}
                      placeholder="Role summary, responsibilities, requirements..."
                      className="w-full min-h-[120px] rounded-lg bg-transparent border border-primary-200/40 text-white px-3 py-2 focus:outline-none focus:border-white/60"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-primary-100 mb-1">Required Skills</label>
                    <div className="flex gap-2 mb-2">
                      <input
                        value={skillInput}
                        onChange={(e) => setSkillInput(e.target.value)}
                        onKeyDown={handleSkillKeyDown}
                        placeholder="e.g., React, Python"
                        className="flex-1 rounded-lg bg-transparent border border-primary-200/40 text-white px-3 py-2 focus:outline-none focus:border-white/60"
                      />
                      <button
                        type="button"
                        onClick={addSkill}
                        className="px-4 py-2 bg-primary-200/40 hover:bg-primary-200/60 text-white rounded-lg transition-colors"
                      >
                        Add
                      </button>
                    </div>
                    {templateSkills.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {templateSkills.map((skill, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center gap-1 px-3 py-1 bg-primary-200/20 border border-primary-200/40 text-white rounded-full text-sm"
                          >
                            {skill}
                            <button
                              type="button"
                              onClick={() => removeSkill(skill)}
                              className="ml-1 hover:text-red-300 transition-colors"
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Interview Settings Section */}
                  <div className="mt-4 pt-4 border-t border-primary-200/20">
                    <h4 className="text-sm font-medium text-white mb-3">Interview Settings</h4>

                    {/* Coding Round Toggle */}
                    <div className="flex items-center justify-between mb-3">
                      <label className="text-sm text-primary-100">Enable Coding Round</label>
                      <button
                        type="button"
                        onClick={() => {
                          if (!hasCodingAccess && !hasCodingRound) {
                            setShowUpgradeModal(true);
                          } else {
                            setHasCodingRound(!hasCodingRound);
                          }
                        }}
                        className={`w-12 h-6 rounded-full transition-colors ${hasCodingRound ? 'bg-green-500' : 'bg-primary-200/40'}`}
                      >
                        <div className={`w-5 h-5 rounded-full bg-white transition-transform ${hasCodingRound ? 'translate-x-6' : 'translate-x-0.5'}`} />
                      </button>
                    </div>

                    {showUpgradeModal && (
                      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                        <div className="bg-[#1e1e1e] border border-primary-200/30 rounded-xl p-6 max-w-md w-full shadow-2xl">
                          <div className="flex items-center gap-3 mb-4 text-yellow-400">
                            <Award className="w-8 h-8" />
                            <h3 className="text-xl font-bold">Premium Feature</h3>
                          </div>

                          <p className="text-white/80 mb-6 leading-relaxed">
                            Coding rounds are not available in the free trial. This is a chargeable feature.
                          </p>

                          <div className="bg-primary-200/10 rounded-lg p-4 mb-6 border border-primary-200/20">
                            <p className="text-sm text-primary-100 mb-1">To enable access, please contact:</p>
                            <p className="text-white font-mono select-all">pavanchakravarthy2000@gmail.com</p>
                          </div>

                          <div className="flex justify-end">
                            <button
                              onClick={() => setShowUpgradeModal(false)}
                              className="px-4 py-2 bg-white text-primary-300 font-medium rounded-lg hover:bg-white/90 transition-colors"
                            >
                              Close
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {hasCodingRound && (
                      <div className="space-y-3 mb-3 pl-2 border-l-2 border-primary-200/30">
                        <div>
                          <label className="block text-xs text-primary-100 mb-1">Coding Time (minutes)</label>
                          <input
                            type="number"
                            value={codingTimeLimit}
                            onChange={(e) => setCodingTimeLimit(Number(e.target.value))}
                            min={5}
                            max={180}
                            className="w-full rounded-lg bg-transparent border border-primary-200/40 text-white px-3 py-1.5 text-sm focus:outline-none focus:border-white/60"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-primary-100 mb-1">Allowed Languages</label>
                          <div className="flex flex-wrap gap-2">
                            {['python', 'javascript', 'java', 'c++', 'go', 'rust'].map((lang) => (
                              <button
                                key={lang}
                                type="button"
                                onClick={() => {
                                  if (allowedLanguages.includes(lang)) {
                                    setAllowedLanguages(allowedLanguages.filter(l => l !== lang));
                                  } else {
                                    setAllowedLanguages([...allowedLanguages, lang]);
                                  }
                                }}
                                className={`px-2 py-1 rounded text-xs transition-colors ${allowedLanguages.includes(lang)
                                  ? 'bg-blue-500 text-white'
                                  : 'bg-primary-200/20 text-white/70 hover:bg-primary-200/40'
                                  }`}
                              >
                                {lang}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Coding Questions from Bank */}
                        <div>
                          <label className="block text-xs text-primary-100 mb-1">
                            Coding Questions
                            {selectedCodingQuestionIds.length > 0 && (
                              <span className="ml-1 text-green-400">({selectedCodingQuestionIds.length} selected)</span>
                            )}
                          </label>
                          {loadingCodingQuestions ? (
                            <div className="text-xs text-white/50 py-2">Loading questions...</div>
                          ) : availableCodingQuestions.length > 0 ? (
                            <div className="max-h-40 overflow-y-auto space-y-1 rounded border border-primary-200/20 p-2">
                              {availableCodingQuestions.map((q) => (
                                <label
                                  key={q.id}
                                  className={`flex items-start gap-2 p-1.5 rounded cursor-pointer hover:bg-primary-200/20 ${selectedCodingQuestionIds.includes(q.id) ? 'bg-primary-200/20' : ''
                                    }`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedCodingQuestionIds.includes(q.id)}
                                    onChange={() => {
                                      setSelectedCodingQuestionIds(prev =>
                                        prev.includes(q.id)
                                          ? prev.filter(id => id !== q.id)
                                          : [...prev, q.id]
                                      );
                                    }}
                                    className="mt-0.5 accent-green-500"
                                  />
                                  <div className="flex-1 min-w-0">
                                    <div className="text-xs text-white truncate">{q.title}</div>
                                    <div className="text-[10px] text-white/50">
                                      {q.difficulty && <span className={`mr-2 ${q.difficulty === 'easy' ? 'text-green-400' :
                                        q.difficulty === 'medium' ? 'text-yellow-400' : 'text-red-400'
                                        }`}>{q.difficulty}</span>}
                                      {q.language && <span>{q.language}</span>}
                                    </div>
                                  </div>
                                </label>
                              ))}
                            </div>
                          ) : (
                            <div className="text-xs text-white/40 py-2">No coding questions available in the bank</div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Difficulty Level */}
                    <div className="mb-3">
                      <label className="block text-xs text-primary-100 mb-1">Difficulty Level</label>
                      <div className="flex gap-2">
                        {(['easy', 'medium', 'hard'] as const).map((level) => (
                          <button
                            key={level}
                            type="button"
                            onClick={() => setDifficulty(level)}
                            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${difficulty === level
                              ? level === 'easy' ? 'bg-green-500 text-white'
                                : level === 'medium' ? 'bg-yellow-500 text-white'
                                  : 'bg-red-500 text-white'
                              : 'bg-primary-200/20 text-white/70 hover:bg-primary-200/40'
                              }`}
                          >
                            {level.charAt(0).toUpperCase() + level.slice(1)}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Q&A Settings */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-primary-100 mb-1">Q&A Questions</label>
                        <input
                          type="number"
                          value={qaQuestionCount}
                          onChange={(e) => setQaQuestionCount(Number(e.target.value))}
                          min={1}
                          max={20}
                          className="w-full rounded-lg bg-transparent border border-primary-200/40 text-white px-3 py-1.5 text-sm focus:outline-none focus:border-white/60"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-primary-100 mb-1">Time/Question (min)</label>
                        <input
                          type="number"
                          value={qaTimePerQuestion}
                          onChange={(e) => setQaTimePerQuestion(Number(e.target.value))}
                          min={1}
                          max={10}
                          className="w-full rounded-lg bg-transparent border border-primary-200/40 text-white px-3 py-1.5 text-sm focus:outline-none focus:border-white/60"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3 mt-4">
                    <button
                      onClick={saveJobPosition}
                      disabled={savingJobPosition || !templateTitle.trim()}
                      className="flex-1 bg-white text-primary-300 py-2 px-4 rounded-lg font-semibold hover:bg-primary-100 hover:text-white transition-colors disabled:opacity-50"
                    >
                      {savingJobPosition ? 'Saving...' : editingJobPositionId ? 'Update Position' : 'Create Position'}
                    </button>
                    {editingJobPositionId && (
                      <button
                        onClick={resetJobPositionForm}
                        className="px-4 py-2 rounded-lg font-semibold text-white bg-primary-200/40 hover:bg-primary-200/60 transition-colors"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Job Positions List */}
              <div className="lg:col-span-2">
                {loadingJobPositions ? (
                  <div className="flex justify-center py-12">
                    <div className="w-8 h-8 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
                  </div>
                ) : jobPositions.length === 0 ? (
                  <div className="text-center py-12 border border-primary-200/20 rounded-xl">
                    <FileText className="w-16 h-16 text-white/30 mx-auto mb-4" />
                    <p className="text-white/70 mb-2">No job positions yet</p>
                    <p className="text-white/50 text-sm">Create your first job position to start matching candidates</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {jobPositions.map((job) => (
                      <div key={job.id} className="bg-primary-200/10 rounded-xl p-5 border border-primary-200/20">
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div>
                            <h4 className="text-white font-semibold">{job.title}</h4>
                            {job.department && <p className="text-primary-100 text-sm">{job.department}</p>}
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => editJobPosition(job)}
                              className="text-white/80 hover:text-white text-sm font-medium"
                            >
                              Edit
                            </button>
                            <span className="text-white/20">|</span>
                            <button
                              onClick={() => deleteJobPosition(job.id)}
                              className="text-red-300/80 hover:text-red-300 text-sm font-medium"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                        {job.description && (
                          <p className="text-white/80 text-sm whitespace-pre-line mb-3 line-clamp-3">
                            {job.description}
                          </p>
                        )}
                        {job.required_skills && job.required_skills.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-primary-200/20">
                            <div className="flex flex-wrap gap-1.5">
                              {job.required_skills.map((skill, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 bg-primary-200/10 border border-primary-200/30 text-white/90 rounded text-xs"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {/* Interview Settings Summary */}
                        {job.interview_settings && (
                          <div className="mt-3 pt-3 border-t border-primary-200/20">
                            <div className="flex flex-wrap gap-2 text-xs">
                              {job.interview_settings.has_coding_round && (
                                <span className="px-2 py-0.5 bg-green-500/20 text-green-300 border border-green-500/30 rounded">
                                  Coding Round
                                </span>
                              )}
                              {job.interview_settings.qa_question_count && (
                                <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded">
                                  {job.interview_settings.qa_question_count} Q&A
                                </span>
                              )}
                              {job.interview_settings.coding_time_limit && (
                                <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded">
                                  {Math.round(job.interview_settings.coding_time_limit / 60)}min coding
                                </span>
                              )}
                              {job.interview_settings.allowed_languages && job.interview_settings.allowed_languages.length > 0 && (
                                <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 rounded">
                                  {job.interview_settings.allowed_languages.join(', ')}
                                </span>
                              )}
                              {job.interview_settings.coding_question_ids && job.interview_settings.coding_question_ids.length > 0 && (
                                <span className="px-2 py-0.5 bg-orange-500/20 text-orange-300 border border-orange-500/30 rounded">
                                  {job.interview_settings.coding_question_ids.length} coding Q
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
