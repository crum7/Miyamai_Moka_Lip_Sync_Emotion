#!/bin/bash

# 画像のダウンロードと解凍
ZIP_FILE="moca_illust.zip"
SORTED_DIR="Moca_illust_divide"
HASH_LIST="hash_list.txt"

pip install -r requirements.txt

# ZIP のダウンロードと解凍
if [ ! -d "moca_illust" ]; then
    echo "📥 画像をダウンロード中..."

    if command -v wget > /dev/null; then
        wget --show-progress -q https://www.ah-soft.com/moca/moca_illust.zip -O "$ZIP_FILE"
    elif command -v curl > /dev/null; then
        curl -# -o "$ZIP_FILE" https://www.ah-soft.com/moca/moca_illust.zip
    else
        echo "❌ wget も curl も見つかりません！手動でダウンロードしてください。"
        exit 1
    fi

    if [ -f "$ZIP_FILE" ]; then
        echo "📂 画像を解凍中..."
        unzip -q "$ZIP_FILE"
        rm "$ZIP_FILE"
    else
        echo "❌ ダウンロードに失敗しました！"
        exit 1
    fi
else
    echo "✅ 画像フォルダが既に存在します。ダウンロードをスキップします。"
fi

# ハッシュを計算する関数
calculate_hash() {
    sha256sum "$1" | awk '{print $1}'
}

# 分類先ディレクトリを作成
mkdir -p "$SORTED_DIR"

# 画像ファイルの総数を取得
total_files=$(find "moca_illust" -type f -name "*.png" | wc -l)
count=0

# プログレスバー関数
progress_bar() {
    local progress=$((count * 40 / total_files))
    local bar=$(printf "%-${progress}s" "=")
    printf "\r📊 進行中: [%-40s] %d%% (%d/%d)" "$bar" $((count * 100 / total_files)) "$count" "$total_files"
}

# 画像をスキャンして分類
echo "🔍 画像の分類を開始します..."

find "moca_illust" -type f -name "*.png" | while read -r file; do
    ((count++))
    file_hash=$(calculate_hash "$file")

    # ハッシュリストと照合
    match=$(grep "$file_hash" "$HASH_LIST")

    if [ -n "$match" ]; then
        category=$(echo "$match" | awk '{print $1}' | cut -d'/' -f1)
        filename=$(echo "$match" | awk '{print $1}' | cut -d'/' -f2)

        mkdir -p "$SORTED_DIR/$category"
        mv "$file" "$SORTED_DIR/$category/$filename"
    fi

    progress_bar
done

# 画像フォルダを削除
echo -e "\n🗑️  分類後に moca_illust フォルダを削除します..."
rm -rf "moca_illust"

# Lip_Sync_Movieフォルダを作成
echo "📁 Lip_Sync_Movie フォルダを作成します..."
mkdir -p "Lip_Sync_Movie"
echo "✅ Lip_Sync_Movie フォルダを作成しました！"

echo "🎉 画像の分類が完了しました！ ($count ファイルを処理しました)"