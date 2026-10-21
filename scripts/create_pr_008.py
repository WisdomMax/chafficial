"""Aside 브라우저를 통한 GitHub PR #8 자동 생성 스크립트."""

import subprocess
import time


def create_pr():
    target_url = "https://github.com/WisdomMax/chafficial/compare/feat/directive-007-real-listing-poc...feat/directive-008-market-data-expansion"

    js_code = f"""
async function run() {{
  await openTab('{target_url}');
  await sleep(4000);

  // 1. 'Create pull request' 버튼 클릭하여 에디터 진입
  await page.evaluate(() => {{
    const buttons = Array.from(document.querySelectorAll('button, a'));
    const btn = buttons.find(b => b.textContent && b.textContent.includes('Create pull request'));
    if (btn) btn.click();
  }});
  await sleep(3000);

  // 2. PR 제목 및 설명 입력
  await page.evaluate(() => {{
    const titleInput = document.querySelector('input[name="pull_request[title]"]') || document.querySelector('#pull_request_title');
    if (titleInput) {{
      titleInput.value = 'feat(directive-008): market data expansion to 417 real cars and valuation accuracy validation';
    }}
  }});
  await sleep(1000);

  // 3. 최종 'Create pull request' 제출 버튼 클릭
  const submitRes = await page.evaluate(() => {{
    const buttons = Array.from(document.querySelectorAll('button'));
    const submitBtn = buttons.find(b => b.textContent && b.textContent.trim() === 'Create pull request' && !b.disabled);
    if (submitBtn) {{
      submitBtn.click();
      return {{ success: true }};
    }}
    return {{ success: false }};
  }});

  await sleep(4000);
  const currentUrl = page.url();
  console.log('PR_URL:' + currentUrl);
}}
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
    create_pr()
