"""Aside 브라우저를 통한 GitHub PR 자동 생성 스크립트."""

import subprocess


def create_pr():
    js_code = """
async function run() {
  await openTab('https://github.com/WisdomMax/chafficial/pull/new/feat/directive-003b-data-feasibility');
  await sleep(4000);

  // PR 제목 및 설명 입력
  await page.evaluate(() => {
    const titleInput = document.querySelector('input[name="pull_request[title]"]') || document.querySelector('#pull_request_title');
    if (titleInput) {
      titleInput.value = 'feat(directive-003b): real data sources research and access feasibility validation';
    }
  });
  await sleep(1000);

  // 버튼 클릭
  const clickRes = await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const createBtn = buttons.find(b => b.textContent && b.textContent.includes('Create pull request'));
    if (createBtn && !createBtn.disabled) {
      createBtn.click();
      return { success: true };
    }
    return { success: false };
  });

  await sleep(4000);
  const currentUrl = page.url();
  console.log('PR_URL:' + currentUrl);
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
    create_pr()
