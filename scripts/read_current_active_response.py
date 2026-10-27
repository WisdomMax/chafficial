import json
import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const page = await attachActiveBrowserTab();
  console.log('ACTIVE_URL:' + await page.url());
  console.log('ACTIVE_TITLE:' + await page.title());

  // '다시 시도' 버튼 클릭 처리
  const retried = await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('다시 시도'));
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  });
  if (retried) {
    console.log('RETRY_CLICKED:true');
    await sleep(4000);
  }

  await sleep(1500);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  const res = await page.evaluate(() => {
    // 모든 assistant 메시지 컨테이너 탐색
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      const lastTurn = turns[turns.length - 1];
      return { found: true, text: lastTurn.innerText, html: lastTurn.innerHTML.slice(0, 1000) };
    }
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {
      const lastArt = articles[articles.length - 1];
      return { found: true, text: lastArt.innerText, html: lastArt.innerHTML.slice(0, 1000) };
    }
    return { found: false, text: document.body.innerText, html: '' };
  });

  console.log('RESULT_FOUND:' + res.found);
  console.log('RESULT_LEN:' + res.text.length);
  console.log('CONTENT_START');
  console.log(res.text);
  console.log('CONTENT_END');
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
)

lines = res.stdout.splitlines()
in_content = False
content_lines = []
for l in lines:
    if l == "CONTENT_START":
        in_content = True
        continue
    if l == "CONTENT_END":
        in_content = False
        continue
    if in_content:
        content_lines.append(l)

result_text = "\n".join(content_lines)
with open("reports/LATEST_CHATGPT_DIRECTIVE.txt", "w", encoding="utf-8") as f:
    f.write(result_text)

print(f"[+] 저장 완료: {len(result_text)}자 -> reports/LATEST_CHATGPT_DIRECTIVE.txt")
print("미리보기 (앞 400자):")
print(result_text[:400])
print("\n미리보기 (뒤 400자):")
print(result_text[-400:])
