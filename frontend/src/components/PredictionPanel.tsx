import { BarChart3, Trophy } from "lucide-react";

import type { DataSourceStatus, PredictionResponse } from "../types";

type PredictionPanelProps = {
  prediction: PredictionResponse | null;
  error: string | null;
  homeTeam: string;
  awayTeam: string;
  sources: DataSourceStatus[];
};

export function PredictionPanel({ prediction, error, homeTeam, awayTeam, sources }: PredictionPanelProps) {
  if (error) {
    return <aside className="result-panel error-panel">{error}</aside>;
  }

  if (!prediction) {
    return (
      <aside className="result-panel empty-panel">
        <BarChart3 size={28} />
        <p>Enter game context and run a prediction.</p>
      </aside>
    );
  }

  const homePct = Math.round(prediction.home_win_probability * 100);
  const awayPct = Math.round(prediction.away_win_probability * 100);
  const calibratedPct = Math.round(prediction.calibrated_home_win_probability * 100);
  const factorDrivers = prediction.feature_importance.length
    ? prediction.feature_importance.slice(0, 3)
    : Object.entries(prediction.factors)
        .sort(([, left], [, right]) => Math.abs(right) - Math.abs(left))
        .slice(0, 3)
        .map(([name, value]) => ({ name, value, impact: Math.abs(value), direction: value > 0 ? "home" : value < 0 ? "away" : "neutral" }));

  return (
    <aside className="result-panel">
      <div className="winner-header">
        <Trophy size={24} />
        <div>
          <p className="eyebrow">Projected winner</p>
          <h2>{prediction.predicted_winner}</h2>
        </div>
      </div>
      <p className="summary">{prediction.summary}</p>
      <div className="probability-stack">
        <ProbabilityBar label={homeTeam} value={homePct} />
        <ProbabilityBar label={awayTeam} value={awayPct} />
      </div>
      <div className="metric-grid">
        <Metric label="Confidence" value={titleCase(prediction.confidence)} />
        <Metric label="Calibrated home" value={`${calibratedPct}%`} />
      </div>
      <div className="ensemble-list">
        <p className="eyebrow">Ensemble</p>
        {prediction.ensemble.map((model) => (
          <div key={model.name}>
            <span>{model.name}</span>
            <strong>{Math.round(model.home_win_probability * 100)}%</strong>
            <em>{Math.round(model.weight * 100)}% weight</em>
          </div>
        ))}
      </div>
      <div className="driver-list">
        <p className="eyebrow">Top drivers</p>
        {factorDrivers.map((factor) => (
          <div key={factor.name}>
            <span>{titleCase(factor.name.replace("_", " "))}</span>
            <strong className={factor.direction === "home" ? "positive" : factor.direction === "away" ? "negative" : ""}>
              {formatSigned(factor.value)}
            </strong>
          </div>
        ))}
      </div>
      <div className="factor-list">
        {Object.entries(prediction.factors).map(([key, value]) => (
          <div key={key}>
            <span>{titleCase(key.replace("_", " "))}</span>
            <strong>{formatSigned(value)}</strong>
          </div>
        ))}
      </div>
      {sources.length > 0 ? (
        <div className="source-list">
          <p className="eyebrow">Sources</p>
          {sources.map((source) => (
            <div key={source.name}>
              <span className={source.enabled ? "source-enabled" : "source-disabled"}>{source.name}</span>
              <small>{source.detail}</small>
            </div>
          ))}
        </div>
      ) : null}
      {prediction.model_notes.length > 0 ? (
        <div className="note-list">
          <p className="eyebrow">Model notes</p>
          {prediction.model_notes.map((note) => (
            <small key={note}>{note}</small>
          ))}
        </div>
      ) : null}
    </aside>
  );
}

function ProbabilityBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="probability-row">
      <div>
        <span>{label}</span>
        <strong>{value}%</strong>
      </div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function titleCase(value: string) {
  return value.replace(/\w\S*/g, (text) => text.charAt(0).toUpperCase() + text.slice(1).toLowerCase());
}

function formatSigned(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}
