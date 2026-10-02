/** Isolated browser regression: editing resource metadata must not mutate flags. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.QA_PLAYWRIGHT_MODULE || 'playwright');
const args = process.argv.slice(2);
const option = (name, fallback) => { const index = args.indexOf(name); return index >= 0 ? args[index + 1] : fallback; };
const origin = option('--url', 'http://127.0.0.1:4183');
const artifacts = path.resolve(option('--artifacts', 'work/qa/admin-resources'));

async function run() {
  fs.mkdirSync(artifacts, { recursive: true });
  const browser = await chromium.launch({ headless: true, channel: option('--channel', 'chrome') });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.setDefaultTimeout(12000);
  const user = { id: 9002, username: 'qa_admin', email: null, role: 'admin', is_active: true };
  let challenge = {
    id: 901, code: 'LAB-01', name: 'Prueba de recursos', description: 'Edita únicamente el material de apoyo.',
    instructions: 'Instrucciones originales.', difficulty: 'Básico', category: 'MISC', scenario: null,
    mitre_technique: 'T1046', asset_references: ['QA-LINUX'], points: 100,
    is_published: true, completed: false, flag_count: 2,
    flags: [
      { id: 701, label: 'Dynamic fixture', mode: 'dynamic', template: 'FLAG{lab-01_{{USER}}_{{RUN_ID}}_{{RAND}}}', flag_order: 1, is_active: true },
      { id: 702, label: 'Static fixture', mode: 'static', template: null, flag_order: 2, is_active: true },
    ],
  };
  const flagMutations = [];
  const unexpectedRequests = [];
  const pageErrors = [];
  const challengeUpdates = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.route('**/api/**', async route => {
    const request = route.request();
    const endpoint = new URL(request.url()).pathname.replace('/api/v1', '');
    let status = 200, body;
    if (endpoint === '/auth/login') body = { access_token: 'qa-fixture-admin-session', user };
    else if (endpoint === '/auth/me') body = user;
    else if (endpoint === '/challenges' && request.method() === 'GET') body = [challenge];
    else if (endpoint === '/challenges/LAB-01' && request.method() === 'PUT') {
      const update = JSON.parse(request.postData());
      challengeUpdates.push(update);
      challenge = { ...challenge, ...update };
      body = challenge;
    } else if (endpoint.startsWith('/challenges/LAB-01/flags')) {
      flagMutations.push(`${request.method()} ${endpoint}`);
      body = challenge;
    } else if (endpoint === '/ranking') body = { rows: [] };
    else if (endpoint === '/ws/ranking/session') body = { websocket_path: '/api/v1/ws/ranking', expires_at: new Date(Date.now() + 900000).toISOString() };
    else if (endpoint === '/reports/progress') body = [];
    else if (endpoint === '/users/visible') body = [user];
    else if (endpoint === '/groups') body = [{ id: 301, code: 'QA-GROUP', name: 'Grupo de prueba', description: '', is_active: true, members: [], challenges: [{ challenge_id: 901, code: 'LAB-01', name: challenge.name }] }];
    else if (endpoint === '/laboratories') body = [{ id: 201, code: 'QA-LAB', name: 'Laboratorio de prueba', description: '', segment: 'QA', status: 'active', vms: [{ id: 202, laboratory_id: 201, name: 'QA-LINUX', os: 'Linux', ip_address: '192.0.2.15', role: 'victim', profile: 'qa', network_role: 'test', vlan: 'test', subnet: '192.0.2.0/24', status: 'ready' }] }];
    else { unexpectedRequests.push(`${request.method()} ${endpoint}`); status = 500; body = { detail: 'Unexpected isolated QA request' }; }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.routeWebSocket('**/api/v1/ws/ranking**', socket => socket.onMessage(() => {}));
  const result = { environment: 'isolated admin API fixtures', checks: [], limitations: ['No real administrative API, flags, groups, database or resources are changed.'] };
  try {
    await page.goto(origin);
    await page.getByLabel('Usuario', { exact: true }).fill('qa_admin');
    await page.getByLabel('Contraseña', { exact: true }).fill('fixture');
    await page.getByRole('button', { name: 'Entrar a la plataforma' }).click();
    await page.locator('.sidebar').getByRole('button', { name: 'Retos', exact: true }).click();
    await page.locator('tbody tr').filter({ hasText: 'LAB-01' }).getByRole('button', { name: 'Editar', exact: true }).click();
    const modal = page.locator('.challenge-modal');
    await modal.waitFor();
    await modal.getByLabel(/Instrucciones del reto/).fill('Instrucciones actualizadas sin cambiar flags.');
    await modal.getByRole('button', { name: '+ Añadir recurso', exact: true }).click();
    const resource = modal.locator('.learning-resource-editor-row').first();
    await resource.getByLabel('Título', { exact: true }).fill('Video sobre SSH');
    await resource.getByLabel('URL del recurso', { exact: true }).fill('https://example.invalid/ssh-video');
    await modal.getByRole('button', { name: '+ Añadir recurso', exact: true }).click();
    const slides = modal.locator('.learning-resource-editor-row').nth(1);
    await slides.getByLabel(/Tipo de recurso/).selectOption('presentation');
    await slides.getByLabel('Título', { exact: true }).fill('Diapositivas SSH');
    await slides.getByLabel('URL del recurso', { exact: true }).fill('/media/ssh-slides.pdf');
    await modal.getByRole('button', { name: 'Guardar cambios', exact: true }).click();
    await modal.waitFor({ state: 'detached' });
    assert.equal(challengeUpdates.length, 1);
    assert.match(challengeUpdates[0].instructions, /Instrucciones actualizadas sin cambiar flags/);
    assert.match(challengeUpdates[0].instructions, /Video sobre SSH/);
    assert.match(challengeUpdates[0].instructions, /Diapositivas SSH/);
    assert.equal(flagMutations.length, 0, 'Editing learning resources must not issue any flag mutation');
    result.checks.push({ name: 'Editing resources/instructions makes no flag mutation requests', result: 'PASS' });
    console.log('PASS Editing resources/instructions makes no flag mutation requests');
    await page.locator('tbody tr').filter({ hasText: 'LAB-01' }).getByRole('button', { name: 'Editar', exact: true }).click();
    await modal.waitFor();
    assert.equal(await modal.getByLabel(/Instrucciones del reto/).inputValue(), 'Instrucciones actualizadas sin cambiar flags.');
    assert.equal(await modal.locator('.learning-resource-editor-row').count(), 2);
    assert.equal(await modal.locator('.flag-builder-row').count(), 2);
    assert.deepEqual(pageErrors, []);
    assert.deepEqual(unexpectedRequests, []);
    await page.screenshot({ path: path.join(artifacts, 'resource-editor.png'), fullPage: true });
    result.checks.push({ name: 'Saved materials reopen correctly and existing flag metadata remains', result: 'PASS' });
    console.log('PASS Saved materials reopen correctly and existing flag metadata remains');
  } catch (error) {
    result.checks.push({ name: 'Admin resource browser regression', result: 'FAIL', message: error.message });
    await page.screenshot({ path: path.join(artifacts, 'failure.png'), fullPage: true });
    throw error;
  } finally {
    result.flagMutations = flagMutations;
    result.pageErrors = pageErrors;
    result.unexpectedRequests = unexpectedRequests;
    fs.writeFileSync(path.join(artifacts, 'results.json'), JSON.stringify(result, null, 2));
    await browser.close();
  }
}

run().catch(error => { console.error(error.message); process.exitCode = 1; });
