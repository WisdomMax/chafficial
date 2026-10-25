import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(4000);

  const data = await p.evaluate(() => {
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    return {
      count: turns.length,
      lastTurnText: turns.length > 0 ? turns[turns.length - 1].innerText : "",
      secondLastTurnText: turns.length > 1 ? turns[turns.length - 2].innerText : "",
      stopBtnExists: !!(document.querySelector('button[data-testid="stop-button"]') || document.querySelector('button[aria-label*="중지"]')),
    };
  });

  console.log('TURN_DATA:' + JSON.stringify(data));
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
    if line.startswith("TURN_DATA:"):
        print(line[:300])
        data = json.loads(line[len("TURN_DATA:"):])
        print(f"총 어시스턴트 턴 수: {data.get('count')}")
        print(f"생성 중 여부: {data.get('stopBtnExists')}")
        last_text = data.get('lastTurnText', '')
        print(f"최신 턴 길이: {len(last_text)}")
        with open("latest_assistant_turn.txt", "w", encoding="utf-8") as f:
            f.write(last_text)
        break
