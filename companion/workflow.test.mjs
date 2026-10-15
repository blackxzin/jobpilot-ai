import test from 'node:test';
import assert from 'node:assert/strict';
import { isTrustedVacancyUrl, validateRequest, planFields, challengeDetected } from './workflow.mjs';

test('trusted HTTPS Gupy and LinkedIn vacancy URLs', () => {
  assert.equal(isTrustedVacancyUrl('https://empresa.gupy.io/jobs/123'), true);
  assert.equal(isTrustedVacancyUrl('https://www.linkedin.com/jobs/view/123'), true);
  for (const url of ['http://gupy.io/jobs/12','https://gupy.io.evil.com/jobs/2','file:///tmp/a','https://user:pass@gupy.io/jobs/2']) {
    assert.equal(isTrustedVacancyUrl(url), false);
  }
});
test('requires an explicit user click/consent', () => {
  assert.throws(() => validateRequest({ job: { url: 'https://empresa.gupy.io/jobs/1' }, profile: {} }), /Confirme/);
});
test('only fills whitelisted profile fields', () => {
  assert.deepEqual(planFields({ name: ' Ana ', salary: '5000', cpf: '123', email: 'ana@test.com' }).map(x => x.key), ['name','email']);
});
test('stops on challenges', () => {
  assert.equal(challengeDetected('Access Denied', ''), true);
  assert.equal(challengeDetected('Job application', 'Welcome'), false);
});
