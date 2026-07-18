import { RefreshCw } from "lucide-react";

import { sportProfiles } from "../sportProfiles";
import type { ModelStatus, Sport } from "../types";

type SportCapability = ModelStatus["capabilities"][number];

export function SportInsight({
  sport,
  capability,
}: {
  sport: Sport;
  capability: SportCapability | null;
}) {
  const profile = sportProfiles[sport];
  return (
    <section className="insight-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Sport intelligence</p>
          <h2>{profile.label}</h2>
        </div>
        <span className={capability?.live_schedule ? "status-pill enabled" : "status-pill"}>
          {capability?.live_schedule ? "Live data" : "Manual mode"}
        </span>
      </div>
      <div className="insight-list">
        <Metric label="Signal set" value={profile.metric} />
        <Metric label="Data source" value={profile.data} />
        <Metric label="Model logic" value={profile.model} />
      </div>
      {capability?.notes.length ? (
        <div className="readiness-notes">
          {capability.notes.map((note) => (
            <small key={note}>{note}</small>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function ModelReadiness({
  status,
  capability,
  onRefresh,
}: {
  status: ModelStatus | null;
  capability: SportCapability | null;
  onRefresh: () => void;
}) {
  return (
    <section className="insight-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Model readiness</p>
          <h2>{status?.active_model ?? "Model status unavailable"}</h2>
        </div>
        <button className="secondary-button" type="button" onClick={onRefresh}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>
      <div className="capability-grid">
        <Capability label="Schedule" enabled={Boolean(capability?.live_schedule)} />
        <Capability label="Live state" enabled={Boolean(capability?.live_state)} />
        <Capability label="Odds" enabled={Boolean(capability?.odds)} />
        <Capability label="Expected value" enabled={Boolean(capability?.expected_value)} />
        <Capability label="Trained model" enabled={Boolean(capability?.trained_model)} />
      </div>
      <small className="model-footnote">
        {status?.trained_artifact_loaded
          ? `Loaded artifact: ${status.trained_artifact_path}`
          : "Set XGBOOST_MODEL_PATH to switch from the deterministic scaffold to a trained model artifact."}
      </small>
    </section>
  );
}

function Capability({ label, enabled }: { label: string; enabled: boolean }) {
  return <span className={enabled ? "capability enabled" : "capability"}>{label}</span>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
