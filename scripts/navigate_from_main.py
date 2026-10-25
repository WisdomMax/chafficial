import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const p = await openTab("https://chatgpt.com/");
  await sleep(6000);

  // 사이드바에서 '중고차 강화학습' 링크 찾기
  const clicked = await p.evaluate(() => {
    const links = Array.from(document.querySelectorAll('a'));
    const targetLink = links.find(a => a.innerText.includes('중고차 강화학습') || (a.href && a.href.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3')));
    if (targetLink) {
      targetLink.click();
      return { ok: true, href: targetLink.href, text: targetLink.innerText };
    }
    return { ok: false };
  });

  console.log('SIDEBAR_CLICK:' + JSON.stringify(clicked));
  await sleep(6000);

  const title = await p.title();
  const url = await p.url();
  const bodyText = await p.evaluate(() => document.body.innerText);
  console.log('FINAL_URL:' + url);
  console.log('FINAL_TITLE:' + title);
  console.log('BODY_LEN:' + bodyText.length);
  const isError = bodyText.includes('대화 기록을 불러올 수 없습니다') || bodyText.includes('이 ChatGPT 대화를 불러올 수 없습니다');
  console.log('IS_ERROR:' + isError);
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
    print(line)
