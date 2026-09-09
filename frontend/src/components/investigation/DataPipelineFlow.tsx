import React from 'react';
import { motion } from 'motion/react';
import {
  Satellite,
  Scan,
  Sparkles,
  Wind,
  Radio,
  Scale,
  FileCheck,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

export const DataPipelineFlow: React.FC = () => {
  const stages = [
    {
      step: 1,
      title: 'SAR Acquisition',
      sub: 'Sentinel-1 C-Band',
      icon: Satellite,
      color: 'text-cyan-400',
      border: 'border-cyan-500/40',
      tag: 'OBSERVED',
      tagColor: 'bg-cyan-950 text-cyan-300 border-cyan-500/30',
    },
    {
      step: 2,
      title: 'AI Segmentation',
      sub: 'SegFormer MiT + Loss',
      icon: Scan,
      color: 'text-blue-400',
      border: 'border-blue-500/40',
      tag: 'INFERRED',
      tagColor: 'bg-blue-950 text-blue-300 border-blue-500/30',
    },
    {
      step: 3,
      title: 'Lookalike Discrimination',
      sub: 'ConvNeXt Damping Clf',
      icon: Sparkles,
      color: 'text-purple-400',
      border: 'border-purple-500/40',
      tag: 'INFERRED',
      tagColor: 'bg-purple-950 text-purple-300 border-purple-500/30',
    },
    {
      step: 4,
      title: 'Drift Hindcast',
      sub: 'Lagrangian ERA5 + HYCOM',
      icon: Wind,
      color: 'text-teal-400',
      border: 'border-teal-500/40',
      tag: 'SIMULATED',
      tagColor: 'bg-teal-950 text-teal-300 border-teal-500/30',
    },
    {
      step: 5,
      title: 'AIS Reconstruction',
      sub: 'Spatial Corridor Match',
      icon: Radio,
      color: 'text-sky-400',
      border: 'border-sky-500/40',
      tag: 'TRACKED',
      tagColor: 'bg-sky-950 text-sky-300 border-sky-500/30',
    },
    {
      step: 6,
      title: 'Multi-Factor Ranking',
      sub: 'Composite Attribution',
      icon: Scale,
      color: 'text-amber-400',
      border: 'border-amber-500/40',
      tag: 'CANDIDATE',
      tagColor: 'bg-amber-950 text-amber-300 border-amber-500/30',
    },
    {
      step: 7,
      title: 'Legal Dossier',
      sub: 'Verifiable Evidence',
      icon: FileCheck,
      color: 'text-emerald-400',
      border: 'border-emerald-500/40',
      tag: 'INVESTIGATION',
      tagColor: 'bg-emerald-950 text-emerald-300 border-emerald-500/30',
    },
  ];

  return (
    <div className="w-full bg-[#070c16]/90 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white tracking-wide uppercase">
            MARINeX End-to-End Operational Pipeline
          </h3>
          <p className="text-xs text-slate-400">
            From radar backscatter to court-admissible vessel attribution
          </p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          ALL STAGES AUTOMATED
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3">
        {stages.map((st) => {
          const Icon = st.icon;
          return (
            <div
              key={st.step}
              className={`relative p-3 rounded-xl bg-[#0a111e] border ${st.border} flex flex-col justify-between`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono font-bold text-slate-500">
                  0{st.step}
                </span>
                <span
                  className={`text-[8px] font-mono font-bold px-1.5 py-0.2 rounded border ${st.tagColor}`}
                >
                  {st.tag}
                </span>
              </div>

              <div className="my-2">
                <Icon className={`w-5 h-5 ${st.color} mb-1.5`} />
                <h4 className="text-xs font-bold text-white leading-tight">
                  {st.title}
                </h4>
                <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                  {st.sub}
                </p>
              </div>

              <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden mt-1">
                <div className="h-full bg-emerald-400/80 w-full" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
