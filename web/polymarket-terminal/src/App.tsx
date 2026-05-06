function App() {
  return (
    <main className="terminal-shell" aria-label="Polymarket terminal">
      <section className="terminal-panel">
        <div className="terminal-bar">
          <span className="terminal-title">POLYMARKET TERMINAL</span>
          <span className="terminal-status">PORT 4177</span>
        </div>
        <div className="terminal-body">
          <p className="terminal-line">
            <span className="terminal-prompt">&gt;</span> Initializing web terminal scaffold
          </p>
          <p className="terminal-muted">Market workspaces will load here in later tasks.</p>
        </div>
      </section>
    </main>
  );
}

export default App;
