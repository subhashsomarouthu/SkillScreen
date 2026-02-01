'use client';

import { motion } from 'framer-motion';
import { User, Building2, Mail, Calendar, Shield, Briefcase, Globe, Users } from 'lucide-react';
import NavBar from '@/components/NavBar';
import Footer from '@/components/Footer';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function ProfilePage() {
    const { user, isAuthenticated, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isLoading, isAuthenticated, router]);

    if (isLoading) {
        return (
            <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
                <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    if (!user) {
        return null;
    }

    const getRoleBadgeColor = (role: string) => {
        switch (role?.toLowerCase()) {
            case 'admin': return 'bg-red-500/20 text-red-400 border-red-500/30';
            case 'recruiter': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
            case 'hiring_manager': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
            case 'team_lead': return 'bg-green-500/20 text-green-400 border-green-500/30';
            case 'hr': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
            default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        }
    };

    return (
        <div className="min-h-screen bg-[#0A0A0A] text-white">
            <NavBar />

            {/* Background Effects */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 blur-[120px] rounded-full" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 blur-[120px] rounded-full" />
            </div>

            <div className="relative z-10 max-w-4xl mx-auto px-6 py-24">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-12"
                >
                    <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl shadow-blue-500/20">
                        <span className="text-4xl font-bold text-white">
                            {user.name?.charAt(0).toUpperCase() || 'U'}
                        </span>
                    </div>
                    <h1 className="text-3xl md:text-4xl font-bold mb-2">{user.name}</h1>
                    <div className={`inline-flex items-center gap-2 px-4 py-1 rounded-full text-sm font-medium border ${getRoleBadgeColor(user.userType || '')}`}>
                        <Shield className="w-4 h-4" />
                        {user.userType?.replace('_', ' ').charAt(0).toUpperCase() + (user.userType?.slice(1).replace('_', ' ') || '') || 'User'}
                    </div>
                </motion.div>

                {/* Profile Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* User Details */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1 }}
                        className="bg-white/5 rounded-2xl border border-white/10 p-6"
                    >
                        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                            <User className="w-5 h-5 text-blue-400" />
                            User Details
                        </h2>
                        <div className="space-y-4">
                            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl">
                                <Mail className="w-5 h-5 text-white/50" />
                                <div>
                                    <p className="text-white/50 text-sm">Email</p>
                                    <p className="text-white">{user.email || 'N/A'}</p>
                                </div>
                            </div>

                            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl">
                                <Briefcase className="w-5 h-5 text-white/50" />
                                <div>
                                    <p className="text-white/50 text-sm">Role</p>
                                    <p className="text-white capitalize">{user.userType?.replace('_', ' ') || 'N/A'}</p>
                                </div>
                            </div>

                            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl">
                                <Calendar className="w-5 h-5 text-white/50" />
                                <div>
                                    <p className="text-white/50 text-sm">User ID</p>
                                    <p className="text-white font-mono text-sm">{user.id || 'N/A'}</p>
                                </div>
                            </div>
                        </div>
                    </motion.div>

                    {/* Organization Details */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                        className="bg-white/5 rounded-2xl border border-white/10 p-6"
                    >
                        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                            <Building2 className="w-5 h-5 text-purple-400" />
                            Organization Details
                        </h2>
                        <div className="space-y-4">
                            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl">
                                <Building2 className="w-5 h-5 text-white/50" />
                                <div>
                                    <p className="text-white/50 text-sm">Organization Name</p>
                                    <p className="text-white">{user.organizationName || 'N/A'}</p>
                                </div>
                            </div>

                            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl">
                                <Globe className="w-5 h-5 text-white/50" />
                                <div>
                                    <p className="text-white/50 text-sm">Organization ID</p>
                                    <p className="text-white font-mono text-sm">{user.organizationId || 'N/A'}</p>
                                </div>
                            </div>

                            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl">
                                <Users className="w-5 h-5 text-white/50" />
                                <div>
                                    <p className="text-white/50 text-sm">Account Status</p>
                                    <p className="text-green-400 flex items-center gap-2">
                                        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                                        Active
                                    </p>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>

                {/* Account Actions */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="mt-8 p-6 bg-white/5 rounded-2xl border border-white/10"
                >
                    <h2 className="text-xl font-semibold mb-4">Account Actions</h2>
                    <div className="flex flex-wrap gap-4">
                        <button
                            onClick={() => router.push('/recruiter')}
                            className="px-6 py-3 bg-blue-500 hover:bg-blue-600 rounded-lg font-medium transition-colors"
                        >
                            Go to Dashboard
                        </button>
                        <button className="px-6 py-3 bg-white/10 hover:bg-white/20 rounded-lg font-medium transition-colors">
                            Edit Profile (Coming Soon)
                        </button>
                    </div>
                </motion.div>
            </div>

            <Footer />
        </div>
    );
}
