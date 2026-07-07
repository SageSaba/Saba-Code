#!/bin/bash

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install it to run this script."
    exit 1
fi

# Check if both arguments are provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <text_prompt> <audio_file_path>"
    exit 1
fi

TEXT_PROMPT="$1"
AUDIO_FILE="$2"

# Check if the audio file exists
if [ ! -f "$AUDIO_FILE" ]; then
    echo "Error: Audio file does not exist: $AUDIO_FILE"
    exit 1
fi

# Determine the audio format from the file extension (wav or mp3)
EXTENSION=$(echo "${AUDIO_FILE##*.}" | tr '[:upper:]' '[:lower:]')
case "$EXTENSION" in
    wav|mp3)
        AUDIO_FORMAT="$EXTENSION"
        ;;
    *)
        echo "Error: Unsupported audio format: .$EXTENSION (supported: .wav, .mp3)"
        exit 1
        ;;
esac

# Base64 encode the audio file to a temp file (too large to pass as an argument)
TMPDIR_WORK=$(mktemp -d)
trap 'rm -rf "$TMPDIR_WORK"' EXIT
base64 < "$AUDIO_FILE" | tr -d '\n' > "$TMPDIR_WORK/audio.b64"

# Construct the JSON payload
# Model can be overridden, e.g.: OPENAI_AUDIO_MODEL=gpt-audio-1.5 ./audio-prompt.sh ...
MODEL="${OPENAI_AUDIO_MODEL:-gpt-audio-mini}"

jq -n \
    --arg model "$MODEL" \
    --arg text "$TEXT_PROMPT" \
    --rawfile audio "$TMPDIR_WORK/audio.b64" \
    --arg format "$AUDIO_FORMAT" \
    '{
        model: $model,
        modalities: ["text"],
        messages: [
            {
                role: "user",
                content: [
                    {type: "text", text: $text},
                    {
                        type: "input_audio",
                        input_audio: {
                            data: $audio,
                            format: $format
                        }
                    }
                ]
            }
        ]
    }' > "$TMPDIR_WORK/payload.json"

# Make the API call
curl -s "https://api.openai.com/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d @"$TMPDIR_WORK/payload.json" | jq .
