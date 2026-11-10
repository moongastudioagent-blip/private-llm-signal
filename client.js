/**
 * Private LLM client for the signal platform.
 * Set PRIVATE_LLM_URL in your Railway environment variables to the
 * Cloudflare Tunnel URL (e.g. https://your-name.trycloudflare.com).
 */

// Works in Node (Railway backend) and browser (Vite/Next via NEXT_PUBLIC_ prefix)
const LLM_BASE =
  process.env.PRIVATE_LLM_URL ||
  process.env.NEXT_PUBLIC_PRIVATE_LLM_URL ||
  "http://localhost:8000";

const LLM_API_KEY =
  process.env.LLM_API_KEY ||
  process.env.NEXT_PUBLIC_LLM_API_KEY ||
  "";

function authHeaders() {
  const h = { "Content-Type": "application/json" };
  if (LLM_API_KEY) h["Authorization"] = `Bearer ${LLM_API_KEY}`;
  return h;
}

export async function askHelp(question, context = "") {
  const res = await fetch(`${LLM_BASE}/help`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ question, context }),
  });
  if (!res.ok) throw new Error(`LLM error: ${res.status}`);
  const { answer } = await res.json();
  return answer;
}

export async function sendChat(message, history = [], system = "") {
  const body = { message, history };
  if (system) body.system = system;

  const res = await fetch(`${LLM_BASE}/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`LLM error: ${res.status}`);
  const { reply } = await res.json();
  return reply;
}

export async function checkHealth() {
  const res = await fetch(`${LLM_BASE}/health`);
  return res.json();
}
