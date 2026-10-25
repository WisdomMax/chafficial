import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(3000);

  const info = await p.evaluate(() => {
    const allArticles = Array.from(document.querySelectorAll('article'));
    const allRoles = Array.from(document.querySelectorAll('[data-message-author-role]')).map(el => el.getAttribute('data-message-author-role'));
    const proseMirrors = document.querySelectorAll('div.ProseMirror').length;
    const bodyText = document.body.innerText;
    
    // 마지막 4000자에서 혹시 에러 메시지나 버튼이 있는지
    return {
      title: document.title,
      url: window.location.href,
      articleCount: allArticles.length,
      roles: allRoles,
      proseMirrors,
      bodyTail: bodyText.slice(-3000)
    };
  });

  console.log('DOM_INFO:' + JSON.stringify(info));
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
    if line.startswith("DOM_INFO:"):
        data = json.loads(line[len("DOM_INFO:"):])
        print("페이지 타이틀:", data.get("title"))
        print("URL:", data.get("url"))
        print("article 수:", data.get("articleCount"))
        print("roles:", data.get("roles"))
        print("--- bodyTail (마지막 1500자) ---")
        print(data.get("bodyTail", "")[-1500:])
        break
