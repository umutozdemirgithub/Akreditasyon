import React, { useEffect, useState } from "react";
import { Lock, LogOut, ShieldCheck } from "lucide-react";

function LoginScreen({ onLogin, busy, error }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const canvasRef = React.useRef(null);

  // Particle Effect
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    let particles = [];
    const colors = ['#60a5fa', '#93c5fd', '#a5b4fc', '#c4d0ff'];

    class Particle {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 2.5 + 0.8;
        this.speedX = Math.random() * 0.6 - 0.3;
        this.speedY = Math.random() * 0.6 - 0.3;
        this.color = colors[Math.floor(Math.random() * colors.length)];
        this.opacity = Math.random() * 0.6 + 0.3;
      }
      update() {
        this.x += this.speedX;
        this.y += this.speedY;
        if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
        if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
      }
      draw() {
        ctx.save();
        ctx.globalAlpha = this.opacity;
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    }

    function init() {
      particles = [];
      for (let i = 0; i < 120; i++) {
        particles.push(new Particle());
      }
    }

    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p, i) => {
        p.update();
        p.draw();

        // Bağlantı çizgileri
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          
          if (distance < 110) {
            ctx.save();
            ctx.globalAlpha = (110 - distance) / 110 * 0.15;
            ctx.strokeStyle = '#60a5fa';
            ctx.lineWidth = 0.6;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
            ctx.restore();
          }
        }
      });
      frameId = requestAnimationFrame(animate);
    }

    let frameId;
    init();
    animate();

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (frameId) cancelAnimationFrame(frameId);
    };
  }, []);

  return (
    <main className="login-pro">
      <canvas id="particle-canvas" ref={canvasRef} />
      
      <div className="login-pro-card">
        <div className="card-header">
          <div className="shield-glow">
            <ShieldCheck size={58} strokeWidth={1.6} />
          </div>
          <h2>Akreditasyon Enterprise</h2>
          <p>Kurumsal Akreditasyon ve Kalite Yönetim Sistemi</p>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); onLogin(username, password); }}>
          {error && <div className="alert error" style={{ marginBottom: "24px" }}>{error}</div>}
          
          <div className="field">
            <input 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              placeholder="Kullanıcı Adı" 
              autoComplete="username"
            />
          </div>
          
          <div className="field">
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              placeholder="Şifre" 
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className="pro-btn" disabled={busy}>
            {busy ? "Giriş yapılıyor..." : "GÜVENLİ GİRİŞ YAP"}
          </button>
        </form>

        <div style={{ marginTop: "32px", fontSize: "13.5px", color: "#64748b", opacity: 0.8 }}>
          © 2026 Akreditasyon Platformu • Tüm Hakları Saklıdır
        </div>
      </div>
    </main>
  );
}

function ChangePasswordScreen({ user, onSubmit, onLogout, busy, error, message }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState("");

  function submit(event) {
    event.preventDefault();
    setLocalError("");
    if (newPassword !== confirmPassword) {
      setLocalError("Yeni şifre ve tekrar alanı aynı olmalıdır.");
      return;
    }
    onSubmit(currentPassword, newPassword);
  }

  return (
    <main className="login-pro change-password-page">
      <div className="login-pro-card change-password-card">
        <div className="card-header">
          <div className="shield-glow">
            <Lock size={54} strokeWidth={1.7} />
          </div>
          <h2>Şifre Değişimi Zorunlu</h2>
          <p>{user.full_name || user.username}, güvenli devam etmek için ilk şifrenizi değiştirin.</p>
        </div>

        <form onSubmit={submit}>
          {(error || localError) && <div className="alert error" style={{ marginBottom: "18px" }}>{localError || error}</div>}
          {message && <div className="alert success" style={{ marginBottom: "18px" }}>{message}</div>}

          <div className="field">
            <input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              placeholder="Mevcut şifre"
              autoComplete="current-password"
            />
          </div>
          <div className="field">
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="Yeni güçlü şifre"
              autoComplete="new-password"
            />
          </div>
          <div className="field">
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Yeni şifre tekrar"
              autoComplete="new-password"
            />
          </div>

          <div className="password-policy-note">
            En az 10 karakter, büyük/küçük harf, rakam ve özel karakter kullanın.
          </div>

          <button type="submit" className="pro-btn" disabled={busy}>
            {busy ? "Güncelleniyor..." : "ŞİFREMİ GÜNCELLE"}
          </button>
          <button type="button" className="ghost-button logout-inline" onClick={onLogout}>
            <LogOut size={16} /> Çıkış yap
          </button>
        </form>
      </div>
    </main>
  );
}

export { LoginScreen, ChangePasswordScreen };
