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

  const res = await p.evaluate(() => {
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      const last = turns[turns.length - 1];
      return { ok: true, text: last.innerText };
    }
    return { ok: false, text: "" };
  });

  console.log('TAIL_RESPONSE:' + JSON.stringify(res));
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

for line in res.stdout.splitlines():
    if line.startswith("TAIL_RESPONSE:"):
        data = json.loads(line[len("TAIL_RESPONSE:"):])
        text = data.get("text", "")
        with open("latest_gpt_tail_clean.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[+] 성공: {len(text)}자 추출 완료")
        break
