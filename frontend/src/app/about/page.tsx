'use client';

import { motion } from 'framer-motion';
import NavBar from '@/components/NavBar';
import Footer from '@/components/Footer';
import Link from 'next/link';

export default function AboutPage() {
  const heroImage =
    'https://source.unsplash.com/featured/900x900?team,interview&sig=1';
  const missionImage =
    'https://source.unsplash.com/featured/900x600?meeting,office&sig=2';
  const galleryImages = [
    'https://source.unsplash.com/featured/600x450?recruiter,conversation&sig=3',
    'https://source.unsplash.com/featured/600x450?job,interview&sig=4',
    'https://source.unsplash.com/featured/600x450?professional,meeting&sig=5',
    'https://source.unsplash.com/featured/600x450?team,discussion&sig=6',
    'https://source.unsplash.com/featured/600x450?office,collaboration&sig=7',
    'https://source.unsplash.com/featured/600x450?career,success&sig=8',
  ];

  return (
    <div className="min-h-screen bg-black">
      <NavBar />

      <div className="relative">
        {/* Hero Section */}
        <section className="pt-32 pb-20 px-6">
          <div className="max-w-6xl mx-auto">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
              >
                <h1 className="text-4xl md:text-6xl font-bold text-white leading-tight">
                  Connecting Talent with Opportunities
                </h1>
                <p className="text-white/70 mt-6 text-lg leading-relaxed">
                  Your trusted partner in modern hiring — combining AI‑powered interviews with
                  practical, recruiter‑friendly workflows to help teams hire faster and more fairly.
                </p>
                <div className="mt-8">
                  <Link
                    href="/contact"
                    className="inline-flex items-center px-6 py-3 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
                  >
                    Find Your Next Hire
                  </Link>
                </div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, delay: 0.1 }}
                className="rounded-2xl overflow-hidden border border-white/10 bg-white/5"
              >
                <img
                  src={heroImage}
                  alt="Interview panel"
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </motion.div>
            </div>
          </div>
        </section>

        {/* Mission + Vision */}
        <section className="py-20 px-6">
          <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="rounded-2xl overflow-hidden border border-white/10 bg-white/5"
            >
              <img
                src={missionImage}
                alt="Mission meeting"
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="space-y-8"
            >
              <div>
                <h2 className="text-3xl font-bold text-white mb-3">Our Mission</h2>
                <p className="text-white/70 leading-relaxed">
                  We believe that hiring should be a seamless, unbiased, and data-driven process.
                  SkillScreen empowers recruiters with intelligent tools to assess candidates fairly,
                  saving time while ensuring the best talent rises to the top. Our platform combines
                  the human touch of traditional interviews with the precision and scalability of AI.
                </p>
              </div>
              <div>
                <h2 className="text-3xl font-bold text-white mb-3">Our Vision</h2>
                <p className="text-white/70 leading-relaxed">
                  To create a world where every hiring decision is transparent, skill‑first, and inclusive —
                  helping teams discover potential beyond resumes while giving candidates a fair chance to shine.
                </p>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Gallery */}
        <section className="py-20 px-6">
          <div className="max-w-6xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="text-center mb-10"
            >
              <h2 className="text-3xl md:text-4xl font-bold text-white">
                Showcasing success stories and career journeys
              </h2>
            </motion.div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {galleryImages.map((src, index) => (
                <div
                  key={index}
                  className="rounded-2xl overflow-hidden border border-white/10 bg-white/5"
                >
                  <img
                    src={src}
                    alt={`Gallery ${index + 1}`}
                    className="w-full h-56 object-cover"
                    loading="lazy"
                  />
                </div>
              ))}
            </div>
          </div>
        </section>

      </div>

      <Footer />
    </div>
  );
}

