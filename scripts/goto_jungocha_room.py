import json
import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_TAB_ID = "B953A3E68E4EA5A5D719FA615BB330C5"
JUNGOCHA_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

js_code = f"""
async function run() {{
  const page = await attachBrowserTab('{TARGET_TAB_ID}');
  console.log('BEFORE_URL:' + await page.url());
  await page.goto('{JUNGOCHA_URL}');
  await sleep(5000);

  // '다시 시도' 버튼이 있으면 클릭
  const retried = await page.evaluate(() => {{
    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('다시 시도'));
    if (btn) {{
      btn.click();
      return true;
    }}
    return false;
  }});
  console.log('RETRIED:' + retried);
  if (retried) await sleep(4000);

  console.log('AFTER_TITLE:' + await page.title());
  console.log('AFTER_URL:' + await page.url());

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  const text = await page.evaluate(() => document.body.innerText);
  console.log('BODY_LEN:' + text.length);
  console.log('BODY_START');
  console.log(text.slice(-8000));
  console.log('BODY_END');
}}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
)

lines = res.stdout.splitlines()
in_body = False
body_lines = []
for l in lines:
    if l == "BODY_START":
        in_body = True
        continue
    if l == "BODY_END":
        in_body = False
        continue
    if in_body:
        body_lines.append(l)

result_text = "\n".join(body_lines)
with open("reports/JUNGOCHA_LATEST_DIRECTIVE.txt", "w", encoding="utf-8") as f:
    f.write(result_text)

print(f"[+] 저장 완료: {len(result_text)}자 -> reports/JUNGOCHA_LATEST_DIRECTIVE.txt")
print("출력 요약:")
for l in lines:
    if not in_body and not l.startswith("BODY_"):
        print(l)
