const LINKEDIN = /^(www\.)?linkedin\.com$/i;
const GUPY = /(^|\.)gupy\.io$/i;
export function isTrustedVacancyUrl(value) {
  try {
    const u = new URL(value);
    return u.protocol === 'https:' && !u.username && !u.password &&
      (LINKEDIN.test(u.hostname) || GUPY.test(u.hostname));
  } catch { return false; }
}
export function validateRequest(data) {
  if (!data || typeof data !== 'object' || !data.consent) {
    throw new Error('Confirme a candidatura antes de iniciar.');
  }
  if (!data.job || !isTrustedVacancyUrl(data.job.url)) {
    throw new Error('Link de vaga inválido. Use LinkedIn ou Gupy.');
  }
  if (typeof data.job.title !== 'string' || data.job.title.length > 255) {
    throw new Error('Título da vaga inválido.');
  }
  if (!data.profile || typeof data.profile !== 'object') throw new Error('Perfil ausente.');
  return data;
}
export function challengeDetected(title, body) {
  return /captcha|verify you are human|verifique que você é humano|cloudflare|access denied/i.test(title + ' ' + body);
}
export function planFields(profile) {
  const candidates = [
    ['name', /^(nome completo|full name)$/i],
    ['email', /^(e-mail|email)$/i],
    ['phone', /^(celular|telefone|phone)$/i],
    ['linkedin', /^(linkedin|perfil do linkedin)$/i],
  ];
  return candidates.flatMap(([key, label]) => {
    const value = profile[key];
    return typeof value === 'string' && value.trim() ? [{ key, label, value: value.trim() }] : [];
  });
}
