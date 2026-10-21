"""Aside 브라우저의 탭을 연결하여 PR #8 생성을 확정하는 스크립트."""

import subprocess


def finalize_pr():
    js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const ghTab = tabs.find(t => t.url && t.url.includes('github.com'));
  if (ghTab) {
    await attachBrowserTab(ghTab.targetId);
  } else {
    await openTab('https://github.com/WisdomMax/chafficial/compare/feat/directive-007-real-listing-poc...feat/directive-008-market-data-expansion');
  }
  await sleep(4000);

  // 1. Create pull request 녹색 버튼 클릭
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button, a'));
    const btn = btns.find(b => b.innerText && b.innerText.includes('Create pull request'));
    if (btn) btn.click();
  });
  await sleep(3500);

  // 2. 제목 입력
  await page.evaluate(() => {
    const titleInput = document.querySelector('input[name="pull_request[title]"]') || document.querySelector('#pull_request_title');
    if (titleInput) {
      titleInput.value = 'feat(directive-008): market data expansion to 417 real cars and valuation accuracy validation';
    }
  });
  await sleep(1500);

  // 3. 폼 내부의 최종 Create pull request 버튼 클릭
  const clickRes = await page.evaluate(() => {
    const formBtns = Array.from(document.querySelectorAll('form button, div.discussion-timeline-actions button'));
    const btn = formBtns.find(b => b.innerText && b.innerText.trim() === 'Create pull request');
    if (btn && !btn.disabled) {
      btn.click();
      return { success: true };
    }
    const allBtns = Array.from(document.querySelectorAll('button'));
    const submitBtn = allBtns.find(b => b.innerText && b.innerText.trim() === 'Create pull request' && !b.disabled);
    if (submitBtn) {
      submitBtn.click();
      return { success: true };
    }
    return { success: false };
  });

  await sleep(5000);
  console.log('CLICK_STATUS:' + JSON.stringify(clickRes));
  console.log('FINAL_URL:' + page.url());
}
await run();
"""

    res = subprocess.run(
        ["/Users/wisdom/.local/bin/aside", "--profile", "c759b216-69cc-436b-941a-dab4e621632d", "repl", js_code],
        check=False,
        capture_output=True,
        text=True,
    )
    print(res.stdout)


if __name__ == "__main__":
    finalize_pr()
