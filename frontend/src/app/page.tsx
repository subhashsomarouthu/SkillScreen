'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import NavBar from '@/components/NavBar';
import Hero from '@/components/Hero';
import Features from '@/components/Features';
import Footer from '@/components/Footer';
import { FeaturesGrid } from '@/components/FeaturesGrid';
import { UndetectableSection } from '@/components/UndetectableSection';
import { useAuth } from '@/contexts/AuthContext';

import { AnimatedGradientBackground } from '@/components/ui/animated-gradient-background';

export default function Home() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, getToken } = useAuth();

  useEffect(() => {
    // Log the token
    const token = getToken();
    console.log('Current JWT Token:', token);

    // Redirect authenticated users to their appropriate dashboard
    if (isAuthenticated && user && !isLoading) {
      // Check role first (admin takes priority)
      if (user.role === 'admin') {
        router.push('/admin');
      } else if (user.role === 'recruiter' || user.role === 'hiring_manager' || user.role === 'team_lead' || user.role === 'hr') {
        router.push('/recruiter');
      } else {
        // Fallback to candidate for other roles
        router.push('/candidate');
      }
    }
  }, [isAuthenticated, user, isLoading, router, getToken]);

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-white"></div>
      </div>
    );
  }

  // Don't render if user is authenticated (will redirect)
  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="relative min-h-screen">
      <AnimatedGradientBackground
        startingGap={110}
        Breathing={true}
        gradientColors={[
          "#1a1a1a",
          "#234C6A",
          "#456882",
          "#1B3C53",
          "#2979FF"
        ]}
        gradientStops={[20, 40, 60, 80, 100]}
        animationSpeed={0.015}
        breathingRange={5}
        topOffset={-20}
        containerClassName="opacity-90 absolute inset-0 -z-10 min-h-full"
      />
      {/* Main content */}
      <div className="relative">
        <NavBar />
        <Hero />
        <FeaturesGrid />
        <UndetectableSection />
        {/*<Features /> */}
        <Footer />
      </div>
    </div>
  );
}