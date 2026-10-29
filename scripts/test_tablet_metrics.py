import asyncio
from playwright.async_api import async_playwright

async def inspect_dom():
    with open(".env") as f:
        env_lines = f.readlines()
    pw = None
    for line in env_lines:
        if line.startswith("CHAMART_ADMIN_PASSWORD="):
            pw = line.strip().split("=", 1)[1]
            break

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 834, "height": 1194})
        page = await context.new_page()
        await page.goto("http://localhost:8501/")
        await page.wait_for_load_state("networkidle")

        await page.evaluate("""async (password) => {
            await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: "admin", password: password })
            });
        }""", pw)

        await page.reload()
        await page.wait_for_load_state("networkidle")
        await page.click("#nav-vehicles")
        await page.wait_for_timeout(1000)

        headers = await page.evaluate("""() => {
            const ths = Array.from(document.querySelectorAll("#view-vehicles thead th"));
            return ths.map(th => {
                return {
                    text: th.innerText.split("\\n").join(" "),
                    width: th.offsetWidth,
                    height: th.offsetHeight
                };
            });
        }""")
        print("=== TH INFO ===")
        for h in headers:
            t = h["text"]
            w = h["width"]
            ht = h["height"]
            print(f"{t}: width={w}px, height={ht}px")

        first_row = await page.evaluate("""() => {
            const row = document.querySelector("#vehicleTableBody tr");
            if (!row) return [];
            const tds = Array.from(row.querySelectorAll("td"));
            return tds.map(td => {
                return {
                    text: td.innerText.split("\\n").join(" "),
                    width: td.offsetWidth,
                    height: td.offsetHeight
                };
            });
        }""")
        print("=== FIRST ROW INFO ===")
        for cell in first_row:
            t = cell["text"][:35]
            w = cell["width"]
            ht = cell["height"]
            print(f"{t}: width={w}px, height={ht}px")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_dom())
