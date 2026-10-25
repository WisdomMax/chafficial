import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(3000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  const text = await p.evaluate(() => {
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      return turns[turns.length - 1].innerText;
    }
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {
      return articles[articles.length - 1].innerText;
    }
    return document.body.innerText;
  });

  console.log("DIRECTIVE_045B_START");
  console.log(text);
  console.log("DIRECTIVE_045B_END");
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

full_output = res.stdout
start_tag = "DIRECTIVE_045B_START\n"
end_tag = "\nDIRECTIVE_045B_END"
if start_tag in full_output and end_tag in full_output:
    extracted = full_output.split(start_tag)[1].split(end_tag)[0]
    with open("directive_045b_full.txt", "w", encoding="utf-8") as f:
        f.write(extracted)
    print(f"[+] 성공: directive_045b_full.txt 저장 완료 ({len(extracted)}자)")
else:
    with open("directive_045b_full.txt", "w", encoding="utf-8") as f:
        f.write(full_output)
    print(f"[-] 태그 미발견, 전체 저장 ({len(full_output)}자)")
