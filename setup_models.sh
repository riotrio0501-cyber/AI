#!/bin/bash
# 声のモデルを models/ にダウンロードする（済みならスキップ）
set -e
cd "$(dirname "$0")"
HF=https://huggingface.co
get() { [ -s "$2" ] || { mkdir -p "$(dirname "$2")"; curl -fsSL -o "$2" "$HF/$1"; }; }
B=models/sbv2/bert/deberta-v2-large-japanese-char-wwm
for f in config.json pytorch_model.bin special_tokens_map.json tokenizer_config.json vocab.txt; do
  get ku-nlp/deberta-v2-large-japanese-char-wwm/resolve/main/$f $B/$f
done
for f in config.json koharune-ami.safetensors style_vectors.npy; do
  get litagin/sbv2_koharune_ami/resolve/main/koharune-ami/$f models/sbv2/models/koharune-ami/$f
done
echo "models ready"
