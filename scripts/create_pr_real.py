"""GitHub PR #8 확실한 생성 스크립트."""

import json
import subprocess
import time


def create_pr():
    target_url = "https://github.com/WisdomMax/chafficial/compare/feat/directive-007-real-listing-poc...feat/directive-008-market-data-expansion?expand=1"

    js_code = f"""
async function run() {{
  await openTab('{target_url}');
  await sleep(5000);

  // 현재 페이지 URL 및 버튼들 확인
  const info = await page.evaluate(() => {{
    const buttons = Array.from(document.querySelectorAll('button')).map(b => ({{
      text: b.innerText ? b.innerText.trim() : '',
      type: b.type,
      disabled: b.disabled,
      className: b.className
    }}));
    return {{
      url: window.location.href,
      title: document.title,
      buttons: buttons.filter(b => b.text.length > 0)
    }};
  }});
  console.log("PAGE_INFO:" + JSON.stringify(info));

  // 1. PR 제목 입력
  await page.evaluate(() => {{
    const titleInput = document.querySelector('input[name="pull_request[title]"]') || document.querySelector('#pull_request_title');
    if (titleInput) {{
      titleInput.value = 'feat(directive-008): market data expansion to 417 real cars and valuation accuracy validation';
    }}
  }});
  await sleep(1000);

  // 2. 제출 버튼 찾아서 클릭
  const clickResult = await page.evaluate(() => {{
    // form 내부의 submit 버튼 우선
    const form = document.querySelector('form[action*="/pull"]');
    if (form) {{
      const submitBtn = Array.from(form.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Create pull request') && !b.disabled);
      if (submitBtn) {{
        submitBtn.click();
        return {{ method: 'form_submit_button', text: submitBtn.innerText }};
      }}
    }}

    const allButtons = Array.from(document.querySelectorAll('button'));
    const btn = allButtons.find(b => b.innerText && b.innerText.includes('Create pull request') && !b.disabled);
    if (btn) {{
      btn.click();
      return {{ method: 'all_buttons', text: btn.innerText }};
    }}
    return {{ method: 'not_found' }};
  }});

  console.log("CLICK_RESULT:" + JSON.stringify(clickResult));

  // 제출 후 URL 변경 대기
  for (let i = 0; i < 10; i++) {{
    await sleep(1500);
    const curr = page.url();
    if (curr.includes('/pull/') && !curr.includes('/compare/')) {{
      console.log("SUCCESS_PR_URL:" + curr);
      break;
    }}
  }}
  console.log("FINAL_URL:" + page.url());
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
    if res.stderr:
        print("STDERR:", res.stderr)


if __name__ == "__main__":
    create_pr()
