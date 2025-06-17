const DEBUG = true;
const log = (...a) => DEBUG && console.log('[DEBUG]', ...a);
const puzzleSelect  = document.getElementById('puzzle-select');
const puzzleInfo    = document.getElementById('puzzle-info');
const formContainer = document.getElementById('form-container');
const addStepBtn    = document.getElementById('add-step');
const validateBtn   = document.getElementById('validate');
const resultDiv     = document.getElementById('result');
const rankingList   = document.getElementById('ranking');
let currentPuzzle   = null;

function createInput() {
  const row = document.createElement('div');
  row.className = 'input-row';
  const input = document.createElement('input');
  input.type = 'text';
  input.placeholder = 'https://ja.wikipedia.org/wiki/記事';
  input.addEventListener('input', () => {
    const ok = /^https:\/\/ja\.wikipedia\.org\/wiki\/[^#?]+/.test(input.value);
    input.classList.toggle('invalid', !ok);
  });
  const remove = document.createElement('button');
  remove.textContent = '－';
  remove.addEventListener('click', () => row.remove());
  row.appendChild(input);
  row.appendChild(remove);
  formContainer.appendChild(row);
}

function resetInputs() {
  formContainer.innerHTML = '';
  createInput();
}

addStepBtn.addEventListener('click', createInput);

function extractTitleFromUrl(url) {
  const m = url.match(/^https:\/\/ja\.wikipedia\.org\/wiki\/([^#?]+)/);
  if (!m) return '';
  let title = decodeURIComponent(m[1]).replace(/_/g, ' ');
  title = title.charAt(0).toUpperCase() + title.slice(1);
  return title.trim();
}

function updatePuzzleInfo() {
  if (!currentPuzzle) return;
  puzzleInfo.textContent = `Start: ${currentPuzzle.start_title} → Goal: ${currentPuzzle.goal_title}`;
}

function loadPuzzles() {
  fetch('/api/puzzles')
    .then(r => r.json())
    .then(data => {
      puzzleSelect.innerHTML = '';
      data.puzzles.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.puzzle_id;
        opt.textContent = `${p.start_title} → ${p.goal_title}`;
        puzzleSelect.appendChild(opt);
      });
      currentPuzzle = data.puzzles[0];
      puzzleSelect.value = currentPuzzle.puzzle_id;
      updatePuzzleInfo();
      fetchRanking();
    })
    .catch(err => console.error('Puzzle fetch error', err));
}

puzzleSelect.addEventListener('change', () => {
  const id = Number(puzzleSelect.value);
  fetch('/api/puzzles')
    .then(r => r.json())
    .then(data => {
      currentPuzzle = data.puzzles.find(p => p.puzzle_id === id);
      updatePuzzleInfo();
      resetInputs();
      fetchRanking();
    });
});

function fetchRanking() {
  rankingList.innerHTML = '';
  if (!currentPuzzle) return;
  fetch(`/api/ranking?puzzle_id=${currentPuzzle.puzzle_id}`)
    .then(r => r.json())
    .then(data => {
      (data.ranking || []).forEach(row => {
        const li = document.createElement('li');
        li.textContent = `${row.user_name}: ${row.step_count} steps`;
        rankingList.appendChild(li);
      });
    })
    .catch(err => console.error('Ranking error', err));
}

validateBtn.addEventListener('click', () => {
  if (!currentPuzzle) return;
  const inputs = Array.from(formContainer.querySelectorAll('input'));
  const titles = inputs.map(inp => extractTitleFromUrl(inp.value));
  if (titles.some(t => !t)) {
    resultDiv.textContent = 'URLを確認してください';
    return;
  }
  const route = [currentPuzzle.start_title, ...titles, currentPuzzle.goal_title];
  fetch('/api/validate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({puzzle_id: currentPuzzle.puzzle_id, route})
  })
    .then(r => r.json())
    .then(data => {
      if (data.valid) {
        resultDiv.textContent = `成功! ステップ数: ${data.step_count}`;
        fetchRanking();
      } else if (data.failed_step) {
        resultDiv.textContent = `失敗: ステップ${data.failed_step}でリンクが見つかりません`;
        const bad = inputs[data.failed_step - 1];
        if (bad) bad.classList.add('invalid');
      } else if (data.error) {
        resultDiv.textContent = `エラー: ${data.error}`;
      } else {
        resultDiv.textContent = '未知のエラー';
      }
    })
    .catch(err => {
      console.error('Fetch error', err);
      resultDiv.textContent = '通信エラー';
    });
});

loadPuzzles();
resetInputs();
