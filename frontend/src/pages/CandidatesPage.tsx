import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MarineXApi } from '../services/api';
import { VesselCandidate } from '../types';
import { CategoryBadge } from '../components/investigation/CategoryBadge';
import { CandidateVesselCard } from '../components/investigation/CandidateVesselCard';
import { useMarinexStore } from '../store/useMarinexStore';
import {
  Users,
  Ship,
  Search,
  Sliders,
  ChevronRight,
  ShieldAlert,
  ArrowUpDown,
  ArrowUpRight,
  FileText,
} from 'lucide-react';

export const CandidatesPage: React.FC = () => {
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState<VesselCandidate[]>([]);
  const [filterClass, setFilterClass] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  const { openEvidenceDrawer } = useMarinexStore();

  useEffect(() => {
    loadCandidates();
  }, []);

  const loadCandidates = async () => {
    setLoading(true);
    try {
      const invs = await MarineXApi.getInvestigations();
      if (invs.length > 0) {
        const cands = await MarineXApi.getCandidates(invs[0].slick_id);
        setCandidates(cands);
      }
    } catch (err) {
      console.error('Failed to load candidates:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredCandidates = candidates.filter((c) => {
    const matchesClass =
      filterClass === 'ALL' || c.classification === filterClass;
    const matchesSearch =
      (c.vessel?.vessel_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.vessel?.mmsi?.toString().includes(searchQuery);
    return matchesClass && matchesSearch;
  });

  return (
    <div className="space-y-12">
      {/* Editorial Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-8 border-b border-monochrome-800/80">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono tracking-widest uppercase text-monochrome-400 px-2 py-0.5 border border-monochrome-800 rounded">
              VESSEL ATTRIBUTION RANKING MATRIX
            </span>
            <CategoryBadge category="CANDIDATE" size="xs" />
          </div>

          <h1 className="text-4xl sm:text-6xl font-display font-extrabold tracking-tighter text-monochrome-50">
            Attribution Candidate Ranking
          </h1>

          <p className="text-sm sm:text-base font-heading text-monochrome-400 font-light max-w-3xl">
            Correlating spatio-temporal proximity, trajectory intersection geometry, course/speed anomalies, and AIS continuity gaps to prioritize potential discharging vessels.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => navigate('/investigation')}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded bg-monochrome-100 text-[#05070a] hover:bg-cyan-400 text-xs font-heading font-bold uppercase tracking-wider transition-all cursor-pointer"
          >
            <span>Open Investigation Room</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl border border-monochrome-800/80 bg-monochrome-950/50">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          {['ALL', 'PRIMARY_SUSPECT', 'SECONDARY_SUSPECT'].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilterClass(tab)}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-all ${
                filterClass === tab
                  ? 'bg-monochrome-100 text-[#05070a] font-bold'
                  : 'bg-monochrome-900/60 text-monochrome-400 hover:text-monochrome-200 border border-monochrome-800'
              }`}
            >
              {tab.replace('_', ' ')}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-monochrome-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by vessel name or MMSI..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded bg-monochrome-900 border border-monochrome-800 text-xs font-mono text-monochrome-200 placeholder-monochrome-600 focus:outline-none focus:border-cyan-400"
          />
        </div>
      </div>

      {/* Ranked Candidate List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCandidates.map((cand, idx) => (
          <CandidateVesselCard
            key={cand.id || idx}
            candidate={cand}
            isTopRanked={idx === 0}
            rank={idx + 1}
            onSelect={(c) => openEvidenceDrawer(c)}
          />
        ))}
      </div>
    </div>
  );
};
