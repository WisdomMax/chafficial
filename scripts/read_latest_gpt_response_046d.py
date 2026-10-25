import json
import subprocess
import sys

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const page = await attachActiveBrowserTab();
  await sleep(1000);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(2000);

  const res = await page.evaluate(() => {
    // 1. role="assistant"
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      return { type: 'role_assistant', text: turns[turns.length - 1].innerText };
    }
    // 2. article
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {
      return { type: 'article', text: articles[articles.length - 1].innerText };
    }
    // 3. body tail
    return { type: 'body_tail', text: document.body.innerText.slice(-4000) };
  });

  console.log('EXTRACTED_TYPE:' + res.type);
  console.log('EXTRACTED_TEXT_START');
  console.log(res.text);
  console.log('EXTRACTED_TEXT_END');
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
)

print(res.stdout)
