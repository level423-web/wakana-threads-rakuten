# wakana-threads-rakuten

Threads×楽天アフィリエイトの投稿ネタを半自動化するプロジェクト。
詳しい役割分担・ワークフローは `CLAUDE.md` を参照。

## セットアップ

## 使い方
結果は `output/rakuten_candidates_日付.json` に保存されます。

## 次にやること
1. `config/product_keywords.yaml` を自分の投稿ジャンルに合わせて編集
2. Threadsでバズっている投稿を見つけたら `config/buzz_patterns.md` に記録
3. 商品候補とバズパターンが揃ったら、Claude Codeに「この商品でThreads投稿文を3パターン作って」と依頼
