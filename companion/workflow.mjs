const LINKEDIN = /^(www\.)?linkedin\.com$/i;
const GUPY = /(^|\.)gupy\.io$/i;
export function vacancyPlatform(value) {
  try {
    const host = new URL(value).hostname.toLowerCase();
    if (LINKEDIN.test(host)) return 'linkedin';
    if (GUPY.test(host)) return 'gupy';
  } catch { /* invalid URL */ }
  return null;
}
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
  if (data.resume_text !== undefined && (typeof data.resume_text !== 'string' || data.resume_text.length > 12000)) {
    throw new Error('Contexto do currículo inválido.');
  }
  if (data.matched_keywords !== undefined && (!Array.isArray(data.matched_keywords) || data.matched_keywords.length > 40 || data.matched_keywords.some(item => typeof item !== 'string' || item.length > 80))) {
    throw new Error('Palavras-chave da vaga inválidas.');
  }
  return data;
}
export function challengeDetected(title, body) {
  return /captcha|verify you are human|verifique que você é humano|cloudflare|access denied/i.test(title + ' ' + body);
}
export function planFields(profile, resumeText = '', matchedKeywords = []) {
  const text = resumeText.slice(0, 12000);
  const email = text.match(/[\w.+-]+@[\w-]+\.[\w.]+/i)?.[0] || '';
  const contactLines = text.split(/\r?\n/).filter(line => {
    const digits = line.replace(/\D/g, '').length;
    const looksLikeContact = /(?:telefone|celular|phone|whatsapp|\+|\(|\s{2,})/i.test(line);
    return digits >= 10 && digits <= 13 && looksLikeContact && /\d[\d\s().+-]{8,}\d/.test(line);
  });
  const phoneLine = contactLines.find(line => /(?:telefone|celular|phone|whatsapp)/i.test(line)) || contactLines[0] || '';
  const phone = phoneLine.match(/\+?[\d][\d\s().-]{8,}[\d]/)?.[0]?.trim() || '';
  const linkedin = text.match(/https?:\/\/(?:www\.)?linkedin\.com\/in\/[\w%-]+/i)?.[0] || '';
  const profileWithResume = {
    ...profile,
    email: profile.email || email,
    phone: profile.phone || phone,
    linkedin: profile.linkedin || linkedin,
  };
  const candidates = [
    ['name', /^(nome completo|full name)$/i],
    ['email', /^(e-mail|email)$/i],
    ['phone', /^(celular|telefone|phone)$/i],
    ['linkedin', /^(linkedin|perfil do linkedin)$/i],
  ];
  const fields = candidates.flatMap(([key, label]) => {
    const value = profileWithResume[key];
    return typeof value === 'string' && value.trim() ? [{ key, label, value: value.trim() }] : [];
  });
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(line => line.length >= 24 && line.length <= 500);
  const keywords = matchedKeywords.map(value => value.trim()).filter(Boolean);
  const relevantLines = lines
    .map((line, index) => ({ line, index, hits: keywords.filter(keyword => line.toLocaleLowerCase().includes(keyword.toLocaleLowerCase())).length }))
    .filter(item => item.hits > 0)
    .sort((a, b) => b.hits - a.hits || a.index - b.index)
    .slice(0, 4)
    .map(item => item.line);
  if (relevantLines.length) {
    const evidence = relevantLines.join(' ');
    fields.push({ key: 'resume_evidence', label: /^(resumo|sobre você|fale sobre você|apresentação|experiência relevante|relevant experience|about you|professional summary)$/i, value: evidence.slice(0, 1200) });
    const supportedKeywords = keywords.filter(keyword => text.toLocaleLowerCase().includes(keyword.toLocaleLowerCase()));
    if (supportedKeywords.length) fields.push({ key: 'resume_skills', label: /^(competências|habilidades|skills|tecnologias|technical skills)$/i, value: supportedKeywords.join(', ') });
  }
  return fields;
}
