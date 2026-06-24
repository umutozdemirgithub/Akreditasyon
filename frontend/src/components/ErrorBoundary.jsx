import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Keep this visible in the browser console without collapsing the whole app to a blank page.
    console.error("UI render error:", error, info);
  }

  componentDidUpdate(prevProps) {
    if (this.props.resetKey !== prevProps.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      return (
        <section className="editor-panel error-panel">
          <div className="editor-header">
            <div>
              <span className="badge danger">Arayüz hatası</span>
              <h2>Bu ekran yüklenirken bir sorun oluştu.</h2>
            </div>
            {this.props.onReset && <button type="button" onClick={this.props.onReset}>Gösterge paneline dön</button>}
          </div>
          <p className="muted">Sayfa tamamen boş kalmasın diye hata yakalandı. Lütfen bu hata mesajını teknik destekle paylaşın.</p>
          <pre className="error-details">{this.state.error?.message || String(this.state.error)}</pre>
        </section>
      );
    }
    return this.props.children;
  }
}
