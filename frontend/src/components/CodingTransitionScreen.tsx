'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Code2, Timer, ArrowRight, Coffee, Brain } from 'lucide-react';

interface CodingTransitionScreenProps {
  onStartCoding: () => void;
  questionCount: number;
}

export default function CodingTransitionScreen({
  onStartCoding,
  questionCount
}: CodingTransitionScreenProps) {
  const BREAK_DURATION = 5 * 60; // 5 minutes in seconds
  const [timeRemaining, setTimeRemaining] = useState(BREAK_DURATION);
  const [isTimerPaused, setIsTimerPaused] = useState(false);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }, []);

  useEffect(() => {
    if (isTimerPaused) return;

    const timer = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          onStartCoding();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isTimerPaused, onStartCoding]);

  const handleStartNow = () => {
    setIsTimerPaused(true);
    onStartCoding();
  };

  const progressPercentage = ((BREAK_DURATION - timeRemaining) / BREAK_DURATION) * 100;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 flex items-center justify-center z-50 bg-gradient-to-br from-gray-900 via-purple-900/20 to-gray-900"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.2, type: "spring", stiffness: 100 }}
        className="max-w-2xl w-full mx-6"
      >
        {/* Main Card */}
        <div className="glass-dark rounded-3xl p-8 md:p-12 border border-white/10 shadow-2xl">
          {/* Header Icon */}
          <div className="flex justify-center mb-8">
            <motion.div
              initial={{ y: -20 }}
              animate={{ y: 0 }}
              transition={{ delay: 0.3, type: "spring" }}
              className="relative"
            >
              <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                <Code2 className="w-12 h-12 text-white" />
              </div>
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 2 }}
                className="absolute -top-2 -right-2 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center"
              >
                <Brain className="w-4 h-4 text-white" />
              </motion.div>
            </motion.div>
          </div>

          {/* Title */}
          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-3xl md:text-4xl font-bold text-white text-center mb-4"
          >
            Great Job on the Interview!
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-xl text-white/80 text-center mb-8"
          >
            Next up: <span className="text-blue-400 font-semibold">Coding Challenge</span>
          </motion.p>

          {/* Info Box */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="bg-white/5 rounded-2xl p-6 mb-8 border border-white/10"
          >
            <div className="flex items-center gap-4 mb-4">
              <Coffee className="w-6 h-6 text-amber-400" />
              <span className="text-white/90 font-medium">
                Take a short break before continuing
              </span>
            </div>
            <p className="text-white/60 text-sm leading-relaxed">
              You have completed the video interview portion. The next stage is a coding assessment
              with <span className="text-blue-400 font-semibold">{questionCount} question{questionCount !== 1 ? 's' : ''}</span>.
              Take this time to relax, stretch, or grab some water. The coding round will
              automatically start when the timer ends, or you can begin immediately.
            </p>
          </motion.div>

          {/* Timer Section */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="mb-8"
          >
            {/* Progress Bar */}
            <div className="relative h-2 bg-white/10 rounded-full mb-4 overflow-hidden">
              <motion.div
                className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progressPercentage}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>

            {/* Timer Display */}
            <div className="flex items-center justify-center gap-3">
              <Timer className="w-6 h-6 text-blue-400" />
              <span className="text-4xl font-mono font-bold text-white">
                {formatTime(timeRemaining)}
              </span>
              <span className="text-white/60 text-sm">remaining</span>
            </div>
          </motion.div>

          {/* Action Buttons */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <button
              onClick={handleStartNow}
              className="group px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold rounded-xl transition-all shadow-lg hover:shadow-blue-500/25 flex items-center justify-center gap-3"
            >
              <span>Start Coding Now</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
          </motion.div>

          {/* Tips */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.9 }}
            className="mt-8 pt-6 border-t border-white/10"
          >
            <p className="text-white/50 text-sm text-center">
              Tip: Read each problem carefully before coding. You can run your code to test it before submitting.
            </p>
          </motion.div>
        </div>
      </motion.div>
    </motion.div>
  );
}
