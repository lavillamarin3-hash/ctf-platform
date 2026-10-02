/**
 * Browser regression checks against an isolated static frontend preview.
 * All API and WebSocket traffic is intercepted. This is NOT a production
 * Guacamole/SSH, PostgreSQL, Redis, injection or physical-cleanup test.
 *
 * Usage:
 *   QA_PLAYWRIGHT_MODULE=/path/to/playwright node scripts/qa/browser-smoke.cjs
 *   --url http://127.0.0.1:4183 --artifacts work/qa/browser
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.QA_PLAYWRIGHT_MODULE || 'playwright');

const args = process.argv.slice(2);
const option = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
};
const origin = option('--url', 'http://127.0.0.1:4183');
const artifacts = path.resolve(option('--artifacts', 'work/qa/browser'));
const libraryPath = path.resolve(option('--guacamole-library', 'work/qa/guacamole-common-js.js'));
const output = { environment: 'isolated browser fixtures', checks: [], limitations: [
  'No real authentication, Guacamole server, SSH command, VM, PostgreSQL or Redis is contacted.',
  'Fixture protocol verifies UI transport and clipboard handling only.',
] };
const fixtureFlag = 'FLAG{qa_fixture_first_run}';
const nextFixtureFlag = 'FLAG{qa_fixture_second_run}';
const user = { id: 9001, username: 'qa_student', email: null, role: 'player', is_active: true };
const challenge = {
  id: 901, code: 'LAB-01', name: 'Reconocimiento SSH controlado',
  description: 'Reconoce el entorno de práctica asignado y encuentra la evidencia.',
  instructions: 'Consulta los servicios y recupera la flag en el laboratorio autorizado.\n\n[CTF_RESOURCES]\n' + JSON.stringify([
    { kind: 'video', title: 'Video de prueba SSH', url: 'https://youtu.be/aBcDeFgHiJk' },
    { kind: 'presentation', title: 'Presentación de prueba', url: 'https://example.invalid/qa-slides.pdf' },
  ]) + '\n[/CTF_RESOURCES]',
  difficulty: 'Básico', category: 'MISC', scenario: 'Laboratorio de prueba',
  mitre_technique: 'T1046', asset_references: ['QA-LINUX'], points: 100,
  is_published: true, flag_count: 1, completed: false,
};
const secondChallenge = {
  ...challenge, id: 902, code: 'WEB-02', name: 'Análisis web intermedio',
  description: 'Revisa la evidencia web asignada.', difficulty: 'Medio', category: 'WEB',
};
const instruction = (...elements) => elements.map(value => `${String(value).length}.${value}`).join(',') + ';';

async function run() {
  fs.mkdirSync(artifacts, { recursive: true });
  assert.ok(fs.existsSync(libraryPath), 'Download the official installed Guacamole client library and pass --guacamole-library PATH');
  const clientLibrary = fs.readFileSync(libraryPath);
  output.guacamoleClientLibrarySha256 = crypto.createHash('sha256').update(clientLibrary).digest('hex');
  const browser = await chromium.launch({ headless: true, channel: option('--channel', 'chrome') });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await context.newPage();
  page.setDefaultTimeout(12000);
  const pageErrors = [];
  const unexpectedRequests = [];
  let runs = [];
  let nextRunId = 9101;
  let starts = 0;
  let failClose = false;
  let activeFlag = fixtureFlag;
  let wsReceived = [];
  let terminalSockets = [];
  let brokerRequests = 0;
  const selectedProtocols = [];
  let offerRdp = true;
  let delegatedReady = false;
  let authAttempts = 0;
  const socketUrls = [];

  page.on('pageerror', error => pageErrors.push(error.message));
  const check = async (name, callback) => {
    try { await callback(); output.checks.push({ name, result: 'PASS' }); console.log(`PASS ${name}`); }
    catch (error) {
      output.checks.push({ name, result: 'FAIL', message: error.message });
      await page.screenshot({ path: path.join(artifacts, 'failure.png'), fullPage: true });
      throw error;
    }
  };
  const capture = async name => {
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
    await page.screenshot({ path: path.join(artifacts, name), fullPage: true });
  };

  await page.route('**/api/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const endpoint = url.pathname.replace('/api/v1', '');
    if (endpoint === '/terminal/client.js') {
      await route.fulfill({ status: 200, contentType: 'application/javascript', body: clientLibrary });
      return;
    }
    let status = 200;
    let body;
    if (endpoint === '/auth/login') body = { access_token: 'qa-fixture-session', user };
    else if (endpoint === '/auth/me') body = user;
    else if (endpoint === '/challenges' || endpoint === '/categories') body = endpoint === '/challenges'
      ? [{ ...challenge, completed: output.completed === true }, secondChallenge]
      : [{ name: 'MISC', challenge_count: 1 }, { name: 'WEB', challenge_count: 1 }];
    else if (endpoint === '/ranking') body = { rows: [{ position: 1, username: user.username, total_points: output.completed ? 100 : 0, challenges_completed: output.completed ? 1 : 0 }] };
    else if (endpoint === '/ws/ranking/session') body = { websocket_path: '/api/v1/ws/ranking', expires_at: new Date(Date.now() + 900000).toISOString() };
    else if (endpoint === '/progress') body = { total_points: output.completed ? 100 : 0, challenges_completed: output.completed ? 1 : 0 };
    else if (endpoint === '/runs') body = runs.map(run => ({ ...run }));
    else if (endpoint === '/player/laboratories') body = [];
    else if (endpoint === '/challenges/LAB-01/start' && request.method() === 'POST') {
      starts += 1;
      let active = runs.find(run => run.status === 'active');
      if (!active) {
        active = { id: nextRunId++, challenge_code: 'LAB-01', status: 'active',
          started_at: new Date().toISOString(), expires_at: new Date(Date.now() + 3600000).toISOString(),
          workspace_strategy: 'guacamole', connection_state: 'ready',
          target_vm_name: 'QA-LINUX', target_vm_ip: '192.0.2.15', target_protocol: 'ssh', laboratory_code: 'QA-LAB',
        };
        runs = [active, ...runs];
      }
      body = { ...active };
    } else if (/^\/runs\/\d+\/terminal\/options$/.test(endpoint)) {
      body = { protocols: offerRdp ? ['ssh', 'rdp'] : ['ssh'] };
    } else if (/^\/runs\/\d+\/terminal\/session$/.test(endpoint)) {
      brokerRequests += 1;
      selectedProtocols.push(JSON.parse(request.postData() || '{}').protocol);
      const id = endpoint.split('/')[2];
      if (!delegatedReady) { status = 428; body = { detail: 'Conecta con tu cuenta de laboratorio para abrir la terminal.' }; }
      else body = { websocket_path: `/api/v1/runs/${id}/terminal/ws`, expires_at: new Date(Date.now() + 900000).toISOString() };
    } else if (endpoint === '/terminal/auth') {
      authAttempts += 1;
      if (authAttempts === 1) { status = 401; body = { detail: 'No se pudo conectar con tu cuenta de laboratorio.' }; }
      else { delegatedReady = true; body = { ready: true }; }
    } else if (endpoint === '/challenges/LAB-01/submissions') {
      const submitted = JSON.parse(request.postData() || '{}').value;
      const correct = submitted === activeFlag;
      if (correct) output.completed = true;
      body = { correct, challenge_completed: correct, awarded_points: correct ? 100 : 0,
        message: correct ? 'Flag correcta. Reto completado.' : 'Flag incorrecta. Revisa la evidencia.' };
    } else if (/^\/runs\/\d+\/close$/.test(endpoint)) {
      const id = Number(endpoint.split('/')[2]);
      const active = runs.find(run => run.id === id);
      if (failClose) { status = 503; body = { detail: 'No se pudo limpiar la instancia. Reintenta el cierre.' }; }
      else { active.status = 'closed'; body = { ...active }; activeFlag = nextFixtureFlag; }
    } else {
      unexpectedRequests.push(`${request.method()} ${endpoint}`);
      status = 500; body = { detail: 'Unexpected request in isolated QA' };
    }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.route('https://www.youtube-nocookie.com/**', route => route.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>Isolated frame fixture; no video playback is tested.</body></html>' }));
  await page.routeWebSocket('**/api/v1/ws/ranking**', socket => { socketUrls.push(socket.url()); socket.onMessage(() => {}); });
  await page.routeWebSocket('**/api/v1/runs/*/terminal/ws**', socket => {
    socketUrls.push(socket.url());
    terminalSockets.push(socket);
    socket.onMessage(message => wsReceived.push(String(message)));
    // Minimal Guacamole protocol fixture: dimensions and synchronization.
    // No shell output or command execution is fabricated.
    setTimeout(() => socket.send(instruction('size', 0, 1000, 600) + instruction('sync', Date.now())), 50);
  });
  const navigate = async label => {
    const menu = page.getByRole('button', { name: 'Abrir menú', exact: true });
    if (await menu.isVisible()) await menu.click();
    await page.locator('.sidebar').getByRole('button', { name: label, exact: true }).click();
  };
  const copyClipboardFromFixture = async value => {
    const socket = terminalSockets.at(-1);
    assert.ok(socket, 'Terminal fixture has not connected');
    socket.send(instruction('clipboard', 7, 'text/plain') + instruction('blob', 7, Buffer.from(value).toString('base64')) + instruction('end', 7));
  };

  try {
    await check('Login, dark/light theme, readable labels', async () => {
      await page.goto(origin);
      await page.getByRole('heading', { name: 'Inicia tu sesión' }).waitFor();
      const toggle = page.locator('.theme-toggle');
      await toggle.click();
      assert.equal(await page.locator('html').getAttribute('data-theme'), 'light');
      await capture('login-light.png');
      await toggle.click();
      await page.getByLabel('Usuario', { exact: true }).fill('qa_student');
      await page.getByLabel('Contraseña', { exact: true }).fill('fixture');
      await page.getByRole('button', { name: 'Entrar a la plataforma' }).click();
      await page.locator('.sidebar').waitFor();
      assert.equal(await page.getByRole('button', { name: 'Notificaciones', exact: true }).count(), 1);
    });
    await check('Assigned catalog, search and difficulty filters', async () => {
      await navigate('Retos');
      assert.equal(await page.locator('.player-challenge-table tbody tr').count(), 2);
      const search = page.getByRole('searchbox');
      await search.fill('reconocimiento');
      assert.equal(await page.locator('.player-challenge-table tbody tr').count(), 1);
      await search.fill('NO_MATCH');
      assert.equal(await page.locator('.player-challenge-table tbody tr').count(), 0);
      await search.fill('');
      await page.getByRole('button', { name: 'Medio', exact: true }).click();
      assert.equal(await page.locator('.player-challenge-table tbody tr').count(), 1);
      assert.match(await page.locator('.player-challenge-table tbody tr').innerText(), /WEB-02/);
      await page.getByRole('button', { name: 'Todas', exact: true }).click();
      await page.locator('.player-challenge-table tbody tr').filter({ hasText: 'LAB-01' }).locator('.challenge-table-title').click();
      await capture('catalog-dark.png');
    });
    await check('Optional learning resources render safe links without exposing metadata', async () => {
      const resources = page.getByRole('region', { name: 'Material de apoyo de MISC', exact: true });
      await resources.waitFor();
      assert.equal(await resources.getByRole('link', { name: 'Abrir presentación ↗' }).getAttribute('href'), 'https://example.invalid/qa-slides.pdf');
      await resources.getByRole('button', { name: 'Ver video', exact: true }).click();
      assert.equal(await resources.locator('iframe').getAttribute('src'), 'https://www.youtube-nocookie.com/embed/aBcDeFgHiJk');
      await resources.getByRole('button', { name: 'Ocultar video', exact: true }).click();
      assert.equal(await resources.locator('iframe').count(), 0);
      assert.equal(await page.locator('.challenge-instructions').innerText(), 'Consulta los servicios y recupera la flag en el laboratorio autorizado.');
    });
    if (args.includes('--catalog-only')) {
      await check('Catalog responsive 1440/768/390 layouts', async () => {
        for (const width of [1440, 768, 390]) {
          await page.setViewportSize({ width, height: 1000 });
          const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
          assert.ok(overflow <= 2, `Horizontal overflow at ${width}px: ${overflow}px`);
          await capture(`catalog-dark-${width}.png`);
        }
        assert.deepEqual(pageErrors, []);
        assert.deepEqual(unexpectedRequests, []);
      });
      return;
    }
    await check('Start laboratory and integrated terminal transport', async () => {
      await page.getByRole('button', { name: 'Iniciar laboratorio', exact: true }).click();
      await page.locator('.laboratory-run-workspace').waitFor();
      const authPassword = page.getByLabel('Contraseña personal', { exact: true });
      await authPassword.waitFor();
      assert.equal(await page.locator('.guacamole-viewport').isVisible(), true, 'Stable canvas area should remain visible during authentication');
      assert.equal(await page.locator('.guacamole-viewport').getAttribute('aria-hidden'), 'true');
      const authCanvas = await page.locator('.guacamole-viewport').boundingBox();
      assert.equal(await page.getByRole('button', { name: 'RDP · Escritorio' }).isEnabled(), true);
      assert.equal(await page.getByRole('button', { name: 'SSH · Terminal' }).getAttribute('aria-pressed'), 'true');
      await authPassword.fill('fixture-wrong');
      await page.locator('.terminal-auth-form').getByRole('button', { name: 'Conectar', exact: true }).click();
      await page.getByText('No se pudo conectar con tu cuenta de laboratorio.', { exact: true }).waitFor();
      assert.equal(await authPassword.inputValue(), '', 'Personal password must be cleared after rejected authentication');
      await authPassword.fill('fixture-personal');
      await page.locator('.terminal-auth-form').getByRole('button', { name: 'Conectar', exact: true }).click();
      await page.waitForFunction(() => document.querySelector('.terminal-state')?.textContent?.match(/Conectad|En línea|Activa/));
      const connectedCanvas = await page.locator('.guacamole-viewport').boundingBox();
      assert.ok(Math.abs(connectedCanvas.height - authCanvas.height) <= 2, 'Authentication must not collapse and re-expand the terminal canvas');
      assert.ok(Math.abs(connectedCanvas.width - authCanvas.width) <= 2, 'Authentication must not shift the page width');
      assert.equal(runs.filter(run => run.status === 'active').length, 1);
      assert.equal(brokerRequests, 2);
      assert.deepEqual(selectedProtocols, ['ssh', 'ssh']);
      assert.equal(await page.locator('iframe').count(), 0);
      const display = page.locator('.guacamole-canvas');
      await display.click();
      await page.keyboard.type('whoami');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(100);
      assert.ok(wsReceived.some(value => value.includes('key')), 'Keyboard input must reach fixture transport');
    });
    await check('SSH/RDP selector switches one client and terminal-only fullscreen', async () => {
      const panel = page.locator('.embedded-terminal-panel').first();
      const sshCanvas = await panel.locator('.guacamole-viewport').boundingBox();
      await panel.getByRole('button', { name: 'RDP · Escritorio' }).click();
      await page.waitForFunction(() => document.querySelector('.terminal-state')?.textContent?.includes('Conectada'));
      const rdpCanvas = await panel.locator('.guacamole-viewport').boundingBox();
      assert.ok(Math.abs(rdpCanvas.height - sshCanvas.height) <= 2, 'Protocol switching must keep the display frame stable');
      assert.equal(selectedProtocols.at(-1), 'rdp');
      assert.equal(await panel.getByRole('region', { name: 'Escritorio RDP interactivo' }).count(), 1);
      assert.equal(await panel.locator('.guacamole-canvas').count(), 1, 'Only one display mount is permitted');
      await panel.getByRole('button', { name: 'Pantalla completa de conexión' }).click();
      await page.waitForFunction(() => document.fullscreenElement?.classList.contains('embedded-terminal-panel'));
      await page.screenshot({ path: path.join(artifacts, 'terminal-fullscreen-rdp.png') });
      await panel.getByRole('button', { name: 'Salir de pantalla completa' }).click();
      await page.waitForFunction(() => !document.fullscreenElement);
      await panel.getByRole('button', { name: 'SSH · Terminal' }).click();
      await page.waitForFunction(() => document.querySelector('.terminal-state')?.textContent?.includes('Conectada'));
      assert.equal(selectedProtocols.at(-1), 'ssh');
      assert.equal(await panel.getByRole('region', { name: 'Terminal SSH interactiva' }).count(), 1);
      await capture('terminal-selector-ssh.png');
      await page.setViewportSize({ width: 390, height: 900 });
      await panel.getByRole('button', { name: 'Pantalla completa de conexión' }).click();
      await page.waitForFunction(() => document.fullscreenElement?.classList.contains('embedded-terminal-panel'));
      const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
      assert.ok(mobileOverflow <= 2, `Terminal fullscreen overflows mobile by ${mobileOverflow}px`);
      await page.screenshot({ path: path.join(artifacts, 'terminal-fullscreen-ssh-390.png') });
      await panel.getByRole('button', { name: 'Salir de pantalla completa' }).click();
      await page.waitForFunction(() => !document.fullscreenElement);
      await page.setViewportSize({ width: 1440, height: 1000 });
    });
    await check('Reopening the assigned challenge reuses the active run', async () => {
      await navigate('Dashboard');
      await navigate('Retos');
      await page.locator('.player-challenge-table tbody tr').filter({ hasText: 'LAB-01' }).locator('.challenge-table-title').click();
      await page.locator('.laboratory-run-workspace').waitFor();
      assert.equal(starts, 1, 'Existing active run must be reused by the UI');
      assert.equal(runs.filter(run => run.status === 'active').length, 1);
      assert.equal(runs[0].id, 9101);
      const connect = page.getByRole('button', { name: /Conectar terminal|Abrir terminal/ });
      if (await connect.count()) await connect.click();
      await page.waitForFunction(() => document.querySelector('.terminal-state')?.textContent?.match(/Conectad|En línea|Activa/));
    });
    await check('Notes, clipboard, incorrect/correct backend response and candidate persistence', async () => {
      const notes = page.getByLabel('Notas del laboratorio', { exact: true });
      const candidate = page.getByLabel('Flag lista para enviar', { exact: true });
      await notes.fill('FLAG{qa_wrong_fixture}');
      await page.getByRole('button', { name: 'Usar notas', exact: true }).click();
      await page.getByRole('button', { name: 'Enviar flag', exact: true }).click();
      await page.getByText('Flag incorrecta. Revisa la evidencia.', { exact: true }).waitFor();
      assert.equal(await candidate.inputValue(), 'FLAG{qa_wrong_fixture}');
      await copyClipboardFromFixture(fixtureFlag);
      await page.getByRole('button', { name: 'Usar selección', exact: true }).click();
      await page.waitForFunction(expected => document.querySelector('.lab-flag-candidate')?.value === expected, fixtureFlag);
      assert.equal(await candidate.inputValue(), fixtureFlag);
      await page.getByRole('button', { name: 'Copiar flag', exact: true }).click();
      await page.getByText('Flag copiada al portapapeles.', { exact: true }).waitFor();
      assert.equal(await page.evaluate(() => navigator.clipboard.readText()), fixtureFlag);
      await candidate.fill('');
      await page.getByRole('button', { name: 'Pegar flag', exact: true }).click();
      // navigator.clipboard.readText resolves after the click handler; wait for
      // the resulting UI value, not for Playwright's click dispatch alone.
      await page.waitForFunction(expected => document.querySelector('.lab-flag-candidate')?.value === expected, fixtureFlag);
      assert.equal(await candidate.inputValue(), fixtureFlag);
      await page.getByRole('button', { name: 'Enviar flag', exact: true }).click();
      await page.getByText('Flag correcta. Reto completado.', { exact: true }).waitFor();
      assert.equal(await candidate.inputValue(), fixtureFlag, 'Submission reload must preserve prepared candidate');
      assert.equal(await notes.inputValue(), 'FLAG{qa_wrong_fixture}');
    });
    await check('Notification bell marks operational events without storing a flag', async () => {
      const bell = page.locator('.topbar-actions .notification');
      await page.waitForFunction(() => Number(document.querySelector('.topbar-actions .notification span')?.textContent) >= 3);
      await bell.click();
      const panel = page.getByRole('region', { name: 'Avisos recientes' });
      assert.ok(await panel.locator('.notification-item').count() >= 3);
      const panelText = await panel.innerText();
      assert.match(panelText, /Laboratorio listo/);
      assert.match(panelText, /Flag correcta/);
      assert.ok(!panelText.includes(fixtureFlag), 'Notification copy must never reveal submitted flag');
      assert.ok(!(await page.evaluate(() => sessionStorage.getItem('ctf:notifications:9001') || '')).includes(fixtureFlag), 'Stored notification must not contain submitted flag');
      await panel.getByRole('button', { name: 'Marcar todas como leídas' }).click();
      assert.equal(await bell.getAttribute('aria-label'), 'Notificaciones');
      await panel.getByRole('button', { name: 'Cerrar notificaciones' }).click();
    });
    await check('Closing failure retains workspace and flag; retry closes run', async () => {
      failClose = true;
      await page.getByRole('button', { name: 'Cerrar laboratorio', exact: true }).click();
      await page.getByText('No se pudo limpiar la instancia. Reintenta el cierre.', { exact: true }).first().waitFor();
      assert.equal(await page.locator('.laboratory-run-workspace').count(), 1);
      assert.equal(await page.getByLabel('Flag lista para enviar', { exact: true }).inputValue(), fixtureFlag);
      failClose = false;
      await page.getByRole('button', { name: 'Cerrar laboratorio', exact: true }).click();
      await page.locator('.laboratory-run-workspace').waitFor({ state: 'detached' });
      assert.equal(runs.filter(run => run.status === 'active').length, 0);
    });
    await check('Repeat run has new run identity and fresh candidate/notes scope', async () => {
      offerRdp = false;
      await navigate('Retos');
      await page.locator('.player-challenge-table tbody tr').filter({ hasText: 'LAB-01' }).locator('.challenge-table-title').click();
      await page.getByRole('button', { name: /Reabrir entorno de práctica|Iniciar laboratorio/ }).first().click();
      await page.locator('.laboratory-run-workspace').waitFor();
      assert.equal(runs.filter(run => run.status === 'active').length, 1);
      assert.equal(runs[0].id, 9102);
      assert.notEqual(activeFlag, fixtureFlag);
      assert.equal(await page.getByLabel('Flag lista para enviar', { exact: true }).inputValue(), '');
      assert.equal(await page.getByLabel('Notas del laboratorio', { exact: true }).inputValue(), '');
      await page.getByRole('button', { name: 'RDP · Escritorio' }).waitFor();
      assert.equal(await page.getByRole('button', { name: 'RDP · Escritorio' }).isDisabled(), true);
    });
    await check('Light/dark laboratory and responsive 1440/768/390 layouts', async () => {
      await capture('laboratory-dark.png');
      await page.getByRole('button', { name: user.username }).click();
      await page.getByRole('button', { name: 'Preferencias', exact: true }).click();
      await page.getByRole('button', { name: 'Claro', exact: true }).click();
      const closeModal = page.locator('.modal-card').getByRole('button', { name: '×', exact: true });
      await closeModal.click();
      assert.equal(await page.locator('html').getAttribute('data-theme'), 'light');
      for (const width of [1440, 768, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
        assert.ok(overflow <= 2, `Horizontal overflow at ${width}px: ${overflow}px`);
        const typography = await page.evaluate(() => Object.fromEntries(['body', '.challenge-detail h2', '.lab-notebook', '.lab-flag-candidate'].map(selector => [selector, parseFloat(getComputedStyle(document.querySelector(selector)).fontSize)])));
        assert.ok(typography.body >= 16 && typography['.challenge-detail h2'] >= 16 && typography['.lab-notebook'] >= 15 && typography['.lab-flag-candidate'] >= 15, `Important text is too small at ${width}px: ${JSON.stringify(typography)}`);
        (output.layouts ||= []).push({ width, horizontalOverflow: overflow, typography });
        await capture(`laboratory-light-${width}.png`);
      }
      const close = page.getByRole('button', { name: 'Cerrar laboratorio', exact: true });
      assert.ok(await close.isVisible(), 'Close action must remain available on mobile');
    });
    await check('Expired run pending physical cleanup retains a visible retry action', async () => {
      await page.getByLabel('Notas del laboratorio', { exact: true }).fill('Evidence notes retained until cleanup succeeds.');
      runs[0].status = 'expired';
      runs[0].connection_state = 'active';
      runs[0].expires_at = new Date(Date.now() - 60000).toISOString();
      await page.reload();
      await navigate('Mis conexiones');
      await page.getByRole('heading', { name: 'El laboratorio ha expirado', exact: true }).waitFor();
      assert.equal(await page.locator('.laboratory-run-workspace').count(), 1);
      assert.equal(await page.locator('.guacamole-canvas').count(), 0, 'Expired runs must not keep a terminal');
      assert.equal(await page.getByLabel('Notas del laboratorio', { exact: true }).inputValue(), 'Evidence notes retained until cleanup succeeds.');
      await page.getByRole('button', { name: 'Usar notas', exact: true }).click();
      assert.equal(await page.getByRole('button', { name: 'Enviar flag', exact: true }).isDisabled(), true);
      const close = page.getByRole('button', { name: 'Cerrar laboratorio', exact: true });
      assert.equal(await close.isEnabled(), true);
      failClose = true;
      await close.click();
      await page.getByText('No se pudo limpiar la instancia. Reintenta el cierre.', { exact: true }).first().waitFor();
      assert.equal(await page.locator('.laboratory-run-workspace').count(), 1);
      assert.equal(await close.isEnabled(), true);
      await navigate('Retos');
      await page.locator('.player-challenge-table tbody tr').filter({ hasText: 'LAB-01' }).locator('.challenge-table-title').click();
      await page.getByRole('heading', { name: 'El laboratorio ha expirado', exact: true }).waitFor();
      assert.equal(await close.isEnabled(), true, 'The challenge detail must also retain the cleanup retry');
      await capture('expired-cleanup.png');
      failClose = false;
      await close.click();
      await page.locator('.laboratory-run-workspace').waitFor({ state: 'detached' });
    });
    await check('No uncaught frontend errors or unexpected API requests', async () => {
      assert.deepEqual(pageErrors, []);
      assert.deepEqual(unexpectedRequests, []);
      assert.ok(socketUrls.every(value => !/[?&]token=/i.test(value)), 'No WebSocket URL may expose a JWT token');
      output.webSocketUrlsHaveNoJWT = true;
    });
  } finally {
    output.starts = starts;
    output.brokerRequests = brokerRequests;
    output.authAttempts = authAttempts;
    output.protocolMessagesReceived = wsReceived.length;
    output.pageErrors = pageErrors;
    output.unexpectedRequests = unexpectedRequests;
    fs.writeFileSync(path.join(artifacts, 'results.json'), JSON.stringify(output, null, 2));
    await browser.close();
  }
}

run().catch(error => { console.error(error.message); process.exitCode = 1; });
