const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  // Capture console logs
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
  
  // Capture failed requests
  page.on('requestfailed', request => {
    console.log(`FAILED REQUEST: ${request.url()} - ${request.failure().errorText}`);
  });

  page.on('response', response => {
    if (!response.ok()) {
      console.log(`BAD RESPONSE: ${response.url()} - ${response.status()}`);
    }
  });

  // Automatically accept confirmation dialogs
  page.on('dialog', async dialog => {
    console.log(`DIALOG APPEARED: ${dialog.message()}`);
    await dialog.accept();
    console.log('DIALOG ACCEPTED');
  });

  console.log("Navigating to history page...");
  await page.goto('http://localhost:3000/history', { waitUntil: 'networkidle0' });
  
  console.log("Looking for 'Clear All History' button...");
  const clearBtn = await page.$('button::-p-text(Clear All History)');
  if (clearBtn) {
    console.log("Clicking 'Clear All History'...");
    await clearBtn.click();
    await new Promise(r => setTimeout(r, 2000));
  } else {
    console.log("'Clear All History' button not found. Maybe history is empty?");
  }

  console.log("Navigating to main page...");
  await page.goto('http://localhost:3000/', { waitUntil: 'networkidle0' });
  
  console.log("Looking for 'Delete Runtime History' button...");
  const deleteBtn = await page.$('button::-p-text(Delete Runtime History)');
  if (deleteBtn) {
    console.log("Clicking 'Delete Runtime History'...");
    await deleteBtn.click();
    await new Promise(r => setTimeout(r, 2000));
  } else {
    console.log("'Delete Runtime History' button not found.");
  }
  
  await browser.close();
})();
