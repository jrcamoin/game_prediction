import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, BarChart3, Loader2, Trophy } from "lucide-react";

import { predictGame } from "./api";
import type { PredictionRequest, PredictionResponse, Sport, TeamInput } from "./types";
import "./styles.css";

const sports: Sport[] = ["football", "basketball", "baseball", "hockey", "soccer"];

const defaultHome: TeamInput = {
  name: "Home Team",
  rating: 1545,
  recent_wins: 4,
  recent_losses: 1,
  injuries: 1,
  rest_days: 4,
  moneyline: -135,
};

const defaultAway: TeamInput = {
  name: "Away Team",
  rating: 1510,
  recent_wins: 3,
  recent_losses: 2,
  injuries: 2,
  rest_days: 3,
  moneyline: 115,
};

function App() {
  const [sport, setSport] = useState<Sport>("football");
  const [homeTeam, setHomeTeam] = useState<TeamInput>(defaultHome);
  const [awayTeam, setAwayTeam] = useState<TeamInput>(defaultAway);
  const [neutralSite, setNeutralSite] = useState(false);
  const [homeTravelMiles, setHomeTravelMiles] = useState(0);
  const [awayTravelMiles, setAwayTravelMiles] = useState(550);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const payload = useMemo<PredictionRequest>(
    () => ({
      sport,
      home_team: homeTeam,
      away_team: awayTeam,
      neutral_site: neutralSite,
      home_travel_miles: homeTravelMiles,
      away_travel_miles: awayTravelMiles,
    }),
    [awayTeam, awayTravelMiles, homeTeam, homeTravelMiles, neutralSite, sport],
  );

  async function handlePredict() {
    setIsLoading(true);
    setError(null);
    try {
      setPrediction(await predictGame(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Sports model workspace</p>
          <h1>Game Winner Predictor</h1>
        </div>
        <button className="primary-button" onClick={handlePredict} disabled={isLoading}>
          {isLoading ? <Loader2 className="spin" size={18} /> : <Activity size={18} />}
          Predict
        </button>
      </section>

      <section className="workspace">
        <div className="input-panel">
          <div className="field-group">
            <label htmlFor="sport">Sport</label>
            <select id="sport" value={sport} onChange={(event) => setSport(event.target.value as Sport)}>
              {sports.map((item) => (
                <option key={item} value={item}>
                  {titleCase(item)}
                </option>
              ))}
            </select>
          </div>

          <div className="teams-grid">
            <TeamForm title="Home" team={homeTeam} onChange={setHomeTeam} />
            <TeamForm title="Away" team={awayTeam} onChange={setAwayTeam} />
          </div>

          <div className="settings-row">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={neutralSite}
                onChange={(event) => setNeutralSite(event.target.checked)}
              />
              Neutral site
            </label>
            <NumberField label="Home travel" value={homeTravelMiles} onChange={setHomeTravelMiles} min={0} max={10000} />
            <NumberField label="Away travel" value={awayTravelMiles} onChange={setAwayTravelMiles} min={0} max={10000} />
          </div>
        </div>

        <PredictionPanel prediction={prediction} error={error} homeTeam={homeTeam.name} awayTeam={awayTeam.name} />
      </section>
    </main>
  );
}

type TeamFormProps = {
  title: string;
  team: TeamInput;
  onChange: (team: TeamInput) => void;
};

function TeamForm({ title, team, onChange }: TeamFormProps) {
  const update = <K extends keyof TeamInput>(key: K, value: TeamInput[K]) => {
    onChange({ ...team, [key]: value });
  };

  return (
    <div className="team-card">
      <h2>{title}</h2>
      <div className="field-group">
        <label htmlFor={`${title}-name`}>Team name</label>
        <input id={`${title}-name`} value={team.name} onChange={(event) => update("name", event.target.value)} />
      </div>
      <div className="field-grid">
        <NumberField label="Rating" value={team.rating} onChange={(value) => update("rating", value)} min={1000} max={2200} />
        <NumberField label="Recent wins" value={team.recent_wins} onChange={(value) => update("recent_wins", value)} min={0} max={10} />
        <NumberField label="Recent losses" value={team.recent_losses} onChange={(value) => update("recent_losses", value)} min={0} max={10} />
        <NumberField label="Injuries" value={team.injuries} onChange={(value) => update("injuries", value)} min={0} max={20} />
        <NumberField label="Rest days" value={team.rest_days} onChange={(value) => update("rest_days", value)} min={0} max={14} />
        <NumberField
          label="Moneyline"
          value={team.moneyline ?? 0}
          onChange={(value) => update("moneyline", value === 0 ? null : value)}
          min={-5000}
          max={5000}
        />
      </div>
    </div>
  );
}

type NumberFieldProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
};

function NumberField({ label, value, onChange, min, max }: NumberFieldProps) {
  const id = label.toLowerCase().replaceAll(" ", "-");
  return (
    <div className="field-group">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}

type PredictionPanelProps = {
  prediction: PredictionResponse | null;
  error: string | null;
  homeTeam: string;
  awayTeam: string;
};

function PredictionPanel({ prediction, error, homeTeam, awayTeam }: PredictionPanelProps) {
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
        <Metric label="Model score" value={prediction.score.toFixed(2)} />
      </div>
      <div className="factor-list">
        {Object.entries(prediction.factors).map(([key, value]) => (
          <div key={key}>
            <span>{titleCase(key.replace("_", " "))}</span>
            <strong>{value.toFixed(2)}</strong>
          </div>
        ))}
      </div>
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

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
