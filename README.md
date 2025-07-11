# Wikipedia Race 日本語版

このリポジトリは、Wikipedia の記事間を最少クリックで辿るゲーム「Wikipedia Race」の簡易実装です。

## メモ: 生SQLからORMへの切り替えを検討

## 構成

- `frontend/` : GitHub Pages などの静的ホスティングで公開する HTML/JavaScript
- `backend/`  : Flask による API サーバ
  - `routes/`   : ルーティング定義
  - `services/` : Wikipedia 連携や DB 操作を担当
- `static_pages/` : バックエンドを使用しない GitHub Pages 向けの純粋な HTML/CSS/JavaScript

## セットアップ

1. Python 3.x を用意し、依存パッケージをインストールします。

```bash
pip install -r backend/requirements.txt
```

2. API サーバを起動します。

```bash
python backend/app.py
```

3. `frontend/index.html` をブラウザで開くとゲームを試すことができます。

## テスト

開発時には `pytest` を用いてテストを実行できます。依存関係をインストール後、
次のコマンドを実行してください。

```bash
pytest
```

## 仕組み

- `/api/puzzles` でスタート記事とゴール記事のペアを取得します。
- `/api/validate` にユーザーが入力した経路を送信すると、各ステップでリンクが存在するか MediaWiki API を通じて確認します。
- 正当であればステップ数を返し、そうでなければ失敗したステップ番号を返します。

## GitHub Pages 静的版

`static_pages/` ディレクトリには、バックエンドを使用せず Wikipedia API だけで動作
する簡易版を用意しています。GitHub Pages へそのまま配置することで動作確認できます。
`puzzles.json` にスタートとゴールの記事を定義しており、ブラウザのみで検証を行いま
す。

## 免責

本アプリケーションは学習目的のサンプルであり、Wikipedia の利用規約を遵守して利用してください。
