const formContainer = document.getElementById('form-container');
const addStepBtn = document.getElementById('add-step');
const validateBtn = document.getElementById('validate');
const resultDiv = document.getElementById('result');
let currentPuzzle = null;

function createInput() {
    // 入力欄と削除ボタンを持つ行要素
    const row = document.createElement('div');
    row.className = 'input-row';

    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'https://ja.wikipedia.org/wiki/記事';
    input.addEventListener('input', () => {
        const re = /^https:\/\/ja\.wikipedia\.org\/wiki\/.+/;
        if (re.test(input.value)) {
            input.classList.remove('invalid');
        } else {
            input.classList.add('invalid');
        }
    });

    const removeBtn = document.createElement('button');
    removeBtn.textContent = '－';
    removeBtn.addEventListener('click', () => row.remove());

    row.appendChild(input);
    row.appendChild(removeBtn);
    formContainer.appendChild(row);
}

addStepBtn.addEventListener('click', () => {
    createInput();
});

async function loadPuzzle() {
    const resp = await fetch('puzzles.json');
    const data = await resp.json();
    currentPuzzle = data.puzzles[0];
    const info = document.getElementById('puzzle-info');
    info.textContent = `Start: ${currentPuzzle.start_title} → Goal: ${currentPuzzle.goal_title}`;
}

async function checkLinkExists(sourceTitle, targetTitle) {
    /**
     * Query the MediaWiki API to determine if `sourceTitle` links to
     * `targetTitle`. The API paginates results via `plcontinue`, so we
     * repeatedly fetch pages until the link is found or no more data is
     * available.
     */

    const baseParams = {
        action: 'query',
        prop: 'links',
        titles: sourceTitle,
        pllimit: 'max',
        format: 'json',
        origin: '*'
    };

    let next = null;
    while (true) {
        const params = new URLSearchParams(baseParams);
        if (next) params.set('plcontinue', next);

        const url = `https://ja.wikipedia.org/w/api.php?${params.toString()}`;
        const resp = await fetch(url);
        const data = await resp.json();

        const pages = data.query && data.query.pages ? data.query.pages : {};
        for (const key in pages) {
            const links = pages[key].links || [];
            if (links.some(l => l.title === targetTitle)) {
                return true;
            }
        }

        next = data.continue && data.continue.plcontinue;
        if (!next) break;
    }
    return false;
}

validateBtn.addEventListener('click', async () => {
    if (!currentPuzzle) return;
    const inputs = Array.from(formContainer.querySelectorAll('input'));
    const titles = inputs.map(inp => inp.value.match(/wiki\/(.+)/)?.[1] || '');
    if (titles.some(t => !t)) {
        resultDiv.textContent = 'URLを確認してください';
        return;
    }
    const route = [currentPuzzle.start_title, ...titles, currentPuzzle.goal_title];
    for (let i = 0; i < route.length - 1; i++) {
        try {
            const ok = await checkLinkExists(route[i], route[i + 1]);
            if (!ok) {
                resultDiv.textContent = `失敗: ステップ${i + 1}でリンクが見つかりません`;
                const targetInput = inputs[i];
                if (targetInput) targetInput.classList.add('invalid');
                return;
            }
        } catch (e) {
            resultDiv.textContent = '通信エラー';
            return;
        }
    }
    resultDiv.textContent = `成功! ステップ数: ${route.length - 1}`;
});

loadPuzzle();
createInput();
