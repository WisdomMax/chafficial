"""GitHub PR #8 즉시 생성 스크립트 (?expand=1 적용)."""

import subprocess


def create_pr():
    target_url = "https://github.com/WisdomMax/chafficial/compare/feat/directive-007-real-listing-poc...feat/directive-008-market-data-expansion?expand=1"

    js_code = f"""
async function run() {{
  await openTab('{target_url}');
  await sleep(5000);

  // 1. 제목 입력
  await page.evaluate(() => {{
    const titleInput = document.querySelector('input[name="pull_request[title]"]') || document.querySelector('#pull_request_title');
    if (titleInput) {{
      titleInput.value = 'feat(directive-008): market data expansion to 417 real cars and valuation accuracy validation';
    }}
  }});
  await sleep(1500);

  // 2. 제출 버튼 클릭
  const clickRes = await page.evaluate(() => {{
    const submitBtn = Array.from(document.querySelectorAll('button')).find(
      b => b.innerText && b.innerText.trim() === 'Create pull request' && !b.disabled
    );
    if (submitBtn) {{
      submitBtn.click();
      return {{ success: true }};
    }}
    return {{ success: false }};
  }});

  await sleep(5000);
  console.log('PR_CLICK_RESULT:' + JSON.stringify(clickRes));
  console.log('FINAL_PAGE_URL:' + page.url());
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
