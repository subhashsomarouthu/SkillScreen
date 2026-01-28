'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, Play, Send, CheckCircle, XCircle, Loader2, Code2 } from 'lucide-react';
import { API_BASE_URL } from '@/lib/config';
import { getInterviewToken } from '@/lib/interviewToken';
import { useAuth } from '@/contexts/AuthContext';

interface CodingChallengeProps {
  userType: 'candidate' | 'recruiter';
  participantName: string;
  interviewId?: string;
  codingQuestionIds?: string[];
  language?: string;
  onComplete?: () => void;
}

interface TestResult {
  input: string;
  expectedOutput: string;
  actualOutput?: string;
  passed?: boolean;
  error?: string;
}

interface CodingQuestion {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  starter_code: string;
  test_cases: Array<{
    input: string;
    expected_output: string;
    is_hidden?: boolean;
  }>;
}

interface CodingSession {
  session_id: string;
  question_id: string;
  status: string;
  code?: string;
  is_correct?: boolean;
  score?: number;
}

// Language mapping for Judge0
const LANGUAGE_MAP: Record<string, { id: number; name: string; extension: string }> = {
  'python': { id: 71, name: 'Python', extension: '.py' },
  'javascript': { id: 63, name: 'JavaScript', extension: '.js' },
  'java': { id: 62, name: 'Java', extension: '.java' },
  'cpp': { id: 54, name: 'C++', extension: '.cpp' },
  'c': { id: 50, name: 'C', extension: '.c' },
};

export default function CodingChallenge({
  userType,
  participantName,
  interviewId,
  codingQuestionIds = [],
  language = 'python',
  onComplete
}: CodingChallengeProps) {
  const { getToken } = useAuth();

  // Question navigation state
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [questions, setQuestions] = useState<CodingQuestion[]>([]);
  const [sessions, setSessions] = useState<Map<string, CodingSession>>(new Map());
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(true);

  // Code editor state
  const [code, setCode] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState(language);

  // Execution state
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [executionSummary, setExecutionSummary] = useState<{
    passed: number;
    total: number;
    runtime?: number;
    memory?: number;
  } | null>(null);

  // Completion tracking
  const [submittedQuestions, setSubmittedQuestions] = useState<Set<string>>(new Set());

  // Get auth token
  const getAuthToken = useCallback(() => {
    const tokenData = getInterviewToken();
    return tokenData?.token || getToken();
  }, [getToken]);

  // Fetch questions on mount
  useEffect(() => {
    if (codingQuestionIds.length === 0) {
      setIsLoadingQuestions(false);
      return;
    }

    const fetchQuestions = async () => {
      setIsLoadingQuestions(true);
      const token = getAuthToken();

      try {
        const fetchedQuestions: CodingQuestion[] = [];

        for (const questionId of codingQuestionIds) {
          const response = await fetch(`${API_BASE_URL}/orchestration/api/coding/questions/${questionId}`, {
            headers: {
              'Content-Type': 'application/json',
              ...(token && { 'Authorization': `Bearer ${token}` })
            }
          });

          if (response.ok) {
            const data = await response.json();
            console.log('📝 Fetched question:', questionId, data);
            if (data.success && data.data) {
              // Map visible_test_cases to test_cases format
              const testCases = (data.data.visible_test_cases || data.data.test_cases || []).map((tc: any) => ({
                input: tc.input,
                expected_output: tc.expectedOutput || tc.expected_output,
                is_hidden: tc.isHidden || tc.is_hidden || false
              }));

              fetchedQuestions.push({
                id: data.data.id,
                title: data.data.title,
                description: data.data.description,
                difficulty: data.data.difficulty,
                starter_code: data.data.starter_code?.[selectedLanguage] || data.data.starter_code?.python || '',
                test_cases: testCases
              });
            }
          } else {
            console.error('Failed to fetch question:', questionId, response.status);
          }
        }

        setQuestions(fetchedQuestions);

        // Set initial code from first question
        if (fetchedQuestions.length > 0) {
          setCode(fetchedQuestions[0].starter_code || '# Write your solution here\n');
        }
      } catch (error) {
        console.error('Failed to fetch questions:', error);
      } finally {
        setIsLoadingQuestions(false);
      }
    };

    fetchQuestions();
  }, [codingQuestionIds, getAuthToken, selectedLanguage]);

  // Create or get coding session for current question
  const getOrCreateSession = useCallback(async (questionId: string): Promise<CodingSession | null> => {
    // Check if session already exists
    const existingSession = sessions.get(questionId);
    if (existingSession) {
      return existingSession;
    }

    // Create new session
    const token = getAuthToken();

    try {
      const response = await fetch(`${API_BASE_URL}/orchestration/api/coding/sessions/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({
          interview_id: interviewId,
          question_id: questionId,
          language: selectedLanguage
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('📋 Session created response:', data);
        if (data.success && data.data) {
          // Session ID is in data.data.session.id (not data.data.session_id)
          const sessionId = data.data.session?.id || data.data.session_id;
          if (sessionId) {
            const session: CodingSession = {
              session_id: sessionId,
              question_id: questionId,
              status: 'started'
            };
            setSessions(prev => new Map(prev).set(questionId, session));
            console.log('✅ Session stored:', session);
            return session;
          }
        }
      }
    } catch (error) {
      console.error('Failed to create session:', error);
    }

    return null;
  }, [sessions, interviewId, selectedLanguage, getAuthToken]);

  // Run code (test execution)
  const runCode = async () => {
    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) return;

    setIsRunning(true);
    setTestResults([]);
    setExecutionSummary(null);

    const token = getAuthToken();
    const session = await getOrCreateSession(currentQuestion.id);

    if (!session) {
      setIsRunning(false);
      alert('Failed to create coding session. Please try again.');
      return;
    }

    try {
      // Call the test endpoint to run against visible test cases
      const response = await fetch(`${API_BASE_URL}/orchestration/api/coding/sessions/${session.session_id}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({
          code: code,
          language: selectedLanguage
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('🧪 Test response:', data);
        if (data.success && data.data) {
          // Results are in test_results.results (from coding-service evaluate_code)
          const testData = data.data.test_results || data.data;
          const results = testData.results || data.data.results || [];
          const testResultsMapped: TestResult[] = results.map((r: any) => ({
            input: r.input || '',
            expectedOutput: r.expected_output || r.expectedOutput || '',
            actualOutput: r.actual_output || r.actualOutput || r.stdout || '',
            passed: r.passed,
            error: r.error || r.stderr
          }));

          setTestResults(testResultsMapped);
          setExecutionSummary({
            passed: results.filter((r: any) => r.passed).length,
            total: results.length,
            runtime: testData.totalExecutionTime || data.data.execution_time,
            memory: data.data.memory_usage
          });
        }
      } else {
        const errorData = await response.json();
        console.error('Run failed:', errorData);
        setTestResults([{
          input: '',
          expectedOutput: '',
          actualOutput: '',
          passed: false,
          error: errorData.detail || 'Execution failed'
        }]);
      }
    } catch (error) {
      console.error('Run error:', error);
      setTestResults([{
        input: '',
        expectedOutput: '',
        actualOutput: '',
        passed: false,
        error: 'Network error. Please try again.'
      }]);
    } finally {
      setIsRunning(false);
    }
  };

  // Submit solution
  const submitSolution = async () => {
    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) return;

    setIsSubmitting(true);
    setTestResults([]);
    setExecutionSummary(null);

    const token = getAuthToken();
    const session = await getOrCreateSession(currentQuestion.id);

    if (!session) {
      setIsSubmitting(false);
      alert('Failed to create coding session. Please try again.');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/orchestration/api/coding/sessions/${session.session_id}/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({
          code: code,
          language: selectedLanguage
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('📤 Submit response:', data);
        if (data.success && data.data) {
          const results = data.data.results || [];
          const testResultsMapped: TestResult[] = results.map((r: any) => ({
            input: r.input || '',
            expectedOutput: r.expected_output || r.expectedOutput || '',
            actualOutput: r.actual_output || r.actualOutput || r.stdout || '',
            passed: r.passed,
            error: r.error || r.stderr,
            hidden: r.hidden
          }));

          setTestResults(testResultsMapped);
          setExecutionSummary({
            passed: data.data.passed_count || results.filter((r: any) => r.passed).length,
            total: data.data.total_count || results.length,
            runtime: data.data.execution_time_ms || data.data.execution_time,
            memory: data.data.memory_used_kb || data.data.memory_usage
          });

          // Mark question as submitted
          setSubmittedQuestions(prev => new Set(prev).add(currentQuestion.id));

          // Update session status
          setSessions(prev => {
            const updated = new Map(prev);
            updated.set(currentQuestion.id, {
              ...session,
              status: 'submitted',
              code: code,
              is_correct: data.data.is_correct,
              score: data.data.score || data.data.score_percentage
            });
            return updated;
          });

          // Check if all questions are submitted
          const newSubmittedSet = new Set(submittedQuestions).add(currentQuestion.id);
          if (newSubmittedSet.size === questions.length && questions.length > 0) {
            // All questions submitted - show completion message
            setTimeout(() => {
              if (onComplete) {
                onComplete();
              }
            }, 2000);
          }
        }
      } else {
        const errorData = await response.json();
        console.error('Submit failed:', errorData);
        alert(errorData.detail || 'Submission failed. Please try again.');
      }
    } catch (error) {
      console.error('Submit error:', error);
      alert('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Navigate to next question
  const goToNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      const nextIndex = currentQuestionIndex + 1;
      setCurrentQuestionIndex(nextIndex);
      setCode(questions[nextIndex].starter_code || '# Write your solution here\n');
      setTestResults([]);
      setExecutionSummary(null);
    }
  };

  // Navigate to previous question
  const goToPrevQuestion = () => {
    if (currentQuestionIndex > 0) {
      const prevIndex = currentQuestionIndex - 1;
      setCurrentQuestionIndex(prevIndex);
      // Restore saved code if available
      const session = sessions.get(questions[prevIndex].id);
      setCode(session?.code || questions[prevIndex].starter_code || '# Write your solution here\n');
      setTestResults([]);
      setExecutionSummary(null);
    }
  };

  // Current question
  const currentQuestion = questions[currentQuestionIndex];
  const isCurrentQuestionSubmitted = currentQuestion ? submittedQuestions.has(currentQuestion.id) : false;
  const allQuestionsSubmitted = questions.length > 0 && submittedQuestions.size === questions.length;

  // Loading state
  if (isLoadingQuestions) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-white/80">Loading coding challenges...</p>
        </div>
      </div>
    );
  }

  // No questions state
  if (questions.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <Code2 className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-white/80">No coding questions available.</p>
          {onComplete && (
            <button
              onClick={onComplete}
              className="mt-4 px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg"
            >
              Continue
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex h-full">
      {/* Main Code Editor Area */}
      <div className="flex-1 flex flex-col">
        {/* Header with Question Navigation */}
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-gray-800">
          <div className="flex items-center space-x-4">
            {/* Question Navigation */}
            <button
              onClick={goToPrevQuestion}
              disabled={currentQuestionIndex === 0}
              className="p-2 rounded-lg hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-5 h-5 text-white" />
            </button>
            <span className="text-white font-medium">
              Question {currentQuestionIndex + 1} of {questions.length}
            </span>
            <button
              onClick={goToNextQuestion}
              disabled={currentQuestionIndex === questions.length - 1}
              className="p-2 rounded-lg hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-5 h-5 text-white" />
            </button>

            {/* Question Status Dots */}
            <div className="flex items-center space-x-2 ml-4">
              {questions.map((q, idx) => (
                <div
                  key={q.id}
                  className={`w-3 h-3 rounded-full cursor-pointer transition-all ${
                    idx === currentQuestionIndex
                      ? 'bg-blue-500 ring-2 ring-blue-300'
                      : submittedQuestions.has(q.id)
                      ? 'bg-green-500'
                      : 'bg-gray-600'
                  }`}
                  onClick={() => {
                    setCurrentQuestionIndex(idx);
                    const session = sessions.get(q.id);
                    setCode(session?.code || q.starter_code || '# Write your solution here\n');
                    setTestResults([]);
                    setExecutionSummary(null);
                  }}
                  title={`Question ${idx + 1}${submittedQuestions.has(q.id) ? ' (Submitted)' : ''}`}
                />
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Language Selector */}
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="bg-[#2A2A2A] text-white text-sm px-3 py-1.5 rounded-md border border-white/10 focus:outline-none focus:border-white/20"
              disabled={isCurrentQuestionSubmitted}
            >
              {Object.entries(LANGUAGE_MAP).map(([key, value]) => (
                <option key={key} value={key}>{value.name}</option>
              ))}
            </select>

            {/* Action Buttons */}
            <button
              onClick={runCode}
              disabled={isRunning || isSubmitting || isCurrentQuestionSubmitted}
              className="flex items-center space-x-2 px-4 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-md text-sm font-medium transition-all disabled:opacity-50"
            >
              {isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>Run</span>
            </button>

            <button
              onClick={submitSolution}
              disabled={isRunning || isSubmitting || isCurrentQuestionSubmitted}
              className={`flex items-center space-x-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all disabled:opacity-50 ${
                isCurrentQuestionSubmitted
                  ? 'bg-gray-500/20 text-gray-400'
                  : 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-400'
              }`}
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : isCurrentQuestionSubmitted ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>{isCurrentQuestionSubmitted ? 'Submitted' : 'Submit'}</span>
            </button>

            {/* Finish All Button */}
            {allQuestionsSubmitted && onComplete && (
              <button
                onClick={onComplete}
                className="flex items-center space-x-2 px-4 py-1.5 bg-purple-500 hover:bg-purple-600 text-white rounded-md text-sm font-medium transition-all"
              >
                <CheckCircle className="w-4 h-4" />
                <span>Finish Coding</span>
              </button>
            )}
          </div>
        </div>

        {/* Code Editor */}
        <div className="flex-1 bg-[#1E1E1E]">
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full h-full bg-transparent text-white font-mono text-sm p-4 resize-none focus:outline-none"
            placeholder="Write your solution here..."
            readOnly={userType === 'recruiter' || isCurrentQuestionSubmitted}
            spellCheck={false}
            data-allow-copy="true"
            data-allow-paste="true"
            data-allow-cut="true"
            data-allow-select="true"
          />
        </div>
      </div>

      {/* Right Panel - Question and Terminal */}
      <div className="w-[450px] flex flex-col border-l border-white/10">
        {/* Question Section */}
        <div className="h-1/2 border-b border-white/10 p-4 overflow-y-auto bg-gray-800/50">
          {currentQuestion && (
            <>
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-xl font-semibold text-white">{currentQuestion.title}</h2>
                  {isCurrentQuestionSubmitted && (
                    <span className="flex items-center text-green-400 text-sm">
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Submitted
                    </span>
                  )}
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  currentQuestion.difficulty === 'easy' ? 'bg-green-500/20 text-green-300' :
                  currentQuestion.difficulty === 'medium' ? 'bg-yellow-500/20 text-yellow-300' :
                  'bg-red-500/20 text-red-300'
                }`}>
                  {currentQuestion.difficulty?.charAt(0).toUpperCase() + currentQuestion.difficulty?.slice(1)}
                </span>
              </div>
              <div className="text-white/80 text-sm whitespace-pre-line leading-relaxed">
                {currentQuestion.description}
              </div>

              {/* Sample Test Cases */}
              {currentQuestion.test_cases && currentQuestion.test_cases.filter(tc => !tc.is_hidden).length > 0 && (
                <div className="mt-6">
                  <h3 className="text-white font-medium mb-3">Examples:</h3>
                  {currentQuestion.test_cases.filter(tc => !tc.is_hidden).slice(0, 2).map((tc, idx) => (
                    <div key={idx} className="mb-4 bg-gray-700/30 rounded-lg p-3">
                      <div className="text-white/60 text-xs mb-1">Input:</div>
                      <code className="text-green-400 text-sm">{tc.input}</code>
                      <div className="text-white/60 text-xs mt-2 mb-1">Expected Output:</div>
                      <code className="text-blue-400 text-sm">{tc.expected_output}</code>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Terminal Section */}
        <div className="h-1/2 bg-[#1E1E1E] p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold text-white mb-4">Output</h3>

          {testResults.length === 0 ? (
            <div className="text-white/60 text-sm">
              Run your code to see the output here...
            </div>
          ) : (
            <div className="space-y-4">
              {/* Summary */}
              {executionSummary && (
                <div className={`p-3 rounded-lg ${
                  executionSummary.passed === executionSummary.total
                    ? 'bg-green-500/10 border border-green-500/30'
                    : 'bg-red-500/10 border border-red-500/30'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {executionSummary.passed === executionSummary.total ? (
                      <CheckCircle className="w-5 h-5 text-green-400" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-400" />
                    )}
                    <span className={`font-medium ${
                      executionSummary.passed === executionSummary.total ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {executionSummary.passed}/{executionSummary.total} Test Cases Passed
                    </span>
                  </div>
                  {executionSummary.runtime && (
                    <div className="text-white/60 text-sm">
                      Runtime: {executionSummary.runtime}ms
                    </div>
                  )}
                </div>
              )}

              {/* Individual Test Results */}
              {testResults.map((result, index) => (
                <div key={index} className="font-mono text-sm border-l-2 pl-3 ${
                  result.passed ? 'border-green-500' : 'border-red-500'
                }">
                  <div className="flex items-center gap-2 mb-1">
                    {result.passed ? (
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <span className="text-white/80">Test Case {index + 1}</span>
                  </div>
                  {result.input && (
                    <div className="text-white/60 ml-6">Input: {result.input}</div>
                  )}
                  {result.expectedOutput && (
                    <div className="text-white/60 ml-6">Expected: {result.expectedOutput}</div>
                  )}
                  {result.actualOutput && (
                    <div className={`ml-6 ${result.passed ? 'text-green-400' : 'text-red-400'}`}>
                      Output: {result.actualOutput}
                    </div>
                  )}
                  {result.error && (
                    <div className="text-red-400 ml-6 mt-1">
                      Error: {result.error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
