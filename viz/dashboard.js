import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.2.0";
import { createRoot } from "https://esm.sh/react-dom@18.2.0/client";

const fetchState = async () => {
  const res = await fetch("/api/state");
  if (!res.ok) {
    throw new Error(`Failed to fetch state (${res.status})`);
  }
  return res.json();
};

const useDashboardData = (intervalMs = 1200) => {
  const [data, setData] = useState({ tasks: [], gepa: {}, history: [], tui: "", rationale: "" });
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer;
    const pull = async () => {
      try {
        const next = await fetchState();
        if (!cancelled) {
          setData(next);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError("Live data unavailable");
        }
      } finally {
        if (!cancelled) {
          timer = setTimeout(pull, intervalMs);
        }
      }
    };
    pull();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [intervalMs]);

  return { data, error };
};

const MetricCard = ({ title, value, hint }) => {
  const display = value === undefined || value === null ? "—" : value;
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="value">
        {display}
        {hint ? <small>{hint}</small> : null}
      </div>
    </div>
  );
};

const TaskItem = ({ task }) => {
  const status = task.status || "pending";
  return (
    <li>
      <p className="task-title">{task.description}</p>
      <span className={`status ${status}`}>
        <span className="dot" /> {status.replace("_", " ")}
      </span>
      {task.metadata?.notes ? <div className="subtitle">{task.metadata.notes}</div> : null}
    </li>
  );
};

const TuiPanel = ({ text }) => <div className="tui">{text || "Awaiting updates…"}</div>;

const HistoryStrip = ({ items }) => {
  if (!items.length) return <div className="subtitle">History will appear as agents work.</div>;
  return (
    <div className="history">
      {items.map((entry, idx) => (
        <span key={`${entry.task_id}-${idx}`} className="chip">
          Task {entry.task_id}: {entry.status}
          {entry.notes ? ` · ${entry.notes.slice(0, 64)}` : ""}
        </span>
      ))}
    </div>
  );
};

const GepaTimeline = ({ scores }) => {
  if (!scores || !scores.length) {
    return <div className="subtitle">GEPA metrics will populate after the first task completes.</div>;
  }
  const capped = scores.slice(-14);
  return (
    <div className="gepa-bars">
      {capped.map((score, idx) => (
        <div
          key={`${score}-${idx}`}
          className="gepa-bar"
          title={`Score ${score.toFixed(2)}`}
          style={{ height: `${Math.max(4, Math.min(100, score * 100))}%` }}
        />
      ))}
    </div>
  );
};

const App = () => {
  const { data, error } = useDashboardData();
  const tasks = data.tasks || [];
  const gepa = data.gepa || {};
  const totals = useMemo(() => {
    const counts = { total: tasks.length, pending: 0, in_progress: 0, complete: 0, failed: 0 };
    tasks.forEach((task) => {
      const key = task.status || "pending";
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }, [tasks]);

  const updatedAt = data.updated_at ? new Date(data.updated_at * 1000).toLocaleTimeString() : "—";
  const recentHistory = (data.history || []).slice(-6).reverse();

  return (
    <div className="page">
      <header>
        <div>
          <h1>GEPA · Live Task Dashboard</h1>
          <div className="pill">Streaming progress and GEPA composite metrics</div>
        </div>
        <div className="updated">Updated: {updatedAt}</div>
      </header>

      <div className="grid metrics">
        <MetricCard title="GEPA composite" value={(gepa.composite_score ?? 0).toFixed(3)} hint="Score" />
        <MetricCard title="Latest task score" value={gepa.latest_score !== null && gepa.latest_score !== undefined ? gepa.latest_score.toFixed(2) : "—"} hint="last result" />
        <MetricCard title="Checklist" value={`${totals.complete}/${totals.total}`} hint="done" />
        <MetricCard title="Traces seen" value={gepa.total_traces ?? 0} hint="examples" />
        <MetricCard title="Prompt state" value={gepa.best_prompt ? "learned" : "baseline"} hint={gepa.best_prompt?.slice(0, 32) || "default"} />
      </div>

      <div className="layout">
        <div className="panel tasks">
          <h2>
            <span className="dot" />
            Ordered checklist
          </h2>
          {error ? <span className="error">{error}</span> : null}
          <ol>
            {tasks.length ? tasks.map((task) => <TaskItem key={task.id} task={task} />) : <div className="subtitle">No tasks yet—launch a goal to see activity.</div>}
          </ol>
        </div>

        <div className="panel">
          <h2>
            <span className="dot" />
            Embedded TUI visualizer
          </h2>
          <div className="subtitle">Mirrors the agent&apos;s markdown checklist live.</div>
          <TuiPanel text={data.tui} />
        </div>
      </div>

      <div className="panel" style={{ marginTop: "18px" }}>
        <h2>
          <span className="dot" />
          GEPA metric timeline
        </h2>
        <GepaTimeline scores={gepa.scores} />
      </div>

      <div className="panel" style={{ marginTop: "18px" }}>
        <h2>
          <span className="dot" />
          Progress history
        </h2>
        <HistoryStrip items={recentHistory} />
      </div>
    </div>
  );
};

const root = createRoot(document.getElementById("root"));
root.render(<App />);
