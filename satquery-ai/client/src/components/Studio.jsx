import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, Upload, ArrowRight, ShieldCheck, Cpu, Layers, 
  Clock, CheckCircle2, AlertCircle, FileText, Download, 
  Maximize2, Eye, GitCompare, RefreshCw, Layers3, Terminal,
  Zap, Info, MapPin, Globe, Compass
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

export default function Studio({ user, location }) {
  const [samples, setSamples] = useState([]);
  const [selectedSample, setSelectedSample] = useState(null);
  const [activeTab, setActiveTab] = useState('location'); // 'location', 'preset', or 'custom'
  
  // Location satellite state
  const [locationScene, setLocationScene] = useState(null);
  const [locLoading, setLocLoading] = useState(false);
  const [locError, setLocError] = useState(null);

  // Custom upload state
  const [fileSlotA, setFileSlotA] = useState(null);
  const [fileSlotB, setFileSlotB] = useState(null);
  const [slotAPreview, setSlotAPreview] = useState(null);
  const [slotBPreview, setSlotBPreview] = useState(null);
  const [slotAMeta, setSlotAMeta] = useState(null);
  const [slotBMeta, setSlotBMeta] = useState(null);
  
  // Query & execution state
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [displayMode, setDisplayMode] = useState('evidence'); // 'evidence' or 'raw'
  const [backendOnline, setBackendOnline] = useState(false);

  // Check health and load samples on mount
  useEffect(() => {
    checkHealthAndLoadSamples();
  }, []);

  // Fetch real satellite image whenever location changes
  useEffect(() => {
    if (location?.lat && location?.lon) {
      loadSatelliteForLocation(location.lat, location.lon, location.display);
    }
  }, [location?.lat, location?.lon, location?.display]);

  async function checkHealthAndLoadSamples() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/benchmark-samples`);
      if (res.ok) {
        const data = await res.json();
        setSamples(data.samples || []);
        if (data.samples && data.samples.length > 0) {
          setSelectedSample(data.samples[0]);
        }
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch (e) {
      console.warn("Backend not yet connected at", API_BASE);
      setBackendOnline(false);
    }
  }

  async function loadSatelliteForLocation(lat, lon, display) {
    setLocLoading(true);
    setLocError(null);
    setResult(null);
    setError(null);
    try {
      const u = new URL(`${API_BASE}/api/v1/location-scene`);
      u.searchParams.set('lat', lat);
      u.searchParams.set('lon', lon);
      u.searchParams.set('display', display || '');
      u.searchParams.set('zoom', '14');
      const res = await fetch(u);
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch satellite scene`);
      const data = await res.json();
      setLocationScene(data);
      const cityName = display ? display.split(',')[0] : 'this area';
      setQuery(`Describe the land-cover and major objects visible in ${cityName}.`);
    } catch (err) {
      console.error("Error loading location satellite:", err);
      setLocError(err.message);
    } finally {
      setLocLoading(false);
    }
  }

  function selectSample(sample) {
    setSelectedSample(sample);
    setError(null);
    setResult(null);
    if (sample.suggested_queries && sample.suggested_queries.length > 0) {
      setQuery(sample.suggested_queries[0]);
    }
  }

  // Handle custom upload file A
  async function handleFileAChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    setFileSlotA(file);
    inspectFile(file, 'A');
  }

  // Handle custom upload file B
  async function handleFileBChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    setFileSlotB(file);
    inspectFile(file, 'B');
  }

  async function inspectFile(file, slot) {
    const formData = new FormData();
    formData.append('files', file);
    try {
      const res = await fetch(`${API_BASE}/api/v1/inspect`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        if (data.images && data.images.length > 0) {
          const img = data.images[0];
          if (slot === 'A') {
            setSlotAPreview(img.preview_base64);
            setSlotAMeta(img.metadata);
          } else {
            setSlotBPreview(img.preview_base64);
            setSlotBMeta(img.metadata);
          }
        }
      }
    } catch (err) {
      console.error("Inspect error:", err);
    }
  }

  async function executeAgenticQuery(queryToRun = null) {
    const q = queryToRun || query;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('query', q);

    if (activeTab === 'location' && location?.lat && location?.lon) {
      formData.append('lat', location.lat);
      formData.append('lon', location.lon);
      formData.append('display', location.display || '');
      formData.append('zoom', '14');
    } else if (activeTab === 'preset' && selectedSample) {
      formData.append('sample_id', selectedSample.id);
    } else {
      if (fileSlotA) formData.append('files', fileSlotA);
      if (fileSlotB) formData.append('files', fileSlotB);
    }

    try {
      const res = await fetch(`${API_BASE}/api/v1/query`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(errJson.detail || 'Execution failed');
      }

      const data = await res.json();
      setResult(data);
      setDisplayMode('evidence');
    } catch (err) {
      setError(err.message || 'Error processing query on remote sensing engine.');
    } finally {
      setLoading(false);
    }
  }

  function downloadAuditReport() {
    if (!result) return;
    const reportData = {
      title: "SatQuery AI — SIH 2026 Remote Sensing Audit Report",
      exported_at: new Date().toISOString(),
      user: user?.email || "Evaluator / Judge",
      location: location?.display || "Benchmark Test Split",
      query: result.query,
      selected_task: result.task,
      synthesis: result.result,
      auditable_trace: result.auditable_trace
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `SatQuery_Audit_Trace_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const currentCity = location?.display ? location.display.split(',')[0] : 'Current Location';

  const locationQueries = [
    `Describe the land-cover and major objects visible in ${currentCity}.`,
    `Highlight the water body or river in this ${currentCity} scene.`,
    `Is there an urban settlement, highway, or building cluster present?`,
    `Use optical and SAR images together to identify built-up and water-covered regions in ${currentCity}.`,
    `Compute NDVI vegetation health and built-up index.`
  ];

  return (
    <div className="studio-container">
      {/* SIH Banner */}
      <div className="sih-banner">
        <div className="sih-tag">
          <Sparkles size={13} />
          <span>SIH 2026 OFFICIAL SCOPE</span>
        </div>
        <div className="sih-title-row">
          <div>
            <h2>SatQuery AI <span>Studio</span></h2>
            <p>Agentic Vision-Language Assistant for Single, Bi-Temporal, & Cross-Modal Satellite Analysis</p>
          </div>
          <div className="engine-status">
            <span className={`status-indicator ${backendOnline ? 'online' : 'offline'}`} />
            <span>Python AI Engine: {backendOnline ? 'Online (FastAPI :8000)' : 'Connecting...'}</span>
          </div>
        </div>
      </div>

      {/* Mode Selectors */}
      <div className="studio-tabs">
        <button 
          className={`studio-tab ${activeTab === 'location' ? 'active' : ''}`}
          onClick={() => setActiveTab('location')}
        >
          <MapPin size={15} />
          <span>Live Searched Location ({currentCity})</span>
        </button>
        <button 
          className={`studio-tab ${activeTab === 'preset' ? 'active' : ''}`}
          onClick={() => setActiveTab('preset')}
        >
          <Cpu size={15} />
          <span>Benchmark Presets (Competition Samples)</span>
        </button>
        <button 
          className={`studio-tab ${activeTab === 'custom' ? 'active' : ''}`}
          onClick={() => setActiveTab('custom')}
        >
          <Upload size={15} />
          <span>Custom GeoTIFF & Cross-Modal Upload</span>
        </button>
      </div>

      {/* Active Tab 1: Live Searched Location Mode */}
      {activeTab === 'location' && (
        <div className="location-active-card">
          <div className="loc-card-left">
            <div className="loc-badge">
              <span className="pulse-green" />
              <span>LIVE HIGH-RES SATELLITE FEED</span>
            </div>
            <h3>{location?.display || 'Global Coordinates'}</h3>
            <p>
              Coordinates: <b>{location?.lat?.toFixed(4)}°N, {location?.lon?.toFixed(4)}°E</b> | Zoom Level: 14 (~10m GSD)
            </p>
            <div className="loc-tags">
              <span>High-Res Optical Satellite</span>
              <span>Cloud-Screened</span>
              <span>Dynamic AI Ingestion</span>
            </div>
          </div>
          <div className="loc-card-right">
            {locLoading ? (
              <div className="loc-loader"><RefreshCw className="spin" size={24}/><span>Acquiring satellite scene...</span></div>
            ) : locationScene?.preview_base64 ? (
              <div className="loc-thumb-wrap">
                <img src={locationScene.preview_base64} alt="Location satellite preview" className="loc-thumb" />
                <span className="loc-thumb-tag">Real Satellite Preview</span>
              </div>
            ) : (
              <div className="loc-placeholder">Search any city in the top bar to inspect!</div>
            )}
          </div>
        </div>
      )}

      {/* Active Tab 2: Benchmark Presets */}
      {activeTab === 'preset' && (
        <div className="preset-grid">
          {samples.map((s) => (
            <div 
              key={s.id}
              className={`preset-card ${selectedSample?.id === s.id ? 'selected' : ''}`}
              onClick={() => selectSample(s)}
            >
              <div className="preset-header">
                <span className="preset-pill">{s.modality}</span>
                <span className="preset-type">{s.type.replace('_', ' ').toUpperCase()}</span>
              </div>
              <h4>{s.title}</h4>
              <p>{s.description}</p>
              <div className="preset-meta">
                <Layers size={12} />
                <span>{s.files.join(' + ')}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Active Tab 3: Custom Upload Slots */}
      {activeTab === 'custom' && (
        <div className="upload-slots-grid">
          {/* Slot 1 */}
          <div className="upload-slot">
            <div className="slot-head">
              <span className="slot-badge">Primary Slot (Optical / T1)</span>
              {slotAMeta && <small>{slotAMeta.width}x{slotAMeta.height} | {slotAMeta.modality}</small>}
            </div>
            <label className="slot-dropzone">
              <input type="file" accept=".tif,.tiff,.png,.jpg,.jpeg" onChange={handleFileAChange} style={{display:'none'}} />
              {slotAPreview ? (
                <img src={slotAPreview} alt="Slot A Preview" className="slot-img-preview" />
              ) : (
                <div className="dropzone-placeholder">
                  <Upload size={24} />
                  <b>Upload Optical / T1 GeoTIFF</b>
                  <span>Supports .tif, .tiff, .png, .jpg</span>
                </div>
              )}
            </label>
          </div>

          {/* Slot 2 */}
          <div className="upload-slot">
            <div className="slot-head">
              <span className="slot-badge">Secondary Slot (SAR / T2 / Pair)</span>
              {slotBMeta && <small>{slotBMeta.width}x{slotBMeta.height} | {slotBMeta.modality}</small>}
            </div>
            <label className="slot-dropzone">
              <input type="file" accept=".tif,.tiff,.png,.jpg,.jpeg" onChange={handleFileBChange} style={{display:'none'}} />
              {slotBPreview ? (
                <img src={slotBPreview} alt="Slot B Preview" className="slot-img-preview" />
              ) : (
                <div className="dropzone-placeholder">
                  <Upload size={24} />
                  <b>Upload SAR / T2 GeoTIFF</b>
                  <span>Bi-temporal pair or RISAT SAR data</span>
                </div>
              )}
            </label>
          </div>
        </div>
      )}

      {/* Suggested Queries Chips */}
      <div className="queries-chips-wrap">
        <span className="chips-label"><Sparkles size={13} /> Suggested Questions for {activeTab === 'location' ? currentCity : 'this Dataset'}:</span>
        <div className="chips-list">
          {(activeTab === 'location' ? locationQueries : (selectedSample?.suggested_queries || [])).map((sq, idx) => (
            <button 
              key={idx} 
              className="query-chip"
              onClick={() => { setQuery(sq); executeAgenticQuery(sq); }}
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Natural Language Query Bar */}
      <div className="query-console">
        <div className="query-input-wrap">
          <Terminal size={17} className="terminal-icon" />
          <input 
            type="text"
            placeholder={`Ask a question about ${activeTab === 'location' ? currentCity : 'the imagery'} (e.g., 'Describe land cover' or 'Highlight the water body')...`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && executeAgenticQuery()}
          />
          <button 
            className="run-btn"
            disabled={loading || !query.trim()}
            onClick={() => executeAgenticQuery()}
          >
            {loading ? <RefreshCw size={15} className="spin" /> : <Zap size={15} />}
            <span>Run Agent</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="error-alert">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Results & Visual Evidence Area */}
      {result && (
        <div className="results-layout">
          {/* Visual Evidence Viewer */}
          <div className="evidence-card">
            <div className="evidence-header">
              <div className="evidence-tabs">
                <button 
                  className={displayMode === 'evidence' ? 'active' : ''}
                  onClick={() => setDisplayMode('evidence')}
                >
                  <Eye size={13} /> Visual Evidence Overlay
                </button>
                <button 
                  className={displayMode === 'raw' ? 'active' : ''}
                  onClick={() => setDisplayMode('raw')}
                >
                  <Layers size={13} /> Ingested Satellite Base
                </button>
              </div>
              <span className="task-pill">{result.task}</span>
            </div>

            <div className="evidence-viewport">
              {displayMode === 'evidence' && result.visual_evidence_base64 && (
                <img 
                  src={result.visual_evidence_base64} 
                  alt="Visual Evidence" 
                  className="evidence-img"
                />
              )}
              {displayMode === 'raw' && result.primary_preview_base64 && (
                <img 
                  src={result.primary_preview_base64} 
                  alt="Raw Imagery" 
                  className="evidence-img"
                />
              )}
            </div>

            <div className="evidence-caption">
              <Info size={13} />
              <span>Evidence-grounded spatial output generated by {result.auditable_trace?.models_or_tools_invoked?.join(', ')}</span>
            </div>
          </div>

          {/* Text Response & Auditable Trace */}
          <div className="response-card">
            {/* Main Natural Language Answer */}
            <div className="answer-section">
              <div className="answer-badge">
                <CheckCircle2 size={14} />
                <span>EVIDENCE-GROUNDED SYNTHESIS</span>
                <span className="conf-score">
                  {(result.auditable_trace?.estimated_confidence * 100).toFixed(0)}% Confidence
                </span>
              </div>
              <p className="answer-text">{result.result?.text_answer}</p>
            </div>

            {/* Metrics Breakdown if available */}
            {result.result?.metrics && (
              <div className="metrics-box">
                <b>Remote Sensing Land-Cover Breakdown ({activeTab === 'location' ? currentCity : 'Scene'})</b>
                <div className="metric-pills">
                  {Object.entries(result.result.metrics).map(([k, v]) => (
                    <div key={k} className="metric-item">
                      <small>{k.replace('_', ' ').toUpperCase()}</small>
                      <span>{v}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.result?.change_breakdown && (
              <div className="metrics-box">
                <b>Bi-Temporal Transition Dynamics</b>
                <div className="metric-pills">
                  {Object.entries(result.result.change_breakdown).map(([k, v]) => (
                    <div key={k} className="metric-item">
                      <small>{k.replace('_', ' ').toUpperCase()}</small>
                      <span>{v}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.result?.cross_modal_metrics && (
              <div className="metrics-box">
                <b>Optical + SAR Complementary Features</b>
                <div className="metric-pills">
                  {Object.entries(result.result.cross_modal_metrics).map(([k, v]) => (
                    <div key={k} className="metric-item">
                      <small>{k.replace('_', ' ').toUpperCase()}</small>
                      <span>{typeof v === 'number' ? `${v}%` : v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Auditable Execution Trace Card (SIH Mandatory Requirement) */}
            <div className="trace-section">
              <div className="trace-header">
                <div className="trace-title">
                  <ShieldCheck size={14} className="shield-icon" />
                  <b>Auditable Execution Trace</b>
                </div>
                <button className="export-btn" onClick={downloadAuditReport} title="Export Trace JSON/PDF">
                  <Download size={13} /> Export Report
                </button>
              </div>

              <div className="trace-terminal">
                <div className="trace-row">
                  <span className="trace-k">Task Type:</span>
                  <span className="trace-v highlight">{result.auditable_trace?.selected_task}</span>
                </div>
                <div className="trace-row">
                  <span className="trace-k">Input Verified:</span>
                  <span className="trace-v">{result.auditable_trace?.input_validation?.modalities?.join(' + ')} ({result.auditable_trace?.input_validation?.dimensions?.join(', ')})</span>
                </div>
                <div className="trace-row">
                  <span className="trace-k">Specialists:</span>
                  <span className="trace-v">{result.auditable_trace?.models_or_tools_invoked?.join(', ')}</span>
                </div>
                <div className="trace-row">
                  <span className="trace-k">Parameters:</span>
                  <span className="trace-v json">{JSON.stringify(result.auditable_trace?.permitted_parameters)}</span>
                </div>
                <div className="trace-row">
                  <span className="trace-k">Co-Registration:</span>
                  <span className="trace-v success">{result.auditable_trace?.input_validation?.co_registration}</span>
                </div>
                <div className="trace-row">
                  <span className="trace-k">Audit Framework:</span>
                  <span className="trace-v">{result.auditable_trace?.eval_framework} (Latency: {result.auditable_trace?.latency_ms}ms)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
