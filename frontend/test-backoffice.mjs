import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';

const SCREENSHOTS_DIR = path.resolve('../docs/screenshots');
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

async function runTest() {
  console.log('--- Iniciando verificación E2E del Backoffice ---');
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  });

  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });

  const uncaughtErrors = [];
  page.on('pageerror', (err) => {
    uncaughtErrors.push(err.message);
    console.error('[Uncaught Page Error]', err);
  });

  console.log('1. Cargando http://127.0.0.1:3000/...');
  const response = await page.goto('http://127.0.0.1:3000/', {
    waitUntil: 'domcontentloaded',
    timeout: 10000,
  });

  if (response.status() !== 200) {
    throw new Error(`HTTP status no es 200: ${response.status()}`);
  }
  console.log('✓ Servidor respondió 200 OK');

  // Esperar a que se monte React
  await page.waitForSelector('aside', { timeout: 5000 });
  console.log('✓ Sidebar montado exitosamente');

  // Verificar título en Sidebar
  const sidebarTitle = await page.locator('aside').textContent();
  if (!sidebarTitle.includes('Multi-Agent Studio')) {
    throw new Error('No se encontró el título en Sidebar');
  }
  console.log('✓ Branding "Multi-Agent Studio" presente');

  // Esperar un momento a que renderice el contenido del dashboard
  await page.waitForTimeout(1000);

  // Verificar vista Dashboard
  const dashboardTitle = await page.locator('h1').textContent();
  console.log(`✓ Dashboard H1: "${dashboardTitle}"`);

  // Tomar captura del Dashboard
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-dashboard.png') });
  console.log('✓ Captura guardada: test-dashboard.png');

  // Navegar a "Generador de Lotes"
  console.log('2. Navegando a Generador de Lotes...');
  await page.click('button:has-text("Generador de Lotes")');
  await page.waitForTimeout(500);
  const studioText = await page.textContent('main');
  if (!studioText.includes('Generador de Campañas & Lotes de Ideas')) {
    throw new Error('Fallo al cargar vista de Generador de Lotes');
  }
  console.log('✓ Vista Studio verificada');
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-studio.png') });

  // Navegar a "Biblioteca de Ideas"
  console.log('3. Navegando a Biblioteca de Ideas...');
  await page.click('button:has-text("Biblioteca de Ideas")');
  await page.waitForTimeout(500);
  const libraryText = await page.textContent('main');
  if (!libraryText.includes('Biblioteca de Ideas & Dossiers Persistidos')) {
    throw new Error('Fallo al cargar vista de Biblioteca');
  }
  console.log('✓ Vista Biblioteca verificada');
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-library.png') });

  // Navegar a "Publicaciones Postiz"
  console.log('4. Navegando a Publicaciones Postiz...');
  await page.click('button:has-text("Publicaciones Postiz")');
  await page.waitForTimeout(500);
  const pubText = await page.textContent('main');
  if (!pubText.includes('Historial de Entregas & Publicaciones Postiz')) {
    throw new Error('Fallo al cargar vista de Publicaciones');
  }
  console.log('✓ Vista Publicaciones verificada');
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-publications.png') });

  // Navegar a "Pipeline & Trazabilidad"
  console.log('5. Navegando a Pipeline & Trazabilidad...');
  await page.click('button:has-text("Pipeline & Trazabilidad")');
  await page.waitForTimeout(500);
  const traceText = await page.textContent('main');
  if (!traceText.includes('Grafo de Ejecución del Pipeline')) {
    throw new Error('Fallo al cargar vista de Pipeline');
  }
  console.log('✓ Vista Pipeline verificada');
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-pipeline.png') });

  // Navegar a "Resultados & Dossiers"
  console.log('6. Navegando a Resultados & Dossiers...');
  await page.click('button:has-text("Resultados & Dossiers")');
  await page.waitForTimeout(500);
  console.log('✓ Vista Resultados verificada');

  // Navegar a "Historial de Tareas"
  console.log('7. Navegando a Historial de Tareas...');
  await page.click('button:has-text("Historial de Tareas")');
  await page.waitForTimeout(500);
  const historyText = await page.textContent('main');
  if (!historyText.includes('Registro de Tareas Multi-Agente')) {
    throw new Error('Fallo al cargar vista de Historial');
  }
  console.log('✓ Vista Historial verificada');
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-history.png') });

  // Navegar a "Arquitectura & Servicios"
  console.log('8. Navegando a Arquitectura & Servicios...');
  await page.click('button:has-text("Arquitectura & Servicios")');
  await page.waitForTimeout(500);
  const systemText = await page.textContent('main');
  if (!systemText.includes('Arquitectura del Sistema & Catálogo de Microservicios')) {
    throw new Error('Fallo al cargar vista de Servicios');
  }
  console.log('✓ Vista Arquitectura & Servicios verificada');
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-system.png') });

  await browser.close();

  if (uncaughtErrors.length > 0) {
    console.error('ERRORES DETECTADOS EN LA PÁGINA:');
    uncaughtErrors.forEach((e) => console.error(' - ', e));
    throw new Error(`Se detectaron ${uncaughtErrors.length} errores.`);
  }

  console.log('--- ¡TODAS LAS PRUEBAS E2E PASARON CON 0 ERRORES! ---');
}

runTest().catch((err) => {
  console.error('Fallo en la prueba:', err);
  process.exit(1);
});
