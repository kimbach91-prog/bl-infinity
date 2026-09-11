const encoder = new TextEncoder();

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function summarize(text) {
  const words = text.trim() ? text.trim().split(/\s+/u) : [];
  const counts = new Map();
  for (const raw of words) {
    const token = raw.toLocaleLowerCase().replace(/[^\p{L}\p{N}_-]+/gu, '');
    if (!token || token.length < 3) continue;
    counts.set(token, (counts.get(token) || 0) + 1);
  }
  const keywords = [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 12)
    .map(([token, count]) => ({ token, count }));
  return {
    chars: [...text].length,
    words: words.length,
    lines: text ? text.split(/\r?\n/u).length : 0,
    keywords,
  };
}

async function prove(prompt, difficulty, budgetPercent) {
  const localDigest = await sha256Hex(prompt);
  const prefix = '0'.repeat(difficulty);
  const batch = Math.max(4, Math.min(64, Math.round(8 + budgetPercent * 1.8)));
  let nonce = 0;
  const startedAt = performance.now();
  while (true) {
    for (let i = 0; i < batch; i += 1) {
      const hash = await sha256Hex(`${localDigest}:${nonce}`);
      if (hash.startsWith(prefix)) {
        return {
          nonce,
          proofHash: hash,
          localDigest,
          attempts: nonce + 1,
          elapsedMs: Math.round(performance.now() - startedAt),
        };
      }
      nonce += 1;
    }
    postMessage({ type: 'progress', attempts: nonce });
    const pauseMs = Math.max(0, Math.round((100 - budgetPercent) / 4));
    if (pauseMs) await new Promise((resolve) => setTimeout(resolve, pauseMs));
  }
}

self.onmessage = async (event) => {
  const message = event.data || {};
  if (message.type !== 'prepare') return;
  try {
    const prompt = String(message.prompt || '');
    const difficulty = Number(message.difficulty || 3);
    const budgetPercent = Math.max(5, Math.min(25, Number(message.budgetPercent || 10)));
    const localSummary = summarize(prompt);
    const proof = await prove(prompt, difficulty, budgetPercent);
    postMessage({ type: 'ready', localSummary, ...proof });
  } catch (error) {
    postMessage({ type: 'error', message: error instanceof Error ? error.message : String(error) });
  }
};
