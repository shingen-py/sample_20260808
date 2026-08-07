# CLAUDE.md — Claude Code向けの入口

@AGENTS.md

このファイルはClaude Codeがプロジェクト開始時に読む指示ファイルです。共通の作業ルールは上の`@AGENTS.md`から読み込みます。ルールを変更するときは、原則として`AGENTS.md`を更新し、このファイルへ同じ内容を複製しないでください。

## このテンプレートで最初に行うこと

1. プロジェクトのルートフォルダで作業する
2. `AGENTS.md`、`PROJECT.md`、`DATA.md`、`TASKS.md`の順に読む
3. `PROJECT.md`または`DATA.md`に「未決定」が残っている場合は、実装を始めない
4. `PROMPTS.md`の「0. MVPを一緒に決める」から、参加者へ一度に1問ずつ質問する
5. 付属サンプルを、参加者が作りたいMVPだと解釈しない

## Claude Codeでの確認

- `/memory`で、この`CLAUDE.md`が読み込まれていることを確認できる
- `PROJECT.md`、`DATA.md`、`TASKS.md`の反映前には、人間へ変更案を示して確認を待つ
- 実装後は`AGENTS.md`に記載されたテストを実行し、画面で確認する操作も伝える
- `CLAUDE.local.md`は個人用の設定に使えるが、共有ルールは書かない

