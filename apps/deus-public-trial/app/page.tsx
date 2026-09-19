'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

const CONSTITUTION_VERSION = 'BL-COMPUTE-ALLIANCE-PUBLIC-V0.1';
const DIFFICULTY = 3;
const MARGIN_PERCENT = 5;

type Message = { role: 'user' | 'assistant' | 'system'; content: string };
type ProofResult = {
  localDigest: string;
  proofNonce: number;
  proofHash: string;
  attempts: number;
  elapsedMs: number;
  localSummary: Record<string, unknown>;
};

export default function PublicTrialPage() {
  const [joined, setJoined] = useState(false);
  const [paused, setPaused] = useState(false);
  const [checked, setChecked] = useState(false);
  const [budget, setBudget] = useState(10);
  const [prompt, setPrompt] = useState('');
  const [busy, setBusy] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [sessionAttempts, setSessionAttempts] = useState(0);
  const [error, setError] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'system',
      content: 'DEUS Public Trial chỉ hiển thị giao diện làm việc công khai. Lõi riêng, prompt lõi, routing nội bộ và dữ liệu bảo vệ không được đưa xuống trình duyệt.',
    },
  ]);
  const workerRef = useRef<Worker | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem('deus-public-alliance-consent');
    if (saved === CONSTITUTION_VERSION) setJoined(true);
    return () => workerRef.current?.terminate();
  }, []);

  const creditedUnits = useMemo(
    () => Math.floor(sessionAttempts * (100 - MARGIN_PERCENT) / 100),
    [sessionAttempts],
  );

  function joinAlliance() {
    if (!checked) return;
    localStorage.setItem('deus-public-alliance-consent', CONSTITUTION_VERSION);
    setJoined(true);
    setPaused(false);
    setError('');
  }

  function revokeAlliance() {
    workerRef.current?.terminate();
    workerRef.current = null;
    localStorage.removeItem('deus-public-alliance-consent');
    setJoined(false);
    setPaused(false);
    setChecked(false);
    setBusy(false);
    setAttempts(0);
  }

  async function prepareLocal(promptValue: string): Promise<ProofResult> {
    return new Promise((resolve, reject) => {
      workerRef.current?.terminate();
      const worker = new Worker('/compute-worker.js');
      workerRef.current = worker;
      worker.onmessage = (event) => {
        const data = event.data || {};
        if (data.type === 'progress') {
          setAttempts(Number(data.attempts || 0));
          return;
        }
        if (data.type === 'error') {
          worker.terminate();
          workerRef.current = null;
          reject(new Error(String(data.message || 'Local worker failed')));
          return;
        }
        if (data.type === 'ready') {
          worker.terminate();
          workerRef.current = null;
          setAttempts(Number(data.attempts || 0));
          setSessionAttempts((value) => value + Number(data.attempts || 0));
          resolve({
            localDigest: String(data.localDigest),
            proofNonce: Number(data.nonce),
            proofHash: String(data.proofHash),
            attempts: Number(data.attempts),
            elapsedMs: Number(data.elapsedMs),
            localSummary: data.localSummary || {},
          });
        }
      };
      worker.onerror = (event) => {
        worker.terminate();
        workerRef.current = null;
        reject(new Error(event.message || 'Local worker error'));
      };
      worker.postMessage({
        type: 'prepare',
        prompt: promptValue,
        difficulty: DIFFICULTY,
        budgetPercent: budget,
      });
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = prompt.trim();
    if (!joined || paused || !text || busy) return;
    if (document.hidden) {
      setError('Tab đang ở nền. DEUS Public Trial không dùng compute khi tab bị ẩn.');
      return;
    }
    setBusy(true);
    setError('');
    setAttempts(0);
    setMessages((items) => [...items, { role: 'user', content: text }]);
    setPrompt('');

    try {
      const proof = await prepareLocal(text);
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          prompt: text,
          session: {
            constitutionVersion: CONSTITUTION_VERSION,
            consent: true,
            localFirst: true,
            contributionMode: 'prompt-bound',
          },
          localDigest: proof.localDigest,
          proofNonce: proof.proofNonce,
          localSummary: {
            ...proof.localSummary,
            computeAttempts: proof.attempts,
            computeElapsedMs: proof.elapsedMs,
            browserBudgetPercent: budget,
          },
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.message || payload?.error || `HTTP ${response.status}`);
      }
      setMessages((items) => [...items, { role: 'assistant', content: String(payload.answer) }]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">DEUS ∞ · PUBLIC TRIAL</div>
          <h1>Liên minh tính toán</h1>
        </div>
        <div className="statusRow">
          <span className="pill ok">CORE ISOLATED</span>
          <span className="pill">LOCAL-FIRST</span>
          <span className="pill warn">CROSS-NODE: STAGED</span>
        </div>
      </header>

      {!joined ? (
        <section className="joinCard">
          <div className="joinIntro">
            <div className="eyebrow">HIẾN PHÁP THAM GIA</div>
            <h2>Muốn dùng DEUS Public Trial, node của bạn cũng tham gia đóng góp compute.</h2>
            <p>
              Đây không phải cơ chế chiếm dụng tài nguyên. Trình duyệt chỉ dùng ngân sách CPU bạn chọn,
              chỉ khi tab đang hoạt động, và bạn có thể pause hoặc rút consent bất kỳ lúc nào.
            </p>
          </div>

          <div className="constitutionGrid">
            <article><strong>1 · Local-first</strong><span>Bài của bạn được tiền xử lý trên chính node của bạn trước.</span></article>
            <article><strong>2 · Idle-only federation</strong><span>Tài nguyên node khác chỉ được dùng khi chúng thực sự rảnh và đã opt-in.</span></article>
            <article><strong>3 · Resource sovereignty</strong><span>Không đọc file, clipboard hay mở shell. Không chạy nền mặc định.</span></article>
            <article><strong>4 · Reversible consent</strong><span>Pause dừng ngay worker; rút consent xóa quyền dùng public trial trên trình duyệt này.</span></article>
            <article><strong>5 · Compute credits</strong><span>Đóng góp được quy đổi thành compute-credit; public preview chưa có cash payout.</span></article>
            <article><strong>6 · Phí điều phối {MARGIN_PERCENT}%</strong><span>DEUS giữ margin nhỏ trên compute-credit để vận hành scheduler và hạ tầng.</span></article>
          </div>

          <label className="consentLine">
            <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
            <span>Tôi hiểu và tự nguyện tham gia {CONSTITUTION_VERSION}. Tôi có thể dừng bất kỳ lúc nào.</span>
          </label>
          <button className="primary" disabled={!checked} onClick={joinAlliance}>Tham gia liên minh và mở DEUS</button>
        </section>
      ) : (
        <div className="workspaceGrid">
          <aside className="sidePanel">
            <div className="panelBlock">
              <div className="panelLabel">NODE CỦA BẠN</div>
              <div className="metric"><span>Trạng thái</span><strong>{paused ? 'PAUSED' : 'ACTIVE'}</strong></div>
              <div className="metric"><span>CPU budget</span><strong>{budget}%</strong></div>
              <input
                className="range"
                type="range"
                min="5"
                max="25"
                step="5"
                value={budget}
                disabled={busy}
                onChange={(e) => setBudget(Number(e.target.value))}
              />
              <div className="hint">Giới hạn public trial: 5–25%. Không chạy khi tab ẩn.</div>
            </div>

            <div className="panelBlock">
              <div className="panelLabel">PHIÊN ĐÓNG GÓP</div>
              <div className="metric"><span>Hash work</span><strong>{sessionAttempts.toLocaleString('vi-VN')}</strong></div>
              <div className="metric"><span>Credit ước tính</span><strong>{creditedUnits.toLocaleString('vi-VN')}</strong></div>
              <div className="metric"><span>Margin</span><strong>{MARGIN_PERCENT}%</strong></div>
              <div className="hint">Credit hiện chỉ là session estimate, chưa phải ledger thanh toán.</div>
            </div>

            <div className="panelBlock">
              <div className="panelLabel">FEDERATION</div>
              <div className="routeLine"><b>1</b><span>Home node xử lý trước</span></div>
              <div className="routeLine"><b>2</b><span>Idle alliance overflow</span></div>
              <div className="routeLine muted"><b>3</b><span>Broker bền vững: chưa bind</span></div>
            </div>

            <button className="secondary" onClick={() => setPaused((value) => !value)}>
              {paused ? 'Tiếp tục đóng góp' : 'Pause compute'}
            </button>
            <button className="dangerGhost" onClick={revokeAlliance}>Rút khỏi liên minh trên trình duyệt này</button>
          </aside>

          <section className="chatPanel">
            <div className="chatHeader">
              <div>
                <div className="eyebrow">PUBLIC-SAFE WORK SURFACE</div>
                <h2>Đưa bài toán cho DEUS</h2>
              </div>
              <div className="computeBadge">
                {busy ? `Local compute · ${attempts.toLocaleString('vi-VN')} work` : paused ? 'Compute paused' : 'Ready'}
              </div>
            </div>

            <div className="messages">
              {messages.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`message ${message.role}`}>
                  <div className="role">{message.role === 'user' ? 'YOU' : message.role === 'assistant' ? 'DEUS' : 'SYSTEM'}</div>
                  <div className="content">{message.content}</div>
                </div>
              ))}
              {busy && <div className="message system"><div className="role">NODE</div><div className="content">Đang local-preprocess và tạo contribution proof…</div></div>}
            </div>

            {error && <div className="errorBox">{error}</div>}

            <form className="composer" onSubmit={submit}>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                maxLength={4000}
                placeholder={paused ? 'Resume compute để tiếp tục dùng DEUS.' : 'Mô tả bài toán của bạn…'}
                disabled={paused || busy}
                rows={4}
              />
              <div className="composerFooter">
                <span>{prompt.length}/4000 · local-first proof required</span>
                <button className="primary" disabled={paused || busy || !prompt.trim()} type="submit">
                  {busy ? 'Đang xử lý…' : 'Gửi bài toán'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      <footer className="footer">
        <span>DEUS Public Trial không phải quyền truy cập DEUS core.</span>
        <span>Không có bằng chứng cross-node thì giao diện không được tuyên bố cross-node đã chạy.</span>
      </footer>
    </main>
  );
}
