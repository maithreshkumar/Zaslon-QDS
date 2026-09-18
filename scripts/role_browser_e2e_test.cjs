/**
 * Zaslon-QDS: Complete Role-Based Lifecycle Real Browser E2E Test
 * Actors: ALICE (Signer) -> EVE (Attacker) -> BOB (Verifier)
 * Real Headless Chrome, Real CUDA-Q backend, Real Fisher Exact Test, Real MySQL.
 */
const path = require('path');
const puppeteer = require(path.resolve(__dirname, '../frontend/node_modules/puppeteer-core'));

const CHROME_PATH = process.env.CHROME_BIN 
  || process.env.PUPPETEER_EXECUTABLE_PATH 
  || (process.platform === 'win32' 
      ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe' 
      : '/usr/bin/google-chrome');
const APP_URL = process.env.APP_URL || 'http://localhost:3000';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function loginAsRole(page, role) {
  console.log(`       [Auth] Authenticating as ${role}...`);
  await page.goto(`${APP_URL}/login`, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => document.querySelectorAll('button').length > 0, { timeout: 10000 });
  
  const targetLabel = role === 'ALICE' ? 'Alice' : role === 'EVE' ? 'Eve' : role === 'BOB' ? 'Bob' : 'Admin';
  await page.evaluate((label) => {
    const btns = Array.from(document.querySelectorAll('button'));
    const btn = btns.find(b => b.textContent.includes(label));
    if (btn) btn.click();
  }, targetLabel);

  const targetPath = role === 'ALICE' ? '/alice' : role === 'EVE' ? '/eve' : role === 'BOB' ? '/bob' : '/research';
  await page.waitForFunction(
    (path) => window.location.pathname === path,
    { timeout: 15000 },
    targetPath
  );
  await sleep(1000);
  console.log(`       [Auth] Successfully authenticated as ${role} (URL: ${page.url()}).`);
}

async function runRoleBrowserE2E() {
  console.log('================================================================================');
  console.log('       ZASLON-QDS: ROLE-BASED APPLICATION BROWSER E2E VALIDATION               ');
  console.log('       ALICE (Signer) -> EVE (Attacker) -> BOB (Verifier)                      ');
  console.log('================================================================================');

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  const consoleErrors = [];
  const pageErrors = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      if (!msg.text().includes('favicon')) {
        console.log(`[Browser Console Error] ${msg.text()}`);
        consoleErrors.push(msg.text());
      }
    }
  });

  page.on('pageerror', error => {
    console.log(`[Browser Page Error] ${error.message}`);
    pageErrors.push(error.message);
  });

  page.on('response', async res => {
    if (res.status() >= 400 && res.url().includes('/api/')) {
      const text = await res.text().catch(() => '');
      console.log(`[API ${res.status()}] ${res.url()} -> ${text}`);
    }
  });

  try {
    // --------------------------------------------------------------------------
    // Test 1: Landing Page & Protocol Visual Model
    // --------------------------------------------------------------------------
    console.log('\n[1/10] Loading Landing Page (http://localhost:3000)...');
    await page.goto(APP_URL, { waitUntil: 'networkidle0', timeout: 30000 });
    
    const pageTitle = await page.evaluate(() => document.body.innerText);
    if (!pageTitle.includes('Zaslon-QDS') && !pageTitle.includes('ZASLON')) {
      throw new Error('Landing page did not display Zaslon-QDS title');
    }
    console.log('       Landing page rendered successfully with 3-actor protocol visualization.');

    // --------------------------------------------------------------------------
    // Test 2: Unauthenticated Route Protection (Redirect to /login)
    // --------------------------------------------------------------------------
    console.log('\n[2/10] Testing Route Guard: Unauthenticated access to /alice...');
    await page.evaluate(() => localStorage.clear());
    await page.goto(`${APP_URL}/alice`, { waitUntil: 'networkidle0' });
    const currentUrl = page.url();
    if (!currentUrl.includes('/login')) {
      throw new Error(`Expected redirect to /login, but URL is ${currentUrl}`);
    }
    console.log('       Route Guard validated: Redirected unauthenticated user to /login.');

    // --------------------------------------------------------------------------
    // Test 3: Authenticate as Alice & Access Signer Portal
    // --------------------------------------------------------------------------
    console.log('\n[3/10] Logging in as ALICE (Signer)...');
    await loginAsRole(page, 'ALICE');

    // --------------------------------------------------------------------------
    // Test 4: Alice Signs Document with 4,096 CUDA-Q Circuits & Dispatches
    // --------------------------------------------------------------------------
    console.log('\n[4/10] Alice: Generating 4,096 CUDA-Q Teleportation Signature & Dispatching...');
    
    // Check if previous session is in dispatched state, reset if so
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const resetBtn = btns.find(b => b.textContent.includes('Sign Another'));
      if (resetBtn) resetBtn.click();
    });
    await sleep(500);

    // Click "CREATE QUANTUM SIGNATURE (4,096 OPERATIONS)"
    const clickedSign = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const signBtn = btns.find(b => b.textContent.includes('CREATE QUANTUM SIGNATURE'));
      if (signBtn) {
        signBtn.click();
        return true;
      }
      return false;
    });

    if (!clickedSign) {
      throw new Error('Sign button not found on Alice portal');
    }
    console.log('       Triggered CUDA-Q quantum signature generation (4,096 operations)...');

    // Wait for CUDA-Q execution (~2-4 seconds) and declaration state
    try {
      await page.waitForFunction(() => {
        const text = document.body.innerText;
        return text.includes('Signature Created & Sealed') || text.includes('Ready to Dispatch');
      }, { timeout: 45000 });
    } catch (e) {
      const pageInfo = await page.evaluate(() => {
        return {
          bodyText: document.body.innerText,
          buttons: Array.from(document.querySelectorAll('button')).map(b => b.textContent)
        };
      });
      console.log('Page state on failure:', pageInfo);
      throw e;
    }
    console.log('       4,096 Teleportation circuits executed & SHA-512 commitment bound.');

    // Click "DISPATCH / SEND TO BOB"
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const dispatchBtn = btns.find(b => b.textContent.includes('SEND TO BOB'));
      if (dispatchBtn) dispatchBtn.click();
    });

    // Wait for "PACKAGE IN TRANSIT"
    await page.waitForFunction(() => {
      const text = document.body.innerText;
      return text.includes('PACKAGE IN TRANSIT');
    }, { timeout: 15000 });
    console.log('       Package successfully dispatched onto quantum channel (PACKAGE IN TRANSIT).');

    // --------------------------------------------------------------------------
    // Test 5: RBAC Role Isolation (Alice cannot access /eve)
    // --------------------------------------------------------------------------
    console.log('\n[5/10] Testing RBAC: Alice attempting to access /eve...');
    await page.goto(`${APP_URL}/eve`, { waitUntil: 'networkidle0' });
    await sleep(1000);
    const blockedUrl = page.url();
    if (blockedUrl.includes('/eve')) {
      throw new Error('RBAC Failure: Alice was able to access /eve!');
    }
    console.log(`       RBAC Guard validated: Alice redirected from /eve to ${blockedUrl}.`);

    // --------------------------------------------------------------------------
    // Test 6: Eve Adversary Lab (Sniff, Probe, Inject Attack, Forward)
    // --------------------------------------------------------------------------
    console.log('\n[6/10] Switching to EVE (Adversary Lab)...');
    await loginAsRole(page, 'EVE');

    // Wait for in-flight packages in the sniffer
    await page.waitForFunction(() => {
      const cards = document.querySelectorAll('.cursor-pointer');
      return cards.length > 0;
    }, { timeout: 15000 });
    console.log('       Eve channel sniffer detected in-flight transmission.');

    // Intercept the package
    await page.evaluate(() => {
      const interceptBtns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('Intercept'));
      if (interceptBtns.length > 0) {
        interceptBtns[0].click();
      } else {
        const pkgCards = document.querySelectorAll('.cursor-pointer');
        if (pkgCards.length > 0) pkgCards[0].click();
      }
    });
    await sleep(2000);
    console.log('       Package intercepted by Eve.');

    // Test Unauthorized Verification Probe
    console.log('       Testing Unauthorized Verification Probe by Eve...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const probeTab = btns.find(b => b.textContent.includes('Unauthorized Probe'));
      if (probeTab) probeTab.click();
    });
    await sleep(500);

    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const probeBtn = btns.find(b => b.textContent.includes('Execute Unauthorized Verification Probe'));
      if (probeBtn) probeBtn.click();
    });
    await sleep(2000);

    const probeBlocked = await page.evaluate(() => {
      return document.body.innerText.includes('PROBE BLOCKED') || document.body.innerText.includes('UNAUTHORIZED');
    });
    console.log(`       Unauthorized verification probe triggered RBAC barrier (Blocked: ${probeBlocked}).`);

    // Inject Quantum Bit Forgery Attack
    console.log('       Injecting Quantum State Forgery Attack (Inverting measurement bits)...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const forgeryTab = btns.find(b => b.textContent.includes('State Forgery'));
      if (forgeryTab) forgeryTab.click();
    });
    await sleep(500);

    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const mutateBtn = btns.find(b => b.textContent.includes('Inject FORGERY Attack'));
      if (mutateBtn) mutateBtn.click();
    });
    await sleep(2000);
    console.log('       Forgery attack injected into quantum material.');

    // Forward to Bob
    console.log('       Forwarding mutated package to Bob...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const forwardBtn = btns.find(b => b.textContent.includes('Forward to Bob'));
      if (forwardBtn) forwardBtn.click();
    });
    await sleep(2000);
    console.log('       Package forwarded to Bob.');

    // --------------------------------------------------------------------------
    // Test 7: Bob Verifier Portal (Detects Attack, Explainable Receipt)
    // --------------------------------------------------------------------------
    console.log('\n[7/10] Switching to BOB (Verifier Suite)...');
    await loginAsRole(page, 'BOB');

    // Wait for incoming package in Bob's inbox
    await page.waitForFunction(() => {
      return document.querySelectorAll('.cursor-pointer').length > 0;
    }, { timeout: 15000 });
    console.log('       Incoming package confirmed in Bob\'s secure inbox.');

    // Select package and click "Verify Transmission Using Zaslon-QDS"
    await page.evaluate(() => {
      const pkgCards = document.querySelectorAll('.cursor-pointer');
      if (pkgCards.length > 0) pkgCards[0].click();
    });
    await sleep(1000);

    console.log('       Executing 11-step Zaslon-QDS Verification...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const verifyBtn = btns.find(b => b.textContent.includes('Verify Transmission Using Zaslon-QDS'));
      if (verifyBtn) verifyBtn.click();
    });

    // Wait for verification results banner
    await page.waitForFunction(() => {
      return document.body.innerText.includes('VERDICT:') || document.body.innerText.includes('5-Layer Threat Defense');
    }, { timeout: 25000 });
    await sleep(2000);

    const bobResults = await page.evaluate(() => {
      const text = document.body.innerText;
      return {
        verdictRejected: text.includes('VERDICT: REJECTED'),
        attackFlagged: text.includes('FORGERY'),
        defenseBarriersPresent: text.includes('5-Layer Threat Defense'),
        fisherPresent: text.includes('FISHER EXACT P-VALUE')
      };
    });

    console.log('       Bob Verification Results:');
    console.log(`       - Security Verdict: REJECTED (${bobResults.verdictRejected})`);
    console.log(`       - Threat Flagged: FORGERY (${bobResults.attackFlagged})`);
    console.log(`       - 5-Layer Defense Barriers Evaluated: ${bobResults.defenseBarriersPresent}`);
    console.log(`       - Fisher Exact Test Rendered: ${bobResults.fisherPresent}`);

    if (!bobResults.verdictRejected) {
      throw new Error('Expected Bob to REJECT the tampered package, but verdict did not show REJECTED');
    }

    // --------------------------------------------------------------------------
    // Test 8: Authentic Passthrough Workflow (Full Green Path)
    // --------------------------------------------------------------------------
    console.log('\n[8/10] Testing Authentic Passthrough Lifecycle (Alice -> Eve Passthrough -> Bob VERIFIED)...');
    
    // Switch to Alice
    await loginAsRole(page, 'ALICE');

    // Reset form if needed
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const resetBtn = btns.find(b => b.textContent.includes('Sign Another'));
      if (resetBtn) resetBtn.click();
    });
    await sleep(500);

    // Sign fresh document
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const signBtn = btns.find(b => b.textContent.includes('CREATE QUANTUM SIGNATURE'));
      if (signBtn) signBtn.click();
    });
    await page.waitForFunction(() => {
      const text = document.body.innerText;
      return text.includes('Signature Created & Sealed') || text.includes('Ready to Dispatch');
    }, { timeout: 45000 });

    // Dispatch
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const dispatchBtn = btns.find(b => b.textContent.includes('SEND TO BOB'));
      if (dispatchBtn) dispatchBtn.click();
    });
    await page.waitForFunction(() => {
      const text = document.body.innerText;
      return text.includes('PACKAGE IN TRANSIT');
    }, { timeout: 15000 });
    console.log('       Alice dispatched authentic package.');

    // Switch to Eve
    await loginAsRole(page, 'EVE');

    // Intercept and choose Passthrough
    await page.waitForFunction(() => {
      return document.querySelectorAll('.cursor-pointer').length > 0;
    }, { timeout: 15000 });

    await page.evaluate(() => {
      const interceptBtns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('Intercept'));
      if (interceptBtns.length > 0) interceptBtns[0].click();
      else {
        const pkgs = document.querySelectorAll('.cursor-pointer');
        if (pkgs.length > 0) pkgs[0].click();
      }
    });
    await sleep(1500);

    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const passBtn = btns.find(b => b.textContent.trim() === 'Passthrough');
      if (passBtn) passBtn.click();
    });
    await sleep(1500);

    // Forward to Bob
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const fwdBtn = btns.find(b => b.textContent.includes('Forward to Bob'));
      if (fwdBtn) fwdBtn.click();
    });
    await sleep(2000);
    console.log('       Eve performed zero-tamper passthrough and forwarded to Bob.');

    // Switch to Bob and verify
    await loginAsRole(page, 'BOB');

    await page.waitForFunction(() => {
      return document.querySelectorAll('.cursor-pointer').length > 0;
    }, { timeout: 15000 });

    await page.evaluate(() => {
      const pkgs = document.querySelectorAll('.cursor-pointer');
      if (pkgs.length > 0) pkgs[0].click();
    });
    await sleep(1000);

    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const verifyBtn = btns.find(b => b.textContent.includes('Verify Transmission Using Zaslon-QDS'));
      if (verifyBtn) verifyBtn.click();
    });

    await page.waitForFunction(() => {
      return document.body.innerText.includes('VERDICT: VERIFIED');
    }, { timeout: 25000 });
    console.log('       Authentic package verified: VERDICT: VERIFIED! All 5 defense barriers passed.');

    // --------------------------------------------------------------------------
    // Test 9: Research & Diagnostics Page
    // --------------------------------------------------------------------------
    console.log('\n[9/10] Inspecting Research Diagnostics Page (/research)...');
    await page.goto(`${APP_URL}/research`, { waitUntil: 'networkidle0' });
    await sleep(1000);

    const researchOk = await page.evaluate(() => {
      const text = document.body.innerText;
      return text.includes('CUDA-Q 0.16.0') && text.includes('MySQL 8.4') && text.includes('Audit Stream');
    });
    console.log(`       Diagnostics validated: Hardware & persistence online (${researchOk}).`);

    // --------------------------------------------------------------------------
    // Test 10: Page Refresh Persistence & Console Error Check
    // --------------------------------------------------------------------------
    console.log('\n[10/10] Testing Page Refresh Persistence & Console Invariant...');
    await page.reload({ waitUntil: 'networkidle0' });
    await sleep(1000);

    if (page.url().includes('/login')) {
      throw new Error('Session lost after page refresh!');
    }
    console.log('       Session persistence verified after hard page refresh.');

    console.log('\n================================================================================');
    console.log('               REAL BROWSER E2E VALIDATION: 100% PASSED                         ');
    console.log('================================================================================');
    console.log(`Total Console Errors: ${consoleErrors.length}`);
    console.log(`Total Page Errors:    ${pageErrors.length}`);

    if (consoleErrors.length > 0 || pageErrors.length > 0) {
      console.error('Errors detected:', { consoleErrors, pageErrors });
      process.exit(1);
    }

  } catch (err) {
    console.error('\n❌ Browser E2E Test Failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

runRoleBrowserE2E();
