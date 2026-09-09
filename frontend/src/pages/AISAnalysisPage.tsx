import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MarineXApi } from '../services/api';
import { Vessel, AISPoint } from '../types';
import { Badge } from '../components/common/Badge';
import {
  Radio,
  Ship,
  Search,
  Activity,
  Compass,
  Clock,
  TrendingDown,
  ChevronRight,
  Anchor,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
} from 'recharts';

export const AISAnalysisPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [selectedVessel, setSelectedVessel] = useState<Vessel | null>(null);
  const [trajectory, setTrajectory] = useState<AISPoint[]>([]);
  const [loadingTracks, setLoadingTracks] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadVessels();
  }, []);

  const loadVessels = async () => {
    try {
      const data = await MarineXApi.getVessels();
      setVessels(data);

      const queryMmsi = searchParams.get('mmsi');
      if (queryMmsi) {
        const found = data.find((v) => v.mmsi === Number(queryMmsi));
        if (found) selectVessel(found);
      } else if (data.length > 0) {
        selectVessel(data[0]);
      }
    } catch (err) {
      console.error('Failed to load vessels:', err);
    }
  };

  const selectVessel = async (vessel: Vessel) => {
    setSelectedVessel(vessel);
    setLoadingTracks(true);
    try {
      const pts = await MarineXApi.getVesselTrajectory(vessel.id);
      // Sort chronologically
      pts.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      setTrajectory(pts);
    } catch (err) {
      console.error('Failed to load trajectory for MMSI:', vessel.mmsi);
    } finally {
      setLoadingTracks(false);
    }
  };

  const chartData = trajectory.map((pt) => ({
    time: new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    sog: pt.speed_over_ground_knots,
    cog: pt.course_over_ground_deg,
    distance: pt.distance_to_origin_km || 0,
  }));

  const filteredVessels = vessels.filter(
    (v) =>
      v.vessel_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      v.mmsi.toString().includes(searchQuery)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <Radio className="w-6 h-6 text-cyan-400" />
          AIS Vessel Telemetry & Kinematics Analysis
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Inspect vessel tracks, speed-over-ground anomalies, sudden course changes, and closest points of approach (CPA) to estimated spill coordinates.
        </p>
      </div>

      {/* Grid: Vessel List vs Trajectory & Kinematics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Vessel List (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search vessel name, MMSI..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {filteredVessels.map((v) => {
              const isSelected = selectedVessel?.id === v.id;
              return (
                <div
                  key={v.id}
                  onClick={() => selectVessel(v)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-slate-900 border-cyan-500/80 shadow-md shadow-cyan-950/40'
                      : 'bg-[#0e1a2c]/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 text-cyan-400">
                        <Ship className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="font-bold text-xs text-white">{v.vessel_name}</h4>
                        <div className="text-[10px] text-slate-400 font-mono">
                          MMSI: {v.mmsi} • Flag: {v.flag}
                        </div>
                      </div>
                    </div>
                    <Badge variant="info" size="sm">
                      {v.vessel_type}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Kinematics Charts & Trackpoints (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {selectedVessel ? (
            <>
              {/* Vessel Telemetry Header Card */}
              <div className="bg-[#0e1a2c]/90 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-extrabold text-white">
                      {selectedVessel.vessel_name}
                    </h2>
                    <Badge variant="primary" size="sm">
                      MMSI: {selectedVessel.mmsi}
                    </Badge>
                    <Badge variant="neutral" size="sm">
                      IMO: {selectedVessel.imo || 'N/A'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 font-mono mt-1">
                    <span>Type: {selectedVessel.vessel_type}</span>
                    <span>•</span>
                    <span>Flag: {selectedVessel.flag}</span>
                    <span>•</span>
                    <span>Length: {selectedVessel.length_m || 240}m</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right font-mono text-xs">
                    <div className="text-slate-400">Recorded Pings</div>
                    <div className="text-white font-bold">{trajectory.length} AIS positions</div>
                  </div>
                </div>
              </div>

              {/* SOG Speed-Over-Ground Chart */}
              <div className="bg-[#0e1a2c]/90 border border-slate-800 rounded-xl p-4 shadow-lg space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-cyan-400" />
                    Speed Over Ground (SOG) Kinematics Profile
                  </h3>
                  <span className="text-[10px] font-mono text-slate-500">Knots vs Time</span>
                </div>

                <div className="h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" fontSize={10} domain={['auto', 'auto']} unit=" kts" />
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: '#0e1a2c',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          fontSize: '11px',
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="sog"
                        stroke="#06b6d4"
                        strokeWidth={2.5}
                        dot={{ fill: '#06b6d4', r: 3 }}
                        activeDot={{ r: 5 }}
                        name="Speed (kts)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Waypoint Telemetry Log Table */}
              <div className="bg-[#0e1a2c]/90 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
                <div className="px-4 py-2.5 bg-slate-900/90 text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center justify-between">
                  <span>Chronological Waypoint Log</span>
                  <span className="text-[10px] text-slate-500 font-normal">Latest First</span>
                </div>
                <div className="max-h-48 overflow-y-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-950/60 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                      <tr>
                        <th className="p-2.5">Timestamp (UTC)</th>
                        <th className="p-2.5">Coordinates</th>
                        <th className="p-2.5">Speed (SOG)</th>
                        <th className="p-2.5">Course (COG)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-200">
                      {trajectory.map((pt, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40">
                          <td className="p-2.5 text-slate-400">
                            {new Date(pt.timestamp).toUTCString().slice(5, 22)}
                          </td>
                          <td className="p-2.5">
                            {pt.latitude.toFixed(4)}°N, {pt.longitude.toFixed(4)}°E
                          </td>
                          <td className="p-2.5 font-bold text-cyan-400">
                            {pt.speed_over_ground_knots} kts
                          </td>
                          <td className="p-2.5 text-slate-300">
                            {pt.course_over_ground_deg}°
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-xs text-slate-500 bg-[#0e1a2c]/80 rounded-xl border border-slate-800">
              Select a vessel to inspect trajectory kinematics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
