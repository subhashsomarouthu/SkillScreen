// Import centralized config
import { API_BASE_URL } from './config';

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  error?: string;
  meta: {
    timestamp: string;
    request_id: string;
    version: string;
  };
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: string;
    organization_id: string;
  };
  expires_in: number;
}

export interface SignupRequest {
  // Organization
  company_name: string;
  company_domain?: string;
  // User
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role?: 'recruiter' | 'hiring_manager' | 'team_lead' | 'hr' | 'admin';
  // Interview template (optional)
  interview_type?: 'behavioral' | 'technical' | 'coding' | 'system_design';
  job_role_name?: string;
  questions?: any[];
}

export interface SignupResponse {
  message: string;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: string;
  };
  organization: {
    id: string;
    name: string;
    domain: string | null;
  };
  interview_template?: any;
}

export interface User {
  id: number;
  name: string;
  email: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;

    const defaultHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add Authorization header if token exists
    const token = this.getToken();
    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const config: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    try {
      const stored = window.localStorage.getItem('intervuai_auth_token');
      if (!stored) return null;
      const parsed = JSON.parse(stored);
      return parsed.token || null;
    } catch {
      return null;
    }
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<ApiResponse<LoginResponse>> {
    return this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async signup(data: SignupRequest): Promise<ApiResponse<SignupResponse>> {
    return this.request<SignupResponse>('/user/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAuthHealth(): Promise<ApiResponse> {
    return this.request('/auth/health');
  }

  // User endpoints
  async getUsers(): Promise<ApiResponse<{ users: User[] }>> {
    return this.request<{ users: User[] }>('/user/users');
  }

  async getUserById(id: number): Promise<ApiResponse<{ user: User }>> {
    return this.request<{ user: User }>(`/user/users/${id}`);
  }

  async getUserHealth(): Promise<ApiResponse> {
    return this.request('/user/health');
  }

  async getMe(): Promise<ApiResponse<{ user: User & { organization?: any } }>> {
    return this.request<{ user: User & { organization?: any } }>('/user/me');
  }

  // Assessment endpoints
  async getQuestions(): Promise<ApiResponse<{ questions: string[] }>> {
    return this.request<{ questions: string[] }>('/assessment/questions');
  }

  async submitAssessment(answer: any): Promise<ApiResponse<{ status: string; answer: any }>> {
    return this.request<{ status: string; answer: any }>('/assessment/submit', {
      method: 'POST',
      body: JSON.stringify(answer),
    });
  }

  // Coding endpoints
  async getProblems(): Promise<ApiResponse<{ problems: string[] }>> {
    return this.request<{ problems: string[] }>('/coding/problems');
  }

  async submitSolution(solution: any): Promise<ApiResponse<{ status: string; solution: any }>> {
    return this.request<{ status: string; solution: any }>('/coding/submit', {
      method: 'POST',
      body: JSON.stringify(solution),
    });
  }

  // Audio-AI endpoints (via gateway -> audio-ai-service)
  async audioProcess(payload: {
    media_url: string;
    session_id?: string;
    candidate_id?: string;
  }): Promise<ApiResponse<any>> {
    // Create abort controller with 10 minute timeout for audio processing
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes

    try {
      const result = await this.request<any>('/audio-ai/api/v1/audio/process', {
        method: 'POST',
        body: JSON.stringify({
          media_url: payload.media_url,
          session_id: payload.session_id ?? 'test-session',
          candidate_id: payload.candidate_id ?? 'test-candidate',
        }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return result;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  async audioTranscribe(payload: {
    media_url: string;
    session_id?: string;
    candidate_id?: string;
  }): Promise<ApiResponse<any>> {
    // Create abort controller with 10 minute timeout for transcription
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes

    try {
      const result = await this.request<any>('/audio-ai/api/audio/transcribe', {
        method: 'POST',
        body: JSON.stringify({
          media_url: payload.media_url,
          session_id: payload.session_id ?? 'test-session',
          candidate_id: payload.candidate_id ?? 'test-candidate',
        }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return result;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  // =========================================
  // Interview Management Methods
  // =========================================

  async getUserInterviews(userId: string): Promise<ApiResponse<{ interviews: any[]; count: number }>> {
    return this.request<{ interviews: any[]; count: number }>(`/media/api/interviews`);
  }

  async getAllInterviews(): Promise<ApiResponse<{ interviews: any[]; count: number }>> {
    // Fetch from media-service and interview-service, then merge
    const [mediaRes, interviewSvcRes] = await Promise.all([
      this.request<{ interviews: any[]; count: number }>('/media/api/interviews'),
      this.request<{ interviews: any[]; count: number }>('/interview/api/interviews').catch(() => ({ success: true, data: { interviews: [], count: 0 }, meta: { timestamp: '', request_id: '', version: '' } } as any))
    ]);

    const mediaList = mediaRes?.data?.interviews ?? [];
    const svcList = interviewSvcRes?.data?.interviews ?? [];

    // De-duplicate by interview_id if present, else by session_id
    const map = new Map<string, any>();
    [...mediaList, ...svcList].forEach((i: any) => {
      const key = i.interview_id || i.session_id || JSON.stringify(i);
      if (!map.has(key)) map.set(key, i);
    });

    const merged = Array.from(map.values());
    return { success: true, data: { interviews: merged, count: merged.length }, meta: mediaRes.meta } as ApiResponse<any>;
  }

  async getInterviewDetails(interviewId: string): Promise<ApiResponse<any>> {
    if (!interviewId) return Promise.reject(new Error('Interview ID is required'));

    // Fetch from interview service (primary source) and assessment service
    const [interviewRes, assessmentRes] = await Promise.all([
      this.request<any>(`/interview/api/interviews/${interviewId}`).catch(() => null),
      this.request<any>(`/assessment/v1/assessment/interview/${interviewId}`).catch(() => null),
    ]);

    // If interview service returns data, use it as base
    if (interviewRes?.success && interviewRes.data) {
      const interview = interviewRes.data;

      // Assessment service returns data directly (not wrapped in {success, data})
      const assessmentAny = assessmentRes as any;
      const assessment = assessmentRes?.success
        ? assessmentRes.data
        : (assessmentAny?.overall_score !== undefined ? assessmentAny : null);

      if (assessment) {
        // Build categories from available scores
        const categories: { name: string; score: number; feedback: string }[] = [
          { name: 'Technical Proficiency', score: assessment.technical_score || 0, feedback: '' },
          { name: 'Communication', score: assessment.communication_score || 0, feedback: '' },
          { name: 'Soft Skills', score: assessment.soft_skills_score || 0, feedback: '' },
        ];

        // Add Coding category if coding results exist in evidence_clips
        const codingResults = assessment.evidence_clips?.service_results?.coding;
        if (codingResults?.length > 0) {
          const codingScore = codingResults[0]?.execution_results?.correctness_score ?? 0;
          categories.push({ name: 'Coding', score: codingScore, feedback: '' });
        }

        // Extract key_strengths and areas_for_improvement from evidence_clips
        const serviceResults = assessment.evidence_clips?.service_results || {};
        const strengths: string[] = [];
        const improvements: string[] = [];

        // From text analysis
        (serviceResults.text || []).forEach((t: any) => {
          if (t.strengths) strengths.push(...t.strengths);
          if (t.areas_for_improvement) improvements.push(...t.areas_for_improvement);
        });
        // From audio analysis
        (serviceResults.audio || []).forEach((a: any) => {
          if (a.communication_score?.strengths) strengths.push(...a.communication_score.strengths);
          if (a.communication_score?.areas_for_improvement) improvements.push(...a.communication_score.areas_for_improvement);
        });
        // From video analysis
        (serviceResults.video || []).forEach((v: any) => {
          if (v.performance?.strengths) strengths.push(...v.performance.strengths);
          if (v.performance?.recommendations?.length) improvements.push(...v.performance.recommendations);
        });

        // Deduplicate
        const uniqueStrengths = [...new Set(strengths)];
        const uniqueImprovements = [...new Set(improvements)];

        interview.analysis = {
          overall_score: assessment.overall_score || 0,
          recommendation: assessment.recommendation || 'needs_review',
          categories,
          key_strengths: uniqueStrengths,
          areas_for_improvement: uniqueImprovements,
          executive_summary: assessment.summary || '',
          reviewer_notes: assessment.reviewer_notes || '',
          proctoring_risk_score: assessment.proctoring_risk_score,
          evidence_clips: assessment.evidence_clips,
        };
      }

      return { success: true, data: interview, meta: interviewRes.meta };
    }

    // Fallback to media service (legacy path)
    return this.request<any>(`/media/api/interviews/${interviewId}`);
  }

  async updateInterviewTranscript(interviewId: string, transcript: any): Promise<ApiResponse<any>> {
    return this.request<any>(`/media/api/interviews/${interviewId}/transcript`, {
      method: 'POST',
      body: JSON.stringify(transcript),
    });
  }

  async updateInterviewStatus(interviewId: string, status: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/interview/api/session/${interviewId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  // =========================================
  // Candidate/Resume Management Methods
  // =========================================

  async uploadResume(file: File, candidateName?: string): Promise<ApiResponse<any>> {
    const formData = new FormData();
    formData.append('file', file);
    if (candidateName) {
      formData.append('candidate_name', candidateName);
    }

    const url = `${this.baseUrl}/media/api/resumes/upload`;
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    return response.json();
  }

  async getAllCandidates(): Promise<ApiResponse<{ candidates: any[]; count: number }>> {
    return this.request<{ candidates: any[]; count: number }>('/media/api/candidates');
  }

  async getUserCandidates(userId: string): Promise<ApiResponse<{ candidates: any[]; count: number }>> {
    return this.request<{ candidates: any[]; count: number }>(`/media/api/candidates`);
  }

  async getCandidate(candidateId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/media/api/candidates/${candidateId}`);
  }

  async scheduleCandidate(candidateId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/media/api/candidates/${candidateId}/schedule`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async updateCandidateStatus(candidateId: string, status: string, interviewId?: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/media/api/candidates/${candidateId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, interview_id: interviewId }),
    });
  }

  // =========================================
  // Interview Session Management Methods
  // =========================================

  async createInterviewSession(userId: string, candidateId?: string): Promise<ApiResponse<any>> {
    return this.request<any>('/interview/api/session/create', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        candidate_id: candidateId,
      }),
    });
  }

  async getInterviewSession(sessionId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/interview/api/session/${sessionId}`);
  }

  async updateSessionStatus(sessionId: string, status: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/interview/api/session/${sessionId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  async saveSessionTranscript(sessionId: string, transcript: any): Promise<ApiResponse<any>> {
    return this.request<any>(`/interview/api/session/${sessionId}/transcript`, {
      method: 'POST',
      body: JSON.stringify(transcript),
    });
  }

  async getTranscriptionResult(sessionId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/audio-ai/api/v1/audio/results/${sessionId}`);
  }

  // =========================================
  // AI Logic Service Methods (Question Generation, Resume Parsing)
  // =========================================

  async parseResumeWithAI(file: File): Promise<ApiResponse<any>> {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${this.baseUrl}/text-service/resumes/parse`;
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    return response.json();
  }

  // Upload resumes and create interviews via interview-service
  async uploadResumeForParsing(files: File | File[], params: {
    organization_id: string;
    job_position_id: string;
    mode?: string;
    max_questions?: number;
    difficulty?: string;
    interview_type?: string;
    target_duration_minutes?: number;
  }): Promise<ApiResponse<any>> {
    const formData = new FormData();
    const fileArray = Array.isArray(files) ? files : [files];

    // Append all files to formData
    fileArray.forEach((file) => {
      formData.append('files', file);
    });

    // Append required params
    formData.append('organization_id', params.organization_id);
    formData.append('job_position_id', params.job_position_id);

    // Append optional interview settings
    if (params.mode) formData.append('mode', params.mode);
    if (params.max_questions) formData.append('max_questions', String(params.max_questions));
    if (params.difficulty) formData.append('difficulty', params.difficulty);
    if (params.interview_type) formData.append('interview_type', params.interview_type);
    if (params.target_duration_minutes) formData.append('target_duration_minutes', String(params.target_duration_minutes));

    const url = `${this.baseUrl}/interview/resumes/upload`;
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    // Don't set Content-Type - let browser set it with boundary for multipart/form-data

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    // Handle non-JSON / error responses gracefully so the UI doesn't crash on 500s
    let payload: any = null;
    try {
      const text = await response.text();
      try {
        payload = text ? JSON.parse(text) : null;
      } catch {
        // Backend may return plain text ("Internal Server Error"), wrap it
        payload = {
          success: false,
          data: null,
          error: text || `Request failed with status ${response.status}`,
          meta: {
            timestamp: new Date().toISOString(),
            request_id: '',
            version: 'v1',
          },
        };
      }
    } catch (e) {
      // If even reading text fails, surface a generic error
      payload = {
        success: false,
        data: null,
        error: (e as Error).message || 'Upload failed',
        meta: {
          timestamp: new Date().toISOString(),
          request_id: '',
          version: 'v1',
        },
      };
    }

    if (!response.ok) {
      // Normalize error shape for callers
      return (payload && typeof payload === 'object' && 'success' in payload)
        ? payload
        : {
          success: false,
          data: null,
          error: `Upload failed with status ${response.status}`,
          meta: {
            timestamp: new Date().toISOString(),
            request_id: '',
            version: 'v1',
          },
        };
    }

    return payload as ApiResponse<any>;
  }

  async createAICandidate(candidateData: {
    name: string;
    email: string;
    phone?: string;
    resume_text: string;
    skills: string[];
    experience_years: number;
    education?: any[];
  }): Promise<ApiResponse<any>> {
    const url = `${this.baseUrl}/text-service/candidates`;
    const token = this.getToken();

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: JSON.stringify(candidateData),
    });

    return response.json();
  }

  async createAIJob(jobData: {
    title: string;
    company: string;
    description: string;
    required_skills: string[];
    experience_level: string;
  }): Promise<ApiResponse<any>> {
    const url = `${this.baseUrl}/text-service/jobs`;
    const token = this.getToken();

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: JSON.stringify(jobData),
    });

    return response.json();
  }

  async startAIInterview(data: {
    candidate_id: string;
    job_id: string;
    interview_type?: string;
    difficulty?: string;
    max_questions?: number;
  }): Promise<ApiResponse<any>> {
    const url = `${this.baseUrl}/text-service/interviews/start`;
    const token = this.getToken();

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: JSON.stringify({
        candidate_id: data.candidate_id,
        job_id: data.job_id,
        interview_type: data.interview_type || 'standard',
        difficulty: data.difficulty || 'medium',
        max_questions: data.max_questions || 9,
        target_duration_minutes: 30
      }),
    });

    return response.json();
  }

  async getInterviewQuestions(sessionId: string): Promise<ApiResponse<any>> {
    const url = `${this.baseUrl}/text-service/interviews/${sessionId}/questions`;
    const token = this.getToken();

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
    });

    return response.json();
  }

  async sendInterviewInvitation(data: {
    candidate_email: string;
    candidate_name: string;
    candidate_id: string;
    session_id: string;
    job_position_id?: string;
    recruiter_name?: string;
    company_name?: string;
    expires_in_hours?: number;
  }): Promise<ApiResponse<any>> {
    const url = `${this.baseUrl}/interview/api/email/send-invitation`;
    const token = this.getToken();

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: JSON.stringify(data),
    });

    return response.json();
  }

  // =========================================
  // Job Position Methods
  // =========================================

  async getJobPositions(organizationId: string): Promise<ApiResponse<{ job_positions: any[]; total: number }>> {
    return this.request<{ job_positions: any[]; total: number }>(`/interview/job-positions?organization_id=${organizationId}`);
  }

  async createJobPosition(data: {
    organization_id: string;
    title: string;
    department?: string;
    description?: string;
    required_skills?: string[];
  }): Promise<ApiResponse<any>> {
    return this.request<any>('/interview/job-positions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateInterviewSettings(jobPositionId: string, settings: {
    has_coding_round?: boolean;
    coding_question_ids?: string[];
    coding_time_limit?: number;
    allowed_languages?: string[];
    qa_question_count?: number;
    qa_time_per_question?: number;
    total_time_limit?: number;
  }): Promise<ApiResponse<any>> {
    return this.request<any>(`/interview/job-positions/${jobPositionId}/interview-settings`, {
      method: 'PATCH',
      body: JSON.stringify(settings),
    });
  }

  async deleteJobPosition(jobPositionId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/interview/job-positions/${jobPositionId}`, {
      method: 'DELETE',
    });
  }

  // =========================================
  // Coding Questions Methods
  // =========================================

  async getCodingQuestions(params?: {
    difficulty?: string;
    language?: string;
  }): Promise<ApiResponse<any>> {
    const queryParams = new URLSearchParams();
    if (params?.difficulty) queryParams.append('difficulty', params.difficulty);
    if (params?.language) queryParams.append('language', params.language);
    const queryString = queryParams.toString();
    return this.request<any>(`/coding/v1/questions${queryString ? `?${queryString}` : ''}`);
  }

  // =========================================
  // Dashboard Methods (Assessment Service)
  // =========================================

  async getDashboardCandidates(params?: {
    job_position_id?: string;
    recommendation?: 'hire' | 'no_hire' | 'maybe' | 'needs_review';
    status?: 'assessed' | 'pending' | 'in_progress' | 'scheduled';
    min_score?: number;
    max_score?: number;
    page?: number;
    page_size?: number;
    sort_by?: 'overall_score' | 'created_at' | 'name' | 'recommendation';
    sort_order?: 'asc' | 'desc';
  }): Promise<ApiResponse<{
    candidates: Array<{
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
    }>;
    pagination: {
      page: number;
      page_size: number;
      total_count: number;
      total_pages: number;
      has_next: boolean;
      has_previous: boolean;
    };
  }>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    const queryString = queryParams.toString();
    return this.request(`/assessment/v1/dashboard/candidates${queryString ? `?${queryString}` : ''}`);
  }

  async getDashboardStats(jobPositionId?: string): Promise<ApiResponse<{
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
  }>> {
    const queryString = jobPositionId ? `?job_position_id=${jobPositionId}` : '';
    return this.request(`/assessment/v1/dashboard/stats${queryString}`);
  }

  async generatePendingAssessments(params?: {
    job_position_id?: string;
    limit?: number;
  }): Promise<ApiResponse<any>> {
    const queryParams = new URLSearchParams();
    if (params?.job_position_id) queryParams.append('job_position_id', params.job_position_id);
    if (params?.limit) queryParams.append('limit', String(params.limit));
    const queryString = queryParams.toString();
    return this.request(`/assessment/v1/dashboard/generate-pending${queryString ? `?${queryString}` : ''}`, {
      method: 'POST',
    });
  }
}

export const apiClient = new ApiClient();
export default apiClient;
