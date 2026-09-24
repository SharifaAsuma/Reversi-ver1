# ============================================================
# IPython(Jupyter Notebook / Colab)のセル内に HTML を直接描画するための機能を読み込む
# ============================================================
from IPython.display import HTML

# ============================================================
# ここから下は「HTML + CSS + JavaScript」を1つの文字列としてまとめている部分。
# Python 側は文字列を保持するだけで、実際のゲーム処理はすべてブラウザ上の
# JavaScript が担当している。
# ============================================================
html_code = '''
<style>
  /* ---------- 画面全体の見た目(CSS)の設定 ---------- */

  /* ページ全体:フォント指定＋中央寄せレイアウト（縦方向に要素を並べる） */
  body { font-family: Arial, sans-serif; display: flex; flex-direction: column; align-items: center; margin-top: 20px; }

  /* ゲーム全体を包む箱:タイトル・ステータス・盤面を縦に中央揃えで並べる */
  #game-container { display: flex; flex-direction: column; align-items: center; }

  /* 盤面:CSS Grid で 50px のマスを 8列 × 8行 に並べる（＝8x8のオセロ盤） */
  #board { display: grid; grid-template-columns: repeat(8, 50px); grid-template-rows: repeat(8, 50px); border: 2px solid #333; margin-top: 20px; }

  /* 1マス分の見た目:緑背景・細い枠線。中身（石）は中央に配置し、クリック可能なカーソルにする */
  .cell { width: 50px; height: 50px; background-color: #008000; border: 1px solid #222; display: flex; justify-content: center; align-items: center; cursor: pointer; }

  /* 石（コマ）の共通スタイル:border-radius: 50% で丸くしている */
  .piece { width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 0.8em; }

  /* 黒石の色 */
  .black { background-color: black; border: 2px solid #555; color: white; }

  /* 白石の色 */
  .white { background-color: white; border: 2px solid #AAA; color: black; }

  /* 「現在のターン」を表示する文字のスタイル */
  #status { margin-top: 10px; font-size: 1.2em; }
</style>

<!-- ---------- 画面の骨組み(HTML) ---------- -->
<div id="game-container">
  <h1>オセロゲーム</h1>

  <!-- 手番表示エリア。JavaScript の updateStatus() から中身が書き換えられる -->
  <div id="status">現在のターン: 黒</div>

  <!-- 盤面エリア。中身は空で、JavaScript の initBoard() が 64個のマスを生成して差し込む -->
  <div id="board"></div>
</div>

<script>
  /* ============================================================
     1. 要素の取得と、ゲームの状態を持つ変数の準備
     ============================================================ */

  // HTML 側で用意した盤面の入れ物とステータス表示欄を JavaScript から操作できるように取得
  const boardElement = document.getElementById('board');
  const statusElement = document.getElementById('status');

  // 盤面の状態を保持する 8x8 の二次元配列。
  // 値の意味 → 0: 空きマス / 1: 黒石 / -1: 白石
  // 黒と白を 1 と -1 にすることで、「-player」と書くだけで相手の石を表せる。
  const board = Array(8).fill(null).map(() => Array(8).fill(0)); // 0: empty, 1: black, -1: white

  // 現在の手番。1 = 黒、-1 = 白。オセロは黒から始まるので初期値は 1。
  let currentPlayer = 1; // 1 for black, -1 for white

  // 周囲8方向へ進むための「移動量」の組。
  // dr[i] が行方向の増減、dc[i] が列方向の増減を表し、
  // i を 0〜7 まで回すと 左上・上・右上・左・右・左下・下・右下 の8方向を調べられる。
  // Directions for checking neighboring cells (8 directions)
  const dr = [-1, -1, -1, 0, 0, 1, 1, 1];
  const dc = [-1, 0, 1, -1, 1, -1, 0, 1];


  /* ============================================================
     2. 盤面の初期化（画面生成 ＋ 初期配置）
     ============================================================ */
  function initBoard() {
    boardElement.innerHTML = ''; // 既存の盤面をいったん消す（作り直し用）

    // 8行 × 8列 ＝ 64個のマス(div.cell)を作って盤面に追加していく
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const cell = document.createElement('div');
        cell.classList.add('cell');

        // data属性に座標を埋め込んでおく。クリック時にここから行・列を読み取る。
        cell.dataset.row = r;
        cell.dataset.col = c;

        // 各マスにクリックイベントを登録（＝ここがプレイヤー操作の入口）
        cell.addEventListener('click', handleCellClick);

        boardElement.appendChild(cell);
      }
    }

    // オセロの初期配置:中央4マスに白黒を斜めに置く
    // Initial setup
    placePiece(3, 3, -1); // 白 / White
    placePiece(3, 4, 1);  // 黒 / Black
    placePiece(4, 3, 1);  // 黒 / Black
    placePiece(4, 4, -1); // 白 / White

    // 手番表示を更新
    updateStatus();
  }


  /* ============================================================
     3. 指定マスに石を置く（見た目と内部データの両方を更新）
     ============================================================ */
  function placePiece(row, col, player) {
    // 二次元の座標(row, col)を、一次元に並んだ子要素の番号へ変換する
    const cellIndex = row * 8 + col;
    const cellElement = boardElement.children[cellIndex];

    if (cellElement) {
      // 見た目の更新:マスの中身を、黒または白の丸い石に差し替える
      cellElement.innerHTML = `<div class="piece ${player === 1 ? 'black' : 'white'}"></div>`;

      // 内部データの更新:配列にも同じ状態を記録する
      // （※この関数は「新規配置」と「ひっくり返し」の両方で使い回されている）
      board[row][col] = player;
    }
  }


  /* ============================================================
     4. その手が合法手かどうかの判定
        条件:空きマスであり、かつ「相手の石が1つ以上続いた先に自分の石がある」方向が
              少なくとも1方向存在すること。
     ============================================================ */
  // Checks if a move is valid for the current player at (row, col)
  function isValidMove(row, col, player) {
    if (board[row][col] !== 0) return false; // すでに石があるマスには置けない

    let canFlip = false;

    // 8方向をそれぞれ調べる
    for (let i = 0; i < 8; i++) {
      let r = row + dr[i];   // 1マス進んだ位置から探索開始
      let c = col + dc[i];
      let hasOpponentPiece = false;

      // その方向に「相手の石」が続く限り進み続ける
      // Check if there's an opponent's piece in this direction
      while (r >= 0 && r < 8 && c >= 0 && c < 8 && board[r][c] === -player) {
        hasOpponentPiece = true;
        r += dr[i];
        c += dc[i];
      }

      // 相手の石が1つ以上あり、その先（盤内）に自分の石があれば挟める＝合法手
      // If an opponent's piece was found, check if it's followed by player's piece
      if (hasOpponentPiece && r >= 0 && r < 8 && c >= 0 && c < 8 && board[r][c] === player) {
        canFlip = true;
        break; // 1方向でも見つかれば十分なので、そこで判定を打ち切る
      }
    }
    return canFlip;
  }


  /* ============================================================
     5. 実際にひっくり返る石の一覧を集める
        isValidMove とほぼ同じ探索をするが、こちらは「どの石が裏返るか」を
        座標のリストとして返す点が違う。
     ============================================================ */
  // Gets all pieces that would be flipped by placing a piece at (row, col)
  function getFlippedPieces(row, col, player) {
    const toFlip = []; // 最終的に裏返す石の座標をためる配列

    for (let i = 0; i < 8; i++) {
      let r = row + dr[i];
      let c = col + dc[i];
      const currentDirFlipped = []; // この方向で挟めそうな相手の石を一時的にためる

      // 相手の石が続く間、候補として記録しながら進む
      while (r >= 0 && r < 8 && c >= 0 && c < 8 && board[r][c] === -player) {
        currentDirFlipped.push({ row: r, col: c });
        r += dr[i];
        c += dc[i];
      }

      // その先に自分の石があれば「挟めた」ので、候補を確定リストに移す。
      // 逆に、盤外に出た場合や空きマスで止まった場合は候補ごと破棄される。
      if (currentDirFlipped.length > 0 && r >= 0 && r < 8 && c >= 0 && c < 8 && board[r][c] === player) {
        toFlip.push(...currentDirFlipped);
      }
    }
    return toFlip;
  }


  /* ============================================================
     6. マスがクリックされたときの処理（ゲーム進行の中心）
     ============================================================ */
  function handleCellClick(event) {
    // クリックされたのがマスの中の「石」だった場合に備え、
    // closest('.cell') で親のマス要素までさかのぼる。
    // Ensure the click was on a cell, not a piece inside it
    let targetCell = event.target;
    if (!targetCell.classList.contains('cell')) {
        targetCell = targetCell.closest('.cell');
    }
    if (!targetCell) return; // マス以外がクリックされた場合は何もしない

    // data属性から座標を取り出す（文字列なので数値へ変換）
    const row = parseInt(targetCell.dataset.row);
    const col = parseInt(targetCell.dataset.col);

    if (isValidMove(row, col, currentPlayer)) {
      // ★注意:裏返る石の一覧は「自分の石を置く前」に求める必要がある。
      //        先に置いてしまうと盤面が変わり、探索結果がずれてしまうため。
      const flipped = getFlippedPieces(row, col, currentPlayer);

      // ① クリックしたマスに自分の石を置く
      // Place the current player's piece
      placePiece(row, col, currentPlayer);

      // ② 挟んだ相手の石を、自分の色で上書きしてひっくり返す
      // Flip the captured pieces
      flipped.forEach(p => {
        placePiece(p.row, p.col, currentPlayer);
      });

      // ③ 手番を交代する（1 ↔ -1 の符号反転で切り替え）
      currentPlayer = -currentPlayer; // Switch player

      // ④ 画面の手番表示を更新
      updateStatus();
    } else {
      // 合法手でなければ警告を出し、手番は交代しない
      alert('そこには置けません。有効な手ではありません。');
    }
  }


  /* ============================================================
     7. 手番表示の更新
     ============================================================ */
  function updateStatus() {
    statusElement.textContent = `現在のターン: ${currentPlayer === 1 ? '黒' : '白'}`;
  }


  /* ============================================================
     8. 起動処理:スクリプト読み込み時に盤面を初期化してゲーム開始
     ============================================================ */
  initBoard(); // Initialize the board when the script loads
</script>
'''

# ============================================================
# 上で組み立てた HTML 文字列を HTML オブジェクトに包み、
# ノートブックの出力領域に描画する（＝ここで実際にゲームが表示される）
# ============================================================
display(HTML(html_code))
