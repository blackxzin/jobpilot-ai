import http from 'node:http';
import { chromium } from 'playwright';
import { isTrustedVacancyUrl, validateRequest, challengeDetected, planFields, vacancyPlatform } from './workflow.mjs';

const PORT = Number(process.env.JOBPILOT_COMPANION_PORT || 8765);
const ALLOWED_ORIGINS = new Set([
  'http://localhost:3000', 'http://127.0.0.1:3000',
  ...(process.env.JOBPILOT_ALLOWED_ORIGINS || '').split(',').filter(Boolean),
]);
let browserContext;
let running = false;

async function getContext() {
  if (!browserContext) {
    browserContext = await chromium.launchPersistentContext(
      process.env.JOBPILOT_BROWSER_PROFILE || './.jobpilot-browser',
      { headless: false, viewport: { width: 1440, height: 900 } },
    );
  }
  return browserContext;
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function visible(locator) {
  try { return await locator.count() === 1 && await locator.isVisible(); }
  catch { return false; }
}

async function runApplication(payload) {
  const ctx = await getContext();
  const page = await ctx.newPage();
  const platform = vacancyPlatform(payload.job.url);
  const result = { state: 'needs_review', platform, reason: '', url: payload.job.url, fields_filled: [] };
  try {
    await page.goto(payload.job.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await sleep(1200);
    if (challengeDetected(await page.title(), (await page.locator('body').innerText()).slice(0, 3000))) {
      result.reason = 'Verificação de acesso: resolva no navegador e execute novamente.';
      return result;
    }
    const currentPlatform = vacancyPlatform(page.url());
    if (currentPlatform !== platform) {
      result.reason = `A página redirecionou para fora de ${platform === 'linkedin' ? 'LinkedIn' : 'Gupy'}. Continue manualmente nesta página.`;
      result.url = page.url();
      return result;
    }

    // Existing login sessions are kept in the local persistent browser profile.
    // No passwords, MFA codes or cookies leave the computer.
    if (/\/login|\/signin|\/checkpoint|\/authwall|\/cadastro|\/register/.test(page.url().toLowerCase())) {
      result.reason = `Faça login${platform === 'gupy' ? '/cadastro' : ''} no ${platform === 'linkedin' ? 'LinkedIn' : 'Gupy'} no navegador e tente novamente.`;
      result.url = page.url();
      return result;
    }

    const start = page.getByRole('button', { name: platform === 'linkedin'
      ? /easy apply|candidatura simplificada|candidatura fácil/i
      : /candidat(?:ar|e-se)|inscrever|aplicar/i }).first();
    if (await start.count() && await start.isVisible()) {
      await start.click();
      await sleep(950);
    }

    const fields = planFields(payload.profile, payload.resume_text || '', payload.matched_keywords || []);
    // Fill only labelled, unambiguous inputs. Never guess sensitive details.
    for (const item of fields) {
      const controls = page.getByLabel(item.label, { exact: false });
      if (await visible(controls)) {
        const tag = await controls.evaluate(el => el.tagName.toLowerCase());
        const type = await controls.getAttribute('type');
        if ((tag === 'input' && !['file', 'checkbox', 'radio', 'hidden'].includes(type)) || tag === 'textarea') {
          if (!(await controls.inputValue()).trim()) {
            await controls.fill(item.value);
            result.fields_filled.push(item.key);
          }
        }
      }
    }

    result.url = page.url();
    const body = await page.locator('body').innerText();
    if (challengeDetected(await page.title(), body.slice(0, 3000))) {
      result.reason = 'CAPTCHA ou verificação de segurança. Conclua manualmente.';
      return result;
    }
    if (/\/login|\/signin|\/checkpoint|\/authwall/.test(page.url().toLowerCase())) {
      result.reason = `Sessão do ${platform === 'linkedin' ? 'LinkedIn' : 'Gupy'} não autenticada. Faça login manualmente.`;
      return result;
    }
    // Form questions vary by employer. We do not click the final submit control
    // unless an explicit supported form adapter verifies every required response.
    result.reason = `Campos conhecidos preenchidos. Revise respostas e anexos e conclua no ${platform === 'linkedin' ? 'LinkedIn' : 'Gupy'}. Envio não confirmado.`;
    return result;
  } catch (err) {
    result.state = 'failed';
    result.reason = String(err.message || err).slice(0, 300);
    return result;
  }
}

const server = http.createServer(async (req, res) => {
  const origin = req.headers.origin || '';
  const headers = {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS.has(origin) ? origin : 'null',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
  const reply = (status, obj) => { res.writeHead(status, headers); res.end(JSON.stringify(obj)); };
  if (!ALLOWED_ORIGINS.has(origin)) return reply(403, { error: 'Origin not allowed' });
  if (req.method === 'OPTIONS') return reply(204, {});
  if (req.method === 'GET' && req.url === '/health') return reply(200, { ready: true, busy: running });
  if (req.method !== 'POST' || req.url !== '/apply') return reply(404, { error: 'Not found' });
  if (running) return reply(409, { error: 'Já existe uma candidatura aberta.' });
  if (req.method === 'POST' && req.url === '/apply') running = true;
  let raw = '';
  try {
    for await (const chunk of req) {
      raw += chunk.toString();
      if (raw.length > 80000) return reply(413, { error: 'Payload too large' });
    }
    const payload = validateRequest(JSON.parse(raw));
    return reply(200, await runApplication(payload));
  } catch (err) {
    return reply(400, { error: String(err.message || err).slice(0, 280) });
  } finally {
    running = false;
  }
});
server.listen(PORT, '127.0.0.1', () => {
  process.stdout.write('JobPilot companion disponível em http://127.0.0.1:' + PORT + '\\n');
});
