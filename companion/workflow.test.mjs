import test from 'node:test';
import assert from 'node:assert/strict';
import { isTrustedVacancyUrl, validateRequest, planFields, challengeDetected, vacancyPlatform } from './workflow.mjs';

test('trusted HTTPS Gupy and LinkedIn vacancy URLs', () => {
  assert.equal(isTrustedVacancyUrl('https://empresa.gupy.io/jobs/123'), true);
  assert.equal(isTrustedVacancyUrl('https://www.linkedin.com/jobs/view/123'), true);
  for (const url of ['http://gupy.io/jobs/12','https://gupy.io.evil.com/jobs/2','file:///tmp/a','https://user:pass@gupy.io/jobs/2']) {
    assert.equal(isTrustedVacancyUrl(url), false);
  }
});
test('detects supported vacancy platforms', () => {
  assert.equal(vacancyPlatform('https://www.linkedin.com/jobs/view/123'), 'linkedin');
  assert.equal(vacancyPlatform('https://empresa.gupy.io/jobs/123'), 'gupy');
  assert.equal(vacancyPlatform('https://linkedin.com.evil.test/jobs/123'), null);
});
test('requires an explicit user click/consent', () => {
  assert.throws(() => validateRequest({ job: { url: 'https://empresa.gupy.io/jobs/1' }, profile: {} }), /Confirme/);
});
test('only fills whitelisted profile fields', () => {
  assert.deepEqual(planFields({ name: ' Ana ', salary: '5000', cpf: '123', email: 'ana@test.com' }).map(x => x.key), ['name','email']);
});
test('uses resume contact and only evidence-backed vacancy keywords', () => {
  const fields = planFields({ name: 'Ana' }, 'ana.cv@email.com\n+55 11 99999-8888\nDesenvolvi APIs com Python e FastAPI em produção.', ['Python', 'AWS']);
  assert.equal(fields.find(field => field.key === 'email')?.value, 'ana.cv@email.com');
  assert.equal(fields.find(field => field.key === 'phone')?.value, '+55 11 99999-8888');
  assert.equal(fields.find(field => field.key === 'resume_evidence')?.value, 'Desenvolvi APIs com Python e FastAPI em produção.');
  assert.equal(fields.find(field => field.key === 'resume_skills')?.value, 'Python');
});
test('stops on challenges', () => {
  assert.equal(challengeDetected('Access Denied', ''), true);
  assert.equal(challengeDetected('Job application', 'Welcome'), false);
});
