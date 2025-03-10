import os
import json
import random
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip


def create_green_background(image):
    #画像にグリーンバックを合成して返す
    image = image.convert("RGBA")
    background = Image.new("RGBA", image.size, (0, 255, 0, 255))
    combined = Image.alpha_composite(background, image)
    return combined.convert("RGB")

def should_close_eyes():
    # 20%の確率で目を閉じる
    return random.random() < 0.2

# グローバル定義
VOWEL_MAPPING = {
    "あ": "a",
    "い": "i",
    "う": "u",
    "え": "e",
    "お": "o",
    "ん": "nn"
}
MOKA_EMOTIONS = ['bosoboso', 'doyaru', 'honwaka', 'angry', 'teary']

# .lab ファイルからの母音抽出（口パク用）
def classify_vowel_from_phoneme(phoneme):
    vowel_map = {
        'a': 'あ',
        'i': 'い',
        'u': 'う',
        'e': 'え',
        'o': 'お',
        'n': 'ん'
    }
    return vowel_map.get(phoneme.lower(), None)

def parse_lab_file(lab_file_path, time_conversion_factor=10000000.0):
    # .lab ファイルを解析して、母音と開始時刻（秒単位）のリストを返す
    vowels = []
    times = []
    with open(lab_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                try:
                    start_time = float(parts[0]) / time_conversion_factor
                    phoneme = parts[2]
                    vowel = classify_vowel_from_phoneme(phoneme)
                    if vowel:
                        vowels.append(vowel)
                        times.append(start_time)
                except ValueError:
                    print(f"無効な行をスキップ: {line.strip()}")
                    continue
    return vowels, times

def merge_consecutive_vowels(vowels, times):
    # 隣接する同一母音をマージする
    if not vowels:
        return [], []
    
    merged_vowels = [vowels[0]]
    merged_times = [times[0]]
    previous_vowel = vowels[0]
    
    for vowel, t in zip(vowels[1:], times[1:]):
        if vowel != previous_vowel:
            merged_vowels.append(vowel)
            merged_times.append(t)
            previous_vowel = vowel
    return merged_vowels, merged_times

def extract_phoneme_timing_lab(lab_file):
    #.lab ファイルから母音とタイミングを取得し、連続同一母音をマージする
    vowels, times = parse_lab_file(lab_file)
    merged_vowels, merged_times = merge_consecutive_vowels(vowels, times)
    return merged_times, merged_vowels

# 動画生成
def generate_video(block_index, max_emotion, onset_times, vowels, audio_path, output_path):
    # 各フレームに対応する画像（感情・口パク）を組み合わせ、動画を生成する
    frames = []
    durations = []
    base_path = "Moca_illust_divide"
    emotion_folder = f"{base_path}/{max_emotion}"
    closed_eye_folder = f"{base_path}/{max_emotion}_close_eyes"

    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    buffer = 0.02  # 20ミリ秒のバッファ

    for i, start_time in enumerate(onset_times):
        romaji_vowel = VOWEL_MAPPING.get(vowels[i], "a")
        folder = closed_eye_folder if should_close_eyes() else emotion_folder
        image_path = f"{folder}/{romaji_vowel}.png"

        if os.path.exists(image_path):
            original_image = Image.open(image_path)
            green_image = create_green_background(original_image)
            frames.append(green_image)
        else:
            print(f"画像が見つかりません: {image_path}")

        if i < len(onset_times) - 1:
            duration = max(0.1, onset_times[i + 1] - start_time - buffer)
        else:
            duration = max(0.1, audio_duration - start_time - buffer)
        durations.append(duration)

    if sum(durations) < audio_duration:
        durations[-1] += audio_duration - sum(durations)

    frame_paths = [f"./temp_frame_{i}.png" for i in range(len(frames))]
    for frame, path in zip(frames, frame_paths):
        frame.save(path)

    clip = ImageSequenceClip(frame_paths, durations=durations)
    video = clip.set_audio(audio_clip)

    video.write_videofile(
        output_path,
        fps=60,
        codec="libx264",
        audio_codec="aac",
        bitrate="10M",
        audio_bitrate="320k",
        logger=None
    )

    for path in frame_paths:
        if os.path.exists(path):
            os.remove(path)


def main():
    project_name = input("プロジェクトフォルダ名を入力してください: ").strip()
    project_folder = os.path.join(os.getcwd(), project_name)
    vpp_file = os.path.join(project_folder, f"{project_name}.vpp")

    if not os.path.exists(vpp_file):
        print(f"JSONファイルが見つかりません: {vpp_file}")
        return

    with open(vpp_file, "r", encoding="utf-8") as f:
        content = f.read()
    cleaned_content = content.rstrip("\x00").strip()
    data = json.loads(cleaned_content)
    print("JSONデータの読み込みに成功しました")

    for i, block in enumerate(data["project"]["blocks"]):
        emotions = block.get("emotions", {})
        moka_emotions = {k: v for k, v in emotions.items() if k in MOKA_EMOTIONS}
        max_emotion = max(moka_emotions, key=moka_emotions.get, default="normal")
        print(f"Block {i} の感情: {max_emotion}")

        sentences = " ".join([s["text"] for s in block["sentence-list"]])
        wav_file = os.path.join(project_folder, f"{i}-宮舞モカ-{project_name}.wav")
        if not os.path.exists(wav_file):
            print(f"音声ファイルが見つかりません: {wav_file}")
            continue

        lab_file = os.path.join(project_folder, f"{i}-宮舞モカ-{project_name}.lab")
        if not os.path.exists(lab_file):
            print(f"Block {i}: .lab ファイルが見つかりません。動画生成をスキップします")
            continue

        print(f"Block {i}: .lab ファイルから口パク情報を取得します")
        onset_times, vowels = extract_phoneme_timing_lab(lab_file)
        
        # 出力先フォルダ (Lip_Sync_Movie/{project_name}) を作成
        output_folder = os.path.join(os.getcwd(), "Lip_Sync_Movie", project_name)
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(os.getcwd(), f"Lip_Sync_Movie/{project_name}/block_{i}.mp4")
        generate_video(i, max_emotion, onset_times, vowels, wav_file, output_path)
        print(f"Block {i} の動画を生成しました: {output_path}")

if __name__ == "__main__":
    main()