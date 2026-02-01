'use client';

import { motion } from 'framer-motion';
import { Mail, Phone, MapPin, MessageCircle, Send, ArrowRight } from 'lucide-react';
import NavBar from '@/components/NavBar';
import Footer from '@/components/Footer';
import { useState } from 'react';

export default function ContactPage() {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        subject: '',
        message: ''
    });
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        // Open email client with pre-filled message
        const mailtoLink = `mailto:pavanchakravarthy2000@gmail.com?subject=${encodeURIComponent(formData.subject)}&body=${encodeURIComponent(`From: ${formData.name} (${formData.email})\n\n${formData.message}`)}`;
        window.location.href = mailtoLink;
        setSubmitted(true);
    };

    return (
        <div className="min-h-screen bg-[#0A0A0A] text-white">
            <NavBar />

            {/* Background Effects */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 blur-[120px] rounded-full" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 blur-[120px] rounded-full" />
            </div>

            <div className="relative z-10 max-w-6xl mx-auto px-6 py-24">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-16"
                >
                    <h1 className="text-4xl md:text-5xl font-bold mb-4">Get in Touch</h1>
                    <p className="text-white/60 text-lg max-w-2xl mx-auto">
                        Have questions about SkillScreen? We'd love to hear from you. Send us a message and we'll respond as soon as possible.
                    </p>
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                    {/* Contact Information */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                        className="space-y-8"
                    >
                        <div>
                            <h2 className="text-2xl font-semibold mb-6">Contact Information</h2>
                            <div className="space-y-6">
                                {/* Email */}
                                <a
                                    href="mailto:pavanchakravarthy2000@gmail.com"
                                    className="flex items-center gap-4 p-4 bg-white/5 rounded-xl border border-white/10 hover:bg-white/10 transition-colors group"
                                >
                                    <div className="w-12 h-12 bg-blue-500/20 rounded-full flex items-center justify-center group-hover:bg-blue-500/30 transition-colors">
                                        <Mail className="w-6 h-6 text-blue-400" />
                                    </div>
                                    <div>
                                        <p className="text-white/50 text-sm">Email</p>
                                        <p className="text-white font-medium">pavanchakravarthy2000@gmail.com</p>
                                    </div>
                                    <ArrowRight className="w-5 h-5 text-white/30 ml-auto group-hover:text-white/60 transition-colors" />
                                </a>

                                {/* Support Hours */}
                                <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl border border-white/10">
                                    <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center">
                                        <MessageCircle className="w-6 h-6 text-green-400" />
                                    </div>
                                    <div>
                                        <p className="text-white/50 text-sm">Support Hours</p>
                                        <p className="text-white font-medium">Monday - Friday, 9 AM - 6 PM EST</p>
                                    </div>
                                </div>

                                {/* Response Time */}
                                <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl border border-white/10">
                                    <div className="w-12 h-12 bg-purple-500/20 rounded-full flex items-center justify-center">
                                        <Send className="w-6 h-6 text-purple-400" />
                                    </div>
                                    <div>
                                        <p className="text-white/50 text-sm">Response Time</p>
                                        <p className="text-white font-medium">Within 24-48 hours</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Quick Links */}
                        <div className="p-6 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-xl border border-white/10">
                            <h3 className="font-semibold mb-3">Quick Links</h3>
                            <ul className="space-y-2 text-white/70">
                                <li><a href="/docs" className="hover:text-white transition-colors">→ Documentation</a></li>
                                <li><a href="/pricing" className="hover:text-white transition-colors">→ Pricing</a></li>
                                <li><a href="/about" className="hover:text-white transition-colors">→ About Us</a></li>
                            </ul>
                        </div>
                    </motion.div>

                    {/* Contact Form */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        {submitted ? (
                            <div className="p-8 bg-white/5 rounded-2xl border border-white/10 text-center">
                                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <Send className="w-8 h-8 text-green-400" />
                                </div>
                                <h3 className="text-xl font-semibold mb-2">Message Sent!</h3>
                                <p className="text-white/60">Your email client should have opened. We'll get back to you soon.</p>
                                <button
                                    onClick={() => setSubmitted(false)}
                                    className="mt-4 px-6 py-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
                                >
                                    Send Another Message
                                </button>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit} className="p-8 bg-white/5 rounded-2xl border border-white/10 space-y-6">
                                <h2 className="text-2xl font-semibold mb-4">Send us a Message</h2>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-white/60 text-sm mb-2">Your Name</label>
                                        <input
                                            type="text"
                                            value={formData.name}
                                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                            placeholder="John Doe"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-white/60 text-sm mb-2">Your Email</label>
                                        <input
                                            type="email"
                                            value={formData.email}
                                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                            placeholder="john@example.com"
                                            required
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-white/60 text-sm mb-2">Subject</label>
                                    <input
                                        type="text"
                                        value={formData.subject}
                                        onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                        placeholder="How can we help?"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-white/60 text-sm mb-2">Message</label>
                                    <textarea
                                        value={formData.message}
                                        onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                                        rows={5}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                                        placeholder="Tell us more about your inquiry..."
                                        required
                                    />
                                </div>

                                <button
                                    type="submit"
                                    className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white font-medium rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                                >
                                    <Send className="w-4 h-4" />
                                    Send Message
                                </button>
                            </form>
                        )}
                    </motion.div>
                </div>
            </div>

            <Footer />
        </div>
    );
}
